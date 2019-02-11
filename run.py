import discord
import asyncio
from discord.ext import commands
import os
import shutil
import time
import random

from modules import permissions
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview
from modules import dbhandler
from modules import modchecker
from modules import modelements
from modules import users
from modules import utils
from modules import groupfeed
from modules import requests
from modules import instructions

client = commands.Bot(command_prefix='\'')
client.remove_command('help')
appversion = "b20190211"


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    if not os.path.exists('data/maindb.sqlite3'):
        appinfo = await client.application_info()
        await dbhandler.query("CREATE TABLE users (discordid, osuid, username, osujoindate, pp, country, rankedmaps, args)")
        await dbhandler.query("CREATE TABLE jsondata (mapsetid, contents)")
        await dbhandler.query("CREATE TABLE config (setting, parent, value, flag)")
        await dbhandler.query("CREATE TABLE admins (discordid, permissions)")
        await dbhandler.query("CREATE TABLE modposts (postid, mapsetid, mapid, userid, contents)")
        await dbhandler.query("CREATE TABLE modtracking (mapsetid, channelid, mapsethostdiscordid, roleid, mapsethostosuid, type)")
        await dbhandler.query("CREATE TABLE groupfeedchannels (channelid)")
        await dbhandler.query("CREATE TABLE rankfeedchannels (channelid)")
        await dbhandler.query("CREATE TABLE feedjsondata (feedtype, contents)")
        await dbhandler.query("CREATE TABLE queues (channelid, discordid, guildid)")
        await dbhandler.query("CREATE TABLE modchannels (channelid, roleid, discordid, mapsetid, guildid)")
        await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), "1"]])


@client.command(name="adminlist", brief="Show bot admin list", description="", pass_context=True)
async def adminlist(ctx):
    await ctx.send(embed=await permissions.adminlist())


@client.command(name="makeadmin", brief="Make a user bot admin", description="", pass_context=True)
async def makeadmin(ctx, discordid: str):
    if await permissions.checkowner(ctx.message.author.id):
        await dbhandler.insert('admins', (str(discordid), "0"))
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="restart", brief="Restart the bot", description="", pass_context=True)
async def restart(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Restarting")
        quit()
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="gitpull", brief="Update the bot", description="it just does git pull", pass_context=True)
async def gitpull(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Feteching the latest version from the repository and updating from version %s" % (appversion))
        os.system('git pull')
        quit()
        # exit()
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="dbdump", brief="Database Dump", description="", pass_context=True)
async def dbdump(ctx):
    if await permissions.check(ctx.message.author.id):
        if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["dbdumpchannelid", str(ctx.guild.id)]]))[0][0]):
            await ctx.send(file=discord.File('data/maindb.sqlite3'))
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sql", brief="Executre an SQL query", description="", pass_context=True)
async def sql(ctx, *, query):
    if await permissions.checkowner(ctx.message.author.id):
        if len(query) > 0:
            response = await dbhandler.query(query)
            await ctx.send(response)
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="mapset", brief="Show a mapset", description="", pass_context=True)
async def mapset(ctx, mapsetid: str, text: str = None):
    if await permissions.check(ctx.message.author.id):
        embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
        if embed:
            await ctx.send(content=text, embed=embed)
            # await ctx.delete_message(ctx.message)
        else:
            await ctx.send(content='`No mapset found with that ID`')
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="user", brief="Show a user", description="", pass_context=True)
async def user(ctx, *, username):
    embed = await osuembed.osuprofile(await osuapi.get_user(username))
    if embed:
        await ctx.send(embed=embed)
        # await ctx.delete_message(ctx.message)
    else:
        await ctx.send(content='`No user found with that username`')


@client.command(name="help", brief="Help for users", description="", pass_context=True)
async def help(ctx, admin: str = None):  # TODO: rewrite help
    await instructions.help(ctx, admin, appversion)


@client.command(name="track", brief="Track a mapset", description="", pass_context=True)
async def track(ctx, mapsetid: str, mapsethostdiscordid: str = None):
    if await permissions.check(ctx.message.author.id):
        if mapsethostdiscordid == None:
            mapsethostdiscordid = ctx.message.author.id
        await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 0)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="veto", brief="Track a mapset in this channel in veto mode", description="", pass_context=True)
async def veto(ctx, mapsetid: int, mapsethostdiscordid: int = None):
    if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]):
        if mapsethostdiscordid == None:
            mapsethostdiscordid = ctx.message.author.id
        await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 1)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="unveto", brief="Untrack a mapset in this channel in veto mode", description="", pass_context=True)
async def unveto(ctx, mapsetid: int):
    if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]):
        embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
        await modchecker.untrack(ctx, mapsetid, embed, None)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="untrack", brief="Untrack a mapset", description="", pass_context=True)
async def untrack(ctx, mapsetid: str, trackingtype: str = None):
    if await permissions.check(ctx.message.author.id):
        if trackingtype == "ranked":
            embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
            await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
        elif trackingtype == "all":
            await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ?",[str(mapsetid),]])
            await dbhandler.query(["DELETE FROM jsondata WHERE mapsetid = ?",[str(mapsetid),]])
            await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ?",[str(mapsetid),]])
            await ctx.send('`Mapset with that ID is no longer being tracked anywhere`')
        else:
            embed = None
            await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sublist", brief="List Tracked mapsets", description="", pass_context=True)
async def sublist(ctx):
    if await permissions.check(ctx.message.author.id):
        for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
            embed = await osuembed.mapset(await osuapi.get_beatmap(str(oneentry[0])))
            await ctx.send(content="mapsetid %s | channel <#%s> | mapsethostdiscordid %s \nroleid %s | mapsethostosuid %s | trackingtype %s" % (oneentry), embed=embed)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="verify", brief="Manual verification", description="", pass_context=True)
async def verify(ctx, osuid: str, discordid: int, preverify: str = None):
    if await permissions.check(ctx.message.author.id):
        await users.mverify(ctx, osuid, discordid, preverify)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="userdb", brief="Databased related commands", description="", pass_context=True)
async def userdb(ctx, command: str = None, mention: str = None):
    if await permissions.checkowner(ctx.message.author.id):
        await userdb(ctx, command, mention)
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="addgroupfeed", brief="Make a user bot admin", description="", pass_context=True)
async def addgroupfeed(ctx):
    if await permissions.check(ctx.message.author.id):
        await dbhandler.insert('groupfeedchannels', (str(ctx.channel.id),))
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="guildsync", brief="guildsync", description="", pass_context=True)
async def guildsync(ctx):
    if await permissions.check(ctx.message.author.id):
        await users.guildnamesync(ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="request", brief="Request a channel", description="", pass_context=True)
async def requestchannel(ctx, requesttype: str = "help", arg1: str = None, arg2: str = None):  # TODO: Add request
    if requesttype == "queue":
        await requests.queuechannel(client, ctx, arg1, appversion)
    elif requesttype == "mapset":
        await requests.mapsetchannel(client, ctx, arg1, arg2, appversion)
    elif requesttype == "queuehelp":
        await instructions.queuehelp(ctx, appversion)
    elif requesttype == "mapsethelp":
        await instructions.mapsethelp(ctx, appversion)
    else:
        await instructions.queuehelp(ctx, appversion)
        await instructions.mapsethelp(ctx, appversion)


@client.command(name="nuke", brief="Nuke a requested channel", description="", pass_context=True)
async def nuke(ctx):
    if await permissions.check(ctx.message.author.id):
        await requests.mapsetnuke(client, ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="open", brief="open a queue", description="", pass_context=True)
async def openq(ctx):
    await requests.queuesettings(client, ctx, "open")


@client.command(name="close", brief="close a queue", description="", pass_context=True)
async def closeq(ctx):
    await requests.queuesettings(client, ctx, "close")


@client.command(name="hide", brief="hide a queue", description="", pass_context=True)
async def hideq(ctx):
    await requests.queuesettings(client, ctx, "hide")


@client.command(name="add", brief="open a queue", description="", pass_context=True)
async def addm(ctx, discordid: int):
    await requests.modchannelsettings(client, ctx, "add", discordid)


@client.command(name="remove", brief="remove a user from mapset channel", description="", pass_context=True)
async def removem(ctx, discordid: int):
    await requests.modchannelsettings(client, ctx, "remove", discordid)


@client.command(name="abandon", brief="abandon and untrack the set", description="", pass_context=True)
async def abandon(ctx):
    await requests.abandon(client, ctx)


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


async def groupfeed_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await groupfeed.main(client)


# TODO: add rankfeed
# TODO: add background task to check user profiles every few hours. watch for username changes and also serve as mapping feed
# TODO: detect when channel is deleted and automatically untrack

client.loop.create_task(modchecker_background_loop())
client.loop.create_task(groupfeed_background_loop())
client.run(open("data/token.txt", "r+").read(), bot=True)
