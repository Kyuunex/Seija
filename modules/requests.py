from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import utils
import discord
import random
import asyncio

async def mapsetchannel(client, ctx, mapsetid, mapsetname):
    guildmapsetcategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guildmapsetcategory", str(ctx.guild.id)]])
    if guildmapsetcategory:
        try:
            await ctx.send("sure, gimme a moment")
            if int(mapsetid) == 0 or mapsetid == None:
                mapset = None
            else:
                mapset = await osuapi.get_beatmap(mapsetid)

            if mapsetname:
                discordfriendlychannelname = mapsetname.replace(" ", "_").lower()
                rolename = mapsetname
            elif mapset:
                discordfriendlychannelname = mapset['title'].replace(" ", "_").lower()
                rolename = mapset['title']
            else:
                discordfriendlychannelname = None
                rolename = None

            if discordfriendlychannelname:
                guild = ctx.message.guild
                rolecolor = discord.Colour(random.randint(1, 16777215))
                mapsetrole = await guild.create_role(name=rolename, colour=rolecolor)
                category = await utils.get_channel(client.get_all_channels(), int(guildmapsetcategory[0][0]))
                channeloverwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: discord.PermissionOverwrite(
                        create_instant_invite=True,
                        manage_channels=True,
                        manage_roles=True,
                        manage_webhooks=True,
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True,
                        attach_files=True,
                        read_message_history=True,
                        mention_everyone=False
                    ),
                    mapsetrole: discord.PermissionOverwrite(read_messages=True),
                    guild.me: discord.PermissionOverwrite(
                        manage_channels=True,
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await ctx.message.author.add_roles(mapsetrole)
                embed = await osuembed.mapset(mapset)
                await channel.send("%s done!" % (ctx.message.author.mention), embed=embed)
            else:
                await ctx.send("You are not using this command correctly")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("Not enabled in this server yet.")


async def queuechannel(client, ctx, queuetype):
    guildqueuecategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guildqueuecategory", str(ctx.guild.id)]])
    if guildqueuecategory:
        if not await dbhandler.query(["SELECT discordid FROM queues WHERE discordid = ? AND guildid = ?", [str(ctx.message.author.id), str(ctx.guild.id)]]):
            try:
                await ctx.send("sure, gimme a moment")
                if not queuetype:
                    queuetype = "std"
                guild = ctx.message.guild
                channeloverwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: discord.PermissionOverwrite(
                        create_instant_invite=True,
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True,
                        attach_files=True,
                        read_message_history=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                discordfriendlychannelname = "%s-%s-queue" % (ctx.message.author.display_name.replace(" ", "_").lower(), queuetype)
                category = await utils.get_channel(client.get_all_channels(), int(guildqueuecategory[0][0]))
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await channel.send("%s done!" % (ctx.message.author.mention))
                await dbhandler.query(["INSERT INTO queues VALUES (?, ?, ?)", [str(channel.id), str(ctx.message.author.id), str(ctx.guild.id)]])
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("you already have a queue though. or it was deleted, in this case, ping kyuunex")
    else:
        await ctx.send("Not enabled in this server yet.")

async def queuesettings(client, ctx, action):
    if await dbhandler.query(["SELECT discordid FROM queues WHERE discordid = ? AND channelid = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]]):
        try:
            if action == "open":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=True)
                await ctx.send("queue open!")
            elif action == "close":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue closed!")
            elif action == "hide":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue hidden!")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("not your queue")

async def modchannelsettings(client, ctx, action, discordid):
    #if await dbhandler.query(["SELECT discordid FROM queues WHERE discordid = ? AND channelid = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]]):
    if False:
        try:
            discorduser = client.get_user(int(discordid))
            if action == "add":
                await ctx.message.channel.set_permissions(discorduser, read_messages=True, send_messages=True)
                await ctx.send("added user placeholder message!")
            elif action == "remove":
                await ctx.message.channel.set_permissions(discorduser, read_messages=False, send_messages=False)
                await ctx.send("remove person placeholder message!")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("not yet working")

async def mapsetnuke(client, ctx):
    try:
        await ctx.send("nuking channel in 2 seconds!")
        await asyncio.sleep(2)
        await ctx.message.channel.delete(reason="Manually nuked the channel due to abuse")
    except Exception as e:
        await ctx.send(e)