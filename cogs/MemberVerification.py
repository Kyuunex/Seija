import discord
from discord.ext import commands
from modules import db
from modules import permissions
from modules.connections import osu as osu
import time
import asyncio
import osuembed
import datetime
import upsidedown


class MemberVerification(commands.Cog, name="Member Verification"):
    def __init__(self, bot):
        self.bot = bot
        self.verify_channel_list = db.query(["SELECT value FROM config WHERE setting = ?", ["guild_verify_channel"]])

    @commands.command(name="verify", brief="Manually verify a user", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def verify(self, ctx, osu_id: str, user_id: int, preverify: str = None):
        try:
            if preverify == "preverify":
                await self.verifyer(ctx.message.channel, str(user_id), None, osu_id, "Preverified: %s" % (str(user_id)))
            elif preverify == "restricted":
                db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", [str(user_id), str(osu_id), "", "", "", "", "", ""]])
                await ctx.send("lol ok")
            else:
                await self.verifyer(ctx.message.channel, ctx.guild.get_member(user_id), ctx.message.guild, osu_id, "Manually Verified: %s" % (ctx.guild.get_member(user_id).name))
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in verify")
            print(e)

    @commands.command(name="unverify", brief="Unverify a member and delete it from db", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def unverify(self, ctx, user_id):
        db.query(["DELETE FROM users WHERE user_id = ?", [str(user_id), ]])
        member = ctx.guild.get_member(int(user_id))
        if member:
            try:
                await member.edit(roles=[])
                await member.edit(nick=None)
                await ctx.send("Done")
            except Exception as e:
                await ctx.send(e)

    @commands.command(name="mass_verify", brief="Insert multiple users into the database from a csv file", description="", pass_context=True)
    @commands.check(permissions.is_owner)
    async def mass_verify(self, ctx, mention_users: str = None):
        try:
            # TODO: this might be broken check later
            csv_file = open("data/users.csv", encoding="utf8").read().splitlines()
            if mention_users == "m":
                tag = "Preverified: <@%s>"
            else:
                tag = "Preverified: %s"
            for one_user in csv_file:
                uzer = one_user.split(',')
                await self.verifyer(ctx.message.channel, str(uzer[1]), None, uzer[0], tag % (str(uzer[1])))
                await asyncio.sleep(1)
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in userdb")
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            guildverifychannel = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_verify_channel", str(member.guild.id)]])
            if guildverifychannel:
                join_channel_object = self.bot.get_channel(int((guildverifychannel)[0][0]))
                if not member.bot:
                    lookupuser = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]])
                    if lookupuser:
                        print("user %s joined with osu_id %s" % (str(member.id), str(lookupuser[0][0])))
                        verifyattempt = await self.verifyer(join_channel_object, member, member.guild, lookupuser[0][0], "Welcome aboard %s! Since we know who you are, I have automatically verified you. Enjoy your stay!" % (member.mention))

                        if not verifyattempt:
                            await join_channel_object.send("Hello %s. We have a verification system in this server, to keep raids and spam out. It seems like you are in my database but the profile I know of you is restricted. If this is not correct, tag Kyuunex. Actually this message should never come up idk why it did." % (member.mention))
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

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            try:
                for verify_channel_id in self.verify_channel_list:
                    if message.channel.id == int(verify_channel_id[0]):
                        split_message = []
                        if '/' in message.content:
                            split_message = message.content.split('/')

                        if 'https://osu.ppy.sh/u' in message.content:
                            osu_id_to_lookup = split_message[4].split(' ')[0]
                            verifyattempt = await self.verifyer(message.channel, message.author, message.guild, osu_id_to_lookup, "`Verified: %s`" % (message.author.name))
                            if not verifyattempt:
                                await message.channel.send('verification failure, I can\'t find any profile from that link or any beatmaps associated with your account. If you are restricted, ping a manager. If you are not restricted, then maybe osu website is down at this moment and in that case, ping a manager or try again later.')
                        elif message.content.lower() == 'yes':
                            verifyattempt = await self.verifyer(message.channel, message.author, message.guild, message.author.name, "`Verified: %s`" % (message.author.name))
                            if not verifyattempt:
                                await message.channel.send('verification failure, your discord username does not match a username of any osu account. possible reason can be that you changed your discord username before typing `yes`. In this case, link your profile.')
            except Exception as e:
                print(time.strftime('%X %x %Z'))
                print("in on_message")
                print(e)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            guildverifychannel = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_verify_channel", str(member.guild.id)]])
            if guildverifychannel:
                join_channel_object = self.bot.get_channel(int((guildverifychannel)[0][0]))
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
    
    async def get_role_based_on_reputation(self, guild, osuaccountid):
        ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(osuaccountid)))
        if ranked_amount >= 10:
            return discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_experienced_mapper_role", str(guild.id)]]))[0][0]))
        elif ranked_amount >= 1:
            return discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_ranked_mapper_role", str(guild.id)]]))[0][0]))
        else:
            return discord.utils.get(guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_mapper_role", str(guild.id)]]))[0][0]))


    async def update_member_first_time(self, member, role, nickname):
        try:
            await member.add_roles(role)
        except Exception as e:
            print(e)
        try:
            await member.edit(nick=nickname)
        except Exception as e:
            print(e)

    async def verifyer(self, channel, member, guild, lookup_string, response):
        # Defaults
        osuusername = None
        osu_join_date = ""
        pp = "0"
        country = ""
        ranked_amount = "0"
        no_sync = "0"

        try:
            osuprofile = await osu.get_user(u=lookup_string)
            if osuprofile:
                osuusername = str(osuprofile.name)
                osuaccountid = str(osuprofile.id)
                osu_join_date = str(osuprofile.join_date)
                pp = str(osuprofile.pp_raw)
                country = str(osuprofile.country)
                embed = await osuembed.user(osuprofile)
            else:
                authorsmap = await osu.get_beatmap(u=lookup_string)
                if authorsmap:
                    osuusername = str(authorsmap.creator)
                    osuaccountid = str(authorsmap.creator_id)
                    embed = await osuembed.beatmapset(authorsmap)

            if osuusername:

                role = await self.get_role_based_on_reputation(guild, osuaccountid)

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
                        if type(member) is str:
                            pass
                        else:
                            await self.update_member_first_time(member, role, osuusername)
                        
                        await channel.send(content=response, embed=embed)
                else:
                    print("adding user %s in database" % (user_id,))

                    check_back_user_id = db.query(["SELECT user_id FROM users WHERE osu_id = ?", [str(osuaccountid)]])
                    if check_back_user_id: # TODO: fix
                        if str(check_back_user_id[0][0]) != str(member.id):
                            await channel.send("side note: this osu account is already linked to <@%s> in my database. if there's a problem, for example, you got a new discord account, ping kyuunex." % (check_back_user_id[0][0]))

                    if type(member) is str:
                        pass
                    else:
                        await self.update_member_first_time(member, role, osuusername)
                    db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", [user_id, osuaccountid, osuusername, osu_join_date, pp, country, ranked_amount, no_sync]])
                    await channel.send(content=response, embed=embed)
                return True
            else:
                return None
        except Exception as e:
            print(e)
            print("Connection issues?")
            await channel.send(content="It looks like osu's website is down so I can't verify at this moment. Ping managers or something or try again later.")

    async def count_ranked_beatmapsets(self, beatmapsets):
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


def setup(bot):
    bot.add_cog(MemberVerification(bot))
