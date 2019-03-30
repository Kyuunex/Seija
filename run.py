#!/usr/bin/env python3

import discord
import asyncio
from discord.ext import commands
import os

from modules import permissions
from modules import osuapi
from modules import osuembed
from modules import dbhandler
from modules import modchecker
from modules import users
from modules import mapchannel
from modules import queuechannel
from modules import docs
from modules import aprilfools

client = commands.Bot(command_prefix='\'')
client.remove_command('help')
appversion = "b20190330"


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    if not os.path.exists('data/maindb.sqlite3'):
        appinfo = await client.application_info()
        await dbhandler.query("CREATE TABLE users (discordid, osuid, username, osujoindate, pp, country, rankedmaps, args)")
        await dbhandler.query("CREATE TABLE userevents (osuid, contents)")
        await dbhandler.query("CREATE TABLE config (setting, parent, value, flag)")
        await dbhandler.query("CREATE TABLE admins (discordid, permissions)")
        await dbhandler.query("CREATE TABLE modposts (postid, mapsetid, mapid, userid, contents)")
        await dbhandler.query("CREATE TABLE modtracking (mapsetid, channelid, mapsethostdiscordid, roleid, mapsethostosuid, type)")
        await dbhandler.query("CREATE TABLE notices (timestamp, notice)")
        await dbhandler.query("CREATE TABLE queues (channelid, discordid, guildid)")
        await dbhandler.query("CREATE TABLE mapchannels (channelid, roleid, discordid, mapsetid, guildid)")
        await dbhandler.query("CREATE TABLE namebackups (id, name)")
        await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), "1"]])


@client.command(name="adminlist", brief="Show bot admin list.", description="", pass_context=True)
async def adminlist(ctx):
    await ctx.send(embed=await permissions.adminlist())


@client.command(name="makeadmin", brief="Add a user to bot admin list.", description="", pass_context=True)
async def makeadmin(ctx, discordid: str):
    if await permissions.checkowner(ctx.message.author.id):
        await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(discordid), "0"]])
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="restart", brief="Restart the bot.", description="", pass_context=True)
async def restart(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Restarting")
        quit()
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="gitpull", brief="Update the bot.", description="Grabs the latest version from GitHub.", pass_context=True)
async def gitpull(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Fetching the latest version from the repository and updating from version %s" % (appversion))
        os.system('git pull')
        quit()
        # exit()
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="dbdump", brief="Perform a database dump.", description="", pass_context=True)
async def dbdump(ctx):
    if await permissions.check(ctx.message.author.id):
        if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["dbdumpchannelid", str(ctx.guild.id)]]))[0][0]):
            await ctx.send(file=discord.File('data/maindb.sqlite3'))
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sql", brief="Executre an SQL query.", description="", pass_context=True)
async def sql(ctx, *, query):
    if await permissions.checkowner(ctx.message.author.id):
        if len(query) > 0:
            response = await dbhandler.query(query)
            await ctx.send(response)
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="verify", brief="Manually verify a user.", description="", pass_context=True)
async def verify(ctx, osuid: str, discordid: int, preverify: str = None):
    if await permissions.check(ctx.message.author.id):
        await users.mverify(ctx, osuid, discordid, preverify)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="userdb", brief="Guild member and Database related commands.", description="", pass_context=True)
async def userdb(ctx, command: str = None, mention: str = None):
    if await permissions.checkowner(ctx.message.author.id):
        #await users.userdb(ctx, command, mention)
        #await users.guildnamesync(ctx)
        print("temporarly disabled")
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="mapset", brief="Show mapset info.", description="", pass_context=True)
async def mapset(ctx, mapsetid: str, text: str = None):
    if await permissions.check(ctx.message.author.id):
        embed = await osuembed.mapset(await osuapi.get_beatmaps(mapsetid))
        if embed:
            await ctx.send(content=text, embed=embed)
            # await ctx.message.delete()
        else:
            await ctx.send(content='`No mapset found with that ID`')
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="user", brief="Show osu user info.", description="", pass_context=True)
async def user(ctx, *, username):
    embed = await osuembed.osuprofile(await osuapi.get_user(username))
    if embed:
        await ctx.send(embed=embed)
        # await ctx.message.delete()
    else:
        await ctx.send(content='`No user found with that username`')


@client.command(name="help", brief="The pretty help command.", description="", pass_context=True)
async def help(ctx, subhelp: str = None):  # TODO: rewrite help
    await docs.main(ctx, subhelp)


@client.command(name="forcetrack", brief="Force Track a mapset in the current channel.", description="", pass_context=True)
async def forcetrack(ctx, mapsetid: str, mapsethostdiscordid: str = None):
    if await permissions.check(ctx.message.author.id):
        if mapsethostdiscordid == None:
            mapsethostdiscordid = ctx.message.author.id
        await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 0)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="forceuntrack", brief="Force untrack a mapset in the current channel.", description="", pass_context=True)
async def forceuntrack(ctx, mapsetid: str, trackingtype: str = None):
    if await permissions.check(ctx.message.author.id):
        if trackingtype == "ranked":
            embed = await osuembed.mapsetold(await osuapi.get_beatmap(mapsetid))
            await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
        elif trackingtype == "all":
            await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ?",[str(mapsetid),]])
            await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ?",[str(mapsetid),]])
            await ctx.send('`Mapset with that ID is no longer being tracked anywhere`')
        else:
            embed = None
            await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="veto", brief="Track a mapset in the current channel in veto mode.", description="", pass_context=True)
async def veto(ctx, mapsetid: int, mapsethostdiscordid: int = None):
    if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]):
        if mapsethostdiscordid == None:
            mapsethostdiscordid = ctx.message.author.id
        await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 1)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode.", description="", pass_context=True)
async def unveto(ctx, mapsetid: int):
    if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]):
        embed = await osuembed.mapsetold(await osuapi.get_beatmap(mapsetid))
        await modchecker.untrack(ctx, mapsetid, embed, None)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sublist", brief="List all tracked mapsets everywhere.", description="", pass_context=True)
async def sublist(ctx):
    if await permissions.check(ctx.message.author.id):
        for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
            embed = await osuembed.mapsetold(await osuapi.get_beatmap(str(oneentry[0])))
            await ctx.send(content="mapsetid %s | channel <#%s> | mapsethostdiscordid %s \nroleid %s | mapsethostosuid %s | trackingtype %s" % (oneentry), embed=embed)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="af", brief="", description="", pass_context=True)
async def af(ctx, action):
    if await permissions.checkowner(ctx.message.author.id):
        await ctx.message.delete()
        if action == "apply":
            await aprilfools.apply_guild(client, ctx)
            await aprilfools.apply_channels(client, ctx)
            await asyncio.sleep(10)
            await aprilfools.apply_roles(client, ctx)
            await aprilfools.rotate_logo(client, ctx)
            try:
                await ctx.send(file=discord.File("data/imsorry.png"))
            except:
                await ctx.send(":ok_hand:")
        elif action == "restore":
            await aprilfools.restore_guild(client, ctx)
            await aprilfools.restore_channels(client, ctx)
            await asyncio.sleep(10)
            await aprilfools.restore_roles(client, ctx)
            await aprilfools.rotate_logo(client, ctx)
            await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="request", brief="Request ether a queue or mod channel.", description="", pass_context=True)
async def requestchannel(ctx, requesttype: str = "help", arg1: str = None, arg2: str = None):  # TODO: Add request
    if requesttype == "queue":
        await queuechannel.make_queue_channel(client, ctx, arg1)
    elif requesttype == "mapset":
        await mapchannel.make_mapset_channel(client, ctx, arg1, arg2)


@client.command(name="nuke", brief="Nuke a requested channel.", description="", pass_context=True)
async def nuke(ctx):
    if await permissions.check(ctx.message.author.id):
        await mapchannel.nuke_mapset_channel(client, ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="open", brief="Open the queue.", description="", pass_context=True)
async def openq(ctx, title = None, desc = ""):
    await queuechannel.queuesettings(client, ctx, "open", title, desc)


@client.command(name="close", brief="Close the queue.", description="", pass_context=True)
async def closeq(ctx, title = None, desc = ""):
    await queuechannel.queuesettings(client, ctx, "close", title, desc)


@client.command(name="hide", brief="Hide the queue.", description="", pass_context=True)
async def hideq(ctx):
    await queuechannel.queuesettings(client, ctx, "hide")


@client.command(name="add", brief="Add a user in the current mapset channel.", description="", pass_context=True)
async def addm(ctx, discordid: int):
    await mapchannel.mapchannelsettings(client, ctx, "add", discordid)


@client.command(name="remove", brief="Remove a user from the current mapset channel.", description="", pass_context=True)
async def removem(ctx, discordid: int):
    await mapchannel.mapchannelsettings(client, ctx, "remove", discordid)


@client.command(name="abandon", brief="Abandon the mapset and untrack.", description="", pass_context=True)
async def abandon(ctx):
    await mapchannel.abandon(client, ctx)


@client.event
async def on_message(message):
    await users.on_message(client, message)
    await client.process_commands(message)


@client.event
async def on_member_join(member):
    await users.on_member_join(client, member)


@client.event
async def on_member_remove(member):
    await users.on_member_remove(client, member)


async def modchecker_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await modchecker.main(client)


async def users_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await users.mapping_username_loop(client)


# TODO: detect when channel is deleted and automatically untrack

client.loop.create_task(modchecker_background_loop())
client.loop.create_task(users_background_loop())
client.run(open("data/token.txt", "r+").read(), bot=True)
