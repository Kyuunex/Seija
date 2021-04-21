## Modern installation
After making sure you have `git` and Python 3.6+ installed, type the following in the command line  
`python3 -m pip install git+https://github.com/MapsetManagementServer/Seija.git`  
To run the bot, type `python3 -m seija`


### If you are SSHing into a GNU/Linux server, you can just type these to achieve the same thing

```sh
python3 -m pip install git+https://github.com/MapsetManagementServer/Seija.git
mkdir -p $HOME/.local/share/Seija
# wget -O $HOME/.local/share/Seija/maindb.sqlite3 REPLACE_THIS_WITH_DIRECT_FILE_LINK # only do if you are restoring a backup
echo "REPLACE_THIS_WITH_BOT_TOKEN" | tee $HOME/.local/share/Seija/token.txt
echo "REPLACE_THIS_WITH_OSU_API_KEY" | tee $HOME/.local/share/Seija/osu_api_key.txt
echo "REPLACE_THIS_WITH_CLIENT_ID" | tee $HOME/.local/share/Seija/client_id.txt
echo "REPLACE_THIS_WITH_CLIENT_SECRET" | tee $HOME/.local/share/Seija/client_secret.txt
```
For your tokens/api keys:
+ You can get your bot token by registering an application
on [Discord's developer site](https://discord.com/developers/applications/) and creating a bot.
+ You can get your osu api key [here](https://osu.ppy.sh/p/api/)
+ You get client id and client secret by registering an Oauth application on your 
on [your account edit page](https://osu.ppy.sh/home/account/edit)

After that, you can move into installing this bot as a systemd service

## Installing the bot as a systemd service

Create the following file: `/lib/systemd/system/seija.service`  
Inside it, put the following:
```ini
[Unit]
Description=Seija
After=network.target
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=5
User=pi
Type=simple
ExecStart=/usr/bin/python3 -m seija.py

[Install]
WantedBy=multi-user.target
```

The above assumes `pi` as a username of the user the bot will be run under. Change it if it's different. 
Make sure to change the paths too. The default assumes you just clone the thing in the user's home folder.  
Make sure the requirements are installed under the user the bot will be run under.  
After you are done, type `sudo systemctl enable --now seija.service` to enable and start the service.
