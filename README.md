# Seija
This bot is the heart of [The Mapset Management Server](https://discord.gg/8BquKaS). 
It is open-source for collaborative purposes.

This bot does many things in our osu! mapping related Discord server, including:
+ Linking a Discord account to an osu! account, giving appropriate roles.
+ Tracking users' name changes, syncing nicknames.
+ Tracking users' mapping activity.
+ Tracking users' BN/NAT roles on the website, syncing them accordingly in the Discord server.
+ Tracking users' ranked map amount on the website, syncing them accordingly in the Discord server.
+ Creating queue channels, giving the author permissions, and `.close`, `.open` and `.hide` commands.
+ Creating mapset channels, giving participants correct roles, giving management commands to the mapset host.
+ Moving channels to the archive when their owner leaves the server.
+ Restoring permissions when user returns to the server.
+ Automatically putting channels in categories they belong when needed.
+ and many more!

This bot is built using discord.py rewrite library and uses sqlite3 database.

This branch of Seija is version 2.x and is not expected to work beyond Python 3.8, 
as discord.py is discontinued and does not install beyond Python 3.8.
