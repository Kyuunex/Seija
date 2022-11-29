import time
import asyncio
import dateutil
import discord
from discord.ext import commands
from seija.reusables import exceptions
from seija.reusables import list_helpers
from seija.modules import permissions
import json
from seija.embeds import oldembeds as osuembed
from aioosuapi import exceptions as aioosuapi_exceptions
from aioosuwebapi import exceptions as aioosuwebapi_exceptions


class ModChecker(commands.Cog):
    # TODO: add event inserts in db upon track
    def __init__(self, bot):
        self.bot = bot
        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.mod_checker_background_loop())
        )

    async def can_manage_mapset_channel(self, ctx):
        if await permissions.is_admin(ctx):
            return True
        async with self.bot.db.execute("SELECT user_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    async def is_a_mapset_channel(self, ctx):
        async with self.bot.db.execute("SELECT channel_id FROM mapset_channels WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    @commands.command(name="track", brief="Track the mapset in this channel")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def track(self, ctx, tracking_mode="timeline"):
        """
        This tracks the mapset.
        The ID used will be the one specified upon channel creation or set using set_id command.

        tracking_mode: 'timeline' or 'notification'

        timeline mode example: https://i.imgur.com/3pHW9FM.png
        notification mode example: https://i.imgur.com/e2LwWh2.png
        """

        if not await self.can_manage_mapset_channel(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to do this lol")
            return

        if not await self.is_a_mapset_channel(ctx):
            await ctx.send(f"{ctx.author.mention} this command only works in mapset channels lol")
            return

        if tracking_mode.isdigit():
            await ctx.send("you are using the command incorrectly")
            return

        if tracking_mode == "timeline":
            tracking_mode = 1
        elif tracking_mode == "notification":
            tracking_mode = 2
        else:
            await ctx.send("you are using the command incorrectly")
            return

        async with self.bot.db.execute("SELECT mapset_id FROM mod_tracking WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            is_tracked = await cursor.fetchone()
        if is_tracked:
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(ctx.channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(ctx.channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE channel_id = ?", [int(ctx.channel.id)])
            await ctx.send("Deleted all previously existing tracking records in this channel")
            await asyncio.sleep(1)

        async with self.bot.db.execute("SELECT mapset_id FROM mapset_channels WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            mapset_id = await cursor.fetchone()

        if not mapset_id or int(mapset_id[0]) == 0:
            await ctx.send("Set a mapset id for this channel first, using the `.set_id (mapset_id)` command.")
            return

        try:
            discussions = await self.bot.osuscraper.scrape_beatmapset_discussions_array(str(mapset_id[0]))
        except aioosuwebapi_exceptions.HTTPException as e:
            await ctx.send("I am having connection issues with osu servers, try again later", 
                           embed=await exceptions.embed_exception(e))
            return

        if not discussions:
            await ctx.send("I am unable to find a modding v2 page for this mapset, this is odd, are you trolling?")
            return

        if discussions["beatmapset"]["status"] == "graveyard" or discussions["beatmapset"]["status"] == "ranked":
            await ctx.send("i refuse to track graveyarded and ranked sets")
            return

        if tracking_mode == 1:
            await self.insert_mod_history_in_db(discussions, int(ctx.channel.id))

        await self.insert_nomination_history_in_db(discussions, int(ctx.channel.id))

        await self.bot.db.execute("INSERT INTO mod_tracking VALUES (?,?,?,?)",
                                  [int(mapset_id[0]), int(ctx.channel.id), int(tracking_mode), 1800])

        try:
            # TODO: this should not have to be necessary, maybe after new api is out,
            #  we can just build the embed with the discussions response

            beatmap_object = await self.bot.osu.get_beatmapset(s=str(mapset_id[0]))
            embed = await osuembed.beatmapset(beatmap_object)
        except aioosuapi_exceptions.HTTPException as e:
            embed = None
            await ctx.send("I am having connection issues but i still managed to track this idk what happened lol",
                           embed=await exceptions.embed_exception(e))

        await ctx.send("Tracked", embed=embed)

        try:
            await self.unarchive_channel(ctx, "mapset")
        except discord.Forbidden as e:
            await ctx.send("I seem to be having a problem unarchiving the channel. maybe permissions are messed up??",
                           embed=await exceptions.embed_exception(e))

        await self.bot.db.commit()

    @commands.command(name="untrack", brief="Untrack everything in this channel")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def untrack(self, ctx):
        """
        This command will untrack anything that is tracked in this channel.
        """

        if not await self.can_manage_mapset_channel(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to do this lol")
            return

        if not await self.is_a_mapset_channel(ctx):
            await ctx.send(f"{ctx.author.mention} this command only works in mapset channels lol")
            return

        await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE channel_id = ?", [int(ctx.channel.id)])

        await ctx.send("Untracked everything in this channel")

        await self.bot.db.commit()

    @commands.command(name="force_track", brief="Forcefully track a mapset in the current channel")
    @commands.guild_only()
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def force_track(self, ctx, mapset_id, tracking_mode=1):
        """
        Forcefully track any mapset in any channel

        mapset_id: Literally the Mapset ID
        tracking_mode: Tracking mode 1 or 2
        """

        if not mapset_id.isdigit():
            await ctx.send("a mapset_id is supposed to be all numbers")
            return

        if not (tracking_mode == 1 or tracking_mode == 2):
            await ctx.send("tracking mode can either be `notification` or `timeline`")
            return

        async with self.bot.db.execute("SELECT mapset_id FROM mod_tracking "
                                       "WHERE mapset_id = ? AND channel_id = ?",
                                       [int(mapset_id), int(ctx.channel.id)]) as cursor:
            mapset_is_already_tracked = await cursor.fetchone()
        if mapset_is_already_tracked:
            await ctx.send("This mapset is already tracked in this channel")
            return

        try:
            discussions = await self.bot.osuscraper.scrape_beatmapset_discussions_array(int(mapset_id))
        except aioosuwebapi_exceptions.HTTPException as e:
            await ctx.send("connection issues bla bla bla", embed=await exceptions.embed_exception(e))
            return

        if not discussions:
            await ctx.send("I am unable to find a modding v2 page for this mapset")
            return

        if discussions["beatmapset"]["status"] == "graveyard" or discussions["beatmapset"]["status"] == "ranked":
            await ctx.send("i refuse to track graveyarded and ranked sets")
            return

        await self.insert_mod_history_in_db(discussions, int(ctx.channel.id))
        await self.insert_nomination_history_in_db(discussions, int(ctx.channel.id))

        await self.bot.db.execute("INSERT INTO mod_tracking VALUES (?,?,?,?)",
                                  [int(mapset_id), int(ctx.channel.id), tracking_mode, 1800])

        try:
            result = await self.bot.osu.get_beatmapset(s=mapset_id)
            embed = await osuembed.beatmapset(result)

            await ctx.send(f"forcefully tracked in {tracking_mode} mode", embed=embed)
        except aioosuapi_exceptions.HTTPException as e:
            # same as in track
            await ctx.send("tracked", embed=await exceptions.embed_exception(e))

        await self.bot.db.commit()

    @commands.command(name="force_untrack", brief="Forcefully untrack a mapset in the current channel")
    @commands.guild_only()
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def force_untrack(self, ctx, mapset_id):
        """
        Forcefully untrack any mapset from any channel

        mapset_id: Literally the Mapset ID
        """

        if not mapset_id.isdigit():
            await ctx.send("a mapset_id is supposed to be all numbers")
            return

        await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                  [int(mapset_id), int(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mod_post_history WHERE mapset_id = ? AND channel_id = ?",
                                  [int(mapset_id), int(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE mapset_id = ? AND channel_id = ?",
                                  [int(mapset_id), int(ctx.channel.id)])

        try:
            result = await self.bot.osu.get_beatmapset(s=mapset_id)
            embed = await osuembed.beatmapset(result)
            await ctx.send("I untracked this mapset in this channel", embed=embed)
        except aioosuapi_exceptions.HTTPException as e:
            await ctx.send("done", embed=await exceptions.embed_exception(e))

        await self.bot.db.commit()

    @commands.command(name="sublist", brief="List all tracked mapsets everywhere")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def sublist(self, ctx):
        """
        List all mapset channels that exist everywhere
        """

        async with self.bot.db.execute("SELECT mapset_id, channel_id, mode FROM mod_tracking") as cursor:
            track_list = await cursor.fetchall()

        if not track_list:
            await ctx.send("there are no mapset channels anywhere")
            return

        # TODO: maybe we can combine everything in one message instead of spamming mesages?
        for mapset in track_list:
            try:
                result = await self.bot.osu.get_beatmapset(s=str(mapset[0]))
                embed = await osuembed.beatmapset(result)
            except aioosuapi_exceptions.HTTPException as e:
                await ctx.send("Connection issues?", embed=await exceptions.embed_exception(e))
                embed = None
            await ctx.send(content="mapset_id `%s` | channel <#%s> | tracking_mode `%s`" % mapset, embed=embed)

    async def mod_checker_background_loop(self):
        print("Mod checking Background Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)

            async with self.bot.db.execute("SELECT mapset_id, channel_id, mode FROM mod_tracking") as cursor:
                track_list = await cursor.fetchall()

            for track_entry in track_list:
                channel = self.bot.get_channel(int(track_entry[1]))

                if not channel:
                    print(f"channel {track_entry[1]} is deleted for mapset {track_entry[0]}")
                    await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?",
                                              [int(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mapset_channels WHERE channel_id = ?", [int(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE channel_id = ?",
                                              [int(track_entry[1])])
                    await self.bot.db.commit()
                    continue

                mapset_id = int(track_entry[0])
                tracking_mode = int(track_entry[2])

                # okay, so this may seem kinda pointless, but sometimes,
                # it can happen and has already happened that a user may untrack something
                # while the bot is still going through the loop
                # and the bot not seeing any mods in db so it spams literally every mod
                # so this check was added
                async with self.bot.db.execute("SELECT mapset_id, channel_id, mode FROM mod_tracking "
                                               "WHERE mapset_id = ? AND channel_id = ? AND mode = ?",
                                               [int(mapset_id), int(channel.id), int(tracking_mode)]) as cursor:
                    is_no_longer_tracked = await cursor.fetchone()
                if not is_no_longer_tracked:
                    continue

                try:
                    discussions = await self.bot.osuscraper.scrape_beatmapset_discussions_array(mapset_id)
                    if not discussions:
                        # if we are here,
                        # it means the mapset someone got tracked but there is no discussions page for it
                        # TODO: i'll deal with this when the new api comes out
                        continue
                except aioosuwebapi_exceptions.HTTPException as e:
                    # pretty much connection issues
                    print(e)
                    await asyncio.sleep(300)
                    continue

                if not await self.check_status(channel, mapset_id, discussions):
                    continue

                if tracking_mode == 1:
                    await self.timeline_mode_tracking(discussions, channel, mapset_id, tracking_mode)
                elif tracking_mode == 2:
                    await self.notification_mode_tracking(discussions, channel, mapset_id)

                await self.check_nomination_status(discussions, channel, mapset_id, tracking_mode)
                await asyncio.sleep(120)
            await asyncio.sleep(1800)

    async def insert_mod_history_in_db(self, discussions, channel_id):
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if "posts" in mod:
                    for post in mod["posts"]:
                        if post:
                            await self.bot.db.execute("INSERT INTO mod_post_history VALUES (?,?,?)",
                                                      [int(post["id"]), int(mod["beatmapset_id"]), int(channel_id)])
        await self.bot.db.commit()

    async def insert_nomination_history_in_db(self, discussions, channel_id):
        mapset_id = discussions["beatmapset"]["id"]
        async with self.bot.db.execute("SELECT event_id FROM mapset_nomination_history "
                                       "WHERE channel_id = ? AND mapset_id = ?",
                                       [int(channel_id), int(mapset_id)]) as cursor:
            history = await cursor.fetchall()
        for event in discussions["beatmapset"]["events"]:
            if event:
                if self.get_icon(event["type"]):
                    if not list_helpers.in_db_list(history, int(event["id"])):
                        await self.bot.db.execute("INSERT INTO mapset_nomination_history VALUES (?,?,?)",
                                                  [int(event["id"]), int(mapset_id), int(channel_id)])
        await self.bot.db.commit()

    async def check_status(self, channel, mapset_id, discussions):
        # TODO: add back embeds here, when new api comes out maybe, could reuse some api requests
        if not discussions:
            status = "deleted"
        else:
            status = discussions["beatmapset"]["status"]

        if (status == "wip") or (status == "qualified") or (status == "pending"):
            return True
        elif status == "graveyard":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is graveyarded, so I am untracking it. "
                                       "I don't wanna track dead sets. "
                                       "You can track again after it's ungraveyarded "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            return None
        elif status == "deleted":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is deleted, so I am untracking it. "
                                       "why tho????????????? channel archived and will be nuked in a week "
                                       "along with it's role. "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                           ["mapset_archive", int(channel.guild.id)]) as cursor:
                guild_archive_category_id = await cursor.fetchall()
            if guild_archive_category_id:
                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await channel.edit(reason="mapset deleted!", category=archive_category)
            return None
        elif status == "ranked":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_nomination_history WHERE mapset_id = ? AND channel_id = ?",
                                      [int(mapset_id), int(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is ranked, so I am untracking it. "
                                       "There is no point in continuing to do so. "
                                       "Channel archived! "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            async with self.bot.db.execute("SELECT category_id FROM categories "
                                           "WHERE setting = ? AND guild_id = ?",
                                           ["mapset_archive", int(channel.guild.id)]) as cursor:
                guild_archive_category_id = await cursor.fetchall()
            if guild_archive_category_id:
                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await channel.edit(reason="mapset ranked!", category=archive_category)
            return None
        else:
            await channel.send(content="<@155976140073205761> something went wrong, please check the console output.")
            print(f"{status} / {mapset_id}")
            return None

    async def timeline_mode_tracking(self, discussions, channel, mapset_id, tracking_mode):
        async with self.bot.db.execute("SELECT post_id FROM mod_post_history WHERE channel_id = ?",
                                       [int(channel.id)]) as cursor:
            history = await cursor.fetchall()
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if "posts" in mod:
                    for post in mod["posts"]:
                        if post:
                            if not list_helpers.in_db_list(history, int(post["id"])):
                                await self.bot.db.execute("INSERT INTO mod_post_history VALUES (?,?,?)",
                                                          [int(post["id"]), int(mapset_id), int(channel.id)])
                                await self.bot.db.commit()
                                if ((not post["system"]) and
                                        (not post["message"] == "r") and
                                        (not post["message"] == "res") and
                                        (not post["message"] == "resolved")):
                                    post_to_post = await self.mod_post_embed(post, discussions, mod, tracking_mode)
                                    if post_to_post:
                                        await channel.send(embed=post_to_post)

    async def notification_mode_tracking(self, discussions, channel, mapset_id):
        diffs_lol = discussions["beatmapset"]["beatmaps"]
        diffs_lol.append({"id": 0, "version": "All difficulties"})
        for one_difficulty in diffs_lol:
            diff_id = one_difficulty["id"]
            diff_status = await self.check_if_diff_resolved(discussions, diff_id)  # 1 - new mods, 0 - no new mods

            async with self.bot.db.execute("SELECT status FROM mapset_notification_status "
                                           "WHERE mapset_id = ? AND map_id = ? AND channel_id = ?",
                                           [int(mapset_id), int(diff_id), int(channel.id)]) as cursor:
                cached_status_db = await cursor.fetchone()
            if not cached_status_db:
                await self.bot.db.execute("INSERT INTO mapset_notification_status VALUES (?, ?, ?, ?)",
                                          [int(mapset_id), int(diff_id), int(channel.id), int(diff_status)])
                await self.bot.db.commit()
                continue

            cached_status = cached_status_db[0]
            if cached_status != diff_status:
                await self.bot.db.execute("UPDATE mapset_notification_status SET status = ? "
                                          "WHERE mapset_id = ? AND map_id = ? AND channel_id = ?",
                                          [int(diff_status), int(mapset_id), int(diff_id), int(channel.id)])
                await self.bot.db.commit()
                if diff_status == 1:
                    return_message = ""
                    async with self.bot.db.execute("SELECT user_id FROM difficulty_claims WHERE map_id = ?",
                                                   [int(diff_id)]) as cursor:
                        map_owner = await cursor.fetchone()
                    if map_owner:
                        return_message += f"<@{map_owner[0]}> "
                        # TODO: fix the allowed_mentions bullshittery
                        # allowed_mentions=discord.AllowedMentions(users=True)
                    return_message += "new mod(s) on: "
                    return_message += f"**{one_difficulty['version']}**. "
                    return_message += "no further notifications until all mods are resolved for this diff"
                    await channel.send(return_message.replace("@", ""))

    async def check_nomination_status(self, discussions, channel, mapset_id, tracking_mode):
        async with self.bot.db.execute("SELECT event_id FROM mapset_nomination_history WHERE channel_id = ?",
                                       [int(channel.id)]) as cursor:
            history = await cursor.fetchall()
        for event in discussions["beatmapset"]["events"]:
            if event:
                if self.get_icon(event["type"]):
                    if not list_helpers.in_db_list(history, int(event["id"])):
                        await self.bot.db.execute("INSERT INTO mapset_nomination_history VALUES (?,?,?)",
                                                  [int(event["id"]), int(mapset_id), int(channel.id)])
                        await self.bot.db.commit()
                        event_to_post = await self.nomnom_embed(event, discussions, tracking_mode)
                        if event_to_post:
                            await channel.send(embed=event_to_post)

        return None

    def get_icon(self, type):
        if type == "nomination_reset":
            return {
                "text": ":anger_right: Nomination Reset",
                "color": 0xfc7b03,
            }
        elif type == "disqualify":
            return {
                "text": ":broken_heart: Disqualified",
                "color": 0xfc0303,
            }
        elif type == "nominate":
            return {
                "text": ":thought_balloon: Nominated",
                "color": 0x03fc6f,
            }
        elif type == "qualify":
            return {
                "text": ":heart: Qualified",
                "color": 0x0373fc,
            }
        elif type == "rank":
            return {
                "text": ":sparkling_heart: Ranked",
                "color": 0x0373fc,
            }
        return None

    async def check_if_resolved(self, discussions):
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if not mod["resolved"]:
                    return 1

    async def check_if_diff_resolved(self, discussions, diff_id):
        diff_id = int(diff_id)

        if diff_id == 0:
            diff_id = None

        for mod in discussions["beatmapset"]["discussions"]:
            if mod and mod['beatmap_id'] == diff_id:
                if not mod["resolved"]:
                    return 1
        return 0

    async def get_unresolved_diffs(self, discussions):
        return_list = []
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if not mod["resolved"]:
                    if not mod["beatmap_id"]:
                        if not False in return_list:
                            return_list.append(False)
                    else:
                        if not int(mod["beatmap_id"] in return_list):
                            return_list.append(int(mod["beatmap_id"]))
        return return_list

    async def nomnom_embed(self, event, discussions, tracking_mode):
        if not event:
            return None

        title = ""

        icon = self.get_icon(event["type"])

        embed = discord.Embed(
            title=title,
            url=f"https://osu.ppy.sh/beatmapsets/{discussions['beatmapset']['id']}/discussion",
            description=str(icon["text"]),
            color=icon["color"]
        )
        if event["user_id"]:
            embed.set_author(
                name=str(self.get_username_with_group(discussions["beatmapset"]["related_users"], event["user_id"])),
                url=f"https://osu.ppy.sh/users/{event['user_id']}",
                icon_url=f"https://a.ppy.sh/{event['user_id']}"
            )
        embed.set_thumbnail(
            url=f"https://b.ppy.sh/thumb/{discussions['beatmapset']['id']}l.jpg"
        )
        created_at = dateutil.parser.parse(event['created_at'])
        embed.set_footer(
            text=str(created_at.isoformat(' ')),
        )
        return embed

    async def mod_post_embed(self, post, discussions, mod, tracking_mode):
        if not post:
            return None

        mapset_diff_name = str(self.get_diff_name(discussions["beatmapset"]["beatmaps"], mod["beatmap_id"]))
        title = mapset_diff_name

        footer = self.get_mod_type(mod)

        mod_post_contents = await self.build_mod_post_contents(discussions, mod, post)

        embed = discord.Embed(
            title=title,
            url=f"https://osu.ppy.sh/beatmapsets/{discussions['beatmapset']['id']}/discussion#/{mod['id']}",
            description=mod_post_contents,
            color=footer["color"]
        )
        embed.set_author(
            name=str(self.get_username_with_group(discussions["beatmapset"]["related_users"], str(post["user_id"]))),
            url=f"https://osu.ppy.sh/users/{post['user_id']}",
            icon_url=f"https://a.ppy.sh/{post['user_id']}"
        )
        embed.set_thumbnail(
            url=f"https://b.ppy.sh/thumb/{discussions['beatmapset']['id']}l.jpg"
        )
        embed.set_footer(
            text=str(footer["text"]),
            icon_url=str(footer["icon"])
        )
        return embed

    async def build_mod_post_contents(self, discussions, mod, post):
        if mod["message_type"] == "review":
            try:
                parse_this_retarded_json = json.loads(str(post["message"]))
                mod_post_contents = await self.review_to_wall_of_text(discussions, parse_this_retarded_json)
            except KeyError as e:
                print(f"in build mod post contents {str(e)}")
                mod_post_contents = str(post["message"])
        else:
            mod_post_contents = str(post["message"])
        return mod_post_contents

    async def review_to_wall_of_text(self, discussions, parse_this_retarded_json):
        mod_post_contents = ""
        for one_dict in parse_this_retarded_json:
            if one_dict["type"] == "paragraph":
                mod_post_contents += one_dict["text"]
            elif one_dict["type"] == "embed":
                related_mod = self.get_discussion_first_message_from_id(discussions, one_dict["discussion_id"])
                mod_post_contents += f"[{related_mod}]"
                mod_post_contents += f"(https://osu.ppy.sh/beatmapsets/{discussions['beatmapset']['id']}/" \
                                     f"discussion#/{one_dict['discussion_id']})"
            else:
                mod_post_contents += json.dumps(one_dict)
            mod_post_contents += "\n"
        return mod_post_contents

    def get_discussion_first_message_from_id(self, discussions, discussion_id):
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if "posts" in mod:
                    if int(discussion_id) == int(mod["id"]):
                        return mod["posts"][0]["message"]
        return ""

    def get_username_with_group(self, related_users, user_id):
        user = self.get_related_user(related_users, user_id)
        if not user:
            return "Unable to get the username"

        if user["default_group"] == "bng":
            return user["username"] + " [BN]"
        elif user["default_group"] == "bng_limited":
            return user["username"] + " [BN]"
        elif user["default_group"] == "nat":
            return user["username"] + " [NAT]"
        else:
            return user["username"]

    def get_related_user(self, related_users, user_id):
        if user_id:
            for user in related_users:
                if int(user_id) == int(user["id"]):
                    return user
        return None

    def get_diff_name(self, beatmaps, beatmap_id):
        for beatmap in beatmaps:
            if beatmap_id:
                if int(beatmap["id"]) == int(beatmap_id):
                    return beatmap["version"]
            else:
                return "All difficulties"

    def get_mod_type(self, mod):
        if mod["resolved"]:
            return {
                "icon": "https://i.imgur.com/jjxrPpu.png",
                "text": "RESOLVED",
                "color": 0x77b255,
            }

        if mod["message_type"] == "praise":
            return {
                "icon": "https://i.imgur.com/2kFPL8m.png",
                "text": "Praise",
                "color": 0x44aadd,
            }
        elif mod["message_type"] == "hype":
            return {
                "icon": "https://i.imgur.com/fkJmW44.png",
                "text": "Hype",
                "color": 0x44aadd,
            }
        elif mod["message_type"] == "mapper_note":
            return {
                "icon": "https://i.imgur.com/HdmJ9i5.png",
                "text": "Note",
                "color": 0x8866ee,
            }
        elif mod["message_type"] == "problem":
            return {
                "icon": "https://i.imgur.com/qxyuJFF.png",
                "text": "Problem",
                "color": 0xcc5288,
            }
        elif mod["message_type"] == "suggestion":
            return {
                "icon": "https://i.imgur.com/Newgp6L.png",
                "text": "Suggestion",
                "color": 0xeeb02a,
            }
        else:
            return {
                "icon": "",
                "text": mod["message_type"],
                "color": 0xbd3661,
            }

    async def unarchive_channel(self, ctx, setting):
        if int(ctx.channel.category_id) == int(
                await self.get_category_object(ctx.guild, "mapset_archive", id_only=True)):
            await ctx.channel.edit(reason=None, category=await self.get_category_object(ctx.guild, setting))
            await ctx.send("Unarchived")

    async def get_category_object(self, guild, setting, id_only=None):
        # this is fucking retarded
        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       [setting, int(guild.id)]) as cursor:
            category_id = await cursor.fetchall()
        if category_id:
            category = self.bot.get_channel(int(category_id[0][0]))
            if id_only:
                return category.id
            else:
                return category
        else:
            return False


async def setup(bot):
    await bot.add_cog(ModChecker(bot))
