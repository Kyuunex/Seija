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
