import random

import discord
import sqlite3
from discord.ext import commands
from modules import permissions
import osuembed


class MemberVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        conn = sqlite3.connect(self.bot.database_file)
        c = conn.cursor()
        self.verify_channel_list = tuple(c.execute("SELECT channel_id, guild_id FROM channels WHERE setting = ?",
                                                   ["verify"]))
        conn.close()
        self.post_verification_emotes = [
            ["FR", "🥖"],
        ]

    @commands.command(name="verify", brief="Manually verify a member", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def verify(self, ctx, user_id, osu_id):
        member = ctx.guild.get_member(int(user_id))
        if member:
            osu_profile = await self.bot.osu.get_user(u=osu_id)
            if osu_profile:
                member_mapsets = await self.bot.osu.get_beatmapsets(u=str(osu_profile.id))
                ranked_amount = await self.count_ranked_beatmapsets(member_mapsets)
                role = await self.get_role_based_on_reputation(member.guild, ranked_amount)
                try:
                    await member.add_roles(role)
                    await member.edit(nick=osu_profile.name)
                except:
                    pass
                embed = await osuembed.user(osu_profile)
                await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(member.id)])
                await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                          [str(member.id), str(osu_profile.id), str(osu_profile.name),
                                           str(osu_profile.join_date),
                                           str(osu_profile.pp_raw), str(osu_profile.country), str(ranked_amount), "0"])
                await self.bot.db.commit()
                await ctx.send(content=f"Manually Verified: {member.name}", embed=embed)

    @commands.command(name="verify_restricted", brief="Manually verify a restricted member", description="")
    @commands.check(permissions.is_admin)
    async def verify_restricted(self, ctx, user_id, osu_id, username=""):
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(user_id), str(osu_id), username, "", "", "", "", ""])
        await self.bot.db.commit()
        await ctx.send("lol ok")

    @commands.command(name="update_user_discord_account", brief="When user switched accounts, apply this")
    @commands.check(permissions.is_admin)
    async def update_user_discord_account(self, ctx, old_id, new_id, osu_id=""):
        if not old_id.isdigit():
            await ctx.send("old_id must be all digits")
            return None

        try:
            old_account = ctx.guild.get_member(int(old_id))
            if old_account:
                await ctx.send("kicking old account")
                await old_account.kick()
        except Exception as e:
            await ctx.send(e)

        if not new_id.isdigit():
            await ctx.send("new_id must be all digits")
            return None

        await self.bot.db.execute("UPDATE users SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE map_owners SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE queues SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE mapset_channels SET user_id = ? WHERE user_id = ?",
                                  [str(new_id), str(old_id)])
        await self.bot.db.commit()

        if osu_id:
            await self.verify(ctx, new_id, osu_id)
        await ctx.send("okay, done")

    @commands.command(name="unverify", brief="Unverify a member and delete it from db", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def unverify(self, ctx, user_id):
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(user_id)])
        await self.bot.db.commit()
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
                    await channel.send(f"beep boop boop beep, {member.mention} has joined our army of bots")

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
                    async with self.bot.db.execute("SELECT osu_id, osu_username FROM users WHERE user_id = ?",
                                                   [str(member.id)]) as cursor:
                        osu_id = await cursor.fetchall()
                    if osu_id:
                        try:
                            osu_profile = await self.bot.osu.get_user(u=osu_id[0][0])
                            embed = await osuembed.user(osu_profile, 0xffffff, "User left")
                            member_name = osu_profile.name
                        except:
                            print("Connection issues?")
                            embed = None
                            member_name = member.name
                    else:
                        embed = None
                        member_name = member.name
                    async with self.bot.db.execute("SELECT message FROM member_goodbye_messages") as cursor:
                        member_goodbye_messages = await cursor.fetchall()
                    goodbye_message = random.choice(member_goodbye_messages)
                    await channel.send(goodbye_message[0] % member_name, embed=embed)
                else:
                    await channel.send(f"beep boop boop beep, {member.mention} has left our army of bots")

    async def get_role_from_db(self, setting, guild):
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [setting, str(guild.id)]) as cursor:
            role_id = await cursor.fetchall()
        return discord.utils.get(guild.roles, id=int(role_id[0][0]))

    async def get_role_based_on_reputation(self, guild, ranked_amount):
        if ranked_amount >= 10:
            return await self.get_role_from_db("experienced_mapper", guild)
        elif ranked_amount >= 1:
            return await self.get_role_from_db("ranked_mapper", guild)
        else:
            return await self.get_role_from_db("mapper", guild)

    async def respond_to_verification(self, message):
        split_message = []
        if "/" in message.content:
            split_message = message.content.split("/")
        if "https://osu.ppy.sh/u" in message.content:
            profile_id = split_message[4].split("#")[0].split(" ")[0]
            await self.profile_id_verification(message, profile_id)
            return None
        elif message.content.lower() == "yes":
            profile_id = message.author.name
            await self.profile_id_verification(message, profile_id)
            return None
        elif "https://osu.ppy.sh/beatmapsets/" in message.content:
            mapset_id = split_message[4].split("#")[0].split(" ")[0]
            await self.mapset_id_verification(message, mapset_id)
            return None
        else:
            return None

    async def mapset_id_verification(self, message, mapset_id):
        channel = message.channel
        member = message.author
        try:
            mapset = await self.bot.osu.get_beatmapset(s=mapset_id)
        except:
            await channel.send("i am having connection issues to osu servers, verifying you. "
                               "<@155976140073205761> should look into this")
            return None

        if not mapset:
            await channel.send("verification failure, I can\'t find any map with that link")
            return None

        try:
            is_not_restricted = await self.bot.osu.get_user(u=mapset.creator_id)
            if is_not_restricted:
                await channel.send("verification failure, "
                                   "verification through mapset is reserved for restricted users only")
                return None
        except:
            pass

        member_mapsets = await self.bot.osu.get_beatmapsets(u=str(mapset.creator_id))
        ranked_amount = await self.count_ranked_beatmapsets(member_mapsets)
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        async with self.bot.db.execute("SELECT user_id FROM users WHERE osu_id = ?",
                                       [str(mapset.creator_id)]) as cursor:
            check_if_new_discord_account = await cursor.fetchall()
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0][0]) != str(member.id):
                old_user_id = check_if_new_discord_account[0][0]
                await channel.send(f"this osu account is already linked to <@{old_user_id}> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex.")
                return None

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]) as cursor:
            already_linked_to = await cursor.fetchall()
        if already_linked_to:
            if str(mapset.creator_id) != already_linked_to[0][0]:
                await channel.send(f"{member.mention} it seems like your discord account is already in my database "
                                   f"and is linked to <https://osu.ppy.sh/users/{already_linked_to[0][0]}>")
                return None
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=mapset.creator)
                except:
                    pass
                await channel.send(content=f"{member.mention} i already know lol. here, have some roles")
                return None

        try:
            await member.add_roles(role)
            await member.edit(nick=mapset.creator)
        except:
            pass
        embed = await osuembed.beatmapset(mapset)
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(member.id)])
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(member.id), str(mapset.creator_id), str(mapset.creator), "", "", "",
                                   str(ranked_amount), "0"])
        await self.bot.db.commit()
        await channel.send(content=f"`Verified through mapset: {member.name}` \n"
                                   f"You should also read the rules if you haven't already.", embed=embed)

    async def profile_id_verification(self, message, osu_id):
        channel = message.channel
        member = message.author
        try:
            osu_profile = await self.bot.osu.get_user(u=osu_id)
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

        ranked_amount = await self.count_ranked_beatmapsets(await self.bot.osu.get_beatmapsets(u=str(osu_profile.id)))
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]) as cursor:
            already_linked_to = await cursor.fetchall()
        if already_linked_to:
            if str(osu_profile.id) != already_linked_to[0][0]:
                await channel.send(f"{member.mention} it seems like your discord account is already in my database and "
                                   f"is linked to <https://osu.ppy.sh/users/{already_linked_to[0][0]}>")
                return None
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=osu_profile.name)
                except:
                    pass
                await channel.send(content=f"{member.mention} i already know lol. here, have some roles")
                return None

        async with self.bot.db.execute("SELECT user_id FROM users WHERE osu_id = ?", [str(osu_profile.id)]) as cursor:
            check_if_new_discord_account = await cursor.fetchall()
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0][0]) != str(member.id):
                old_user_id = check_if_new_discord_account[0][0]
                await channel.send(f"this osu account is already linked to <@{old_user_id}> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex.")
                return None

        try:
            await member.add_roles(role)
            await member.edit(nick=osu_profile.name)
        except:
            pass
        embed = await osuembed.user(osu_profile)
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(member.id)])
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(member.id), str(osu_profile.id), str(osu_profile.name),
                                   str(osu_profile.join_date),
                                   str(osu_profile.pp_raw), str(osu_profile.country), str(ranked_amount), "0"])
        await self.bot.db.commit()
        verified_message = await channel.send(content=f"`Verified: {member.name}` \n"
                                                      f"You should also read the rules if you haven't already.",
                                              embed=embed)

        await self.add_obligatory_reaction(verified_message, osu_profile)

    async def member_verification(self, channel, member):
        async with self.bot.db.execute("SELECT osu_id, osu_username FROM users WHERE user_id = ?",
                                       [str(member.id)]) as cursor:
            user_db_lookup = await cursor.fetchall()
        if user_db_lookup:
            member_mapsets = await self.bot.osu.get_beatmapsets(u=str(user_db_lookup[0][0]))
            ranked_amount = await self.count_ranked_beatmapsets(member_mapsets)
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
            verified_message = await channel.send(f"Welcome aboard {member.mention}! Since we know who you are, "
                                                  "I have automatically gave you appropriate roles. Enjoy your stay!",
                                                  embed=embed)

            await self.add_obligatory_reaction(verified_message, osu_profile)
        else:
            osu_profile = await self.get_osu_profile(member.name)
            if osu_profile:
                await channel.send(content=f"Welcome {member.mention}! We have a verification system in this server "
                                           "so we can give you appropriate roles and keep raids/spam out. \n"
                                           "Is this your osu! profile? "
                                           "If yes, type `yes`, if not, post a link to your profile.",
                                   embed=await osuembed.user(osu_profile))
            else:
                await channel.send(f"Welcome {member.mention}! We have a verification system in this server "
                                   "so we can give you appropriate roles and keep raids/spam out. \n"
                                   "Please post a link to your osu! profile and I will verify you instantly.")

    async def get_osu_profile(self, name):
        try:
            return await self.bot.osu.get_user(u=name)
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

    async def add_obligatory_reaction(self, message, osu_profile):
        try:
            if osu_profile.country:
                for stereotype in self.post_verification_emotes:
                    if osu_profile.country == stereotype[0]:
                        await message.add_reaction(stereotype[1])
        except Exception as e:
            print(e)


def setup(bot):
    bot.add_cog(MemberVerification(bot))
