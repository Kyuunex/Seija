import random

import discord
import sqlite3
from discord.ext import commands
from discord.utils import escape_markdown
from modules import permissions
from modules import wrappers
import osuembed
import osuwebembed
import datetime


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

    @commands.command(name="verify", brief="Manually verify a member")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def verify(self, ctx, user_id, osu_id):
        """
        Manually verify a member
        :param user_id: Discord account ID
        :param osu_id: osu! account ID
        """

        if not user_id.isdigit():
            await ctx.send("discord account user_id must be all digits")
            return

        member = ctx.guild.get_member(int(user_id))
        if not member:
            await ctx.send("no member found with that user_id")
            return

        try:
            fresh_osu_data = await self.bot.osuweb.get_user_array(osu_id)
        except Exception as e:
            await ctx.send("i have connection issues with osu servers. so i can't do that right now",
                           embed=await wrappers.embed_exception(e))
            return

        if not fresh_osu_data:
            await ctx.send("no osu account found with that osu_id or username")
            return

        ranked_amount = fresh_osu_data["ranked_and_approved_beatmapset_count"]

        try:
            role = await self.get_role_based_on_reputation(member.guild, ranked_amount)
        except:
            role = None

        if not role:
            await ctx.send("i can't find a role to give. something is misconfigured")
            return

        try:
            await member.add_roles(role)
        except Exception as e:
            await ctx.send("i can't give the role", embed=await wrappers.embed_exception(e))

        try:
            await member.edit(nick=fresh_osu_data["username"])
        except Exception as e:
            await ctx.send("i can't update the nickname of this user", embed=await wrappers.embed_exception(e))

        embed = await osuwebembed.user_array(fresh_osu_data)

        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(member.id)])
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(member.id), str(fresh_osu_data["id"]), str(fresh_osu_data["username"]),
                                   str(fresh_osu_data["join_date"]), str(fresh_osu_data["statistics"]["pp"]),
                                   str(fresh_osu_data["country_code"]), str(ranked_amount), "0"])
        await self.bot.db.commit()

        await self.check_group_roles(ctx.channel, member, ctx.guild, fresh_osu_data)
        await ctx.send(content=f"Manually Verified: {member.name}", embed=embed)

    @commands.command(name="verify_restricted", brief="Manually verify a restricted member")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def verify_restricted(self, ctx, user_id, osu_id, username=""):
        """
        Insert a restricted user info into the database. This command does not give any roles.
        :param user_id: Discord account ID
        :param osu_id: osu! account ID
        :param username: osu! account username
        """

        if not user_id.isdigit():
            await ctx.send("discord account user_id must be all digits")
            return

        if not osu_id.isdigit():
            await ctx.send("osu account id must be all digits")
            return

        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(user_id), str(osu_id), username, "", "", "", "", ""])
        await self.bot.db.commit()

        await ctx.send("lol ok")

    @commands.command(name="update_user_discord_account", brief="When user switched accounts, apply this")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def update_user_discord_account(self, ctx, old_id, new_id, osu_id=""):
        """
        A command to migrate stuff from old discord account to a new one.
        :param old_id: an ID of the old Discord account
        :param new_id: an ID of the new Discord account
        :param osu_id: an ID of the osu account
        """

        if not old_id.isdigit():
            await ctx.send("old_id must be all digits")
            return

        if not new_id.isdigit():
            await ctx.send("new_id must be all digits")
            return

        try:
            old_account = ctx.guild.get_member(int(old_id))
            if old_account:
                await ctx.send("kicking old account")
                await old_account.kick()
        except Exception as e:
            await ctx.send(embed=await wrappers.embed_exception(e))

        await self.bot.db.execute("UPDATE users SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE map_owners SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE queues SET user_id = ? WHERE user_id = ?", [str(new_id), str(old_id)])
        await self.bot.db.execute("UPDATE mapset_channels SET user_id = ? WHERE user_id = ?",
                                  [str(new_id), str(old_id)])
        await self.bot.db.commit()

        if osu_id:
            await ctx.send("verifying the new account now")
            await self.verify(ctx, new_id, osu_id)

        await ctx.send("okay, done")

    @commands.command(name="unverify", brief="Unverify a member and delete it from db")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def unverify(self, ctx, user_id):
        """
        Unverify a member and delete it from the database
        :param user_id: Discord account ID
        """

        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(user_id)])
        await self.bot.db.commit()
        await ctx.send("deleted from database")

        member = ctx.guild.get_member(int(user_id))
        if not member:
            return

        try:
            await member.edit(roles=[])
            await member.edit(nick=None)
            await ctx.send("removed nickname and roles")
        except Exception as e:
            await ctx.send("no perms to change nickname and/or remove roles", embed=await wrappers.embed_exception(e))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        for verify_channel_id in self.verify_channel_list:
            if member.guild.id != int(verify_channel_id[1]):
                continue

            channel = self.bot.get_channel(int(verify_channel_id[0]))
            if not channel:
                # something is misconfigured
                continue

            if member.guild.member_count == 1000:
                await channel.send(f"owo, our 1000-th member is here!")

            if member.bot:
                await channel.send(f"beep boop boop beep, {member.mention} has joined our army of bots")
                return

            await self.ask_just_joined_member_to_verify(channel, member)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        for verify_channel_id in self.verify_channel_list:
            if message.channel.id != int(verify_channel_id[0]):
                continue

            if "https://osu.ppy.sh/u" in message.content:
                profile_id = self.grab_osu_profile_id_from_text(message.content)
                await self.profile_id_verification(message, profile_id)
                return

            if message.content.lower() == "yes" and self.is_new_user(message.author) is False:
                profile_id = message.author.name
                await self.profile_id_verification(message, profile_id)
                return

            if "https://osu.ppy.sh/beatmapsets/" in message.content:
                mapset_id = self.grab_osu_mapset_id_from_text(message.content)
                await self.mapset_id_verification(message, mapset_id)
                return

            return

    def grab_osu_profile_id_from_text(self, text):
        split_message = text.split("/")
        return split_message[4].split("#")[0].split(" ")[0]

    def grab_osu_mapset_id_from_text(self, text):
        split_message = text.split("/")
        return split_message[4].split("#")[0].split(" ")[0]

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        for verify_channel_id in self.verify_channel_list:
            if member.guild.id != int(verify_channel_id[1]):
                continue

            channel = self.bot.get_channel(int(verify_channel_id[0]))
            if not channel:
                # something is misconfigured
                continue

            if member.bot:
                await channel.send(f"beep boop boop beep, {member.mention} has left our army of bots")
                return

            async with self.bot.db.execute("SELECT osu_id, osu_username FROM users WHERE user_id = ?",
                                           [str(member.id)]) as cursor:
                osu_id = await cursor.fetchone()

            if osu_id:
                try:
                    fresh_osu_data = await self.bot.osuweb.small_get_user_array(osu_id[0])
                    embed = await osuwebembed.user_array(fresh_osu_data, 0xffffff, "User left")
                    member_name = fresh_osu_data["username"]
                except:
                    print("Connection issues?")
                    embed = None
                    member_name = member.name
            else:
                embed = None
                member_name = member.name

            escaped_member_name = escape_markdown(member_name)

            async with self.bot.db.execute("SELECT message FROM member_goodbye_messages") as cursor:
                member_goodbye_messages = await cursor.fetchall()

            goodbye_message = random.choice(member_goodbye_messages)

            await channel.send(goodbye_message[0] % f"**{escaped_member_name}**", embed=embed)

    async def mapset_id_verification(self, message, mapset_id):
        channel = message.channel
        member = message.author

        try:
            mapset = await self.bot.osu.get_beatmapset(s=mapset_id)
        except Exception as e:
            await channel.send("i am having issues connecting to osu servers to verify you. "
                               "try again later or wait for a manager to help",
                               embed=await wrappers.embed_exception(e))
            return

        if not mapset:
            await channel.send("verification failure, I can't find any map with that link")
            return

        try:
            is_not_restricted = await self.bot.osu.get_user(u=mapset.creator_id)
            if is_not_restricted:
                await channel.send("verification failure, "
                                   "verification through mapset is reserved for restricted users only. "
                                   "this is like this to reduce confusion and errors")
                return
        except:
            pass

        # this won't work on restricted users, thanks peppy.
        # member_mapsets = await self.bot.osu.get_beatmapsets(u=str(mapset.creator_id))
        # ranked_amount = await self.count_ranked_beatmapsets(member_mapsets)
        ranked_amount = 0
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]) as cursor:
            already_linked_to = await cursor.fetchone()
        if already_linked_to:
            if str(mapset.creator_id) != already_linked_to[0]:
                await channel.send(f"{member.mention} it seems like your discord account is already in my database "
                                   f"and is linked to <https://osu.ppy.sh/users/{already_linked_to[0]}>")
                return
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=mapset.creator)
                except:
                    pass
                await channel.send(content=f"{member.mention} i already know lol. here, have some roles")
                return

        async with self.bot.db.execute("SELECT user_id FROM users WHERE osu_id = ?",
                                       [str(mapset.creator_id)]) as cursor:
            check_if_new_discord_account = await cursor.fetchone()
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0]) != str(member.id):
                old_user_id = check_if_new_discord_account[0]
                await channel.send(f"this osu account is already linked to <@{old_user_id}> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex.")
                return

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

        await channel.send(content=f"`Verified through mapset: {escape_markdown(member.name)}` \n"
                                   f"You should also read the rules if you haven't already.", embed=embed)

    async def profile_id_verification(self, message, osu_id):
        channel = message.channel
        member = message.author

        try:
            fresh_osu_data = await self.bot.osuweb.get_user_array(osu_id)
        except Exception as e:
            await channel.send("i am having issues connecting to osu servers to verify you. "
                               "try again later or wait for a manager to help",
                               embed=await wrappers.embed_exception(e))
            return

        if not fresh_osu_data:
            if osu_id.isdigit():
                await channel.send("verification failure, "
                                   "i can't find any profile from that link or you are restricted. "
                                   "if you are restricted, link any of your recently uploaded maps (new site only)")
            else:
                await channel.send("verification failure, "
                                   "either your discord username does not match a username of any osu account "
                                   "at the time you typed 'yes', "
                                   "or you linked an incorrect profile. "
                                   "this error also pops up if you are restricted, in that case, "
                                   "link any of your recently uploaded maps (ranked with the latest name preferred)")
            return

        ranked_amount = fresh_osu_data["ranked_and_approved_beatmapset_count"]
        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]) as cursor:
            already_linked_to = await cursor.fetchone()
        if already_linked_to:
            if str(fresh_osu_data["id"]) != already_linked_to[0]:
                await channel.send(f"{member.mention} it seems like your discord account is already in my database and "
                                   f"is linked to <https://osu.ppy.sh/users/{already_linked_to[0]}>")
                return
            else:
                try:
                    await member.add_roles(role)
                    await member.edit(nick=fresh_osu_data["username"])
                except:
                    pass
                await channel.send(content=f"{member.mention} i already know lol. here, have some roles")
                return

        async with self.bot.db.execute("SELECT user_id FROM users WHERE osu_id = ?",
                                       [str(fresh_osu_data["id"])]) as cursor:
            check_if_new_discord_account = await cursor.fetchone()
        if check_if_new_discord_account:
            if str(check_if_new_discord_account[0]) != str(member.id):
                old_user_id = check_if_new_discord_account[0]
                await channel.send(f"this osu account is already linked to <@{old_user_id}> in my database. "
                                   "if there's a problem, for example, you got a new discord account, ping kyuunex.")
                return

        try:
            await member.add_roles(role)
            await member.edit(nick=fresh_osu_data["username"])
        except:
            pass

        embed = await osuwebembed.user_array(fresh_osu_data)
        await self.bot.db.execute("DELETE FROM users WHERE user_id = ?", [str(member.id)])
        await self.bot.db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                                  [str(member.id), str(fresh_osu_data["id"]), str(fresh_osu_data["username"]),
                                   str(fresh_osu_data["join_date"]), str(fresh_osu_data["statistics"]["pp"]),
                                   str(fresh_osu_data["country_code"]), str(ranked_amount), "0"])
        await self.bot.db.commit()
        verified_message = await channel.send(content=f"`Verified: {escape_markdown(member.name)}` \n"
                                                      f"You should also read the rules if you haven't already.",
                                              embed=embed)

        await self.add_obligatory_reaction(verified_message, fresh_osu_data["country_code"])
        await self.check_group_roles(channel, member, member.guild, fresh_osu_data)

    async def member_is_already_verified_and_just_needs_roles(self, channel, member, user_db_lookup):
        ranked_amount = user_db_lookup[2]

        role = await self.get_role_based_on_reputation(member.guild, ranked_amount)
        await member.add_roles(role)
        try:
            fresh_osu_data = await self.bot.osuweb.get_user_array(user_db_lookup[0])
        except Exception as e:
            await channel.send("okay, i also can't check your osu profile. "
                               "although i do have your osu profile info in my database. "
                               "I'll just use the cached info then",
                               embed=await wrappers.embed_exception(e))
            fresh_osu_data = None

        if fresh_osu_data:
            name = fresh_osu_data["username"]
            embed = await osuwebembed.user_array(fresh_osu_data)
        else:
            name = user_db_lookup[1]
            embed = None

        await member.edit(nick=name)
        verified_message = await channel.send(f"Welcome aboard {member.mention}! Since we know who you are, "
                                              "I have automatically gave you appropriate roles. "
                                              "Enjoy your stay!",
                                              embed=embed)

        await self.add_obligatory_reaction(verified_message, fresh_osu_data["country_code"])
        await self.check_group_roles(channel, member, member.guild, fresh_osu_data)

    async def ask_just_joined_member_to_verify(self, channel, member):
        async with self.bot.db.execute("SELECT osu_id, osu_username, ranked_maps_amount FROM users WHERE user_id = ?",
                                       [str(member.id)]) as cursor:
            user_db_lookup = await cursor.fetchone()
        if user_db_lookup:
            await self.member_is_already_verified_and_just_needs_roles(channel, member, user_db_lookup)
            return

        try:
            fresh_osu_data = await self.bot.osuweb.get_user_array(member.name)
        except Exception as e:
            # connection issues
            await channel.send(f"Welcome {member.mention}! in this server, we have a verification system "
                               "for purposes of giving correct roles and dealing with raids. "
                               "Usually I would ask you to link your osu profile, "
                               "but i seem to be having trouble connecting to osu servers. "
                               "so, now I ask you link your profile and if it does not work, "
                               "wait patiently a little bit and then link your profile again. "
                               "worse case, managers will have to manually let you in. "
                               "it will just take time. ignore the error bellow, this is for the managers. ",
                               embed=await wrappers.embed_exception(e))
            return

        if (fresh_osu_data and
                (self.is_new_user(member) is False) and
                fresh_osu_data["statistics"]["pp"] and
                float(fresh_osu_data["statistics"]["pp"]) > 0):
            await channel.send(content=f"Welcome {member.mention}! We have a verification system in this server "
                                       "so we can give you appropriate roles and keep raids/spam out. \n"
                                       "Is this your osu! profile? "
                                       "If yes, type `yes`, if not, post a link to your profile.",
                               embed=await osuwebembed.small_user_array(fresh_osu_data))
        else:
            await channel.send(f"Welcome {member.mention}! We have a verification system in this server "
                               "so we can give you appropriate roles and keep raids/spam out. \n"
                               "Please post a link to your osu! profile and I will verify you instantly.")

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

    async def add_obligatory_reaction(self, message, country):
        try:
            if country:
                for stereotype in self.post_verification_emotes:
                    if country == stereotype[0]:
                        await message.add_reaction(stereotype[1])
        except Exception as e:
            print(e)

    async def get_role_from_db(self, setting, guild):
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [setting, str(guild.id)]) as cursor:
            role_id = await cursor.fetchone()
        return discord.utils.get(guild.roles, id=int(role_id[0]))

    async def get_role_based_on_reputation(self, guild, ranked_amount):
        if ranked_amount >= 10:
            return await self.get_role_from_db("experienced_mapper", guild)
        elif ranked_amount >= 1:
            return await self.get_role_from_db("ranked_mapper", guild)
        else:
            return await self.get_role_from_db("mapper", guild)

    def is_new_user(self, user):
        user_creation_ago = datetime.datetime.utcnow() - user.created_at
        if abs(user_creation_ago).total_seconds() / 2592000 <= 1 and user.avatar is None:
            return True
        else:
            return False

    async def check_group_roles(self, channel, member, guild, fresh_osu_data):
        group_roles = [
            [7, await self.get_role_from_db("nat", guild)],
            [28, await self.get_role_from_db("bn", guild)],
            [32, await self.get_role_from_db("bn", guild)],
        ]

        user_qualifies_for_these_roles = await self.get_user_qualified_group_roles(fresh_osu_data, group_roles)

        if user_qualifies_for_these_roles:
            for role_to_add in user_qualifies_for_these_roles:
                try:
                    await member.add_roles(role_to_add)
                    await channel.send(f"additionally, i applied the {role_to_add} role")
                except:
                    pass

    async def get_user_qualified_group_roles(self, fresh_osu_data, group_roles):
        return_list = []
        for group in fresh_osu_data["groups"]:
            for group_role in group_roles:
                if int(group["id"]) == int(group_role[0]):
                    return_list.append(group_role[1])
        return return_list


def setup(bot):
    bot.add_cog(MemberVerification(bot))
