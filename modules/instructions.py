import discord

from modules import dbhandler
from modules import permissions


async def help(ctx, admin, appversion):
    helpembed = discord.Embed(title="Seija teaches you how to be a bot master",
                              description="Here are available commands. Any abuse will be dealt with punishment.", color=0xbd3661)

    helpembed.set_author(name="Seija %s" % (appversion),
                         icon_url="https://i.imgur.com/1icHC5a.png")
    helpembed.set_thumbnail(url="https://i.imgur.com/JhL9PV8.png")

    helpembed.add_field(name="'adminlist",
                        value="Shows a list of bot admins", inline=True)

    if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]):
        helpembed.add_field(name="'veto <mapsetid>",
                            value="Track a mapset in this channel in veto mode", inline=True)
        helpembed.add_field(name="'unveto <mapsetid>",
                            value="Untrack a mapset in this channel in veto mode", inline=True)

    if admin == "admin":
        if await permissions.check(ctx.message.author.id):
            helpembed.add_field(
                name="'track", value="Subscribe to a beatmapset discussions in this channel", inline=True)
            helpembed.add_field(
                name="'untrack", value="Unsubscribe from a beatmapset discussions in this channel", inline=True)
            helpembed.add_field(
                name="'sublist", value="Lists all channels and mapsets being tracked", inline=True)
            helpembed.add_field(
                name="'restart", value="Restart the bot", inline=True)
        else:
            await ctx.send(embed=await permissions.error())

    helpembed.set_footer(text="Made by Kyuunex",
                         icon_url='https://avatars0.githubusercontent.com/u/5400432')
    await ctx.send(embed=helpembed)

async def queuehelp(ctx, appversion):
    qname = ctx.message.author.display_name.replace(" ", "_").lower()
    queuehelpembed = discord.Embed(title="With this command, you can create a queue channel.",
                              description="""**__Queue creation command:__**
`'request queue (queue type)` - Create a queue. By default, the queue will be closed.
`(queue type)` is an optional argument that specifies what goes between your username and the word `queue` in the title of the channel. If no argument is supplied, `std` will be automatically filled. Please follow our naming standards.
__Examples:__
`'request queue mania` - This example will create `#%s-mania-queue`
`'request queue taiko-bn` - This example will create `#%s-taiko-bn-queue`

**__Queue management commands:__**
`'open` - Open the queue, everyone can see and post in it.
`'close` - Close the queue, everyone can see but can't post in it. You can also use this command to unhide the queue, but again, nobody will be able to post in it.
`'hide` - Hide the queue, only admins can see the queue. Nobody else can see and post in it.""" % (qname, qname), color=0xbd3661)
    queuehelpembed.set_author(name="Seija %s" % (appversion),
                         icon_url="https://i.imgur.com/1icHC5a.png")
    queuehelpembed.set_footer(text="Made by Kyuunex",
                         icon_url='https://avatars0.githubusercontent.com/u/5400432')
    await ctx.send(embed=queuehelpembed)

async def mapsethelp(ctx, appversion):
    mapsetchannelhelpembed = discord.Embed(title="With this command, you can create a mod notification channel for collaborators.",
                              description="""**__Mapset channel creation command:__**: 
`'request mapset (mapset id) (song name)` - This is the general command to create a channel.
`(song name)` is an optional argument that is not required. But it must be written in quotes if supplied.
If the mapset is not yet uploaded, `(mapset id)` can be set to `0` but in that case, `(song name)` argument is required.
__Examples:__
`'request mapset 817793` - Example usage with mapset id.
`'request mapset 0 "Futanari Nari ni"` - Example usage with just song name.

**__Mapset channel management commands:__**
`'add (discord user id)` - Add a user in the mapset channel.
`'remove (discord user id)` - Remove a user from the mapset channel.
`(discord user id)` is a discord account user id. To get it, you need developer mode enabled in your discord client settings, right click on the user and click "Copy ID"
`'abandon` - If you abandoning the set, whether temporarily or permanently, this will stop all tracking and move the channel to archive category.
`'track` - (command not yet finished)
""", color=0xbd3661)
    mapsetchannelhelpembed.set_author(name="Seija %s" % (appversion), icon_url="https://i.imgur.com/1icHC5a.png")
    mapsetchannelhelpembed.set_footer(text="Made by Kyuunex", icon_url='https://avatars0.githubusercontent.com/u/5400432')
    await ctx.send(embed=mapsetchannelhelpembed)


async def queuecommands(appversion):
    queuecommands = discord.Embed(title="Queue management commands", description="""**Please avoid manually editing channel permissions unless you wanna ban a specific person or a role from your queue.**""", color=0xbd3661)
    queuecommands.add_field(name="'open", value="Open the queue, everyone can see and post in it.", inline=False)
    queuecommands.add_field(name="'close", value="Close the queue, everyone can see but can't post in it. You can also use this command to unhide the queue, but again, nobody will be able to post in it.", inline=False)
    queuecommands.add_field(name="'hide", value="Hide the queue, only admins can see the queue. Nobody else can see and post in it.", inline=False)
    queuecommands.set_author(name="Seija %s" % (appversion), icon_url="https://i.imgur.com/1icHC5a.png")
    queuecommands.set_footer(text="Made by Kyuunex", icon_url='https://avatars0.githubusercontent.com/u/5400432')
    return queuecommands

async def modchannelcommands(appversion):
    modchannelcommands = discord.Embed(title="Mapset channel management commands", description="""`(discord user id)` is a discord account user id. To get it, you need developer mode enabled in your discord client settings, right click on the user and click \"Copy ID\"""", color=0xbd3661)
    modchannelcommands.add_field(name="'add (discord user id)", value="Add a user in the mapset channel.", inline=False)
    modchannelcommands.add_field(name="'remove (discord user id)", value="Remove a user from the mapset channel.", inline=False)
    modchannelcommands.add_field(name="'abandon", value="If you abandoning the set, whether temporarily or permanently, this will stop all tracking and move the channel to archive category.", inline=False)
    modchannelcommands.add_field(name="'track", value="(command not yet finished, ping kyuunex to track)", inline=False)
    modchannelcommands.set_author(name="Seija %s" % (appversion), icon_url="https://i.imgur.com/1icHC5a.png")
    modchannelcommands.set_footer(text="Made by Kyuunex", icon_url='https://avatars0.githubusercontent.com/u/5400432')
    return modchannelcommands