from modules import osuapi
from modules import osuembed
from modules import dbhandler
import discord
import time
import asyncio

async def legacyverify(channel, member, discordid, role, username, text, embed, sv):
	# TODO: literally rewrite this section, account for mapset verification
	if sv:
		osuusername = username
		osuaccountid = sv
		verifypass = True
	else:
		osuprofile = await osuapi.get_user(username)
		if osuprofile:
			osuusername = osuprofile['username']
			osuaccountid = osuprofile['user_id']
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
				print("in users.verify")
				print(e)


		where = [
			['discordid', discordid],
		]
		if await dbhandler.select('users', 'discordid', where):
			print("user %s already in database" % (discordid,))
		else:
			print("adding user %s in database" % (discordid,))
			await dbhandler.insert('users', (discordid, osuaccountid, osuusername)) 

		# Should message be sent with embed?
		if embed == True:
			embed = await osuembed.osuprofile(osuprofile)
			await channel.send(content=text, embed=embed)
		elif embed == False:
			await channel.send(content=text)
		elif embed:
			await channel.send(content=text, embed=embed)

async def guildnamesync(ctx):
	for member in ctx.guild.members:
		if not member.bot:
			wheres = [
				['discordid', str(member.id)]
			]
			query = await dbhandler.select("users", "osuid", wheres)
			if query:
				osuprofile = await osuapi.get_user(query[0][0])
				if osuprofile:
					osuusername = osuprofile['username']
					try:
						await member.edit(nick=osuusername)
					except Exception as e:
						await ctx.send(e)
						await ctx.send("no perms to update %s" % (osuusername))
					await ctx.send("updated %s" % (osuusername))
				else:
					await ctx.send("restricted %s" % (str(query[0][0])))
			else:
				await ctx.send("user %s not in db" % (member.name))
		await asyncio.sleep(1)
