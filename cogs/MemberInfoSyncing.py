from discord.ext import commands
import discord
import time
import asyncio
import datetime


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
                                       "pp, country, ranked_maps_amount, no_sync "
                                       "FROM users WHERE user_id = ?", [str(after.id)]) as cursor:
            query = await cursor.fetchone()

        if not query:
            return

        osu_profile = await self.bot.osu.get_user(u=query[1])
        if not osu_profile:
            return

        for this_guild in notices_channel_list:
            guild = self.bot.get_guild(int(this_guild[0]))

            notices_channel = self.bot.get_channel(int(this_guild[1]))

            if not notices_channel:
                continue

            member = guild.get_member(int(after.id))
            await self.sync_nickname(notices_channel, query, member, osu_profile)

    async def member_name_syncing_loop(self):
        print("Member Info Syncing Loop launched!")

        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)

            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop start")

            async with self.bot.db.execute("SELECT guild_id, channel_id FROM channels WHERE setting = ?",
                                           ["notices"]) as cursor:
                guilds_to_sync = await cursor.fetchall()
            if not guilds_to_sync:
                await asyncio.sleep(14400)
                continue

            async with self.bot.db.execute("SELECT user_id, osu_id, osu_username, osu_join_date, "
                                           "pp, country, ranked_maps_amount, no_sync FROM users") as cursor:
                stored_user_info_list = await cursor.fetchall()

            async with self.bot.db.execute("SELECT guild_id, osu_id FROM restricted_users") as cursor:
                restricted_user_list = await cursor.fetchall()

            for guild_id, notices_channel_id in guilds_to_sync:
                guild = self.bot.get_guild(int(guild_id))
                notices_channel = self.bot.get_channel(int(notices_channel_id))

                await self.sync_the_guild(guild, notices_channel, restricted_user_list, stored_user_info_list)

            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop finished")
            await asyncio.sleep(14400)

    async def sync_the_guild(self, guild, notices_channel, restricted_user_list, stored_user_info_list):
        for member in guild.members:
            if member.bot:
                continue

            stored_user_info = self.get_cached_info(stored_user_info_list, member)
            if not stored_user_info:
                continue

            try:
                # fresh_osu_data = await self.bot.osuweb.get_user_array(stored_user_info[1])
                osu_profile = await self.bot.osu.get_user(u=stored_user_info[1], event_days="1")
            except Exception as e:
                print(e)
                await asyncio.sleep(120)
                break

            if osu_profile:
                await self.sync_nickname(notices_channel, stored_user_info, member, osu_profile)

                await self.bot.db.execute("UPDATE users SET country = ?, pp = ?, "
                                          "osu_join_date = ?, osu_username = ? WHERE user_id = ?;",
                                          [str(osu_profile.country), str(osu_profile.pp_raw),
                                           str(osu_profile.join_date), str(osu_profile.name), str(member.id)])
                await self.bot.db.commit()

            await self.restrict_unrestrict_checks(osu_profile, guild, stored_user_info,
                                                  restricted_user_list, member, notices_channel)
            await asyncio.sleep(1)

    async def restrict_unrestrict_checks(self, osu_profile, guild, stored_user_info,
                                         restricted_user_list, member, notices_channel):
        is_not_restricted = bool(osu_profile)

        if is_not_restricted:
            if (str(guild.id), str(stored_user_info[1])) in restricted_user_list:
                embed = await NoticesEmbeds.unrestricted(stored_user_info, member)
                await notices_channel.send(embed=embed)
                await self.bot.db.execute("DELETE FROM restricted_users "
                                          "WHERE guild_id = ? AND osu_id = ?",
                                          [str(guild.id), str(stored_user_info[1])])
                await self.bot.db.commit()
        else:
            # at this point we are sure that the user is restricted.
            if not (str(guild.id), str(stored_user_info[1])) in restricted_user_list:
                embed = await NoticesEmbeds.restricted(stored_user_info, member)
                await notices_channel.send(embed=embed)
                await self.bot.db.execute("INSERT INTO restricted_users VALUES (?,?)",
                                          [str(guild.id), str(stored_user_info[1])])
                await self.bot.db.commit()

    def get_cached_info(self, cached_user_info_list, member):
        for db_user in cached_user_info_list:
            if str(member.id) == str(db_user[0]):
                return db_user
        return None

    async def sync_nickname(self, notices_channel, db_user, member, osu_profile):
        if str(db_user[2]) != osu_profile.name:
            embed = await NoticesEmbeds.namechange(db_user, member, osu_profile)
            await notices_channel.send(embed=embed)

        if member.display_name != osu_profile.name:
            await self.apply_nickname(db_user, member, notices_channel, osu_profile)

    async def apply_nickname(self, db_user, member, notices_channel, osu_profile):
        now = datetime.datetime.now()
        if "04-01T" in str(now.isoformat()):
            return
        if "03-31T" in str(now.isoformat()):
            return
        if "1" in str(db_user[7]):
            return
        try:
            if member.guild_permissions.administrator:
                return
        except:
            return

        old_nickname = member.display_name
        try:
            await member.edit(nick=osu_profile.name)
            embed = await NoticesEmbeds.nickname_updated(db_user, member, old_nickname, osu_profile)
            await notices_channel.send(embed=embed)
        except:
            embed = await NoticesEmbeds.error_name_change(db_user, member, old_nickname, osu_profile)
            await notices_channel.send(embed=embed)


class NoticesEmbeds:
    @staticmethod
    async def nickname_updated(db_user, member, old_nickname, osu_profile):
        embed = discord.Embed(
            color=0xbd3661,
            description=":pencil2: nickname updated",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="cached_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="current_osu_username", value=osu_profile.name, inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="old_nickname", value=old_nickname, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        return embed

    @staticmethod
    async def error_name_change(db_user, member, old_nickname, osu_profile):
        embed = discord.Embed(
            color=0xFF0000,
            description=":anger: no perms to update nickname",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="cached_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="current_osu_username", value=osu_profile.name, inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.add_field(name="old_nickname", value=old_nickname, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        return embed

    @staticmethod
    async def namechange(db_user, member, osu_profile):
        embed = discord.Embed(
            color=0xbd3661,
            description=":pen_ballpoint: namechange",
            title=member.display_name,
            url=f"https://osu.ppy.sh/users/{db_user[1]}"
        )
        embed.add_field(name="user", value=member.mention, inline=False)
        embed.add_field(name="old_osu_username", value=db_user[2], inline=False)
        embed.add_field(name="new_osu_username", value=osu_profile.name, inline=False)
        embed.add_field(name="osu_id", value=db_user[1], inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        if str(db_user[1]) == str(4116573):
            embed.set_footer(text="btw, this is bor. yes, i actually added this specific message for bor.")
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
        embed.set_thumbnail(url=member.avatar_url)
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
        embed.set_thumbnail(url=member.avatar_url)
        return embed


def setup(bot):
    bot.add_cog(MemberInfoSyncing(bot))
