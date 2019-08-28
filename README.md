# Seija
This bot is the heart of [The Mapset Management Server](https://discord.gg/8BquKaS). It is open-source for collaborative purposes.

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
+ and many more!

This bot is built using discord.py rewrite library and uses sqlite3 database.

**Please read the LICENSE before using.**

---

## Installation Instructions

1. Install `git` and `Python 3.5.3` (or newer) if you don't already have them.
2. Clone this repository using this command `git clone https://github.com/Kyuunex/Seija.git`
3. Install `discord.py` using this command `python3 -m pip install -U discord.py[voice]`.
4. `pip3 install upsidedown feedparser pycountry Pillow`.
5. `pip3 install git+https://github.com/Kyuunex/aioosuapi.git@v1`
6. `pip3 install git+https://github.com/Kyuunex/aioosuapi.git@v2`
7. `pip3 install git+https://github.com/Kyuunex/osudiscordpyembed.git`
8. Create a folder named `data`, then create `token.txt` and `osu_api_key.txt` inside it. Then put your bot token and osu api key in them. 
9. To start the bot, run `seija.bat` if you are on windows or `seija.sh` if you are on linux. Alternatively, you can manually run `seija.py` file but I recommend using the included launchers because it starts the bot in a loop which is required by the `'restart` and `'update` commands.
10. Figure out the rest yourself.