#!/usr/bin/env python3

import discord
import asyncio
from discord.ext import commands
import os
import upsidedown

from modules import permissions
from modules import osuapi
from osuembed import osuembed
from modules import db
from modules import modchecker
from modules import users
from modules import mapchannel
from modules import queuechannel
from modules import docs
from modules import aprilfools
from modules import configmaker

from modules.connections import osu as osu
from modules.connections import database_file as database_file
from modules.connections import bot_token as bot_token


client = commands.Bot(command_prefix='\'')
client.remove_command('help')
appversion = "b20190812"


if not os.path.exists(database_file):
    db.query("CREATE TABLE users (user_id, osu_id, osu_username, osu_join_date, pp, country, ranked_maps_amount, no_sync)")
    db.query("CREATE TABLE user_events (osu_id, contents)")
    db.query("CREATE TABLE config (setting, parent, value, flag)")
    db.query("CREATE TABLE admins (user_id, permissions)")
    db.query("CREATE TABLE mod_posts (post_id, mapset_id, channel_id)")
    db.query("CREATE TABLE mod_tracking (mapset_id, channel_id, mode)")
    db.query("CREATE TABLE mod_tracking_pauselist (mapset_id, channel_id, mode)")
    db.query("CREATE TABLE mapset_status (mapset_id, map_id, channel_id, unresolved)")
    db.query("CREATE TABLE notices (timestamp, notice)")
    db.query("CREATE TABLE restricted_users (guild_id, osu_id)")
    db.query("CREATE TABLE queues (channel_id, user_id, guild_id)")
    db.query("CREATE TABLE mapset_channels (channel_id, role_id, user_id, mapset_id, guild_id)")
    db.query("CREATE TABLE name_backups (id, name)")


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    if not db.query("SELECT * FROM admins"):
        appinfo = await client.application_info()
        db.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), "1"]])
        print("Added %s to admin list" % (appinfo.owner.name))


@client.command(name="adminlist", brief="Show bot admin list", description="", pass_context=True)
async def adminlist(ctx):
    await ctx.send(embed=await permissions.get_admin_list())


@client.command(name="makeadmin", brief="Add a user to bot admin list", description="", pass_context=True)
async def makeadmin(ctx, user_id: str, perms = str("0")):
    if await permissions.check_owner(ctx.message.author.id):
        db.query(["INSERT INTO admins VALUES (?, ?)", [str(user_id), str(perms)]])
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="resetadminlist", brief="Scrap the current admin list and make the bot owner the bot admin", description="", pass_context=True)
async def resetadminlist(ctx,):
    appinfo = await client.application_info()
    if str(ctx.message.author.id) == str(appinfo.owner.id):
        db.query("DELETE FROM admins")
        db.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), str(1)]])
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="restart", brief="Restart the bot", description="", pass_context=True)
async def restart(ctx):
    if await permissions.check(ctx.message.author.id):
        await ctx.send("Restarting")
        quit()
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


@client.command(name="ts", brief="", description="", pass_context=True)
async def ts(ctx, *, string):
    embed = await modchecker.return_clickable(ctx.author, string)
    try:
        await ctx.send(embed=embed)
        await ctx.message.delete()
    except Exception as e:
        print(e)


@client.command(name="dbdump", brief="Perform a database dump", description="", pass_context=True)
async def dbdump(ctx):
    if await permissions.check(ctx.message.author.id):
        if ctx.message.channel.id == int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_db_dump_channel", str(ctx.guild.id)]]))[0][0]):
            await ctx.send(file=discord.File('data/maindb.sqlite3'))
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sql", brief="Executre an SQL query", description="", pass_context=True)
async def sql(ctx, *, query):
    if await permissions.check_owner(ctx.message.author.id):
        if len(query) > 0:
            response = db.query(query)
            await ctx.send(response)
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="verify", brief="Manually verify a user", description="", pass_context=True)
async def verify(ctx, lookup_type: str, osu_id: str, user_id: int, preverify: str = None):
    if await permissions.check(ctx.message.author.id):
        await users.mverify(ctx, lookup_type, osu_id, user_id, preverify)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="userdb", brief="Guild member and Database related commands", description="", pass_context=True)
async def userdb(ctx, command: str = None, mention: str = None):
    if await permissions.check_owner(ctx.message.author.id):
        if command == "mass_verify":
            await users.mass_verify(ctx, mention)
        elif command == "print_all":
            await users.print_all(ctx, mention)
        elif command == "server_check":
            await users.server_check(ctx, mention)
        else:
            pass
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="u", brief="", description="", pass_context=True)
async def uuu(ctx, command: str = None, mention: str = None):
    if await permissions.check(ctx.message.author.id):
        if command == "check_ranked":
            await users.check_ranked(ctx, mention)
        elif command == "check_experienced":
            await users.check_experienced(ctx, mention)
        elif command == "unverify":
            await users.unverify(ctx, mention)
        elif command == "roleless":
            await users.roleless(ctx, mention)
        else:
            pass
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="mapset", brief="Show mapset info", description="", pass_context=True)
async def mapset(ctx, mapset_id: str):
    result = await osu.get_beatmapset(s=mapset_id)
    embed = await osuembed.beatmapset(result)
    if embed:
        await ctx.send(embed=embed)
    else:
        await ctx.send(content='`No mapset found with that ID`')


@client.command(name="user", brief="Show osu user info", description="", pass_context=True)
async def user(ctx, *, username):
    result = await osu.get_user(u=username)
    embed = await osuembed.user(result)
    if embed:
        await ctx.send(embed=embed)
    else:
        await ctx.send(content='`No user found with that username`')


@client.command(name="help", brief="The pretty help command", description="", pass_context=True)
async def help(ctx, subhelp: str = None):  # TODO: rewrite help
    await docs.main(ctx, subhelp)


@client.command(name="forcetrack", brief="Force Track a mapset in the current channel", description="", pass_context=True)
async def forcetrack(ctx, mapset_id: str):
    if await permissions.check(ctx.message.author.id):
        if await modchecker.track(mapset_id, ctx.message.channel.id):
            try:
                mapsetobject = await osuapi.get_beatmaps(mapset_id)
                embed = await osuembed.mapset(mapsetobject)
                await ctx.send("Tracked", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
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
    if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):
        if await modchecker.track(mapset_id, ctx.message.channel.id, "veto"):
            try:
                mapsetobject = await osuapi.get_beatmaps(mapset_id)
                embed = await osuembed.mapset(mapsetobject)
                await ctx.send("Tracked in veto mode", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
        else:
            await ctx.send("Error")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode", description="", pass_context=True)
async def unveto(ctx, mapset_id: int):
    if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):   
        if await modchecker.untrack(mapset_id, ctx.message.channel.id):
            try:
                mapsetobject = await osuapi.get_beatmaps(mapset_id)
                embed = await osuembed.mapset(mapsetobject)
                await ctx.send("Untracked this", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
        else:
            await ctx.send("No tracking record found")
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="sublist", brief="List all tracked mapsets everywhere", description="", pass_context=True)
async def sublist(ctx):
    if await permissions.check(ctx.message.author.id):
        for oneentry in db.query("SELECT * FROM mod_tracking"):
            try:
                mapsetobject = await osuapi.get_beatmaps(str(oneentry[0]))
                embed = await osuembed.mapset(mapsetobject)
                await ctx.send(content="mapset_id %s | channel <#%s> | tracking_mode %s" % (oneentry), embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
    else:
        await ctx.send(embed=await permissions.error())
        
        
@client.command(name="chanlist", brief="List all mapset channel", description="", pass_context=True)
async def chanlist(ctx): # DELETE FROM mapset_channels WHERE role_id = ""
    if await permissions.check_owner(ctx.message.author.id):
        for oneentry in db.query("SELECT * FROM mapset_channels"):
            await ctx.send(content="channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s " % (oneentry))
    else:
        await ctx.send(embed=await permissions.error_owner())
        
        
@client.command(name="cv", brief="", description="", pass_context=True)
async def cv(ctx, *, user_id):
    if await permissions.check(ctx.message.author.id):
        osu_profile = (db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]]))
        if osu_profile:
            osu_id = osu_profile[0][0]
            result = await osu.get_user(u=osu_id)
            embed = await osuembed.user(result)
            await ctx.send("https://osu.ppy.sh/users/%s" % (osu_id), embed=embed)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="af", brief="", description="", pass_context=True)
async def af(ctx, action):
    if await permissions.check_owner(ctx.message.author.id):
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
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="demographics", brief="demographics", description="", pass_context=True)
async def demographics(ctx):
    if await permissions.check(ctx.message.author.id):
        await users.demographics(client, ctx)
    else:
        await ctx.send(embed=await permissions.error())


@client.command(name="from", brief="from", description="", pass_context=True)
async def users_from(ctx, *, country_code = "US"):
    await users.users_from(client, ctx, country_code)


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


@client.command(name="test", brief="test", description="", pass_context=True)
async def test(ctx, u):
    if await permissions.check_owner(ctx.message.author.id):
        print("test")
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="config", brief="", description="", pass_context=True)
async def config(ctx, setting, role_name):
    if await permissions.check_owner(ctx.message.author.id):
        await configmaker.role_setup(client, ctx, setting, role_name)
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="cfg", brief="", description="", pass_context=True)
async def cfg(ctx, setting, an_id):
    if await permissions.check_owner(ctx.message.author.id):
        await configmaker.cfg_setup(client, ctx, setting, an_id)
    else:
        await ctx.send(embed=await permissions.error_owner())


@client.command(name="open", brief="Open the queue", description="", pass_context=True)
async def openq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "open", params)


@client.command(name="close", brief="Close the queue", description="", pass_context=True)
async def closeq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "close", params)


@client.command(name="show", brief="Show the queue", description="", pass_context=True)
async def showq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "show", params)


@client.command(name="hide", brief="Hide the queue", description="", pass_context=True)
async def hideq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "hide", params)


@client.command(name="archive", brief="archive the queue", description="", pass_context=True)
async def archiveq(ctx, *params):
    await queuechannel.queuesettings(client, ctx, "archive", params)


@client.command(name="add", brief="Add a user in the current mapset channel", description="", pass_context=True)
async def addm(ctx, user_id: str):
    await mapchannel.mapset_channelsettings(client, ctx, "add", user_id)


@client.command(name="remove", brief="Remove a user from the current mapset channel", description="", pass_context=True)
async def removem(ctx, user_id: str):
    await mapchannel.mapset_channelsettings(client, ctx, "remove", user_id)


@client.command(name="abandon", brief="Abandon the mapset and untrack", description="", pass_context=True)
async def abandon(ctx):
    await mapchannel.abandon(client, ctx)


@client.command(name="setid", brief="", description="", pass_context=True)
async def set_mapset_id(ctx, mapset_id: int):
    await mapchannel.set_mapset_id(client, ctx, mapset_id)


@client.command(name="setowner", brief="", description="", pass_context=True)
async def set_owner_id(ctx, user_id: int):
    await mapchannel.set_owner_id(client, ctx, user_id)


@client.command(name="track", brief="", description="", pass_context=True)
async def track(ctx, tracking_mode = "classic"):
    await mapchannel.track_mapset(client, ctx, tracking_mode)


@client.command(name="untrack", brief="", description="", pass_context=True)
async def untrack(ctx):
    await mapchannel.untrack_mapset(client, ctx)


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


@client.event
async def on_guild_channel_delete(deleted_channel):
    await mapchannel.on_guild_channel_delete(client, deleted_channel)
    await queuechannel.on_guild_channel_delete(client, deleted_channel)


async def modchecker_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await modchecker.main(client)


async def users_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await users.mapping_username_loop(client)


client.loop.create_task(modchecker_background_loop())
client.loop.create_task(users_background_loop())
client.run(bot_token)
