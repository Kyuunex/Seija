# Installation
After making sure you have `git` and Python 3.6+ installed, 
type the following in the command line to install or update the bot  
`python3 -m pip install git+https://github.com/MapsetManagementServer/Seija.git`  

To run the bot, type `python3 -m seija` in the command line  

### Windows Specific
+ You can get `git` form [here](https://git-scm.com/downloads) 
and Python from [here](https://www.python.org/downloads/windows/)  
+ If you don't know what command line is, on Windows, it's CMD or PowerShell. 
After you install `git` you'll also get a third choice called Git bash. 
+ Or you can just put `python3 -m seija` in a .bat file and click on it.

## Where is the bot's data folder
+ On Windows - `C:\Users\username\AppData\Local\Kyuunex\Seija`
+ On GNU/Linux - `/home/username/.local/share/Seija`
+ On Mac - `/Users/username/Library/Application Support/Seija` (I think, I am not 100% sure because I don't have a mac)

If you are restoring a database backup, it goes into this folder.

## API keys and tokens
You need to either put them in the respective text files in the bot's data folder or 
supply them via environment variables. if you do both, env vars will be used  
| text file  | environment variables | where to get |
| ------------- | ------------- | ------------- |
| token.txt  | SEIJA_TOKEN  | [create a new appuse here and make a bot acc](https://discord.com/developers/applications/) |
| osu_api_key.txt  | SEIJA_OSU_API_KEY  | [create a new app here](https://osu.ppy.sh/p/api/) |
| client_id.txt  | SEIJA_CLIENT_ID  | [register a new app on your account edit page](https://osu.ppy.sh/home/account/edit) |
| client_secret.txt  | SEIJA_CLIENT_SECRET  | [register a new app on your account edit page](https://osu.ppy.sh/home/account/edit) |

### If you are SSHing into a GNU/Linux server, you can just type these to quickly set the bot up.

```sh
python3 -m pip install git+https://github.com/MapsetManagementServer/Seija.git
mkdir -p $HOME/.local/share/Seija
# wget -O $HOME/.local/share/Seija/maindb.sqlite3 REPLACE_THIS_WITH_DIRECT_FILE_LINK # only do if you are restoring a backup
echo "REPLACE_THIS_WITH_BOT_TOKEN" | tee $HOME/.local/share/Seija/token.txt
echo "REPLACE_THIS_WITH_OSU_API_KEY" | tee $HOME/.local/share/Seija/osu_api_key.txt
echo "REPLACE_THIS_WITH_CLIENT_ID" | tee $HOME/.local/share/Seija/client_id.txt
echo "REPLACE_THIS_WITH_CLIENT_SECRET" | tee $HOME/.local/share/Seija/client_secret.txt
```

After that, you can move into installing this bot as a systemd service. 

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
Make sure this is run under the same user the pip3 command was ran as.  
If you want, you can add env vars in this file in the `[Service]` section as per this example
```ini
[Service]
Environment="SEIJA_TOKEN=asgkjshg9hsengiuraowpgwt"
Environment="SEIJA_OSU_API_KEY=sdagh9uiarwgy0s9eghrwet9wegohw78"
```  

After you are done, type `sudo systemctl enable --now seija.service` to enable and start the service.
