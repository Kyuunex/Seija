import time
import asyncio
import discord
from discord.ext import commands

from modules import permissions
from modules import wrappers
import osuwebembed


class RankFeed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.rankfeed_background_loop())
        )

    @commands.command(name="rankfeed_add", brief="Add a rankfeed in the current channel")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def add(self, ctx):
        """
        Start sending information about the latest ranked maps in the channel this command is typed in.
        """

        fresh_entries = await self.bot.osuweb.scrape_latest_ranked_beatmapsets()
        if not fresh_entries:
            await ctx.send("Connection issues with osu website???")
            return

        for mapset_metadata in fresh_entries["beatmapsets"]:
            mapset_id = mapset_metadata["id"]
            async with await self.bot.db.execute("SELECT mapset_id FROM rankfeed_history WHERE mapset_id = ?",
                                                 [str(mapset_id)]) as cursor:
                check_is_already_in_history = await cursor.fetchone()
            if not check_is_already_in_history:
                await self.bot.db.execute("INSERT INTO rankfeed_history VALUES (?)", [str(mapset_id)])

        await self.bot.db.commit()

        async with await self.bot.db.execute("SELECT channel_id FROM rankfeed_channel_list WHERE channel_id = ?",
                                             [str(ctx.channel.id)]) as cursor:
            check_is_channel_already_tracked = await cursor.fetchone()
        if check_is_channel_already_tracked:
            await ctx.send("Rankfeed is already tracked in this channel")
            return

        await self.bot.db.execute("INSERT INTO rankfeed_channel_list VALUES (?)", [str(ctx.channel.id)])
        await ctx.send(":ok_hand:")

        await self.bot.db.commit()

    @commands.command(name="rankfeed_remove", brief="Remove a rankfeed from the current channel")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def remove(self, ctx):
        """
        Stop sending information about the latest ranked maps in the current channel
        """

        await self.bot.db.execute("DELETE FROM rankfeed_channel_list WHERE channel_id = ?", [str(ctx.channel.id)])
        await self.bot.db.commit()
        await ctx.send(":ok_hand:")

    @commands.command(name="rankfeed_tracklist", brief="Show a list of channels where rankfeed is sent")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def tracklist(self, ctx):
        """
        Show a list of channels where information about the latest ranked maps are being sent.
        """

        async with await self.bot.db.execute("SELECT channel_id FROM rankfeed_channel_list") as cursor:
            tracklist = await cursor.fetchall()
        if not tracklist:
            await ctx.send("Rankfeed tracklist is empty")
            return

        buffer = ":notepad_spiral: **Channel list**\n\n"
        for one_entry in tracklist:
            buffer += f"<#{one_entry[0]}>\n"
        embed = discord.Embed(color=0xff6781)

        await wrappers.send_large_embed(ctx.channel, embed, buffer)

    async def rankfeed_background_loop(self):
        print("RankFeed Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(10)

                async with await self.bot.db.execute("SELECT channel_id FROM rankfeed_channel_list") as cursor:
                    rankfeed_channel_list = await cursor.fetchall()
                if not rankfeed_channel_list:
                    # Rankfeed is not enabled
                    await asyncio.sleep(3600)
                    continue

                async with await self.bot.db.execute("SELECT mapset_id FROM rankfeed_history") as cursor:
                    rankfeed_history_check = await cursor.fetchall()
                if not rankfeed_history_check:
                    print("no maps in history so i stop so i don't spam")
                    await asyncio.sleep(3600)
                    continue

                print(time.strftime("%X %x %Z") + " | performing rankfeed check")

                fresh_entries = await self.bot.osuweb.scrape_latest_ranked_beatmapsets()
                if not fresh_entries:
                    print("rankfeed connection issues with osu website???")
                    await asyncio.sleep(3600)
                    continue

                for mapset_metadata in fresh_entries["beatmapsets"]:
                    if mapset_metadata["status"] != "ranked":
                        continue

                    mapset_id = mapset_metadata["id"]
                    async with await self.bot.db.execute("SELECT mapset_id FROM rankfeed_history WHERE mapset_id = ?",
                                                         [str(mapset_id)]) as cursor:
                        check_is_already_in_history = await cursor.fetchone()
                    if check_is_already_in_history:
                        continue

                    embed = await osuwebembed.beatmapset(mapset_metadata, color=0xffc85a)
                    if not embed:
                        print("rankfeed embed returned nothing. this should not happen")
                        continue

                    for rankfeed_channel_id in rankfeed_channel_list:
                        channel = self.bot.get_channel(int(rankfeed_channel_id[0]))
                        if not channel:
                            await self.bot.db.execute("DELETE FROM rankfeed_channel_list WHERE channel_id = ?",
                                                      [str(rankfeed_channel_id[0])])
                            await self.bot.db.commit()
                            print(f"channel with id {rankfeed_channel_id[0]} no longer exists "
                                  "so I am removing it from the list")
                            continue

                        await channel.send(embed=embed)

                    await self.bot.db.execute("INSERT INTO rankfeed_history VALUES (?)", [str(mapset_id)])
                    await self.bot.db.commit()

                print(time.strftime("%X %x %Z") + " | finished rankfeed check")
                await asyncio.sleep(3600)
            except Exception as e:
                print(time.strftime("%X %x %Z"))
                print("in rankfeed_background_loop")
                print(e)
                await asyncio.sleep(3600)


def setup(bot):
    bot.add_cog(RankFeed(bot))
