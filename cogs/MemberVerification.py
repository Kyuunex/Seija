import random

import discord
from discord.ext import commands
from modules import db
from modules import permissions
from modules.connections import osu as osu
import time
import osuembed


class MemberVerification(commands.Cog, name="Member Verification"):
    def __init__(self, bot):
        self.bot = bot
        self.verify_channel_list = db.query(["SELECT value, parent FROM config "
                                             "WHERE setting = ?",
                                             ["guild_verify_channel"]])
        self.member_goodbye_messages = db.query("SELECT message FROM member_goodbye_messages")

    @commands.command(name="verify", brief="Manually verify a member", description="")
    @commands.check(permissions.is_admin)
    async def verify(self, ctx, osu_id: str, user_id: int, flags: str = None):
        if flags == "preverify":
            ok_message = "Preverified: %s" % (str(user_id))
            await self.verifyer(ctx.channel, str(user_id), None, osu_id, ok_message)
        elif flags == "restricted":
            db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                      [str(user_id), str(osu_id), "", "", "", "", "", ""]])
            await ctx.send("lol ok")
        else:
            ok_message = "Manually Verified: %s" % ctx.guild.get_member(user_id).name
            await self.verifyer(ctx.channel, ctx.guild.get_member(user_id), ctx.guild, osu_id, ok_message)

    @commands.command(name="unverify", brief="Unverify a member and delete it from db", description="")
    @commands.check(permissions.is_admin)
    async def unverify(self, ctx, user_id):
        db.query(["DELETE FROM users WHERE user_id = ?", [str(user_id)]])
        member = ctx.guild.get_member(int(user_id))
        if member:
            try:
                await member.edit(roles=[])
                await member.edit(nick=None)
                await ctx.send("Done")
            except:
                await ctx.send("no perms to change nickname and/or remove roles")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        for verify_channel_id in self.verify_channel_list:
            if member.guild.id == int(verify_channel_id[1]):
                channel = self.bot.get_channel(int(verify_channel_id[0]))
                if not member.bot:
                    await self.member_verification(channel, member)
                else:
                    await channel.send('beep boop boop beep, %s has joined our army of bots' % member.mention)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.bot.user.id:
            for verify_channel_id in self.verify_channel_list:
                if message.channel.id == int(verify_channel_id[0]):
                    await self.respond_to_verification(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        for verify_channel_id in self.verify_channel_list:
            if member.guild.id == int(verify_channel_id[1]):
                channel = self.bot.get_channel(int(verify_channel_id[0]))
                if not member.bot:
                    osu_id = db.query(["SELECT osu_id, osu_username FROM users WHERE user_id = ?", [str(member.id)]])
                    if osu_id:
                        try:
                            osu_profile = await osu.get_user(u=osu_id[0][0])
                            embed = await osuembed.user(osu_profile)
                            member_name = osu_profile.name
                        except:
                            print("Connection issues?")
                            embed = None
                            member_name = member.name
                    else:
                        embed = None
                        member_name = member.name
                    goodbye_message = random.choice(self.member_goodbye_messages)
                    await channel.send(goodbye_message[0] % member_name, embed=embed)
                else:
                    await channel.send('beep boop boop beep, %s has left our army of bots' % member.mention)

    async def get_role_from_db(self, setting, guild):
        role_id = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", [setting, str(guild.id)]])
        return discord.utils.get(guild.roles, id=int(role_id[0][0]))

    async def get_role_based_on_reputation(self, guild, osu_id):
        ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(osu_id)))
        if ranked_amount >= 10:
            return await self.get_role_from_db("guild_experienced_mapper_role", guild)
        elif ranked_amount >= 1:
            return await self.get_role_from_db("guild_ranked_mapper_role", guild)
        else:
            return await self.get_role_from_db("guild_mapper_role", guild)

    async def respond_to_verification(self, message):
        split_message = []
        if '/' in message.content:
            split_message = message.content.split('/')
        if 'https://osu.ppy.sh/u' in message.content:
            osu_id_to_lookup = split_message[4].split(' ')[0]
            verify_attempt = await self.verifyer(message.channel, message.author, message.guild, osu_id_to_lookup,
                                                 "`Verified: %s`" % message.author.name)
            if not verify_attempt:
                error_message = "verification failure, " \
                                "I can't find a profile from that link or any beatmaps associated with your account. " \
                                "If you are restricted, ping a manager. " \
                                "If you are not restricted, then maybe osu website is down at this moment " \
                                "and in that case, ping a manager or try again later."
                await message.channel.send(error_message)
        elif message.content.lower() == "yes":
            verify_attempt = await self.verifyer(message.channel, message.author, message.guild, message.author.name,
                                                 "`Verified: %s`" % message.author.name)
            if not verify_attempt:
                error_message = "verification failure, " \
                                "your discord username does not match a username of any osu account. " \
                                "possible reason can be that you changed your discord username before typing `yes`. " \
                                "In this case, post a link to your profile."
                await message.channel.send(error_message)

    async def member_verification(self, channel, member):
        user_db_lookup = db.query(["SELECT osu_id, osu_username FROM users WHERE user_id = ?", [str(member.id)]])
        if user_db_lookup:
            role = await self.get_role_based_on_reputation(member.guild, user_db_lookup[0][0])
            await member.add_roles(role)
            osu_profile = await self.get_osu_profile(user_db_lookup[0][0])
            if osu_profile:
                name = osu_profile.name
                embed = await osuembed.user(osu_profile)
            else:
                name = user_db_lookup[0][1]
                embed = None
            await member.edit(nick=name)
            await channel.send("Welcome aboard %s! Since we know who you are, I have automatically verified you. "
                               "Enjoy your stay!" % member.mention,
                               embed=embed)
        else:
            await channel.send("Welcome %s! We have a verification system in this server "
                               "so we can give you appropriate roles and keep raids/spam out." % member.mention)
            osu_profile = await self.get_osu_profile(member.name)
            if osu_profile:
                await channel.send(content="Is this your osu! profile? "
                                           "If yes, type `yes`, if not, post a link to your profile.",
                                   embed=await osuembed.user(osu_profile))
            else:
                await channel.send('Please post a link to your osu! profile and I will verify you instantly.')

    async def get_osu_profile(self, name):
        try:
            return await osu.get_user(u=name)
        except:
            return None

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
                    response = "verified <@%s>" % user_id

                already_in = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]])
                if already_in:
                    if str(already_in[0][0]) != str(osuaccountid):
                        print("user %s already in database" % (user_id,))
                        await channel.send("it seems like your discord account is already in my database and "
                                           "is linked to <https://osu.ppy.sh/users/%s>, "
                                           "and the profile you linked won't overwrite anything in there. "
                                           "if there's a problem, ping kyuunex" % (already_in[0][0]))
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
                    if check_back_user_id:  # TODO: fix
                        if str(check_back_user_id[0][0]) != str(member.id):
                            await channel.send(
                                "side note: this osu account is already linked to <@%s> in my database. "
                                "if there's a problem, for example, you got a new discord account, ping kyuunex." % (
                                    check_back_user_id[0][0]))

                    if type(member) is str:
                        pass
                    else:
                        await self.update_member_first_time(member, role, osuusername)
                    db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                              [user_id, osuaccountid, osuusername, osu_join_date, pp, country, ranked_amount, no_sync]])
                    await channel.send(content=response, embed=embed)
                return True
            else:
                return None
        except Exception as e:
            print(e)
            print("Connection issues?")
            await channel.send(
                content="It looks like osu's website is down so I can't verify at this moment. "
                        "Ping managers or something or try again later.")

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
