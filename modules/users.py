from modules import osuapi
from modules import osuembed
from modules import dbhandler
import discord
import time
import datetime
import asyncio
import upsidedown

async def legacyverify(channel, member, discordid, role, username, text, embed, sv):
	# TODO: literally rewrite this section, account for mapset verification
	osujoindate = ""
	pp = "0"
	country = ""
	rankedmaps = "0"
	args = "[]"

	if sv:
		osuusername = username
		osuaccountid = sv
		verifypass = True
	else:
		osuprofile = await osuapi.get_user(username)
		if osuprofile:
			osuusername = str(osuprofile['username'])
			osuaccountid = str(osuprofile['user_id'])
			osujoindate = str(osuprofile['join_date'])
			pp = str(osuprofile['pp_raw'])
			country = str(osuprofile['country'])
			verifypass = True
		else:
			await channel.send('<@%s> | Can\'t find your osu profile. If you are restricted, link any of your recently uploaded maps. Works with new website links only. (Preferably ranked map).' % (str(discordid)))
			verifypass = None

	if verifypass:
		# Nicknaming and Role adding	
		if member:
			try:
				await member.add_roles(role)
				await member.edit(nick=osuusername)
			except Exception as e:
				print(time.strftime('%X %x %Z'))
				print("in users.legacyverify")
				print(e)

		where = [
			['discordid', discordid],
		]
		if await dbhandler.select('users', 'discordid', where):
			print("user %s already in database" % (discordid,))
		else:
			print("adding user %s in database" % (discordid,))
			await dbhandler.insert('users', (discordid, osuaccountid, osuusername, osujoindate, pp, country, rankedmaps, args)) 

		# Should message be sent with embed?
		if embed == True:
			embed = await osuembed.osuprofile(osuprofile)
			await channel.send(content=text, embed=embed)
		elif embed == False:
			await channel.send(content=text)
		elif embed:
			await channel.send(content=text, embed=embed)

async def verify(channel, member, role, osulookup):
	# Defaults
	osuusername = None
	osujoindate = ""
	pp = "0"
	country = ""
	rankedmaps = "0"
	args = "[]"

	if "/" in osulookup:
		osulookup = osulookup.split('/')
		verificationtype = str(osulookup[0])
		lookupstr = str(osulookup[1])
	else:
		verificationtype == None

	if verificationtype == "u":
		osuprofile = await osuapi.get_user(lookupstr)
		if osuprofile:
			osuusername = str(osuprofile['username'])
			osuaccountid = str(osuprofile['user_id'])
			osujoindate = str(osuprofile['join_date'])
			pp = str(osuprofile['pp_raw'])
			country = str(osuprofile['country'])
			embed = await osuembed.osuprofile(osuprofile)
	elif verificationtype == "s":
		authorsmapset = await osuapi.get_beatmap(lookupstr)
		if authorsmapset:
			osuusername = str(authorsmapset['creator'])
			osuaccountid = str(authorsmapset['creator_id'])
			embed = await osuembed.mapset(authorsmapset)

	if osuusername:
		if type(member) == "str":
			discordid = member
		else:
			discordid = str(member.id)
			try:
				await member.add_roles(role)
				await member.edit(nick=osuusername)
			except Exception as e:
				print(time.strftime('%X %x %Z'))
				print("in users.verify")
				print(e)

		if await dbhandler.query(["SELECT discordid FROM users WHERE discordid = ?", [discordid,]]):
			print("user %s already in database" % (discordid,))
			# possibly force update the entry in future
		else:
			print("adding user %s in database" % (discordid,))
			await dbhandler.insert('users', (discordid, osuaccountid, osuusername, osujoindate, pp, country, rankedmaps, args)) 

		await channel.send(content="verified <@%s>" % (discordid), embed=embed)
	else:
		await channel.send("user not found")

async def guildnamesync(ctx):
	for member in ctx.guild.members:
		if not member.bot:
			# wheres = [
			# 	['discordid', str(member.id)]
			# ]
			#query = await dbhandler.select("users", "osuid", wheres)
			query = await dbhandler.query(["SELECT * FROM users WHERE discordid = ?", [str(member.id)]])
			if query:
				osuprofile = await osuapi.get_user(query[0][1])
				if osuprofile:
					now = datetime.datetime.now()
					if "04-01T" in str(now.isoformat()):
						osuusername = upsidedown.transform(osuprofile['username'])
					else:
						osuusername = osuprofile['username']
					if member.display_name != osuusername:
						if "nosync" in str(query[0][7]):
							await ctx.send("%s | `%s` | `%s` | username not updated as `nosync` was set for this user" % (member.mention, osuusername, str(query[0][1])))
						else:
							try:
								await member.edit(nick=osuusername)
							except Exception as e:
								await ctx.send(e)
								await ctx.send("%s | `%s` | `%s` | no perms to update" % (member.mention, osuusername, str(query[0][1])))
							await ctx.send("%s | `%s` | `%s` | nickname updated" % (member.mention, osuusername, str(query[0][1])))
					await dbhandler.query(["UPDATE users SET country = ? WHERE discordid = ?;", [str(osuprofile['country']),str(member.id)]])
					await dbhandler.query(["UPDATE users SET pp = ? WHERE discordid = ?;", [str(osuprofile['pp_raw']),str(member.id)]])
					await dbhandler.query(["UPDATE users SET osujoindate = ? WHERE discordid = ?;", [str(osuprofile['join_date']),str(member.id)]])
					await dbhandler.query(["UPDATE users SET username = ? WHERE discordid = ?;", [str(osuprofile['username']),str(member.id)]])
				else:
					await ctx.send("%s | `%s` | `%s` | restricted" % (member.mention, str(query[0][2]), str(query[0][1])))
			else:
				await ctx.send("%s | not in db" % (member.mention))
		#await asyncio.sleep(1)
