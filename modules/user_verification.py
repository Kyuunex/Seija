from modules import db
from modules import users
from osuembed import osuembed
from modules.connections import osu as osu
import discord
import time
import asyncio


async def verify(channel, member, guild, lookup_type, lookup_string, response):
    # Defaults
    osuusername = None
    osu_join_date = ""
    pp = "0"
    country = ""
    ranked_amount = "0"
    no_sync = "0"

    try:
        if lookup_type == "u":
            osuprofile = await osu.get_user(u=lookup_string)
            if osuprofile:
                osuusername = str(osuprofile.name)
                osuaccountid = str(osuprofile.id)
                osu_join_date = str(osuprofile.join_date)
                pp = str(osuprofile.pp_raw)
                country = str(osuprofile.country)
                embed = await osuembed.user(osuprofile)
        elif lookup_type == "s":
            authorsmapset = await osu.get_beatmapset(s=lookup_string)
            if authorsmapset:
                osuusername = str(authorsmapset.creator)
                osuaccountid = str(authorsmapset.creator_id)
                embed = await osuembed.beatmapset(authorsmapset)

        if osuusername:
            ranked_amount = await users.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(osuaccountid)))

            if ranked_amount >= 10:
                role = discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_experienced_mapper_role", str(guild.id)]]))[0][0]))
            elif ranked_amount >= 1:
                role = discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_ranked_mapper_role", str(guild.id)]]))[0][0]))
            else:
                role = discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_mapper_role", str(guild.id)]]))[0][0]))

            if type(member) is str:
                user_id = member
            else:
                user_id = str(member.id)

            if not response:
                response = "verified <@%s>" % (user_id)

            already_in = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]])
            if already_in:
                if str(already_in[0][0]) != str(osuaccountid):
                    print("user %s already in database" % (user_id,))
                    await channel.send("it seems like your discord account is already in my database and is linked to <https://osu.ppy.sh/users/%s>, and the profile you linked won't overwrite anything in there. if there's a problem, ping kyuunex" % (already_in[0][0]))
                    # possibly force update the entry in future
                else:
                    try:
                        if type(member) is str:
                            pass
                        else:
                            await member.add_roles(role)
                            await member.edit(nick=osuusername)
                    except Exception as e:
                        print(time.strftime('%X %x %Z'))
                        print("in users.verify")
                        print(e)
                    await channel.send(content=response, embed=embed)
            else:
                print("adding user %s in database" % (user_id,))

                check_back_user_id = db.query(["SELECT user_id FROM users WHERE osu_id = ?", [str(osuaccountid)]])
                if check_back_user_id: # TODO: fix
                    if str(check_back_user_id[0][0]) != str(member.id):
                        await channel.send("side note: this osu account is already linked to <@%s> in my database. if there's a problem, for example, you got a new discord account, ping kyuunex." % (check_back_user_id[0][0]))
                try:
                    if type(member) is str:
                        pass
                    else:
                        await member.add_roles(role)
                        await member.edit(nick=osuusername)
                except Exception as e:
                    print(time.strftime('%X %x %Z'))
                    print("in users.verify")
                    print(e)
                db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", [user_id, osuaccountid, osuusername, osu_join_date, pp, country, ranked_amount, no_sync]])
                await channel.send(content=response, embed=embed)
            return True
        else:
            return None
    except Exception as e:
        print(e)
        print("Connection issues?")
        await channel.send(content="It looks like osu's website is down so I can't verify at this moment. Ping managers or something or try again later.")

        
async def unverify(ctx, user_id):
    db.query(["DELETE FROM users WHERE user_id = ?", [str(user_id), ]])
    member = ctx.guild.get_member(int(user_id))
    if member:
        try:
            await member.edit(roles=[])
            await member.edit(nick=None)
            await ctx.send("Done")
        except Exception as e:
            await ctx.send(e)


async def manually_verify(ctx, lookup_type, osu_id, user_id, preverify):
    try:
        if preverify == "preverify":
            await verify(ctx.message.channel, str(user_id), None, lookup_type, osu_id, "Preverified: %s" % (str(user_id)))
        elif preverify == "restricted":
            db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", [user_id, osu_id, "", "", "", "", "", ""]])
            await ctx.send("lol ok")
        else:
            await verify(ctx.message.channel, ctx.guild.get_member(user_id), ctx.message.guild, lookup_type, osu_id, "Manually Verified: %s" % (ctx.guild.get_member(user_id).name))
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in verify")
        print(e)


async def mass_verify(ctx, mention_users):
    try:
        # TODO: this might be broken check later
        csv_file = open("data/users.csv", encoding="utf8").read().splitlines()
        if mention_users == "m":
            tag = "Preverified: <@%s>"
        else:
            tag = "Preverified: %s"
        for one_user in csv_file:
            uzer = one_user.split(',')
            await verify(ctx.message.channel, str(uzer[1]), None, "u", uzer[0], tag % (str(uzer[1])))
            await asyncio.sleep(1)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in userdb")
        print(e)


async def on_member_join(client, member):
    try:
        guildverifychannel = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_verify_channel", str(member.guild.id)]])
        if guildverifychannel:
            join_channel_object = client.get_channel(int((guildverifychannel)[0][0]))
            if not member.bot:
                lookupuser = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]])
                if lookupuser:
                    print("user %s joined with osu_id %s" % (str(member.id), str(lookupuser[0][0])))
                    verifyattempt = await verify(join_channel_object, member, member.guild, "u", lookupuser[0][0], "Welcome aboard %s! Since we know who you are, I have automatically verified you. Enjoy your stay!" % (member.mention))

                    if not verifyattempt:
                        await join_channel_object.send("Hello %s. We have a verification system in this server, to keep raids and spam out. It seems like you are in my database but the profile I know of you is restricted. If this is correct, please link any of your uploaded maps (new website only) and I'll verify you instantly. If this is not correct, tag Kyuunex." % (member.mention))
                else:
                    await join_channel_object.send("Welcome %s! We have a verification system in this server so that we know who you are, give you appropriate roles and keep raids/spam out." % (member.mention))
                    try:
                        osuprofile = await osu.get_user(u=member.name)
                    except Exception as e:
                        print(e)
                        print("Connection issues?")
                        osuprofile = None
                    if osuprofile:
                        await join_channel_object.send(content='Is this your osu profile? If yes, type `yes`, if not, link your profile.', embed=await osuembed.user(osuprofile))
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
        guildverifychannel = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_verify_channel", str(member.guild.id)]])
        if guildverifychannel:
            join_channel_object = client.get_channel(int((guildverifychannel)[0][0]))
            if not member.bot:
                osu_id = db.query(["SELECT osu_username FROM users WHERE user_id = ?", [str(member.id)]])
                if osu_id:
                    try:
                        memberprofile = await osu.get_user(u=osu_id[0][0])
                        embed = await osuembed.user(memberprofile)
                    except Exception as e:
                        print(e)
                        print("Connection issues?")
                        embed = None
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
            verifychannel_id = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_verify_channel", str(message.guild.id)]])
            if verifychannel_id:
                if message.channel.id == int(verifychannel_id[0][0]):
                    split_message = []
                    if '/' in message.content:
                        split_message = message.content.split('/')

                    if 'https://osu.ppy.sh/u' in message.content:
                        verifyattempt = await verify(message.channel, message.author, message.guild, "u", (split_message[4].split(' ')[0]), "`Verified: %s`" % (message.author.name))
                        if not verifyattempt:
                            await message.channel.send('verification failure, I can\'t find any profile from that link. If you are restricted, link any of your recently uploaded maps (new website only). if you are not restricted, then maybe osu website is down at this moment and in that case, ping Kyuunex or try again later.')
                    elif 'https://osu.ppy.sh/beatmapsets/' in message.content:
                        verifyattempt = await verify(message.channel, message.author, message.guild, "s", (split_message[4].split('#')[0]), "`Verified through mapset: %s`" % (message.author.name))
                        if not verifyattempt:
                            await message.channel.send('verification failure, I can\'t find any map with that link')
                    elif message.content.lower() == 'yes':
                        verifyattempt = await verify(message.channel, message.author, message.guild, "u", message.author.name, "`Verified: %s`" % (message.author.name))
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