import time
import asyncio
import discord
from discord.ext import commands
from modules import permissions
from modules import wrappers


class FakeUser:
    def __init__(self, cached_info):
        self.user_id = cached_info[0]
        self.id = cached_info[0]
        self.username = cached_info[1]
        self.name = cached_info[1]
        self.country = cached_info[2]

    def __str__(self):
        return self.username


class GroupFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.group_list = (
            (7, "Nomination Assessment Team"),
            (28, "Beatmap Nominators"),
            (32, "Beatmap Nominators (Probationary)"),
            (4, "Global Moderation Team"),
            (11, "Developers"),
            (16, "osu! Alumni"),
            (22, "Support Team"),
        )
        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.groupfeed_background_loop())
        )

    @commands.command(name="groupfeed_add", brief="Add a groupfeed in the current channel", description="")
    @commands.check(permissions.is_admin)
    async def groupfeed_add(self, ctx):
        await self.bot.db.execute("INSERT INTO groupfeed_channel_list VALUES (?)", [str(ctx.channel.id)])
        await self.bot.db.commit()
        await ctx.send(":ok_hand:")

    @commands.command(name="groupfeed_remove", brief="Remove a groupfeed from the current channel", description="")
    async def groupfeed_remove(self, ctx):
        await self.bot.db.execute("DELETE FROM groupfeed_channel_list WHERE channel_id = ?", [str(ctx.channel.id)])
        await self.bot.db.commit()
        await ctx.send(":ok_hand:")

    def unnest_group_member_id(self, group_members):
        buffer = []
        for one_member in group_members:
            buffer.append(str(one_member["id"]))
        return buffer

    async def get_changes(self, fresh_entries, group_id):
        async with await self.bot.db.execute("SELECT osu_id FROM groupfeed_group_members WHERE group_id = ?",
                                             [str(group_id)]) as cursor:
            cached_entries = await cursor.fetchall()
        if not cached_entries:
            # if we are here, it means this group has no members, which means it was recently tracked. 
            # therefore, we'll just put all users inside the db and return empty list
            print(f"populating the db for group {group_id}")

            for one_member in fresh_entries:
                await self.bot.db.execute("INSERT INTO groupfeed_group_members VALUES (?, ?)",
                                          [str(one_member["id"]), str(group_id)])
            await self.bot.db.commit()
            return []

        changes = []

        fresh_entries = self.unnest_group_member_id(fresh_entries)

        # this piece of code checks if there are new members that are not in local db
        cached_entries = wrappers.unnest_list(cached_entries)

        for fresh_member in fresh_entries:
            if not str(fresh_member) in cached_entries:
                await self.bot.db.execute("INSERT INTO groupfeed_group_members VALUES (?, ?)",
                                          [str(fresh_member), str(group_id)])
                changes.append([True, str(fresh_member)])

        await self.bot.db.commit()
        await asyncio.sleep(5)

        # this piece of code checks if there are members in db but not online
        for cached_member in cached_entries:
            if not str(cached_member) in fresh_entries:
                await self.bot.db.execute("DELETE FROM groupfeed_group_members WHERE osu_id = ? AND group_id = ?",
                                          [str(cached_member), str(group_id)])
                changes.append([False, str(cached_member)])

        await self.bot.db.commit()

        return changes

    async def execute_event(self, channel_list, event, group_id):
        group_name = self.get_group_name(group_id)

        if event[0]:
            print(f"groupfeed | {group_name} | added {event[1]}")
            description_template = "%s **%s**\nhas been added to\nthe **%s**"
            color = 0xffbd0e
        else:
            print(f"groupfeed | {group_name} | removed {event[1]}")
            description_template = "%s **%s**\nhas been removed from\nthe **%s**"
            color = 0x2c0e6c

        user = await self.bot.osu.get_user(u=event[1])

        if not user:
            # user is restricted
            async with await self.bot.db.execute("SELECT * FROM groupfeed_member_info WHERE osu_id = ?",
                                                 [str(event[1])]) as cursor:
                cached_info = await cursor.fetchone()
            if not cached_info:
                cached_info = (str(event[1]), "someone???", "white")
            user = FakeUser(cached_info)
            description_template = "%s **%s**\n**has gotten restricted lol**\nand has been removed from\nthe **%s**"
            color = 0x9e0000

        flag_sign = f":flag_{user.country.lower()}:"
        username = user.name

        what_group = f"[{group_name}](https://osu.ppy.sh/groups/{group_id})"
        what_user = f"[{username}](https://osu.ppy.sh/users/{event[1]})"
        thumbnail_url = f"https://a.ppy.sh/{event[1]}"

        description = description_template % (flag_sign, what_user, what_group)

        embed = await self.group_member(thumbnail_url, description, color)
        for channel_id in channel_list:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                await channel.send(embed=embed)

    async def populate_member_info(self, fresh_entries):
        async with await self.bot.db.execute("SELECT osu_id FROM groupfeed_member_info") as cursor:
            cached_info = await cursor.fetchall()
        cached_info = wrappers.unnest_list(cached_info)

        for fresh_member in fresh_entries:
            if not str(fresh_member["id"]) in cached_info:
                await self.bot.db.execute("INSERT INTO groupfeed_member_info VALUES (?, ?, ?)",
                                          [str(fresh_member["id"]), str(fresh_member["username"]),
                                           str(fresh_member["country"]["code"])])
        await self.bot.db.commit()

    async def check_group(self, channel_list, group_id):
        fresh_entries = await self.bot.osuweb.get_group_members(group_id)
        if not fresh_entries:
            print("groupfeed connection problems?")
            return None

        await self.populate_member_info(fresh_entries)

        events = await self.get_changes(fresh_entries, group_id)

        if events:
            for event in events:
                await self.execute_event(channel_list, event, group_id)

    async def groupfeed_background_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(10)

                async with await self.bot.db.execute("SELECT channel_id FROM groupfeed_channel_list") as cursor:
                    channel_list = await cursor.fetchall()
                if not channel_list:
                    await asyncio.sleep(1600)
                    continue

                print(time.strftime("%X %x %Z") + " | performing groupfeed check")

                channel_list = wrappers.unnest_list(channel_list)

                await self.check_group(channel_list, "7")
                await asyncio.sleep(120)
                await self.check_group(channel_list, "28")
                await asyncio.sleep(5)
                await self.check_group(channel_list, "32")
                await asyncio.sleep(120)
                await self.check_group(channel_list, "4")
                await asyncio.sleep(120)
                await self.check_group(channel_list, "11")
                await asyncio.sleep(120)
                await self.check_group(channel_list, "16")
                await asyncio.sleep(120)
                await self.check_group(channel_list, "22")

                print(time.strftime("%X %x %Z") + " | finished groupfeed check")

                await asyncio.sleep(1600)
            except Exception as e:
                print(time.strftime("%X %x %Z"))
                print("in groupfeed_background_loop")
                print(e)
                await asyncio.sleep(3600)

    def get_group_name(self, group_id):
        for group in self.group_list:
            if int(group_id) == group[0]:
                return str(group[1])
        return "Unknown group"

    async def group_member(self, thumbnail_url, description, color):
        embed = discord.Embed(
            description=description,
            color=color
        )
        embed.set_thumbnail(
            url=thumbnail_url
        )
        return embed


def setup(bot):
    bot.add_cog(GroupFeed(bot))
