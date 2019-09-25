#!/usr/bin/env python3

import discord
import os
from discord.ext import commands

from modules import db
from cogs.ModChecker import mod_checking_main_task
from modules import temp_functions

from modules.connections import database_file as database_file
from modules.connections import bot_token as bot_token


command_prefix = '\''
appversion = "a20190925-very-very-experimental"
client = commands.Bot(command_prefix=command_prefix, description='Seija %s' % (appversion))


initial_extensions = [
    'cogs.AprilFools', 
    'cogs.BotManagement', 
    'cogs.Docs', 
    'cogs.MapsetChannel',
    'cogs.MemberManagement',
    'cogs.MemberStatistics',
    'cogs.MemberVerification',
    'cogs.ModChecker',
    'cogs.Osu',
    'cogs.Queue', 
]

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            client.load_extension(extension)
        except Exception as e:
            print(e)


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


async def modchecker_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await mod_checking_main_task(client)


async def users_background_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await temp_functions.mapping_username_loop(client)


client.loop.create_task(modchecker_background_loop())
client.loop.create_task(users_background_loop())
client.run(bot_token)