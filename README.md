# mjs-lobby-bot

A fully featured Discord bot which supports managing games in a [Mahjong Soul] paid tournament lobby.

[Mahjong Soul]: https://mahjongsoul.yo-star.com

## Features

* See who is waiting in the lobby
* Shuffle people into tables randomly and start games
* Show the status of a fixed table layout and start the game with that layout once everyone is ready
* Display all tournament rule settings, ability to update select setting
* Track tournament scores using custom options

All without leaving the friendly confines of Discord!

## Prerequisites

* A tournament lobby.
* A Mahjong Soul account dedicated to the bot, which uses Twitter authentication.
* A Discord application and associated bot token.
* Bot is invited to a server of your choice.
* Python 3.8 with `pipenv`

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
1. Look for websocket payloads that are about 150-200 bytes.
1. In the pipenv shell, use `scripts/mjs_decode 'PASTE PAYLOAD HERE'` until you find the message with `oauth2Login`. The UUID-looking field will then be your access token.

[Websocket Frame Inspector]: https://chrome.google.com/webstore/detail/websocket-frame-inspector/nlajeopfbepekemjhkjcbbnencojpaae?hl=en
[Mahjong Soul Tournament Management]: https://mahjongsoul.tournament.yo-star.com/dhs/index.html
