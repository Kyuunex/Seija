# Seija
This bot is the heart of [The Mapset Management Server](https://discord.gg/8BquKaS). 
It is open-source for collaborative purposes.

This bot does many things in our osu! mapping related Discord server, including:
+ Linking a Discord account to an osu! account.
+ Tracking users' name changes, syncing nicknames.
+ Tracking users' mapping activity.
+ Creating queue channels, giving the author permissions, and `'close`, `'open` and `'hide` commands.
+ Creating mapset channels, giving participants correct roles, giving management commands to the mapset host.
+ Moving channels to the archive when their owner leaves the server.
+ Restring permissions when user returns to the server.
+ Automatically putting channels in categories they belong when needed.
+ Validating users' reputation, checking amount of ranked maps they have.
+ Tracking group changes.
+ Posting new ranked maps.
+ Tracking any user's mapping activity.
+ and many more!

This bot is built using discord.py rewrite library and uses sqlite3 database.

**Please read the LICENSE before using or modifying.** 
It is a copyleft license that requires your modifications to be made available on the same conditions.

---

## Installation Instructions

1. Install `git` and [Python](https://www.python.org/) (version 3.6 or newer compatible) if you don't already have them.
2. Clone this repository. (`git clone https://github.com/MapsetManagementServer/Seija.git`)
3. Install requirements. (`python3 -m pip install -r requirements.txt`)
4. For your tokens/api keys, create a folder named `data` in the repository folder. Inside it create 4 files:
    + Create `token.txt` and put your bot token in. You can get it by registering an application
    on [Discord's developer site](https://discord.com/developers/applications/) and creating a bot.
    + Create `osu_api_key.txt` and put osu api key in. You can get it [here](https://osu.ppy.sh/p/api/)
    + Create `client_id.txt` and `client_secret.txt` and inside them, 
    put client id and secret you get by registering an Oauth application on your 
    on [your account edit page](https://osu.ppy.sh/home/account/edit)
5. If you are restoring a backup, just put the database file in the `data` folder.
6. To start the bot, run `seija.py`. I recommend installing the bot as a `systemd` service though.
7. Figure out the rest yourself.

### If you are SSHing into a GNU/Linux server, you can just type these to achieve the same thing

```sh
cd $HOME
git clone https://github.com/MapsetManagementServer/Seija.git
cd $HOME/Seija
python3 -m pip install -r requirements.txt
mkdir -p $HOME/Seija/data
# wget -O $HOME/Seija/data/maindb.sqlite3 REPLACE_THIS_WITH_DIRECT_FILE_LINK # only do if you are restoring a backup
echo "REPLACE_THIS_WITH_BOT_TOKEN" | tee $HOME/Seija/data/token.txt
echo "REPLACE_THIS_WITH_OSU_API_KEY" | tee $HOME/Seija/data/osu_api_key.txt
echo "REPLACE_THIS_WITH_CLIENT_ID" | tee $HOME/Seija/data/client_id.txt
echo "REPLACE_THIS_WITH_CLIENT_SECRET" | tee $HOME/Seija/data/client_secret.txt
```


## Installing the bot as a systemd service

Create the following file: `/lib/systemd/system/seija.service`  
Inside it, put the following:
```ini
[Unit]
Description=Seija
After=multi-user.target

[Service]
Restart=on-failure
RestartSec=5s
User=pi
Type=simple
WorkingDirectory=/home/pi/Seija/
ExecStart=/usr/bin/python3 /home/pi/Seija/seija.py

[Install]
WantedBy=multi-user.target
```

The above assumes `pi` as a username of the user the bot will be run under. Change it if it's different. 
Make sure to change the paths too. The default assumes you just clone the thing in the user's home folder.  
Make sure the requirements are installed under the user the bot will be run under.  
After you are done, type `sudo systemctl enable --now seija.service` to enable and start the service.
