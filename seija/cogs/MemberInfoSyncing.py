import dateutil
from discord.ext import commands
import discord
import time
import asyncio
import datetime
from aioosuwebapi import exceptions as aioosuwebapi_exceptions


class MemberInfoSyncing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.member_name_syncing_loop())
        )

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.name == after.name:
            return

        async with self.bot.db.execute("SELECT guild_id, channel_id FROM channels WHERE setting = ?",
                                       ["notices"]) as cursor:
            notices_channel_list = await cursor.fetchall()

        if not notices_channel_list:
            return

        async with self.bot.db.execute("SELECT user_id, osu_id, osu_username, osu_join_date, "
                                       "pp, country, ranked_maps_amount, kudosu, no_sync "
                                       "FROM users WHERE user_id = ?", [int(after.id)]) as cursor:
            query = await cursor.fetchone()

        if not query:
            return

        fresh_osu_data = await self.bot.osuweb.get_user_array(query[1])
        if not fresh_osu_data:
            return

        for this_guild in notices_channel_list:
            guild = self.bot.get_guild(int(this_guild[0]))

            notices_channel = self.bot.get_channel(int(this_guild[1]))

            if not notices_channel:
                continue

            member = guild.get_member(int(after.id))
            await self.sync_nickname(notices_channel, query, member, fresh_osu_data)

    async def member_name_syncing_loop(self):
        print("Member Info Syncing Loop launched!")

        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)

            print(time.strftime("%Y/%m/%d %H:%M:%S %Z") + " | member_name_syncing_loop start")

            async with self.bot.db.execute("SELECT guild_id, channel_id FROM channels WHERE setting = ?",
                                           ["notices"]) as cursor:
                guilds_to_sync = await cursor.fetchall()
            if not guilds_to_sync:
                await asyncio.sleep(14400)
                continue

            async with self.bot.db.execute("SELECT user_id, osu_id, osu_username, osu_join_date, pp, country, "
                                           "ranked_maps_amount, kudosu, no_sync, confirmed FROM users") as cursor:
                stored_user_info_list = await cursor.fetchall()

            async with self.bot.db.execute("SELECT guild_id, osu_id FROM restricted_users") as cursor:
                restricted_user_list = await cursor.fetchall()

            for guild_id, notices_channel_id in guilds_to_sync:
                guild = self.bot.get_guild(int(guild_id))
                notices_channel = self.bot.get_channel(int(notices_channel_id))

                await self.sync_the_guild(guild, notices_channel, restricted_user_list, stored_user_info_list)

            print(time.strftime("%Y/%m/%d %H:%M:%S %Z") + " | member_name_syncing_loop finished")
            await asyncio.sleep(14400)

    async def get_role_from_db(self, setting, guild):
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [setting, int(guild.id)]) as cursor:
            role_id = await cursor.fetchone()
        if not role_id:
            return None
        return guild.get_role(int(role_id[0]))

    async def sync_the_guild(self, guild, notices_channel, restricted_user_list, stored_user_info_list):
        mapper_roles = {
            10: await self.get_role_from_db("experienced_mapper", guild),
            1: await self.get_role_from_db("ranked_mapper", guild),
            0: await self.get_role_from_db("mapper", guild),
        }

        group_roles = [
            [7, await self.get_role_from_db("nat", guild)],
            [28, await self.get_role_from_db("bn", guild)],
            [32, await self.get_role_from_db("bn", guild)],
            [35, await self.get_role_from_db("fa", guild)],
        ]

        for member in guild.members:
            if member.bot:
                continue

            stored_user_info = self.get_cached_info(stored_user_info_list, member)
            if not stored_user_info:
                continue

            try:
                fresh_osu_data = await self.bot.osuweb.get_user_array(stored_user_info[1])
            except aioosuwebapi_exceptions.HTTPException as e:
                print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                print("in sync_the_guild, connection issues to osu api v2 servers")
                print("sleeping for 120 seconds")
                print(e)
                await asyncio.sleep(120)
                break

            if fresh_osu_data:
                await self.sync_nickname(notices_channel, stored_user_info, member, fresh_osu_data)
                await self.sync_mapper_roles(notices_channel, stored_user_info, member, mapper_roles, fresh_osu_data)
                await self.sync_group_roles(notices_channel, stored_user_info, member, group_roles, fresh_osu_data)

                await self.bot.db.execute("UPDATE users "
                                          "SET country = ?, pp = ?, osu_username = ?, "
                                          "ranked_maps_amount = ?, kudosu = ? WHERE user_id = ?",
                                          [str(fresh_osu_data["country_code"]), int(fresh_osu_data["statistics"]["pp"]),
                                           str(fresh_osu_data["username"]),
                                           int(fresh_osu_data["ranked_and_approved_beatmapset_count"]),
                                           int(fresh_osu_data["kudosu"]["total"]),
                                           int(member.id)])

                if fresh_osu_data.get('discord'):
                    if str(member) == str(fresh_osu_data.get('discord')):
                        if not int(stored_user_info[9]) == 1:
                            await self.bot.db.execute("UPDATE users SET confirmed = ? WHERE user_id = ?",
                                                      [1, int(member.id)])

                await self.bot.db.commit()

            await self.restrict_unrestrict_checks(fresh_osu_data, guild, stored_user_info,
                                                  restricted_user_list, member, notices_channel)
            await asyncio.sleep(1)

    async def restrict_unrestrict_checks(self, fresh_osu_data, guild, stored_user_info,
                                         restricted_user_list, member, notices_channel):
        is_not_restricted = bool(fresh_osu_data)

        if is_not_restricted:
            if (int(guild.id), int(stored_user_info[1])) in restricted_user_list:
                embed = await NoticesEmbeds.unrestricted(stored_user_info, member)
                await notices_channel.send(embed=embed)
                await self.bot.db.execute("DELETE FROM restricted_users "
                                          "WHERE guild_id = ? AND osu_id = ?",
                                          [int(guild.id), int(stored_user_info[1])])
                await self.bot.db.commit()
        else:
            # at this point we are sure that the user is restricted.
            if not (int(guild.id), int(stored_user_info[1])) in restricted_user_list:
                embed = await NoticesEmbeds.restricted(stored_user_info, member)
                await notices_channel.send(embed=embed)
                await self.bot.db.execute("INSERT INTO restricted_users VALUES (?,?)",
                                          [int(guild.id), int(stored_user_info[1])])
                await self.bot.db.commit()

    def get_cached_info(self, cached_user_info_list, member):
        for db_user in cached_user_info_list:
            if int(member.id) == int(db_user[0]):
                return db_user
        return None

    async def sync_nickname(self, notices_channel, stored_user_info, member, fresh_osu_data):
        if str(stored_user_info[2]) != str(fresh_osu_data["username"]):
            embed = await NoticesEmbeds.namechange(stored_user_info, member, fresh_osu_data)
            await notices_channel.send(embed=embed)

        if member.display_name != str(fresh_osu_data["username"]):
            now = datetime.datetime.now()
            if "04-01T" in str(now.isoformat()):
                return
            if "03-31T" in str(now.isoformat()):
                return
            if int(stored_user_info[8]) == 1:
                return
            if member.guild_permissions.administrator:
                return

            old_nickname = member.display_name
            try:
                await member.edit(nick=fresh_osu_data["username"])
                embed = await NoticesEmbeds.nickname_updated(stored_user_info, member, old_nickname, fresh_osu_data)
                await notices_channel.send(embed=embed)
            except discord.Forbidden as e:
                print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                print(f"in sync_nickname, error changing nickname of {member.display_name} ({member.id})")
                print(e)
                embed = await NoticesEmbeds.error_name_change(stored_user_info, member, old_nickname, fresh_osu_data)
                await notices_channel.send(embed=embed)

    async def sync_group_roles(self, notices_channel, stored_user_info, member, group_roles, fresh_osu_data):
        user_qualifies_for_these_roles = await self.get_user_qualified_group_roles(fresh_osu_data, group_roles)
        user_already_has_these_roles = await self.get_user_existing_group_roles(member, group_roles)

        if set(user_qualifies_for_these_roles) == set(user_already_has_these_roles):
            return

        changes = [None, None]

        if user_already_has_these_roles:
            for role_to_remove in user_already_has_these_roles:
                try:
                    await member.remove_roles(role_to_remove)
                    changes[1] = role_to_remove
                except discord.Forbidden as e:
                    print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                    print(f"no permissions to remove {role_to_remove.name} from {member.display_name}")
                    print(e)

        if user_qualifies_for_these_roles:
            for role_to_add in user_qualifies_for_these_roles:
                try:
                    await member.add_roles(role_to_add)
                    changes[0] = role_to_add
                except discord.Forbidden as e:
                    print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                    print(f"no permissions to add {role_to_add.name} to {member.display_name}")
                    print(e)

        embed = await NoticesEmbeds.group_role_change(stored_user_info, member, changes)
        await notices_channel.send(embed=embed)

    async def get_user_qualified_group_roles(self, fresh_osu_data, group_roles):
        return_list = []
        for group in fresh_osu_data["groups"]:
            for group_role in group_roles:
                if int(group["id"]) == int(group_role[0]):
                    return_list.append(group_role[1])
        return return_list

    async def get_user_existing_group_roles(self, member, group_roles):
        return_list = []
        for role in member.roles:
            for group_role in group_roles:
                if int(role.id) == int(group_role[1].id):
                    return_list.append(group_role[1])
        return list(dict.fromkeys(return_list))  # this has to happen since we use the same BN role for probation BNs

    async def sync_mapper_roles(self, notices_channel, stored_user_info, member, mapper_roles, fresh_osu_data):
        user_qualifies_for_this_role = await self.get_user_qualified_mapper_role(fresh_osu_data, mapper_roles)
        user_already_has_this_role = await self.get_user_existing_mapper_role(member, mapper_roles)

        if user_qualifies_for_this_role == user_already_has_this_role:
            return

        changes = [None, None]

        if user_already_has_this_role:
            try:
                await member.remove_roles(user_already_has_this_role)
                changes[1] = user_already_has_this_role
            except discord.Forbidden as e:
                print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                print(f"no permissions to remove {user_already_has_this_role.name} from {member.display_name}")
                print(e)

        if user_qualifies_for_this_role:
            try:
                await member.add_roles(user_qualifies_for_this_role)
                changes[0] = user_qualifies_for_this_role
            except discord.Forbidden as e:
                print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
                print(f"no permissions to add {user_qualifies_for_this_role.name} to {member.display_name}")
                print(e)

        embed = await NoticesEmbeds.mapper_role_change(stored_user_info, member, changes)
        await notices_channel.send(embed=embed)

    async def get_user_qualified_mapper_role(self, fresh_osu_data, mapper_roles):
        ranked_amount = fresh_osu_data["ranked_and_approved_beatmapset_count"]

        if ranked_amount >= 10:
            return mapper_roles[10]
        elif ranked_amount >= 1:
            return mapper_roles[1]
        else:
            return mapper_roles[0]

    async def get_user_existing_mapper_role(self, member, mapper_roles):
        for role in member.roles:
            for amount_required, mapper_role in mapper_roles.items():
                if int(role.id) == int(mapper_role.id):
                    return mapper_role
        return None


class NoticesEmbeds:
    @staticmethod
    async def nickname_updated(db_user, member, old_nickname, fresh_osu_data):
        embed = discord.Embed(
            color=0xbd3661,
            description=":pencil2: nickname updated",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="cached_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="current_osu_username", value=fresh_osu_data["username"], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="old_nickname", value=old_nickname, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    @staticmethod
    async def error_name_change(db_user, member, old_nickname, fresh_osu_data):
        embed = discord.Embed(
            color=0xFF0000,
            description=":anger: no perms to update nickname",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="cached_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="current_osu_username", value=fresh_osu_data["username"], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="old_nickname", value=old_nickname, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    @staticmethod
    async def namechange(db_user, member, fresh_osu_data):
        embed = discord.Embed(
            color=0xbd3661,
            description=":pen_ballpoint: namechange",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="old_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="new_osu_username", value=fresh_osu_data["username"], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        if int(db_user[1]) == 4116573:
            embed.set_footer(text="btw, this is bor. yes, i actually added this specific message for bor.")
        return embed

    @staticmethod
    async def group_role_change(db_user, member, changes):
        embed = discord.Embed(
            color=0xbd3661,
            description=":label: group role change",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="osu_username", value=db_user[2], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="added group role", value=changes[0], inline=False)
        embed.add_field(name="removed group role", value=changes[1], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    @staticmethod
    async def mapper_role_change(db_user, member, changes):
        embed = discord.Embed(
            color=0xbd3661,
            description=":map: mapper role change",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="osu_username", value=db_user[2], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="added mapper role", value=changes[0], inline=False)
        embed.add_field(name="removed mapper role", value=changes[1], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    @staticmethod
    async def unrestricted(db_user, member):
        embed = discord.Embed(
            color=0xbd3661,
            description=":tada: unrestricted lol",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="osu_username", value=db_user[2], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    @staticmethod
    async def restricted(db_user, member):
        embed = discord.Embed(
            color=0xbd3661,
            description=":hammer: restricted lmao",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="osu_username", value=db_user[2], inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed


async def setup(bot):
    await bot.add_cog(MemberInfoSyncing(bot))
