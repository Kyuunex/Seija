import random

import discord
from discord.ext import commands
from modules import db
from modules import permissions
from modules.connections import osu as osu
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
    @commands.guild_only()
    async def verify(self, ctx, user_id, osu_id):
        member = ctx.guild.get_member(int(user_id))
        if member:
            osu_profile = await osu.get_user(u=osu_id)
            if osu_profile:
                ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(osu_profile.id)))
                role = await self.get_role_based_on_reputation(member.guild, ranked_amount)
                try:
                    await member.add_roles(role)
                    await member.edit(nick=osu_profile.name)
                except:
                    pass
                embed = await osuembed.user(osu_profile)
                db.query(["DELETE FROM users WHERE user_id = ?", [str(member.id)]])
                db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                          [str(member.id), str(osu_profile.id), str(osu_profile.name), str(osu_profile.join_date),
                           str(osu_profile.pp_raw), str(osu_profile.country), str(ranked_amount), "0"]])
                await ctx.send(content="Manually Verified: %s" % member.name, embed=embed)

    @commands.command(name="verify_restricted", brief="Manually verify a restricted member", description="")
    @commands.check(permissions.is_admin)
    async def verify_restricted(self, ctx, user_id, osu_id, username=""):
        db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                  [str(user_id), str(osu_id), username, "", "", "", "", ""]])
        await ctx.send("lol ok")

    @commands.command(name="unverify", brief="Unverify a member and delete it from db", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
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
                            embed = await osuembed.user(osu_profile, 0xffffff, "User left")
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

    async def get_role_based_on_reputation(self, guild, ranked_amount):
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
            profile_id = split_message[4].split('#')[0].split(' ')[0]
            await self.profile_id_verification(message, profile_id)
            return None
        elif message.content.lower() == "yes":
            profile_id = message.author.name
            await self.profile_id_verification(message, profile_id)
            return None
        elif 'https://osu.ppy.sh/beatmapsets/' in message.content:
            mapset_id = split_message[4].split('#')[0].split(' ')[0]
            await self.mapset_id_verification(message, mapset_id)
            return None
        else:
            return None

    async def mapset_id_verification(self, message, mapset_id):
        channel = message.channel
        member = message.author
        try:
            mapset = await osu.get_beatmapset(s=mapset_id)
        except:
            await channel.send("i am having connection issues to osu servers, verifying you. "
                               "<@155976140073205761> should look into this")
            return None

        if not mapset:
            await channel.send("verification failure, I can\'t find any map with that link")
            return None

        try:
            is_not_restricted = await osu.get_user(u=mapset.creator_id)
            if is_not_restricted:
                await channel.send("verification failure, "
                                   "verification through mapset is reserved for restricted users only")
                return None
        except:
            pass

        ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(mapset.creator_id)))
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        check_if_new_discord_account = db.query(["SELECT user_id FROM users "
                                                 "WHERE osu_id = ?",
                                                 [str(mapset.creator_id)]])
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0][0]) != str(member.id):
                await channel.send("this osu account is already linked to <@%s> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex." %
                                   (check_if_new_discord_account[0][0]))
                return None

        already_linked_to = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]])
        if already_linked_to:
            if str(mapset.creator_id) != already_linked_to[0][0]:
                await channel.send("%s it seems like your discord account is already in my database and "
                                   "is linked to <https://osu.ppy.sh/users/%s>" %
                                   (member.mention, already_linked_to[0][0]))
                return None
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=mapset.creator)
                except:
                    pass
                await channel.send(content="%s i already know lol. here, have some roles" % member.mention)
                return None

        try:
            await member.add_roles(role)
            await member.edit(nick=mapset.creator)
        except:
            pass
        embed = await osuembed.beatmapset(mapset)
        db.query(["DELETE FROM users WHERE user_id = ?", [str(member.id)]])
        db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                  [str(member.id), str(mapset.creator_id), str(mapset.creator), "", "", "", str(ranked_amount), "0"]])
        await channel.send(content="`Verified through mapset: %s`" % member.name, embed=embed)

    async def profile_id_verification(self, message, osu_id):
        channel = message.channel
        member = message.author
        try:
            osu_profile = await osu.get_user(u=osu_id)
        except:
            await channel.send("i am having connection issues to osu servers, verifying you. "
                               "<@155976140073205761> should look into this")
            return None

        if not osu_profile:
            if osu_id.isdigit():
                await channel.send("verification failure, "
                                   "i can't find any profile from that link or you are restricted. "
                                   "if you are restricted, link any of your recently uploaded maps (new site only)")
            else:
                await channel.send("verification failure, "
                                   "either your discord username does not match a username of any osu account "
                                   "or you linked an incorrect profile. "
                                   "this error also pops up if you are restricted, in that case, "
                                   "link any of your recently uploaded maps (new site only)")
            return None

        ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(osu_profile.id)))
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        check_if_new_discord_account = db.query(["SELECT user_id FROM users WHERE osu_id = ?", [str(osu_profile.id)]])
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0][0]) != str(member.id):
                await channel.send("this osu account is already linked to <@%s> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex." %
                                   (check_if_new_discord_account[0][0]))
                return None

        already_linked_to = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]])
        if already_linked_to:
            if str(osu_profile.id) != already_linked_to[0][0]:
                await channel.send("%s it seems like your discord account is already in my database and "
                                   "is linked to <https://osu.ppy.sh/users/%s>" %
                                   (member.mention, already_linked_to[0][0]))
                return None
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=osu_profile.name)
                except:
                    pass
                await channel.send(content="%s i already know lol. here, have some roles" % member.mention)
                return None

        try:
            await member.add_roles(role)
            await member.edit(nick=osu_profile.name)
        except:
            pass
        embed = await osuembed.user(osu_profile)
        db.query(["DELETE FROM users WHERE user_id = ?", [str(member.id)]])
        db.query(["INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                  [str(member.id), str(osu_profile.id), str(osu_profile.name), str(osu_profile.join_date),
                   str(osu_profile.pp_raw), str(osu_profile.country), str(ranked_amount), "0"]])
        await channel.send(content="`Verified: %s`" % member.name, embed=embed)

    async def member_verification(self, channel, member):
        user_db_lookup = db.query(["SELECT osu_id, osu_username FROM users WHERE user_id = ?", [str(member.id)]])
        if user_db_lookup:
            ranked_amount = await self.count_ranked_beatmapsets(await osu.get_beatmapsets(u=str(user_db_lookup[0][0])))
            role = await self.get_role_based_on_reputation(member.guild, ranked_amount)
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
