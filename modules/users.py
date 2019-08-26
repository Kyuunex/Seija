
from modules import db
from modules import user_verification
import discord
import time
import datetime
import asyncio
import upsidedown
from osuembed import osuembed
import pycountry
from collections import Counter
import operator
from modules.connections import osu as osu


async def send_notice(notice, channel, now):
    if not db.query(["SELECT notice FROM notices WHERE notice = ?", [notice]]):
        await channel.send(notice)
        db.query(["INSERT INTO notices VALUES (?, ?)", [str(now.isoformat()), notice]])


async def statscalc(data):
    results = dict(Counter(data))
    return reversed(sorted(results.items(), key=operator.itemgetter(1)))


async def demographics(client, ctx):
    async with ctx.channel.typing():
        masterlist = []
        for member in ctx.guild.members:
            if not member.bot:
                query = db.query(["SELECT country FROM users WHERE user_id = ?", [str(member.id)]])
                if query: # [5]
                    masterlist.append(query[0][0])
        stats = await statscalc(masterlist)

        rank = 0
        contents = ""
        memberamount = len(masterlist)

        for oneentry in stats:
            rank += 1
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
            if len(contents) > 1800:
                statsembed = discord.Embed(description=contents, color=0xbd3661)
                statsembed.set_author(name="Server Demographics")
                await ctx.send(embed=statsembed)
                contents = ""
        
        if contents == "":
            contents = "\n"
        statsembed = discord.Embed(description=contents, color=0xbd3661)
        statsembed.set_author(name="Server Demographics")
    await ctx.send(embed=statsembed)


async def users_from(client, ctx, country_code):
    async with ctx.channel.typing():
        try:
            if len(country_code) == 2:
                countryobject = pycountry.countries.get(alpha_2=country_code.upper())
            elif len(country_code) == 3:
                countryobject = pycountry.countries.get(alpha_3=country_code.upper())
            else:
                countryobject = pycountry.countries.get(name=country_code)
            countryname = countryobject.name
            countryflag = ":flag_%s:" % (countryobject.alpha_2.lower())
        except:
            countryobject = None
            countryflag = "\n"
            countryname = "Country not found. Keep in mind that full country names are case-sensetive.\nYou can also try searching with alpha 2 codes."
        masterlist = []
        if countryobject:
            for member in ctx.guild.members:
                if not member.bot:
                    query = db.query(["SELECT osu_username, osu_id FROM users WHERE country = ? AND user_id = ?", [str(countryobject.alpha_2.upper()), str(member.id)]])
                    if query:
                        masterlist.append(query[0])
        memberamount = len(masterlist)
        masterlist.sort()
        contents = "%s members from %s %s\n" % (str(memberamount), countryflag, countryname)

        for one_member in masterlist:
            contents += "[%s](https://osu.ppy.sh/users/%s)\n" % (one_member[0], one_member[1])
            if len(contents) > 1800:
                statsembed = discord.Embed(description=contents, color=0xbd3661)
                statsembed.set_author(name="Country Demographics")
                await ctx.send(embed=statsembed)
                contents = ""
        
        if contents == "":
            contents = "\n"
        statsembed = discord.Embed(description=contents, color=0xbd3661)
        statsembed.set_author(name="Country Demographics")
    await ctx.send(embed=statsembed)


async def roleless(ctx, lookup_in_db):
    for member in ctx.guild.members:
        if len(member.roles) < 2:
            await ctx.send(member.mention)
            if lookup_in_db:
                try:
                    query = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]])
                    if query:
                        await ctx.send("person above is in my database and linked to <https://osu.ppy.sh/users/%s>" % (query[0][0]))
                except Exception as e:
                    await ctx.send(e)


async def mapping_username_loop(client):
    try:
        await asyncio.sleep(3600)
        print(time.strftime('%X %x %Z')+' | user event tracker')
        memberfeedchannellist = db.query(["SELECT * FROM config WHERE setting = ?", ["guild_user_event_tracker"]])
        if memberfeedchannellist:
            now = datetime.datetime.now()
            for onechannel in memberfeedchannellist:
                auditchannel = client.get_channel(int(onechannel[3]))
                feedchannel = client.get_channel(int(onechannel[2]))
                guild = client.get_guild(int(onechannel[1]))
                for member in guild.members:
                    if not member.bot:
                        query = db.query(["SELECT * FROM users WHERE user_id = ?", [str(member.id)]])
                        if query:
                            print(time.strftime('%X %x %Z')+" | mapping_username_loop currently checking %s" % (str(query[0][1])))
                            try:
                                check_if_restricted_user_in_db = db.query(["SELECT osu_id FROM restricted_users WHERE guild_id = ? AND osu_id = ?", [str(guild.id), str(query[0][1])]])
                                osuprofile = await osu.get_user(u=query[0][1], event_days="1")
                                if osuprofile:
                                    await one_guild_member_sync(auditchannel, query, now, member, osuprofile)
                                    await check_events(client, feedchannel, osuprofile, "user_event_history")
                                    if check_if_restricted_user_in_db:
                                        await auditchannel.send("%s | `%s` | `%s` | <https://osu.ppy.sh/users/%s> | unrestricted lol" % (member.mention, str(query[0][2]), str(query[0][1]), str(query[0][1])))
                                        db.query(["DELETE FROM restricted_users WHERE guild_id = ? AND osu_id = ?", [str(guild.id), str(query[0][1])]])
                                else:
                                    # at this point we are sure that the user is restricted.
                                    if not check_if_restricted_user_in_db:
                                        await auditchannel.send("%s | `%s` | `%s` | <https://osu.ppy.sh/users/%s> | restricted" % (member.mention, str(query[0][2]), str(query[0][1]), str(query[0][1])))
                                        db.query(["INSERT INTO restricted_users VALUES (?,?)", [str(guild.id), str(query[0][1])]])
                            except Exception as e:
                                print(e)
                                print("Connection issues?")
                                await asyncio.sleep(120)
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


async def check_events(client, channel, user, history_table_name):
    for event in user.events:
        if not db.query(["SELECT event_id FROM %s WHERE event_id = ?" % (history_table_name), [str(event.id)]]):
            db.query(["INSERT INTO %s VALUES (?, ?, ?)" % (history_table_name), [str(user.id), str(event.id), str(channel.id)]])
            event_color = await get_event_color(event.display_text)
            if event_color:
                result = await osu.get_beatmapset(s=event.beatmapset_id)
                embed = await osuembed.beatmapset(result, event_color)
                if embed:
                    display_text = (event.display_text).replace("@", "")
                    print(display_text)
                    await channel.send(display_text, embed=embed)


async def get_event_color(string):
    if 'has submitted' in string:
        return 0x2a52b2
    elif 'has updated' in string:
        #return 0xb2532a
        return None
    elif 'qualified' in string:
        return 0x2ecc71
    elif 'has been revived' in string:
        return 0xff93c9
    elif 'has been deleted' in string:
        return 0xf2d7d5
    else:
        return None


async def one_guild_member_sync(auditchannel, query, now, member, osuprofile):
    if "04-01T" in str(now.isoformat()):
        osuusername = upsidedown.transform(osuprofile.name)
    else:
        osuusername = osuprofile.name
    if str(query[0][2]) != osuusername:
        await auditchannel.send("`%s` namechanged to `%s`. osu_id = `%s`" % (str(query[0][2]), osuusername, str(query[0][1])))
        if str(query[0][1]) == str(4116573):
            await auditchannel.send("This is bor btw. Yes, I actually added this specific message for bor in this bot.")
    if member.display_name != osuusername:
        if "1" in str(query[0][7]):
            await send_notice("%s | `%s` | `%s` | username not updated as `no_sync` was set for this user" % (str(member.mention), osuusername, str(query[0][1])), auditchannel, now)
        else:
            old_nickname = member.display_name
            try:
                await member.edit(nick=osuusername)
            except Exception as e:
                await auditchannel.send(e)
                await auditchannel.send("%s | `%s` | `%s` | no perms to update" % (member.mention, osuusername, str(query[0][1])))
            await auditchannel.send("%s | `%s` | `%s` | nickname updated, old nickname `%s`" % (member.mention, osuusername, str(query[0][1]), old_nickname))
    db.query(
        [
            "UPDATE users SET country = ?, pp = ?, osu_join_date = ?, osu_username = ? WHERE user_id = ?;",
            [
                str(osuprofile.country),
                str(osuprofile.pp_raw),
                str(osuprofile.join_date),
                str(osuprofile.name),
                str(member.id)
            ]
        ]
    )


async def count_ranked_beatmapsets(beatmapsets):
    try:
        count = 0
        if beatmapsets:
            for beatmapset in beatmapsets:
                if beatmapset.approved == "1" or beatmapset.approved == "2":
                    count += 1
        return count
    except Exception as e:
        print(e)
        return 0


async def check_ranked_amount_by_role(ctx, amount = 1, role_name = "guild_mapper_role"):
    role = discord.utils.get(ctx.guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", [role_name, str(ctx.guild.id)]]))[0][0]))
    if role:
        output = "These fella's are the result of this check:\n"
        async with ctx.channel.typing():
            for member in role.members:
                lookupuser = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]])
                if lookupuser:
                    try:
                        mapsbythisguy = await osu.get_beatmapsets(u=str(lookupuser[0][0]))
                        if mapsbythisguy:
                            try:
                                ranked_amount = await count_ranked_beatmapsets(mapsbythisguy)
                            except Exception as e:
                                print(e)
                                print("Connection issues?")
                                ranked_amount = 0
                            if ranked_amount >= amount:
                                output += "%s\n" % (member.mention)
                        else:
                            print("problem with %s" % (member.display_name))
                    except Exception as e:
                        print(e)
                        print(str(lookupuser[0][0]))
                await asyncio.sleep(0.5)
        await ctx.send(output)
    else:
        await ctx.send("Nope")


async def print_all(ctx, mention_users):
    try:
        if mention_users == "m":
            tag = "<@%s> / %s"
        else:
            tag = "%s / %s"
        for one_user in db.query("SELECT * FROM users"):
            try:
                userprofile = await osu.get_user(u=one_user[1])
                embed = await osuembed.user(userprofile)
            except:
                print("Connection issues?")
                await ctx.send("Connection issues?")
                await asyncio.sleep(10)
                embed = None
            if embed:
                await ctx.send(content=tag % (one_user[0], one_user[2]), embed=embed)
            await asyncio.sleep(1)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in userdb")
        print(e)


async def get_users_not_in_db(ctx, mention_users):
    try:
        responce = "These users are not in my database:\n"
        count = 0
        for member in ctx.guild.members:
            if not member.bot:
                if not db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]]):
                    count += 1
                    if mention_users == "m":
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


#TODO: add general welcome message with one message template chosen from db


async def on_user_update(client, before, after):
    which_guild = db.query(["SELECT * FROM config WHERE setting = ?", ["guild_user_event_tracker"]])
    if which_guild:
        query = db.query(["SELECT * FROM users WHERE user_id = ?", [str(after.id)]])
        if query:
            osuprofile = await osu.get_user(u=query[0][1])
            if osuprofile:
                for this_guild in which_guild:
                    guild = client.get_guild(int(this_guild[1]))
                    now = datetime.datetime.now()
                    auditchannel = client.get_channel(int(this_guild[3]))
                    if auditchannel:
                        member = guild.get_member(int(after.id))
                        await one_guild_member_sync(auditchannel, query, now, member, osuprofile)