from discord.ext import commands
import discord
import time
import asyncio
import datetime
import osuembed
from modules import wrappers


class MemberNameSyncing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.member_name_syncing_loop())
        )

        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.event_history_cleanup_loop())
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

    async def event_history_cleanup_loop(self):
        print("Event History Cleanup Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(10)
                print(time.strftime("%X %x %Z") + " | event_history_cleanup_loop start")
                before = int(time.time()) - 172800
                await self.bot.db.execute("DELETE FROM user_event_history WHERE timestamp < ?", [before])
                await self.bot.db.commit()
                print(time.strftime("%X %x %Z") + " | event_history_cleanup_loop finished")
                await asyncio.sleep(86400)
            except Exception as e:
                print(time.strftime("%X %x %Z"))
                print("in event_history_cleanup_loop")
                print(e)
                await asyncio.sleep(86400)

    async def member_name_syncing_loop(self):
        print("Member Name Syncing Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)
            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop start")
            async with self.bot.db.execute("SELECT guild_id, channel_id FROM channels WHERE setting = ?",
                                           ["member_mapping_feed"]) as cursor:
                member_mapping_feed_list = await cursor.fetchall()
            if not member_mapping_feed_list:
                await asyncio.sleep(14400)
                continue

            async with self.bot.db.execute("SELECT user_id, osu_id, osu_username, osu_join_date, "
                                           "pp, country, ranked_maps_amount, no_sync FROM users") as cursor:
                user_list = await cursor.fetchall()
            async with self.bot.db.execute("SELECT guild_id, osu_id FROM restricted_users") as cursor:
                restricted_user_list = await cursor.fetchall()

            for mapping_feed_channel_id in member_mapping_feed_list:

                feed_channel = self.bot.get_channel(int(mapping_feed_channel_id[1]))
                guild = self.bot.get_guild(int(mapping_feed_channel_id[0]))

                async with self.bot.db.execute("SELECT channel_id FROM channels WHERE setting = ? AND guild_id = ?",
                                               ["notices", str(guild.id)]) as cursor:
                    guild_notices_channel = await cursor.fetchall()

                notices_channel = self.bot.get_channel(int(guild_notices_channel[0][0]))

                await self.cycle_through_members(feed_channel, guild, notices_channel, restricted_user_list, user_list)

            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop finished")
            await asyncio.sleep(14400)

    async def cycle_through_members(self, feed_channel, guild, notices_channel, restricted_user_list, user_list):
        for member in guild.members:
            if member.bot:
                continue

            for db_user in user_list:
                if str(member.id) != str(db_user[0]):
                    continue

                try:
                    osu_profile = await self.bot.osu.get_user(u=db_user[1], event_days="1")
                except Exception as e:
                    print(e)
                    await asyncio.sleep(120)
                    break

                if osu_profile:
                    await self.sync_nickname(notices_channel, db_user, member, osu_profile)
                    await self.check_events(feed_channel, osu_profile)

                    if (str(guild.id), str(db_user[1])) in restricted_user_list:
                        embed = await self.embed_unrestricted(db_user, member)
                        await notices_channel.send(embed=embed)
                        await self.bot.db.execute("DELETE FROM restricted_users "
                                                  "WHERE guild_id = ? AND osu_id = ?",
                                                  [str(guild.id), str(db_user[1])])
                        await self.bot.db.commit()
                else:
                    # at this point we are sure that the user is restricted.
                    if not (str(guild.id), str(db_user[1])) in restricted_user_list:
                        embed = await self.embed_restricted(db_user, member)
                        await notices_channel.send(embed=embed)
                        await self.bot.db.execute("INSERT INTO restricted_users VALUES (?,?)",
                                                  [str(guild.id), str(db_user[1])])
                        await self.bot.db.commit()
                await asyncio.sleep(1)

    async def embed_unrestricted(self, db_user, member):
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

    async def embed_restricted(self, db_user, member):
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

    async def sync_nickname(self, notices_channel, db_user, member, osu_profile):
        if str(db_user[2]) != osu_profile.name:
            embed = await self.embed_namechange(db_user, member, osu_profile)
            await notices_channel.send(embed=embed)

        if member.display_name != osu_profile.name:
            await self.apply_nickname(db_user, member, notices_channel, osu_profile)

        await self.bot.db.execute("UPDATE users SET country = ?, pp = ?, "
                                  "osu_join_date = ?, osu_username = ? WHERE user_id = ?;",
                                  [str(osu_profile.country), str(osu_profile.pp_raw),
                                   str(osu_profile.join_date), str(osu_profile.name), str(member.id)])
        await self.bot.db.commit()

    async def embed_namechange(self, db_user, member, osu_profile):
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
            embed = await self.embed_nickname_updated(db_user, member, old_nickname, osu_profile)
            await notices_channel.send(embed=embed)
        except:
            embed = await self.embed_error_name_change(db_user, member, old_nickname, osu_profile)
            await notices_channel.send(embed=embed)

    async def embed_nickname_updated(self, db_user, member, old_nickname, osu_profile):
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

    async def embed_error_name_change(self, db_user, member, old_nickname, osu_profile):
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

    async def check_events(self, channel, user):
        for event in user.events:
            async with self.bot.db.execute("SELECT event_id FROM user_event_history WHERE event_id = ?",
                                           [str(event.id)]) as cursor:
                is_history_not_empty = await cursor.fetchall()

            if is_history_not_empty:
                return

            await self.bot.db.execute("INSERT INTO user_event_history VALUES (?, ?, ?, ?)",
                                      [str(user.id), str(event.id), str(channel.id), str(int(time.time()))])
            await self.bot.db.commit()

            event_color = await self.get_event_color(event.display_text)

            if not event_color:
                return

            result = await self.bot.osu.get_beatmapset(s=event.beatmapset_id)
            embed = await osuembed.beatmapset(result, event_color)

            if not embed:
                return

            display_text = event.display_text.replace("@", "")
            await channel.send(display_text, embed=embed)

    async def get_event_color(self, event_description):
        if "has submitted" in event_description:
            return 0x2a52b2
        elif "has updated" in event_description:
            # return 0xb2532a
            return None
        elif "qualified" in event_description:
            return 0x2ecc71
        elif "has been revived" in event_description:
            return 0xff93c9
        elif "has been deleted" in event_description:
            return 0xf2d7d5
        else:
            return None


def setup(bot):
    bot.add_cog(MemberNameSyncing(bot))
