# Installation on Windows
### Requirements:
+ Git from https://git-scm.com/downloads
+ Python (version 3.10 minimum) from https://www.python.org/downloads/

### Intents
[Visit this page](https://discord.com/developers/applications/), locate your bot and enable 
- SERVER MEMBERS INTENT
- MESSAGE CONTENT INTENT

### Where is the bot's data folder
`C:\Users\username\AppData\Local\Kyuunex\Seija`  
If you are restoring a database backup, it goes into this folder.

### API keys and tokens
You need to either put them in the respective text files in the bot's data folder or 
supply them via environment variables. if you do both, env vars will be used  

| text file         | environment variables | where to get                                                                         |
|-------------------|-----------------------|--------------------------------------------------------------------------------------|
| token.txt         | SEIJA_TOKEN           | [create a new app, make a bot acc](https://discord.com/developers/applications/)     |
| osu_api_key.txt   | SEIJA_OSU_API_KEY     | [create a new legacy app here](https://osu.ppy.sh/home/account/edit)                 |
| client_id.txt     | SEIJA_CLIENT_ID       | [register a new app on your account edit page](https://osu.ppy.sh/home/account/edit) |
| client_secret.txt | SEIJA_CLIENT_SECRET   | [register a new app on your account edit page](https://osu.ppy.sh/home/account/edit) |

## Installation for production use
Head over to the Releases section, pick the latest release, 
and in its description you will see an installation command. 
Open the Terminal (PowerShell or CMD), paste that in and press enter.

To install the latest unstable version, type the following in the Terminal instead 
```bash
python3 -m pip install git+https://github.com/Kyuunex/Seija.git@master --upgrade
```

To run the bot, type `python3 -m seija` in the Terminal

#### Startup with automatic restart
The purpose of this is to make the bot start automatically on boot, useful for example after a power outage.  
Make a `.bat` file with the following contents and put it into your startup folder.
```bat
@echo off
title Seija
:loop
python3 -m seija
goto loop
pause
```

## Installation for debugging and development
```bash
git clone https://github.com/Kyuunex/Seija.git -b master
cd Seija
```
To run for debugging purposes, type `run_seija.py`  
To install a modified version of the bot for production use, type `pip3 install . --upgrade`
