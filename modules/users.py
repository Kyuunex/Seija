from modules import osuapi
from modules import osuembed
from modules import dbhandler
from modules import usereventfeed
import discord
import time
import datetime
import asyncio
import upsidedown
import pycountry
from collections import Counter
import operator


async def send_notice(notice, channel, now):
    if not await dbhandler.query(["SELECT notice FROM notices WHERE notice = ?", [notice]]):
        await channel.send(notice)
        await dbhandler.query(["INSERT INTO notices VALUES (?, ?)", [str(now.isoformat()), notice]])


async def statscalc(data):
    results = dict(Counter(data))
    return reversed(sorted(results.items(), key=operator.itemgetter(1)))


async def demographics(client, ctx): #TODO" do this
    async with ctx.channel.typing():
        masterlist = []
        for member in ctx.guild.members:
            if not member.bot:
                query = await dbhandler.query(["SELECT country FROM users WHERE discordid = ?", [str(member.id)]])
                if query: # [5]
                    masterlist.append(query[0][0])
        stats = await statscalc(masterlist)

        rank = 0
        count = 0
        contents = ""
        memberamount = len(masterlist)

        for oneentry in stats:
            rank += 1
            count += 1
            amount = str(oneentry[1])+" Members"
            percentage = str(round(float(int(oneentry[1]) * 100 / memberamount), 2))
            try:
                countryobject = pycountry.countries.get(alpha_2=oneentry[0])
                countryname = countryobject.name
                countryflag = ":flag_%s:" % (oneentry[0].lower())
            except:
                countryflag = ":gay_pride_flag:"
                countryname = oneentry[0]
            contents += "**[%s]** : %s **%s** : %s : %s %% \n" % (rank, countryflag, countryname, amount, percentage)
            if count == 20:
                count = 0
                statsembed = discord.Embed(description=contents, color=0xbd3661)
                statsembed.set_author(name="Server Demographics")
                await ctx.send(embed=statsembed)
                contents = ""
        
        if contents == "":
            contents = "\n"
        statsembed = discord.Embed(description=contents, color=0xbd3661)
        statsembed.set_author(name="Server Demographics")
    await ctx.send(embed=statsembed)


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
        authorsmapset = await osuapi.get_beatmaps(lookupstr)
        if authorsmapset:
            osuusername = str(authorsmapset[0]['creator'])
            osuaccountid = str(authorsmapset[0]['creator_id'])
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

        if await dbhandler.query(["SELECT discordid FROM users WHERE discordid = ?", [discordid, ]]):
            print("user %s already in database" % (discordid,))
            # possibly force update the entry in future
        else:
            print("adding user %s in database" % (discordid,))
            await dbhandler.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", [discordid, osuaccountid, osuusername, osujoindate, pp, country, rankedmaps, args]])

        if not response:
            response = "verified <@%s>" % (discordid)

        await channel.send(content=response, embed=embed)
        return True
    else:
        return None


async def guildnamesync(ctx):
    now = datetime.datetime.now()
    for member in ctx.guild.members:
        if not member.bot:
            query = await dbhandler.query(["SELECT * FROM users WHERE discordid = ?", [str(member.id)]])
            if query:
                osuprofile = await osuapi.get_user(query[0][1])
                if osuprofile:
                    await one_guild_member_sync(ctx.channel, query, now, member, osuprofile)
                else:
                    await ctx.channel.send("%s | `%s` | `%s` | restricted" % (member.mention, str(query[0][2]), str(query[0][1])))
            else:
                await ctx.send("%s | not in db" % (member.mention))


async def mapping_username_loop(client):
    try:
        await asyncio.sleep(3600)
        print(time.strftime('%X %x %Z')+' | user event tracker')
        memberfeedchannellist = await dbhandler.query(["SELECT * FROM config WHERE setting = ?", ["usereventtracker"]])
        if memberfeedchannellist:
            now = datetime.datetime.now()
            for onechannel in memberfeedchannellist:
                auditchannel = client.get_channel(int(onechannel[3]))
                feedchannel = client.get_channel(int(onechannel[2]))
                guild = client.get_guild(int(onechannel[1]))
                for member in guild.members:
                    if not member.bot:
                        query = await dbhandler.query(["SELECT * FROM users WHERE discordid = ?", [str(member.id)]])
                        if query:
                            osuprofile = await osuapi.get_user(query[0][1])
                            if osuprofile:
                                await one_guild_member_sync(auditchannel, query, now, member, osuprofile)
                                await usereventfeed.usereventtrack(client, feedchannel, osuprofile, "userevents")
                            else:
                                await send_notice("%s | `%s` | `%s` | restricted" % (member.mention, str(query[0][2]), str(query[0][1])), auditchannel, now)
                        else:
                            await send_notice("%s | not in db" % (member.mention), auditchannel, now)
                        await asyncio.sleep(1)
        print(time.strftime('%X %x %Z')+' | mapping username loop finished')
        await asyncio.sleep(3600)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in membertrack")
        print(e)
        await asyncio.sleep(7200)


async def one_guild_member_sync(auditchannel, query, now, member, osuprofile):
    if "04-01T" in str(now.isoformat()):
        osuusername = upsidedown.transform(
            osuprofile['username'])
    else:
        osuusername = osuprofile['username']
    if member.display_name != osuusername:
        if "nosync" in str(query[0][7]):
            await send_notice("%s | `%s` | `%s` | username not updated as `nosync` was set for this user" % (str(member.id), osuusername, str(query[0][1])), auditchannel, now)
        else:
            try:
                await member.edit(nick=osuusername)
            except Exception as e:
                await auditchannel.send(e)
                await auditchannel.send("%s | `%s` | `%s` | no perms to update" % (member.mention, osuusername, str(query[0][1])))
            await auditchannel.send("%s | `%s` | `%s` | nickname updated, old nickname %s" % (member.mention, osuusername, str(query[0][1]), str(query[0][2])))
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


async def on_member_join(client, member):
    try:
        guildverifychannel = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(member.guild.id)]])
        if guildverifychannel:
            join_channel_object = client.get_channel(int((guildverifychannel)[0][0]))
            if not member.bot:
                lookupuser = await dbhandler.query(["SELECT osuid FROM users WHERE discordid = ?", [str(member.id), ]])
                if lookupuser:
                    print("user %s joined with osuid %s" %
                        (str(member.id), str(lookupuser[0][0])))
                    role = discord.utils.get(member.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(member.guild.id)]]))[0][0]))
                    osulookup = "u/%s" % (lookupuser[0][0])
                    verifyattempt = await verify(join_channel_object, member, role, osulookup, "Welcome aboard %s! Since we know who you are, I have automatically verified you. Enjoy your stay!" % (member.mention))

                    if not verifyattempt:
                        await join_channel_object.send("Hello %s. It seems like you are in my database but the profile I know of you is restricted. If this is correct, please link any of your uploaded maps (new website only) and I'll verify you instantly. If this is not correct, tag Kyuunex." % (member.mention))
                else:
                    await join_channel_object.send("Welcome %s! We have a verification system in this server so we know who you are, give you appropriate roles and keep raids/spam out." % (member.mention))
                    osuprofile = await osuapi.get_user(member.name)
                    if osuprofile:
                        await join_channel_object.send(content='Is this your osu profile? If yes, type `yes`, if not, link your profile.', embed=await osuembed.osuprofile(osuprofile))
                    else:
                        await join_channel_object.send('Please post a link to your osu profile and I will verify you instantly.')
            else:
                await join_channel_object.send('beep boop boop beep, %s has joined our army of bots' % (member.mention))
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in on_member_join")
        print(e)


async def on_member_remove(client, member):
    try:
        guildverifychannel = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(member.guild.id)]])
        if guildverifychannel:
            join_channel_object = client.get_channel(int((guildverifychannel)[0][0]))
            if not member.bot:
                osuid = await dbhandler.query(["SELECT username FROM users WHERE discordid = ?", [str(member.id)]])
                if osuid:
                    embed = await osuembed.osuprofile(await osuapi.get_user(osuid[0][0]))
                else:
                    embed = None
                await join_channel_object.send("%s left this server. Godspeed!" % (str(member.name)), embed=embed)
            else:
                await join_channel_object.send('beep boop boop beep, %s has left our army of bots' % (member.mention))
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in on_member_join")
        print(e)


async def on_message(client, message):
    if message.author.id != client.user.id:
        try:
            verifychannelid = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifychannelid", str(message.guild.id)]])
            if verifychannelid:
                if message.channel.id == int(verifychannelid[0][0]):
                    split_message = []
                    if '/' in message.content:
                        split_message = message.content.split('/')
                    role = discord.utils.get(message.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(message.guild.id)]]))[0][0]))

                    if 'https://osu.ppy.sh/u' in message.content:
                        osulookup = "u/%s" % (split_message[4].split(' ')[0])
                        verifyattempt = await verify(message.channel, message.author, role, osulookup, "Verified: %s" % (message.author.name))
                        if not verifyattempt:
                            await message.channel.send('verification failure, I can\'t find any profile from that link. If you are restricted, link any of your recently uploaded maps (new website only).')
                    elif 'https://osu.ppy.sh/beatmapsets/' in message.content:
                        osulookup = "s/%s" % (split_message[4].split('#')[0])
                        verifyattempt = await verify(message.channel, message.author, role, osulookup, "Verified through mapset: %s" % (message.author.name))
                        if not verifyattempt:
                            await message.channel.send('verification failure, I can\'t find any map with that link')
                    elif message.content.lower() == 'yes':
                        osulookup = "u/%s" % (message.author.name)
                        verifyattempt = await verify(message.channel, message.author, role, osulookup, "Verified: %s" % (message.author.name))
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


async def userdbprintall(ctx, command, mention):
    try:
        if mention == "m":
            tag = "<@%s> / %s"
        else:
            tag = "%s / %s"
        for oneuser in await dbhandler.query("SELECT * FROM users"):
            embed = await osuembed.osuprofile(await osuapi.get_user(oneuser[1]))
            if embed:
                await ctx.send(content=tag % (oneuser[0], oneuser[2]), embed=embed)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in userdb")
        print(e)


async def userdbmassverify(ctx, command, mention):
    try:
        userarray = open("data/users.csv",
                            encoding="utf8").read().splitlines()
        if mention == "m":
            tag = "Preverified: <@%s>"
        else:
            tag = "Preverified: %s"
        for oneuser in userarray:
            uzer = oneuser.split(',')
            await verify(ctx.message.channel, str(uzer[1]), None, "u/%s" % (uzer[0]), tag % (str(uzer[1])))
            await asyncio.sleep(1)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in userdb")
        print(e)


async def userdbservercheck(ctx, command, mention):
    try:
        responce = "These users are not in my database:\n"
        count = 0
        for member in ctx.guild.members:
            if not member.bot:
                if not await dbhandler.query(["SELECT osuid FROM users WHERE discordid = ?", [str(member.id), ]]):
                    count += 1
                    if mention == "m":
                        responce += ("<@%s>\n" % (str(member.id)))
                    else:
                        responce += ("\"%s\" %s\n" %
                                        (str(member.display_name), str(member.id)))
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


async def mverify(ctx, osuid, discordid, preverify):
    try:
        if preverify == "preverify":
            await verify(ctx.message.channel, str(discordid), None, osuid, "Preverified: %s" % (str(discordid)))
        else:
            role = discord.utils.get(ctx.message.guild.roles, id=int((await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["verifyroleid", str(ctx.guild.id)]]))[0][0]))
            await verify(ctx.message.channel, ctx.guild.get_member(discordid), role, osuid, "Manually Verified: %s" % (ctx.guild.get_member(discordid).name))
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in verify")
        print(e)

#TODO: add general welcome message with one message template chosen from db