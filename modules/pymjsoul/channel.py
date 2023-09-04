import asyncio

import websockets

import google.protobuf as pb
from .errors import ERRORS

MSG_TYPE_NOTIFY = 1
MSG_TYPE_REQUEST = 2
MSG_TYPE_RESPONSE = 3

MAX_MSG_INDEX = 2**16

class MethodNotFoundError(Exception):
    def __init__(self, methodName, moduleName):
        self.message = f"No method named '{methodName}' in module '{moduleName}'"
        super().__init__(self.message)

class ResponseTimeoutError(Exception):
    def __init__(self, timeoutDuration):
        self.message = f"Response not received within specified timeout duration ({timeoutDuration}s)"
        super().__init__(self.message)

class GeneralMajsoulError(Exception):
    def __init__(self, errorCode, message):
        self.message = f"ERROR CODE {errorCode}: {message}"
        super().__init__(self.message)

class MajsoulChannel():
    _RESPONSE_TIMEOUT_DURATION = 10

    def __init__(self, proto, log_messages=True):
        self.websocket = None
        self.websocket_lock = asyncio.Lock()

        self.uri = None

        self.proto = proto

        self.index = 0
        self.requests = {}
        self.responses = {}

        self._subscriptions = {}
        self._subscriptions_lock = asyncio.Lock()

        self.MostRecentNotify = None
        self.Notifications = asyncio.Queue()
        self.log_messages = log_messages

    async def connect(self, uri):
        self.uri = uri

        self.websocket = await websockets.connect(self.uri)

        print(f'Connected to {self.uri}')

        asyncio.create_task(self.sustain())
        asyncio.create_task(self.listen())
        asyncio.create_task(self.eventloop())

    async def sustain(self, ping_interval=3):
        '''
        Looping coroutine that keeps the connection to the server alive.
        '''
        while self.websocket.open:
            await self.websocket.ping()
            await asyncio.sleep(ping_interval)

    async def subscribe(self, name, cb):
        async with self._subscriptions_lock:
            if name in self._subscriptions:
                self._subscriptions[name].append(cb)
            else:
                self._subscriptions[name] = [cb]

    async def eventloop(self):
        ''' Event loop running as a separate coroutine to listen(), otherwise we can run into deadlock. '''
        while True:
            name, msg = await self.Notifications.get()
            if name in self._subscriptions:
                for sub_callback in self._subscriptions[name]:
                    await sub_callback(name, msg)
            else:
                print(f"Notification for {name} had no subscribers.")

    async def listen(self):
        '''
        Looping coroutine that receives messages from the server.
        '''
        async for message in self.websocket:
            msgType = int.from_bytes(message[0:1], 'little')

            if msgType == MSG_TYPE_NOTIFY:
                msgPayload = message[1:]
                name, data = self.unwrap(msgPayload)

                name = name.strip(f'.{self.proto.DESCRIPTOR.package}')

                try:
                    msgDescriptor = self.message_lookup(name)
                except KeyError as e:
                    print(e)
                    continue

                msgClass = pb.reflection.MakeClass(msgDescriptor)

                msg = msgClass()
                msg.ParseFromString(data)

                # Duplicate notifications can be received next to each other.
                # Never process the same message twice.
                if (name, msg) != self.MostRecentNotify:
                    print("Notification received.")
                    print(name)
                    print(msg)
                    self.MostRecentNotify = (name, msg)

                    await self.Notifications.put((name, msg))
            elif msgType == MSG_TYPE_RESPONSE:
                print("Response received.")
                msgIndex = int.from_bytes(message[1:3], 'little')
                msgPayload = message[3:]

                if msgIndex in self.requests:
                    name, data = self.unwrap(msgPayload)
                    self.responses[msgIndex] = data

                    resEvent = self.requests[msgIndex]
                    resEvent.set()

    async def close(self):
        await self.websocket.close()

    async def send(self, name:str, data:bytes):
        '''
        Sends a message/request to the server.

        Param:
            name : str
                Full name of the protobuf message to be sent. Example: ".lq.Lobby.oauth2Login:"

            data : bytes
                Message payload to be sent. This needs to be a byte string. After creating a protobuf message 'msg'
                you can call msg.SerializeToString() and pass it in as this parameter.

        Info:
            The messages that are sent/received are formatted differently depending on the type of message (notify/request/response).

            REQUEST/RESPONSE

            Byte #:     0       1       2       3       4       5     .... and so on
                     ___|___ ___|___ ___|___ ___|___ ___|___ ___|___
                    |       |               |
                    | MSG   |    MESSAGE    |      MESSAGE            ....
                    | TYPE  |     INDEX     |      PAYLOAD            .... rest of the message
                    |_______|_______ _______|_______ _______ _______

            NOTIFY:

            Byte #:     0       1       2    .... and so on
                     ___|___ ___|___ ___|___
                    |       |
                    | MSG   |    MESSAGE     ....
                    | TYPE  |    PAYLOAD     .... rest of the message
                    |_______|_______ _______
        '''

        msgIndex = self.index
        self.index = (self.index + 1) % MAX_MSG_INDEX

        wrapped = self.wrap(name, data)
        message = MSG_TYPE_REQUEST.to_bytes(1, 'little') + msgIndex.to_bytes(2, 'little') + wrapped

        resEvent = asyncio.Event()
        self.requests[msgIndex] = resEvent

        async with self.websocket_lock:
            await self.websocket.send(message)

            try:
                await asyncio.wait_for(resEvent.wait(), timeout=self._RESPONSE_TIMEOUT_DURATION)
            except asyncio.TimeoutError:
                del self.requests[msgIndex]
                raise ResponseTimeoutError(self._RESPONSE_TIMEOUT_DURATION)

            res = self.responses[msgIndex]

            del self.responses[msgIndex]
            del self.requests[msgIndex]

            return res

    async def call(self, methodName, **msgFields):
        '''
        Simpler method for sending requests. Looks up the request and processes the fields for you.
        Use this instead of MajsoulChannel.send

        Param:
            methodName : str
                Name of the method to be called (without package name). Example: 'oauth2Login'

            **msgFields : dict
                Fields to be entered into the protobuf message.

        Example Usage:
            res = await self.call(
                methodName = 'oauth2LoginContestManager',
                type = 10,
                access_token = 'YOUR_TOKEN_HERE',
                reconnect = True
            )
        '''

        # Optional method hack
        serviceName = None
        if 'serviceName' in msgFields:
            serviceName = msgFields['serviceName']
            del msgFields['serviceName']

        methodDescriptor = self.method_lookup(methodName, serviceName)

        msgName = f'.{methodDescriptor.full_name}'

        reqMessageClass = pb.reflection.MakeClass(methodDescriptor.input_type)
        reqMessage = reqMessageClass(**msgFields)

        resData = await self.send(msgName, reqMessage.SerializeToString())

        resMessageClass = pb.reflection.MakeClass(methodDescriptor.output_type)
        resMessage = resMessageClass()
        resMessage.ParseFromString(resData)

        if resMessage.error.code:
            print(resMessage)
            raise GeneralMajsoulError(resMessage.error.code, ERRORS.get(resMessage.error.code, 'Unknown error'))

        if self.log_messages:
            print(resMessage)

        return resMessage

    def method_lookup(self, methodName, serviceName):
        methodDescriptor = None

        if serviceName:
            serviceDescriptor = self.proto.DESCRIPTOR.services_by_name[serviceName]
            methodDescriptor = serviceDescriptor.FindMethodByName(methodName)
        else:
            for serviceDescriptor in self.proto.DESCRIPTOR.services_by_name.values():
                try:
                    methodDescriptor = serviceDescriptor.FindMethodByName(methodName)
                    # if not found then continue to the next serviceDescriptor
                    if methodDescriptor == None:
                        continue
                    break
                # legacy, keeping this for now
                except KeyError:
                    continue

        if methodDescriptor == None:
            raise MethodNotFoundError(methodName, self.proto.__name__)

        return methodDescriptor

    def message_lookup(self, messageName):
        return self.proto.DESCRIPTOR.message_types_by_name[messageName]

    def wrap(self, name, data):
        msg = self.proto.Wrapper(name=name, data=data)

        return msg.SerializeToString()

    def unwrap(self, wrapped):
        msg = self.proto.Wrapper()
        msg.ParseFromString(wrapped)

        return msg.name, msg.data

async def main():
    import proto.lq.liqi_pb2 as lq
    import mjsoul
    import uuid

    channel = MajsoulChannel(lq, log_messages=False)

    servers = await mjsoul.get_recommended_servers()

    await channel.connect(servers[0])

    res = await channel.call(
        methodName='oauth2Login',
        type=10,
        access_token='YOUR_TOKEN_HERE',
    )

    res = await channel.call(
        methodName='fetchGameRecord',
        game_uuid='200924-3e856303-84e7-411e-8666-ac2859d895cc',
    )

    print(res.head.result)

if __name__ == "__main__":
    asyncio.run(main())
