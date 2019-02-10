from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import utils
from modules import instructions
import discord
import random
import asyncio


async def mapsetchannel(client, ctx, mapsetid, mapsetname, appversion):
    guildmapsetcategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guildmapsetcategory", str(ctx.guild.id)]])
    if guildmapsetcategory:
        try:
            await ctx.send("sure, gimme a moment")
            if int(mapsetid) == 0 or mapsetid == None:
                mapset = None
                mapsetid = "0"
                desc = ""
            else:
                mapset = await osuapi.get_beatmap(mapsetid)
                mapsetid = str(mapsetid)
                desc = "https://osu.ppy.sh/beatmapsets/%s" % (mapsetid)

            if mapsetname:
                discordfriendlychannelname = mapsetname.replace(
                    " ", "_").lower()
                rolename = mapsetname
            elif mapset:
                discordfriendlychannelname = mapset['title'].replace(
                    " ", "_").lower()
                rolename = mapset['title']
            else:
                discordfriendlychannelname = None
                rolename = None

            if discordfriendlychannelname:
                guild = ctx.message.guild
                rolecolor = discord.Colour(random.randint(1, 16777215))
                mapsetrole = await guild.create_role(name=rolename, colour=rolecolor, mentionable=True)
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
                #embed = await osuembed.mapset(mapset)
                await channel.send("%s done!" % (ctx.message.author.mention), embed=await instructions.modchannelcommands(appversion))
                await dbhandler.query(["INSERT INTO modchannels VALUES (?, ?, ?, ?, ?)", [str(channel.id), str(mapsetrole.id), str(ctx.message.author.id), str(mapsetid), str(ctx.guild.id)]])
            else:
                await ctx.send("You are not using this command correctly")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("Not enabled in this server yet.")


async def queuechannel(client, ctx, queuetype, appversion):
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
                discordfriendlychannelname = "%s-%s-queue" % (
                    ctx.message.author.display_name.replace(" ", "_").lower(), queuetype)
                category = await utils.get_channel(client.get_all_channels(), int(guildqueuecategory[0][0]))
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await dbhandler.query(["INSERT INTO queues VALUES (?, ?, ?)", [str(channel.id), str(ctx.message.author.id), str(ctx.guild.id)]])
                await channel.send("%s done!" % (ctx.message.author.mention), embed=await instructions.queuecommands(appversion))
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
    roleidlist = await dbhandler.query(["SELECT roleid FROM modchannels WHERE discordid = ? AND channelid = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])
    if roleidlist:
        try:
            member = ctx.guild.get_member(int(discordid))
            role = discord.utils.get(ctx.guild.roles, id=int(roleidlist[0][0]))
            if action == "add":
                await member.add_roles(role, reason="added to mapset")
                await ctx.send("added %s in this channel" % (member.mention))
            elif action == "remove":
                await member.remove_roles(role, reason="removed from mapset")
                await ctx.send("removed %s from this channel" % (member.mention))
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("not your mapset channel")


async def mapsetnuke(client, ctx):
    roleidlist = await dbhandler.query(["SELECT roleid FROM modchannels WHERE channelid = ?", [str(ctx.message.channel.id)]])
    if roleidlist:
        try:
            await ctx.send("nuking channel and role in 2 seconds! untracking also")
            await asyncio.sleep(2)
            role = discord.utils.get(ctx.guild.roles, id=int(roleidlist[0][0]))

            mapsetid = await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE channelid = ?", [str(ctx.message.channel.id)]])
            if mapsetid:
                await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ?",[str(mapsetid[0][0]),]])
                await dbhandler.query(["DELETE FROM jsondata WHERE mapsetid = ?",[str(mapsetid[0][0]),]])
                await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ?",[str(mapsetid[0][0]),]])
                await ctx.send("untracked")
                await asyncio.sleep(2)

            await dbhandler.query(["DELETE FROM modchannels WHERE channelid = ?", [str(ctx.message.channel.id)]])
            await role.delete(reason="Manually nuked the role due to abuse")
            await ctx.message.channel.delete(reason="Manually nuked the channel due to abuse")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("this is not a mapset channel")
