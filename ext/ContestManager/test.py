from pymjsoul.client import ContestManager
import asyncio

async def main():
    import pymjsoul.proto.dhs.dhs_pb2 as dhs
    client = ContestManager(dhs)
    await client.login('e0719795-a8d8-4f91-91c6-c152126a7bb2')
    print(client.contest_list)

if __name__ == "__main__":
    asyncio.run(main())