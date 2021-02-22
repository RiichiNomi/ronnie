# mjs-lobby-bot

A fully featured Discord bot which supports managing games in a [Mahjong Soul] paid tournament lobby.

[Mahjong Soul]: https://mahjongsoul.yo-star.com

## Features

* See who is waiting in the lobby (`ms/list`)
* Shuffle people into tables randomly and start games (`ms/shuffle` or clicking emojis)
* Show the status of a fixed table layout and start the game with that layout once everyone is ready (`ms/tournament`), switch back to casual mode (`ms/casual`)
* Pause and unpause games in progress (`ms/pause`, `ms/unpause`) and end them (`ms/terminate`)
* Display all tournament rule settings (`ms/rules`), ability to update select settings (`ms/setrule`)
* Track tournament scores using custom options (`ms/score`)

All without leaving the friendly confines of Discord!

## Prerequisites

* A tournament lobby. Check out the [guide] for how to purchase one.
* A Mahjong Soul account dedicated to the bot, which uses Twitter authentication.
* A Discord application and associated bot token.
* Bot is invited to a server of your choice.
* Python 3.8 with `pipenv`

[guide]: https://docs.google.com/document/d/15MW4yLDGqpc8FjySEqYmHFyUAq5mJWW8PtQwG-Hdw3s/edit

## Installation

1. `pipenv install`
1. `pipenv shell`
1. `cp config.env.example config.env`. Fill in all the fields that you can (see below for obtaining the `mahjong_soul_access_token`)
1. `./start.sh`

It's recommended to run the actual bot in a screen.

## Obtaining the OAuth token for Mahjong Soul

1. Install [Websocket Frame Inspector].
1. Load the [Mahjong Soul Tournament Management] page. (This is a nice one because it won't establish the websocket connection right away)
1. Enable the Frame Inspector and put the window aside.
1. Complete the Twitter authentication process.
1. Back in the Frame Inspector, look for websocket payloads that are about 150-200 bytes.
1. In the pipenv shell, use `scripts/mjs_decode 'PASTE PAYLOAD HERE'` against those payloads until you find the message that looks like this:

```
root:
    1 <chunk> = ".lq.CustomizedContestManagerApi.oauth2LoginContestManager"
    2 <chunk> = message:
        1 <varint> = 10
        2 <chunk> = "xxxxxxxx-yyyy-zzzz-aaaa-bbbbbbbbbbbb"
```

The last line will contain your access token, paste the value between the quotes as your access token in `config.env`

[Websocket Frame Inspector]: https://chrome.google.com/webstore/detail/websocket-frame-inspector/nlajeopfbepekemjhkjcbbnencojpaae?hl=en
[Mahjong Soul Tournament Management]: https://mahjongsoul.tournament.yo-star.com/dhs/index.html
