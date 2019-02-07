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
from modules import groupelements
from modules import feedchecker
from modules import requests
from modules import instructions

client = commands.Bot(command_prefix='\'')
client.remove_command('help')
appversion = "b20190207"

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
		await dbhandler.query("CREATE TABLE modchannels (channelid, roleid, discordid, guildid)")
		await dbhandler.query(["INSERT INTO admins VALUES (?, ?)", [str(appinfo.owner.id), "1"]])

@client.command(name="adminlist", brief="Show bot admin list", description="", pass_context=True)
async def adminlist(ctx):
	await ctx.send(embed=await permissions.adminlist())

@client.command(name="makeadmin", brief="Make a user bot admin", description="", pass_context=True)
async def makeadmin(ctx, discordid: str):
	if await permissions.checkowner(ctx.message.author.id) :
		await dbhandler.insert('admins', (str(discordid), "0"))
		await ctx.send(":ok_hand:")
	else :
		await ctx.send(embed=await permissions.ownererror())

@client.command(name="restart", brief="Restart the bot", description="", pass_context=True)
async def restart(ctx):
	if await permissions.check(ctx.message.author.id) :
		await ctx.send("Restarting")
		quit()
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="gitpull", brief="Update the bot", description="it just does git pull", pass_context=True)
async def gitpull(ctx):
	if await permissions.check(ctx.message.author.id) :
		await ctx.send("Updating.")
		os.system('git pull')
		quit()
		#exit()
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="dbdump", brief="Database Dump", description="", pass_context=True)
async def dbdump(ctx):
	if await permissions.check(ctx.message.author.id) :
		if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["dbdumpchannelid", str(ctx.guild.id)]]))[0][0]):
			await ctx.send(file=discord.File('data/maindb.sqlite3'))
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="sql", brief="Executre an SQL query", description="", pass_context=True)
async def sql(ctx, *, query):
	if await permissions.checkowner(ctx.message.author.id) :
		if len(query) > 0:
			response = await dbhandler.query(query)
			await ctx.send(response)
	else :
		await ctx.send(embed=await permissions.ownererror())

@client.command(name="mapset", brief="Show a mapset", description="", pass_context=True)
async def mapset(ctx, mapsetid: str, text: str = None):
	if await permissions.check(ctx.message.author.id) :
		embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
		if embed:
			await ctx.send(content=text, embed=embed)
			#await ctx.delete_message(ctx.message)
		else:
			await ctx.send(content='`No mapset found with that ID`')
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="user", brief="Show a user", description="", pass_context=True)
async def user(ctx, *, username):
	if await permissions.check(ctx.message.author.id) :
		embed = await osuembed.osuprofile(await osuapi.get_user(username))
		if embed:
			await ctx.send(embed=embed)
			#await ctx.delete_message(ctx.message)
		else:
			await ctx.send(content='`No user found with that username`')
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="help", brief="Help for users", description="", pass_context=True)
async def help(ctx, admin: str = None): # TODO: rewrite help
	await instructions.help(ctx, admin, appversion)

@client.command(name="track", brief="Track a mapset", description="", pass_context=True)
async def track(ctx, mapsetid: str, mapsethostdiscordid: str = None):
	if await permissions.check(ctx.message.author.id) :
		if mapsethostdiscordid == None:
			mapsethostdiscordid = ctx.message.author.id
		await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 0)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="veto", brief="Track a mapset in this channel in veto mode", description="", pass_context=True)
async def veto(ctx, mapsetid: int, mapsethostdiscordid: int = None):
	if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]) :
		if mapsethostdiscordid == None:
			mapsethostdiscordid = ctx.message.author.id
		await modchecker.track(ctx, str(mapsetid), str(mapsethostdiscordid), 1)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="unveto", brief="Untrack a mapset in this channel in veto mode", description="", pass_context=True)
async def unveto(ctx, mapsetid: int):
	if ctx.message.channel.id == int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["vetochannelid", str(ctx.guild.id)]]))[0][0]) :
		embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
		await modchecker.untrack(ctx, mapsetid, embed, None)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="untrack", brief="Untrack a mapset", description="", pass_context=True)
async def untrack(ctx, mapsetid: str, trackingtype: str = None):
	if await permissions.check(ctx.message.author.id) :
		if trackingtype == "ranked":
			embed = await osuembed.mapset(await osuapi.get_beatmap(mapsetid))
			await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
		elif trackingtype == "all":
			where = [
				['mapsetid', str(mapsetid)]
			]
			await dbhandler.delete('modtracking', where)
			await dbhandler.delete('jsondata', where)
			await dbhandler.delete('modposts', where)
			await ctx.send('`Mapset with that ID is no longer being tracked anywhere`')
		else:
			embed = None
			await modchecker.untrack(ctx, mapsetid, embed, trackingtype)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="sublist", brief="List Tracked mapsets", description="", pass_context=True)
async def sublist(ctx):
	if await permissions.check(ctx.message.author.id) :
		for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
			embed = await osuembed.mapset(await osuapi.get_beatmap(str(oneentry[0])))
			await ctx.send(content="mapsetid %s | channel <#%s> | mapsethostdiscordid %s \nroleid %s | mapsethostosuid %s | trackingtype %s" % (oneentry), embed=embed)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="verify", brief="Manual verification", description="", pass_context=True)
async def verify(ctx, osuid: str, discordid: int, preverify: str = None):
	if await permissions.check(ctx.message.author.id) :
		try:
			if preverify == "preverify":
				await users.verify(ctx.message.channel, str(discordid), None, osuid, "Preverified: %s" % (str(discordid)))
			else:
				role = discord.utils.get(ctx.message.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(ctx.guild.id)]]))[0][0]))
				await users.verify(ctx.message.channel, ctx.guild.get_member(discordid), role, osuid, "Manually Verified: %s" % (ctx.guild.get_member(discordid).name))
		except Exception as e:
			print(time.strftime('%X %x %Z'))
			print("in verify")
			print(e)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="userdb", brief="Databased related commands", description="", pass_context=True)
async def userdb(ctx, command: str = None, mention: str = None): 
	if await permissions.checkowner(ctx.message.author.id) :
		try:
			if command == "printall":
				if mention == "m":
					tag = "<@%s> / %s"
				else:
					tag = "%s / %s"
				for oneuser in await dbhandler.query("SELECT * FROM users"):
					embed = await osuembed.osuprofile(await osuapi.get_user(oneuser[1]))
					if embed:
						await ctx.send(content=tag % (oneuser[0], oneuser[2]), embed=embed)
			elif command == "massverify":
				userarray = open("data/users.csv", encoding="utf8").read().splitlines()
				if mention == "m":
					tag = "Preverified: <@%s>"
				else:
					tag = "Preverified: %s"
				for oneuser in userarray:
					uzer = oneuser.split(',')
					await users.verify(ctx.message.channel, str(uzer[1]), None, "u/%s" % (uzer[0]), tag % (str(uzer[1])))
					await asyncio.sleep(1)
			elif command == "servercheck":
				responce = "These users are not in my database:\n"
				count = 0 
				for member in ctx.guild.members:
					if not member.bot:
						if not await dbhandler.query(["SELECT osuid FROM users WHERE discordid = ?", [str(member.id),]]):
							count += 1
							if mention == "m":
								responce += ("<@%s>\n" % (str(member.id)))
							else:
								responce += ("\"%s\" %s\n" % (str(member.display_name), str(member.id)))
							if count > 40:
								count = 0
								responce += ""
								await ctx.send(responce)
								responce = "\n"
				responce += ""
				await ctx.send(responce)
		except Exception as e:
			print(time.strftime('%X %x %Z'))
			print("in userdb")
			print(e)
	else :
		await ctx.send(embed=await permissions.ownererror())

@client.command(name="groupfeed", brief="Make a user bot admin", description="", pass_context=True)
async def groupfeed(ctx):
	if await permissions.check(ctx.message.author.id) :
		await dbhandler.insert('groupfeedchannels', (str(ctx.channel.id),))
		await ctx.send(":ok_hand:")
	else :
		await ctx.send(embed=await permissions.error())
		await ctx.send(embed=await permissions.ownererror())

@client.command(name="guildsync", brief="guildsync", description="", pass_context=True)
async def guildsync(ctx):
	if await permissions.check(ctx.message.author.id) :
		await users.guildnamesync(ctx)
	else :
		await ctx.send(embed=await permissions.error())

@client.command(name="request", brief="Request a channel", description="", pass_context=True)
async def requestchannel(ctx, requesttype: str = "help", arg1: str = None, arg2: str = None): # TODO: Add request
	if requesttype == "queue":
		await requests.queuechannel(client, ctx, arg1)
	elif requesttype == "mapset":
		await requests.mapsetchannel(client, ctx, arg1, arg2)
	else:
		await instructions.request(ctx)

@client.command(name="nuke", brief="Nuke a requested channel", description="", pass_context=True)
async def nuke(ctx): # TODO:
	if await permissions.check(ctx.message.author.id) :
		await requests.mapsetnuke(client, ctx)
	else :
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
	await ctx.send("not yet added")


#####################################################################################################

@client.event
async def on_message(message):
	if message.author.id != client.user.id :
		try:
			verifychannelid = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(message.guild.id)]])
			if verifychannelid:
				if message.channel.id == int(verifychannelid[0][0]) :
					split_message = []
					if '/' in message.content:
						split_message = message.content.split('/')
					role = discord.utils.get(message.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(message.guild.id)]]))[0][0]))

					if 'https://osu.ppy.sh/u' in message.content:
						osulookup = "u/%s" % (split_message[4].split(' ')[0])
						verifyattempt = await users.verify(message.channel, message.author, role, osulookup, "Verified: %s" % (message.author.name))
						if not verifyattempt:
							await message.channel.send('verification failure, I can\'t find any profile from that link. If you are restricted, link any of your recently uploaded maps (new website only).')
					elif 'https://osu.ppy.sh/beatmapsets/' in message.content:
						osulookup = "s/%s" % (split_message[4].split('#')[0])
						verifyattempt = await users.verify(message.channel, message.author, role, osulookup, "Verified through mapset: %s" % (message.author.name))
						if not verifyattempt:
							await message.channel.send('verification failure, I can\'t find any map with that link')
					elif message.content.lower() == 'yes':
						osulookup = "u/%s" % (message.author.name)
						verifyattempt = await users.verify(message.channel, message.author, role, osulookup, "Verified: %s" % (message.author.name))
						if not verifyattempt:
							await message.channel.send('verification failure, your discord username does not match a username of any osu account. possible reason can be that you changed your discord username before typing `yes`. In this case, link your profile.')
					elif 'https://ripple.moe/u' in message.content:
						await message.channel.send('ugh, this bot does not do automatic verification from ripple, please ping Kyuunex')
					elif 'https://osu.gatari.pw/u' in message.content:
						await message.channel.send('ugh, this bot does not do automatic verification from gatari, please ping Kyuunex')
		except Exception as e:
			print(time.strftime('%X %x %Z'))
			print("in on_message")
			print(e)
	await client.process_commands(message)

@client.event
async def on_member_join(member):
	try:
		guildverifychannel = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(member.guild.id)]])
		if guildverifychannel:
			join_channel_object = await utils.get_channel(client.get_all_channels(), int((guildverifychannel)[0][0]))
			lookupuser = await dbhandler.query(["SELECT osuid FROM users WHERE discordid = ?", [str(member.id),]])
			if lookupuser:
				print("user %s joined with osuid %s" % (str(member.id),str(lookupuser[0][0])))
				role = discord.utils.get(member.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(member.guild.id)]]))[0][0]))
				osulookup = "u/%s" % (lookupuser[0][0])
				verifyattempt = await users.verify(join_channel_object, member, role, osulookup, "Welcome aboard %s! Since we know who you are, I have automatically verified you. Enjoy your stay!" % (member.mention))

				if not verifyattempt:
					await join_channel_object.send("Hello %s. It seems like you are in my database but the profile I know of you is restricted. If this is correct, please link any of your uploaded maps (new website only) and I'll verify you instantly. If this is not correct, tag Kyuunex." % (member.mention))
			else:
				await join_channel_object.send("Welcome %s! We have a verification system in this server so we know who you are, give you appropriate roles and keep raids/spam out." % (member.mention))
				osuprofile = await osuapi.get_user(member.name)
				if osuprofile:
					await join_channel_object.send(content='Is this your osu profile? If yes, type `yes`, if not, link your profile.', embed=await osuembed.osuprofile(osuprofile))
				else :
					await join_channel_object.send('Please post a link to your osu profile and I will verify you instantly.')
	except Exception as e:
		print(time.strftime('%X %x %Z'))
		print("in on_member_join")
		print(e)

@client.event
async def on_member_remove(member):
	try:
		guildverifychannel = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(member.guild.id)]])
		if guildverifychannel:
			join_channel_object = await utils.get_channel(client.get_all_channels(), int((guildverifychannel)[0][0]))
			await join_channel_object.send("%s left this server. Godspeed!" % (str(member.name)))
	except Exception as e:
		print(time.strftime('%X %x %Z'))
		print("in on_member_join")
		print(e)

async def modchecker_background_loop():
	await client.wait_until_ready()
	while not client.is_closed():
		try:
			await asyncio.sleep(120)
			for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
				channel = await utils.get_channel(client.get_all_channels(), int(oneentry[1]))
				mapsetid = oneentry[0]
				trackingtype = str(oneentry[5])
				print(time.strftime('%X %x %Z')+' | '+oneentry[0])
				
				beatmapsetdiscussionobject = await osuwebapipreview.discussion(mapsetid)
				if beatmapsetdiscussionobject:
					newevents = await modchecker.compare(beatmapsetdiscussionobject["beatmapset"]["discussions"], mapsetid)
					
					if newevents:
						for newevent in newevents:
							newevent = newevents[newevent]
							if newevent:
								for subpostobject in newevent['posts']:
									if not subpostobject['system']:
										if not await dbhandler.query(["SELECT postid FROM modposts WHERE postid = ?", [subpostobject['id'],]]):
											await dbhandler.insert('modposts', (subpostobject['id'], mapsetid, newevent["beatmap_id"], subpostobject['user_id'], subpostobject['message']))
											modtopost = await osuembed.modpost(subpostobject, beatmapsetdiscussionobject, newevent, trackingtype)
											if modtopost:
												await channel.send(embed=modtopost)
				else:
					print(time.strftime('%X %x %Z')+" | Possible connection issues")
					await asyncio.sleep(300)
				await asyncio.sleep(120)
			await asyncio.sleep(1800)
		except Exception as e:
			print(time.strftime('%X %x %Z'))
			print("in background_loop")
			print(e)
			print(newevent)
			await asyncio.sleep(300)

async def groupfeed_background_loop():
	await client.wait_until_ready()
	while not client.is_closed():
		try:
			print(time.strftime('%X %x %Z')+' | groupfeed')
			groupfeedchannellist = await dbhandler.query("SELECT channelid FROM groupfeedchannels")
			if groupfeedchannellist:
				await groupelements.groupcheck(client, groupfeedchannellist, "7", "Quality Assurance Team")
				await asyncio.sleep(5)
				await groupelements.groupcheck(client, groupfeedchannellist, "28", "Beatmap Nomination Group")
				await asyncio.sleep(120)
				await groupelements.groupcheck(client, groupfeedchannellist, "4", "Global Moderation Team")
				#await asyncio.sleep(120)
				#await groupelements.groupcheck(client, groupfeedchannellist, "11", "Developers")
				#await asyncio.sleep(120)
				#await groupelements.groupcheck(client, groupfeedchannellist, "16", "osu! Alumni")
				#await asyncio.sleep(120)
				#await groupelements.groupcheck(client, groupfeedchannellist, "22", "Support Team Redux")
			await asyncio.sleep(1600)
		except Exception as e:
			print(time.strftime('%X %x %Z'))
			print("in groupfeed_background_loop")
			print(e)
			await asyncio.sleep(3600)

# TODO: add rankfeed
# TODO: add background task to check user profiles every few hours. watch for username changes and also serve as mapping feed
# TODO: detect when channel is deleted and automatically untrack

client.loop.create_task(modchecker_background_loop())
client.loop.create_task(groupfeed_background_loop())
client.run(open("data/token.txt", "r+").read(), bot=True)