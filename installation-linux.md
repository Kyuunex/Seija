# Installation on Linux (Non-docker)

### Requirements:
+ `git`
+ `python3` (version 3.10 minimum)
+ `python3-venv`

### Intents
[Visit this page](https://discord.com/developers/applications/), locate your bot and enable 
- SERVER MEMBERS INTENT
- MESSAGE CONTENT INTENT

### Where is the bot's data folder
`/home/user/.local/share/Seija`  
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

### Installation for production use
```sh
mkdir -p $HOME/.local/share/Seija
python3 -m venv $HOME/.local/share/Seija/.venv
source $HOME/.local/share/Seija/.venv/bin/activate
python3 -m pip install git+https://github.com/Kyuunex/Seija.git@master --upgrade  # You can replace this with a release if you want
```
Repeat the commands 3 and 4 for upgrading.

### Bot Configuration
```sh
# wget -O $HOME/.local/share/Seija/maindb.sqlite3 REPLACE_THIS_WITH_DIRECT_FILE_LINK  # optional database backup restore
echo "REPLACE_THIS_WITH_BOT_TOKEN" | tee $HOME/.local/share/Seija/token.txt
echo "REPLACE_THIS_WITH_OSU_API_KEY" | tee $HOME/.local/share/Seija/osu_api_key.txt
echo "REPLACE_THIS_WITH_CLIENT_ID" | tee $HOME/.local/share/Seija/client_id.txt
echo "REPLACE_THIS_WITH_CLIENT_SECRET" | tee $HOME/.local/share/Seija/client_secret.txt
```

### Configuring the bot as a systemd service
The purpose of this is to make the bot start automatically on boot, useful for example after a power outage.  

Create the following file: `/etc/systemd/system/seija.service`  
Inside it, put the following:
```ini
[Unit]
Description=Seija
After=network.target
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=10
User=user
Type=simple
ExecStart=/home/user/.local/share/Seija/venv/bin/python3 -m seija

[Install]
WantedBy=multi-user.target
```

The above assumes `user` as a username of the user the bot will be run under. Change it if it's different. 
Make sure this is run under the same user the pip3 command was ran as.  
If you want, you can add env vars in this file in the `[Service]` section as per this example
```ini
[Service]
Environment="SEIJA_TOKEN=your_bot_token_goes_here"
Environment="SEIJA_OSU_API_KEY=your_osu_api_key_goes_here"
```  

After you are done, type `sudo systemctl enable --now seija.service` to enable and start the service.
