#!/usr/bin/env python3

import discord
import asyncio
from discord.ext import commands
import os
import upsidedown

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
appversion = "b20190612"


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    if not os.path.exists('data/maindb.sqlite3'):
        appinfo = await client.application_info()
        await dbhandler.query("CREATE TABLE users (user_id, osu_id, osu_username, osu_join_date, pp, country, ranked_maps_amount, args)")
        await dbhandler.query("CREATE TABLE user_events (osu_id, contents)")
        await dbhandler.query("CREATE TABLE config (setting, parent, value, flag)")
        await dbhandler.query("CREATE TABLE admins (user_id, permissions)")
        await dbhandler.query("CREATE TABLE mod_posts (post_id, mapset_id, channel_id)")
        await dbhandler.query("CREATE TABLE mod_tracking (mapset_id, channel_id, mode)")
        await dbhandler.query("CREATE TABLE mapset_status (mapset_id, channel_id, unresolved)")
        await dbhandler.query("CREATE TABLE notices (timestamp, notice)")
        await dbhandler.query("CREATE TABLE queues (channel_id, user_id, guild_id)")
        await dbhandler.query("CREATE TABLE mapset_channels (channel_id, role_id, user_id, mapset_id, guild_id)")
        await dbhandler.query("CREATE TABLE name_backups (id, name)")
        await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), "1"]])


@client.command(name="adminlist", brief="Show bot admin list", description="", pass_context=True)
async def adminlist(ctx):
    await ctx.send(embed=await permissions.adminlist())


@client.command(name="makeadmin", brief="Add a user to bot admin list", description="", pass_context=True)
async def makeadmin(ctx, user_id: str, perms = str("0")):
    appinfo = await client.application_info()
    if await permissions.checkowner(ctx.message.author.id) or await permissions.checkowner(str(appinfo.owner.id)):
        await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(user_id), str(perms)]])
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


@client.command(name="update", brief="Update the bot", description="it just does git pull", pass_context=True)
async def update(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Updating.")
        os.system('git pull')
        quit()
        # exit()
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="echo", brief="Echo a string", description="", pass_context=True)
async def echo(ctx, *, string):
    if await permissions.check(ctx.message.author.id):
        await ctx.message.delete()
        await ctx.send(upsidedown.transform(string))
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="dbdump", brief="Perform a database dump", description="", pass_context=True)
async def dbdump(ctx):
    if await permissions.check(ctx.message.author.id):
        if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_db_dump_channel", str(ctx.guild.id)]]))[0][0]):
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


@client.command(name="verify", brief="Manually verify a user", description="", pass_context=True)
async def verify(ctx, osu_id: str, user_id: int, preverify: str = None):
    if await permissions.check(ctx.message.author.id):
        await users.mverify(ctx, osu_id, user_id, preverify)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="userdb", brief="Guild member and Database related commands", description="", pass_context=True)
async def userdb(ctx, command: str = None, mention: str = None):
    if await permissions.checkowner(ctx.message.author.id):
        if command == "check_ranked":
            await users.check_ranked(ctx, mention)
        elif command == "mass_verify":
            await users.mass_verify(ctx, mention)
        elif command == "print_all":
            await users.print_all(ctx, mention)
        elif command == "server_check":
            await users.server_check(ctx, mention)
        else:
            pass
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="mapset", brief="Show mapset info", description="", pass_context=True)
async def mapset(ctx, mapset_id: str, text: str = None):
    embed = await osuembed.mapset(await osuapi.get_beatmaps(mapset_id))
    if embed:
        await ctx.send(content=text, embed=embed)
    else:
        await ctx.send(content='`No mapset found with that ID`')


@client.command(name="user", brief="Show osu user info", description="", pass_context=True)
async def user(ctx, *, username):
    embed = await osuembed.osuprofile(await osuapi.get_user(username))
    if embed:
        await ctx.send(embed=embed)
        # await ctx.message.delete()
    else:
        await ctx.send(content='`No user found with that username`')


@client.command(name="help", brief="The pretty help command", description="", pass_context=True)
async def help(ctx, subhelp: str = None):  # TODO: rewrite help
    await docs.main(ctx, subhelp)


@client.command(name="forcetrack", brief="Force Track a mapset in the current channel", description="", pass_context=True)
async def forcetrack(ctx, mapset_id: str):
    if await permissions.check(ctx.message.author.id):
        if await modchecker.track(mapset_id, ctx.message.channel.id):
            await ctx.send("Tracked", embed=await osuembed.mapset(await osuapi.get_beatmaps(mapset_id)))
        else:
            await ctx.send("Error")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="forceuntrack", brief="Force untrack a mapset in the current channel", description="", pass_context=True)
async def forceuntrack(ctx, mapset_id: str):
    if await permissions.check(ctx.message.author.id):
        if await modchecker.untrack(mapset_id, ctx.message.channel.id):
            await ctx.send("Untracked")
        else:
            await ctx.send("No tracking record found")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="veto", brief="Track a mapset in the current channel in veto mode", description="", pass_context=True)
async def veto(ctx, mapset_id: int):
    if await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):
        if await modchecker.track(mapset_id, ctx.message.channel.id, "1"):
            await ctx.send("Tracked in veto mode", embed=await osuembed.mapset(await osuapi.get_beatmaps(mapset_id)))
        else:
            await ctx.send("Error")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode", description="", pass_context=True)
async def unveto(ctx, mapset_id: int):
    if await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):   
        if await modchecker.untrack(mapset_id, ctx.message.channel.id):
            embed = await osuembed.mapset(await osuapi.get_beatmaps(mapset_id))
            await ctx.send("Untracked this", embed=embed)
        else:
            await ctx.send("No tracking record found")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sublist", brief="List all tracked mapsets everywhere", description="", pass_context=True)
async def sublist(ctx):
    if await permissions.check(ctx.message.author.id):
        for oneentry in await dbhandler.query("SELECT * FROM mod_tracking"):
            embed = await osuembed.mapset(await osuapi.get_beatmaps(str(oneentry[0])))
            await ctx.send(content="mapset_id %s | channel <#%s> | tracking_mode %s" % (oneentry), embed=embed)
    else:
        await ctx.send(embed=await permissions.error())
        
        
@client.command(name="chanlist", brief="List all mapset channel", description="", pass_context=True)
async def chanlist(ctx):
    if await permissions.checkowner(ctx.message.author.id):
        for oneentry in await dbhandler.query("SELECT * FROM mapset_channels"):
            await ctx.send(content="channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s | " % (oneentry))
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="af", brief="", description="", pass_context=True)
async def af(ctx, action):
    if await permissions.checkowner(ctx.message.author.id):
        await ctx.message.delete()
        if action == "apply":
            await aprilfools.apply_guild(client, ctx)
            await aprilfools.apply_channels(client, ctx)
            await asyncio.sleep(10)
            await aprilfools.apply_roles(client, ctx)
            #await aprilfools.rotate_logo(client, ctx)
            try:
                await ctx.send(file=discord.File("data/imsorry.png"))
            except:
                await ctx.send(":ok_hand:")
        elif action == "restore":
            await aprilfools.restore_guild(client, ctx)
            await aprilfools.restore_channels(client, ctx)
            await asyncio.sleep(10)
            await aprilfools.restore_roles(client, ctx)
            #await aprilfools.rotate_logo(client, ctx)
            await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.ownererror())


@client.command(name="demographics", brief="demographics", description="", pass_context=True)
async def demographics(ctx):
    if await permissions.check(ctx.message.author.id):
        await users.demographics(client, ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="request", brief="Request ether a queue or mod channel", description="", pass_context=True)
async def requestchannel(ctx, requesttype: str = "help", arg1: str = None, arg2: str = None):  # TODO: Add request
    if requesttype == "queue":
        await queuechannel.make_queue_channel(client, ctx, arg1)
    elif requesttype == "mapset":
        await mapchannel.make_mapset_channel(client, ctx, arg1, arg2)


@client.command(name="nuke", brief="Nuke a requested channel", description="", pass_context=True)
async def nuke(ctx):
    if await permissions.check(ctx.message.author.id):
        await mapchannel.nuke_mapset_channel(client, ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="open", brief="Open the queue", description="", pass_context=True)
async def openq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "open", params)


@client.command(name="close", brief="Close the queue", description="", pass_context=True)
async def closeq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "close", params)


@client.command(name="hide", brief="Hide the queue", description="", pass_context=True)
async def hideq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "hide", params)


@client.command(name="add", brief="Add a user in the current mapset channel", description="", pass_context=True)
async def addm(ctx, user_id: int):
    await mapchannel.mapset_channelsettings(client, ctx, "add", user_id)


@client.command(name="remove", brief="Remove a user from the current mapset channel", description="", pass_context=True)
async def removem(ctx, user_id: int):
    await mapchannel.mapset_channelsettings(client, ctx, "remove", user_id)


@client.command(name="abandon", brief="Abandon the mapset and untrack", description="", pass_context=True)
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
