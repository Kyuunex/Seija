from modules import osuapi
from modules import osuembed
from modules import dbhandler
import discord
import time
import datetime
import asyncio
import upsidedown


async def verify(channel, member, role, osulookup, response):
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
		if type(member) is str:
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
		
		if not response:
			response = "verified <@%s>" % (discordid)
		
		await channel.send(content=response, embed=embed)
		return True
	else:
		return None

async def guildnamesync(ctx):
	for member in ctx.guild.members:
		if not member.bot:
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
					await dbhandler.query(
						[
							"UPDATE users SET country = ?, pp = ?, osujoindate = ?, username = ? WHERE discordid = ?;",
							[
								str(osuprofile['country']), 
								str(osuprofile['pp_raw']), 
								str(osuprofile['join_date']), 
								str(osuprofile['username']), 
								str(member.id)
							]
						]
					)
				else:
					await ctx.send("%s | `%s` | `%s` | restricted" % (member.mention, str(query[0][2]), str(query[0][1])))
			else:
				await ctx.send("%s | not in db" % (member.mention))
		await asyncio.sleep(0.3)
