import discord

from modules import dbhandler
from modules import permissions

async def help(ctx, admin, appversion):
	helpembed=discord.Embed(title="Seija teaches you how to be a bot master", description="Here are available commands. Any abuse will be dealt with punishment.", color=0xbd3661)

	helpembed.set_author(name="Seija %s" % (appversion), icon_url="https://i.imgur.com/1icHC5a.png")
	helpembed.set_thumbnail(url="https://i.imgur.com/JhL9PV8.png")
	
	helpembed.add_field(name="'adminlist", value="Shows a list of bot admins", inline=True)
	
	if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]) :
		helpembed.add_field(name="'veto <mapsetid>", value="Track a mapset in this channel in veto mode", inline=True)
		helpembed.add_field(name="'unveto <mapsetid>", value="Untrack a mapset in this channel in veto mode", inline=True)

	if admin == "admin":
		if await permissions.check(ctx.message.author.id) :
			helpembed.add_field(name="'track", value="Subscribe to a beatmapset discussions in this channel", inline=True)
			helpembed.add_field(name="'untrack", value="Unsubscribe from a beatmapset discussions in this channel", inline=True)
			helpembed.add_field(name="'sublist", value="Lists all channels and mapsets being tracked", inline=True)
			helpembed.add_field(name="'restart", value="Restart the bot", inline=True)
		else :
			await ctx.send(embed=await permissions.error())

	helpembed.set_footer(text = "Made by Kyuunex", icon_url='https://avatars0.githubusercontent.com/u/5400432')
	await ctx.send(embed=helpembed)

async def request(ctx):
    await ctx.send("""With this command, you can create ether a queue channel or a mod notification channel for collaborators.

`[something/whatever]` - means you only choose one option listed in the square brackets
**Please avoid manually editing channel permissions unless you wanna ban a specific person from your queue.**

**Available commands for queues**:
`'request queue [std/taiko/ctb/mania]` - create a queue
`'open` - open that queue, everyone can see and post in it.
`'close` - close that queue, everyone can see but can't post in it.
`'hide` - hide the queue, only admins can see the queue. nobody else can see and post in it.

**Available commands for mapset channels**: 
**(this functionality is not enabled yet, i'm just writing all the instructions in one go)**
`'request mapset (mapset id) (song name)` - this is the general command to create a channel.
(song name) is an optional argument that is not required. But it must be written in quotes if supplied.
If the mapset is not yet uploaded, (mapset id) can be set to `0` but in that case, (song name) argument is required.
`'request mapset 817793` - example usage 1
`'request mapset 0 "Futanari Nari ni"` - example usage 2

`'add (discord user id)` - add a user in the mapset channel. (discord user id) is a discord account user id of the person. to get it, you need developer mode enabled in discord and right click on the user and click "copy id"
`'remove (discord user id)` - add a user in the mapset channel.
`'abandon` - if you abandoning the set, whether temporarily or permanently, this will stop all tracking and move the channel to archive category.""")