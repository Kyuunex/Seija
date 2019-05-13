import discord

from modules import dbhandler
from modules import permissions

help_thumbnail = "https://i.imgur.com/JhL9PV8.png"
author_icon = "https://i.imgur.com/1icHC5a.png"
author_text = "Seija"

footer_icon = 'https://avatars0.githubusercontent.com/u/5400432'
footer_text = "Made by Kyuunex"

async def main(ctx, subhelp):
    if subhelp == "admin":
        if await permissions.check(ctx.message.author.id):
            await ctx.send(embed=await admin())
        else:
            await ctx.send(embed=await permissions.error())
    elif subhelp == "veto":
        if await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND value = ?", ["guild_veto_channel", str(ctx.message.channel.id)]]):
            await ctx.send(embed=await veto())
    elif subhelp == "mapchannel":
        await ctx.send(embed=await mapchannel())
    elif subhelp == "queue":
        await ctx.send(embed=await queue(ctx.message.author.display_name))
    elif subhelp == "mapchannelmanagement":
        await ctx.send(embed=await mapchannelmanagement())
    elif subhelp == "queuemanagement":
        await ctx.send(embed=await queuemanagement())
    else:
        await ctx.send(embed=await help())


async def help():
    embed = discord.Embed(title="Seija teaches you how to be a bot master.", description="Any abuse will be dealt with punishment.", color=0xbd3661)

    embed.add_field(name="'help mapchannel", value="To bring up a help menu for requesting a mapset channel.", inline=True)
    embed.add_field(name="'help queue", value="To bring up a help menu for requesting a queue channel.", inline=True)
    embed.add_field(name="'help mapchannelmanagement", value="To bring mapset channel management commands.", inline=True)
    embed.add_field(name="'help queuemanagement", value="To bring up queue channel management commands.", inline=True)
    embed.add_field(name="'help admin", value="Commands for admins.", inline=True)
    #embed.add_field(name="'help veto", value="Commands for tracking in veto mode.", inline=True)

    embed.set_thumbnail(url=help_thumbnail)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def admin():
    embed = discord.Embed(title="Seija teaches you how to be a bot master.", description="These commands are intended only for bot admins.", color=0xbd3661)

    embed.add_field(name="'adminlist", value="Shows a list of bot admins.", inline=True)
    embed.add_field(name="'forcetrack <mapset_id>", value="Subscribe to a beatmapset discussions in this channel.", inline=True)
    embed.add_field(name="'forceuntrack <mapset_id>", value="Unsubscribe from a beatmapset discussions in this channel.", inline=True)
    embed.add_field(name="'sublist", value="Lists all channels and mapsets being tracked.", inline=True)
    embed.add_field(name="'restart", value="Restart the bot.", inline=True)

    embed.set_thumbnail(url=help_thumbnail)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def veto():
    embed = discord.Embed(title="Seija teaches you how to be a bot master.", description="~~BNS PLEZ MUTUAL~~ Here are veto tracking commands.", color=0xbd3661)

    embed.add_field(name="'veto <mapset_id>", value="Track a mapset in this channel in veto mode.", inline=True)
    embed.add_field(name="'unveto <mapset_id>", value="Untrack a mapset in this channel in veto mode.", inline=True)

    embed.set_thumbnail(url=help_thumbnail)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def queue(author):
    qname = author.replace(" ", "_").lower()
    embed = discord.Embed(title="With this command, you can create a queue channel.",
                              description="""**__Queue creation command:__**
`'request queue (queue type)` - Create a queue. By default, the queue will be closed.
`(queue type)` is an optional argument that specifies what goes between your username and the word `queue` in the title of the channel. If no argument is supplied, `std` will be automatically filled. Please follow our naming standards.

**__Examples:__**
`'request queue mania` - This example will create `#%s-mania-queue`
`'request queue taiko-bn` - This example will create `#%s-taiko-bn-queue`

For queue management commands, type `'help queuemanagement`""" % (qname, qname), color=0xbd3661)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def mapchannel():
    embed = discord.Embed(title="With this command, you can create a mapset channel for collaborators.",
                              description="""**__Mapset channel creation command:__**: 
`'request mapset (mapset id) (song name)` - This is the general command to create a channel.
`(song name)` is an optional argument that is not required. But it must be written in quotes if supplied.
If the mapset is not yet uploaded, `(mapset id)` can be set to `0` but in that case, `(song name)` argument is required.

**__Examples:__**
`'request mapset 817793` - Example usage with mapset id.
`'request mapset 0 "Futanari Nari ni"` - Example usage with just song name.

For mapset channel management commands, type `'help mapchannelmanagement`
**And __DO NOT__ create a mapset channel for single person sets. Only do it if you have guest difficulties or if this is a collab.**""", color=0xbd3661)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def queuemanagement():
    embed = discord.Embed(title="Queue management commands", description="""**Please avoid manually editing channel permissions unless you wanna ban a specific person or a role from your queue or unless the bot is down.**""", color=0xbd3661)
    embed.add_field(name="'open", value="Open the queue, everyone can see and post in it.", inline=False)
    embed.add_field(name="'close", value="Close the queue, everyone can see but can't post in it. You can also use this command to unhide the queue, but again, nobody will be able to post in it.", inline=False)
    embed.add_field(name="'hide", value="Hide the queue, only admins can see the queue. Nobody else can see and post in it.", inline=False)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


async def mapchannelmanagement():
    embed = discord.Embed(title="Mapset channel management commands", description="""`(discord user id)` is a discord account user id. To get it, you need developer mode enabled in your discord client settings, right click on the user and click \"Copy ID\"""", color=0xbd3661)
    embed.add_field(name="'add (discord user id)", value="Add a user in the mapset channel.", inline=False)
    embed.add_field(name="'remove (discord user id)", value="Remove a user from the mapset channel.", inline=False)
    embed.add_field(name="'abandon", value="If you abandoning the set, whether temporarily or permanently, this will stop all tracking and move the channel to archive category.", inline=False)
    embed.add_field(name="'track", value="(command not yet finished, ping kyuunex to track)", inline=False)
    embed.set_author(name=author_text, icon_url=author_icon)
    embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed