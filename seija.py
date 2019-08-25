#!/usr/bin/env python3

import discord
import asyncio
from discord.ext import commands
import os
import upsidedown

from modules import permissions
from osuembed import osuembed
from modules import db
from modules import modchecker
from modules import users
from modules import user_verification
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
appversion = "b20190826"


if not os.path.exists(database_file):
    db.query("CREATE TABLE users (user_id, osu_id, osu_username, osu_join_date, pp, country, ranked_maps_amount, no_sync)")
    db.query("CREATE TABLE user_event_history (osu_id, event_id, channel_id)")
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
    await ctx.send(embed=permissions.get_admin_list())


@client.command(name="makeadmin", brief="Add a user to bot admin list", description="", pass_context=True)
async def makeadmin(ctx, user_id: str, perms = str("0")):
    if permissions.check_owner(ctx.message.author.id):
        db.query(["INSERT INTO admins VALUES (?, ?)", [str(user_id), str(perms)]])
        await ctx.send(":ok_hand:")
    else:
        await ctx.send(embed=permissions.error_owner())


@client.command(name="restart", brief="Restart the bot", description="", pass_context=True)
async def restart(ctx):
    if permissions.check(ctx.message.author.id):
        await ctx.send("Restarting")
        quit()
        quit()
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="update", brief="Update the bot", description="it just does git pull", pass_context=True)
async def update(ctx):
    if permissions.check(ctx.message.author.id):
        await ctx.send("Updating.")
        os.system('git pull')
        quit()
        # exit()
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="echo", brief="Echo a string upside down", description="", pass_context=True)
async def echo(ctx, *, string):
    if permissions.check(ctx.message.author.id):
        await ctx.message.delete()
        await ctx.send(upsidedown.transform(string))
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="ts", brief="Send an osu editor clickable timestamp", description="Must start with a timestamp", pass_context=True)
async def ts(ctx, *, string):
    embed = await modchecker.return_clickable(ctx.author, string)
    try:
        await ctx.send(embed=embed)
        await ctx.message.delete()
    except Exception as e:
        print(e)


@client.command(name="dbdump", brief="Perform a database dump", description="", pass_context=True)
async def dbdump(ctx):
    if permissions.check(ctx.message.author.id):
        if ctx.message.channel.id == int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_db_dump_channel", str(ctx.guild.id)]]))[0][0]):
            await ctx.send(file=discord.File(database_file))
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="sql", brief="Executre an SQL query", description="", pass_context=True)
async def sql(ctx, *, query):
    if permissions.check_owner(ctx.message.author.id):
        if len(query) > 0:
            response = db.query(query)
            await ctx.send(response)
    else:
        await ctx.send(embed=permissions.error_owner())


@client.command(name="verify", brief="Manually verify a user", description="", pass_context=True)
async def verify(ctx, lookup_type: str, osu_id: str, user_id: int, preverify: str = None):
    if permissions.check(ctx.message.author.id):
        await user_verification.manually_verify(ctx, lookup_type, osu_id, user_id, preverify)
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="mass_verify", brief="Insert multiple users into the database from a csv file", description="", pass_context=True)
async def mass_verify(ctx, mention_users: str = None):
    if permissions.check_owner(ctx.message.author.id):
        await user_verification.mass_verify(ctx, mention_users)
    else:
        await ctx.send(embed=permissions.error_owner())


@client.command(name="print_all", brief="Print all users and their profiles from db", description="", pass_context=True)
async def print_all(ctx, mention_users: str = None):
    if permissions.check_owner(ctx.message.author.id):
        await users.print_all(ctx, mention_users)
    else:
        await ctx.send(embed=permissions.error_owner())

    
@client.command(name="get_users_not_in_db", brief="Get a list of users who are not in db", description="", pass_context=True)
async def get_users_not_in_db(ctx, mention_users: str = None):
    if permissions.check_owner(ctx.message.author.id):
        await users.get_users_not_in_db(ctx, mention_users)
    else:
        await ctx.send(embed=permissions.error_owner())


@client.command(name="check_ranked", brief="Return ranked mappers who don't have the role", description="", pass_context=True)
async def check_ranked(ctx):
    if permissions.check(ctx.message.author.id):
        await users.check_ranked_amount_by_role(ctx, 1, "guild_mapper_role")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="check_experienced", brief="Return experienced mappers who don't have the role", description="", pass_context=True)
async def check_experienced(ctx):
    if permissions.check(ctx.message.author.id):
        await users.check_ranked_amount_by_role(ctx, 10, "guild_ranked_mapper_role")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="unverify", brief="Unverify a member and delete it from db", description="", pass_context=True)
async def unverify(ctx, user_id):
    if permissions.check(ctx.message.author.id):
        await user_verification.unverify(ctx, user_id)
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="roleless", brief="Get a list of members without a role", description="", pass_context=True)
async def roleless(ctx, lookup_in_db: str = None):
    if permissions.check(ctx.message.author.id):
        await users.roleless(ctx, lookup_in_db)
    else:
        await ctx.send(embed=permissions.error())


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


@client.command(name="help", brief="Help command", description="", pass_context=True)
async def help(ctx, subhelp = None):
    await docs.main(ctx, subhelp)


@client.command(name="dashboard", brief="The pretty help command", description="", pass_context=True)
async def dashboard(ctx):
    if permissions.check(ctx.message.author.id):
        await ctx.send_help()
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="forcetrack", brief="Force Track a mapset in the current channel", description="", pass_context=True)
async def forcetrack(ctx, mapset_id: str):
    if permissions.check(ctx.message.author.id):
        if await modchecker.track(mapset_id, ctx.message.channel.id):
            try:
                result = await osu.get_beatmapset(s=mapset_id)
                embed = await osuembed.beatmapset(result)
                await ctx.send("Tracked", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
        else:
            await ctx.send("Error")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="forceuntrack", brief="Force untrack a mapset in the current channel", description="", pass_context=True)
async def forceuntrack(ctx, mapset_id: str):
    if permissions.check(ctx.message.author.id):
        if await modchecker.untrack(mapset_id, ctx.message.channel.id):
            await ctx.send("Untracked")
        else:
            await ctx.send("No tracking record found")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="veto", brief="Track a mapset in the current channel in veto mode", description="", pass_context=True)
async def veto(ctx, mapset_id: int):
    if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):
        if await modchecker.track(mapset_id, ctx.message.channel.id, "veto"):
            try:
                result = await osu.get_beatmapset(s=mapset_id)
                embed = await osuembed.beatmapset(result)
                await ctx.send("Tracked in veto mode", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
        else:
            await ctx.send("Error")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode", description="", pass_context=True)
async def unveto(ctx, mapset_id: int):
    if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):   
        if await modchecker.untrack(mapset_id, ctx.message.channel.id):
            try:
                result = await osu.get_beatmapset(s=mapset_id)
                embed = await osuembed.beatmapset(result)
                await ctx.send("Untracked this", embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
        else:
            await ctx.send("No tracking record found")
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="sublist", brief="List all tracked mapsets everywhere", description="", pass_context=True)
async def sublist(ctx):
    if permissions.check(ctx.message.author.id):
        for oneentry in db.query("SELECT * FROM mod_tracking"):
            try:
                result = await osu.get_beatmapset(s=str(oneentry[0]))
                embed = await osuembed.beatmapset(result)
                await ctx.send(content="mapset_id %s | channel <#%s> | tracking_mode %s" % (oneentry), embed=embed)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
    else:
        await ctx.send(embed=permissions.error())
        
        
@client.command(name="chanlist", brief="List all mapset channel", description="", pass_context=True)
async def chanlist(ctx):
    if permissions.check(ctx.message.author.id):
        for oneentry in db.query("SELECT * FROM mapset_channels"):
            await ctx.send(content="channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s " % (oneentry))
    else:
        await ctx.send(embed=permissions.error())
        
        
@client.command(name="cv", brief="Check which osu account is a discord account linked to", description="", pass_context=True)
async def cv(ctx, *, user_id):
    if permissions.check(ctx.message.author.id):
        osu_profile = (db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]]))
        if osu_profile:
            osu_id = osu_profile[0][0]
            result = await osu.get_user(u=osu_id)
            embed = await osuembed.user(result)
            await ctx.send("https://osu.ppy.sh/users/%s" % (osu_id), embed=embed)
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="af", brief="April fools commands", description="", pass_context=True)
async def af(ctx, action):
    if permissions.check_owner(ctx.message.author.id):
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
        await ctx.send(embed=permissions.error_owner())


@client.command(name="demographics", brief="Send server demographics stats", description="", pass_context=True)
async def demographics(ctx):
    if permissions.check(ctx.message.author.id):
        await users.demographics(client, ctx)
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="from", brief="Get a list of members from specified country", description="Takes Alpha-2, Alpha-3 codes and full country names.", pass_context=True)
async def users_from(ctx, *, country_code = "US"):
    await users.users_from(client, ctx, country_code)


@client.command(name="request", brief="Request ether a queue or mod channel", description="", pass_context=True)
async def requestchannel(ctx, requesttype: str = "help", arg1: str = None, arg2: str = None):
    if requesttype == "queue":
        await queuechannel.make_queue_channel(client, ctx, arg1)
    elif requesttype == "mapset":
        await mapchannel.make_mapset_channel(client, ctx, arg1, arg2)


@client.command(name="nuke", brief="Nuke a requested mapset channel", description="", pass_context=True)
async def nuke(ctx):
    if permissions.check(ctx.message.author.id):
        await mapchannel.nuke_mapset_channel(client, ctx)
    else:
        await ctx.send(embed=permissions.error())


@client.command(name="config", brief="Insert a role related config in db for the current guild", description="", pass_context=True)
async def config(ctx, setting, role_name):
    if permissions.check_owner(ctx.message.author.id):
        await configmaker.role_setup(client, ctx, setting, role_name)
    else:
        await ctx.send(embed=permissions.error_owner())


@client.command(name="cfg", brief="Insert a config in db for the current guild", description="", pass_context=True)
async def cfg(ctx, setting, an_id):
    if permissions.check_owner(ctx.message.author.id):
        await configmaker.cfg_setup(client, ctx, setting, an_id)
    else:
        await ctx.send(embed=permissions.error_owner())


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


@client.command(name="archive", brief="Archive the queue", description="", pass_context=True)
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


@client.command(name="setid", brief="Set a mapset id for this channel", description="Useful if you created this channel without setting an id", pass_context=True)
async def set_mapset_id(ctx, mapset_id: int):
    await mapchannel.set_mapset_id(client, ctx, mapset_id)


@client.command(name="setowner", brief="Transfer set ownership to another discord account", description="user_id can only be that discord account's id", pass_context=True)
async def set_owner_id(ctx, user_id: int):
    await mapchannel.set_owner_id(client, ctx, user_id)


@client.command(name="track", brief="Track the mapset in this channel", description="", pass_context=True)
async def track(ctx, tracking_mode = "classic"):
    await mapchannel.track_mapset(client, ctx, tracking_mode)


@client.command(name="untrack", brief="Untrack everything in this channel", description="", pass_context=True)
async def untrack(ctx):
    await mapchannel.untrack_mapset(client, ctx)


@client.event
async def on_message(message):
    await user_verification.on_message(client, message)
    await client.process_commands(message)


@client.event
async def on_member_join(member):
    await user_verification.on_member_join(client, member)
    await queuechannel.on_member_join(client, member)
    await mapchannel.on_member_join(client, member)


@client.event
async def on_member_remove(member):
    await user_verification.on_member_remove(client, member)
    await queuechannel.on_member_remove(client, member)
    await mapchannel.on_member_remove(client, member)


@client.event
async def on_guild_channel_delete(deleted_channel):
    await mapchannel.on_guild_channel_delete(client, deleted_channel)
    await queuechannel.on_guild_channel_delete(client, deleted_channel)


@client.event
async def on_user_update(before, after):
    await users.on_user_update(client, before, after)


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
