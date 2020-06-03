import time
import asyncio
import discord
from discord.ext import commands
from modules import wrappers
from modules import permissions
import json
import osuembed


class ModChecker(commands.Cog):
    # TODO: add event inserts in db upon track
    def __init__(self, bot):
        self.bot = bot
        self.bot.background_tasks.append(
            self.bot.loop.create_task(self.mod_checker_background_loop())
        )

    @commands.command(name="track", brief="Track the mapset in this channel", description="")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def track(self, ctx, tracking_mode="timeline"):
        async with self.bot.db.execute("SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]) as cursor:
            mapset_owner_check = await cursor.fetchall()
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return None

        if tracking_mode.isdigit():
            await ctx.send("you are using the command incorrectly")
            return None
        else:
            if tracking_mode == "timeline":
                tracking_mode = "timeline"
            elif tracking_mode == "notification":
                tracking_mode = "notification"
            else:
                await ctx.send("you are using the command incorrectly")
                return None

        async with self.bot.db.execute("SELECT mapset_id FROM mod_tracking WHERE channel_id = ?",
                                       [str(ctx.channel.id)]) as cursor:
            is_tracked = await cursor.fetchall()
        if is_tracked:
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [str(ctx.channel.id)])
            await self.bot.db.execute("DELETE FROM mod_posts WHERE channel_id = ?", [str(ctx.channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_events WHERE channel_id = ?", [str(ctx.channel.id)])
            await ctx.send("Deleted all previously existing tracking records in this channel")
            await asyncio.sleep(1)

        async with self.bot.db.execute("SELECT mapset_id FROM mapset_channels WHERE channel_id = ?",
                                       [str(ctx.channel.id)]) as cursor:
            mapset_id = await cursor.fetchall()
        if not mapset_id:
            await ctx.send("Set a mapset id for this channel first, using the `.set_id (mapset_id)` command.")
            return None
        if str(mapset_id[0][0]) == "0":
            await ctx.send("Set a mapset id for this channel first, using the `.set_id (mapset_id)` command.")
            return None

        discussions = await self.bot.osuweb.get_beatmapset_discussions(str(mapset_id[0][0]))
        if not discussions:
            await ctx.send("I am unable to find a modding v2 page for this mapset")
            return None

        if discussions["beatmapset"]["status"] == "graveyard" or discussions["beatmapset"]["status"] == "ranked":
            await ctx.send("i refuse to track graveyarded and ranked sets")
            return None

        if tracking_mode == "timeline":
            await self.insert_mod_history_in_db(discussions, str(ctx.channel.id))

        await self.insert_nomination_history_in_db(discussions, str(ctx.channel.id))

        await self.bot.db.execute("INSERT INTO mod_tracking VALUES (?,?,?)",
                                  [str(mapset_id[0][0]), str(ctx.channel.id), tracking_mode])
        try:
            beatmap_object = await self.bot.osu.get_beatmapset(s=str(mapset_id[0][0]))
            embed = await osuembed.beatmapset(beatmap_object)

            await ctx.send("Tracked", embed=embed)
            try:
                await self.unarchive_channel(ctx, "mapset")
            except:
                pass
        except:
            await ctx.send("Connection issues? try again")
        await self.bot.db.commit()

    @commands.command(name="untrack", brief="Untrack everything in this channel", description="")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def untrack(self, ctx):
        async with self.bot.db.execute("SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]) as cursor:
            mapset_owner_check = await cursor.fetchall()
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return None

        await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [str(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mod_posts WHERE channel_id = ?", [str(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mapset_events WHERE channel_id = ?", [str(ctx.channel.id)])
        await ctx.send("Untracked everything in this channel")
        await self.bot.db.commit()

    @commands.command(name="veto", brief="Track a mapset in the current channel in veto mode", description="")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def veto(self, ctx, mapset_id):
        async with self.bot.db.execute("SELECT channel_id FROM channels WHERE setting = ? AND channel_id = ?",
                                       ["veto", str(ctx.channel.id)]) as cursor:
            is_veto_channel = await cursor.fetchall()

        if is_veto_channel:
            return None

        if not mapset_id.isdigit():
            await ctx.send("a mapset_id is supposed to be all numbers")
            return None

        async with self.bot.db.execute("SELECT mapset_id FROM mod_tracking "
                                       "WHERE mapset_id = ? AND channel_id = ?",
                                       [str(mapset_id), str(ctx.channel.id)]) as cursor:
            mapset_is_already_tracked = await cursor.fetchall()
        if mapset_is_already_tracked:
            await ctx.send("This mapset is already tracked in this channel")
            return None

        discussions = await self.bot.osuweb.get_beatmapset_discussions(str(mapset_id))
        if not discussions:
            await ctx.send("I am unable to find a modding v2 page for this mapset")
            return None

        if discussions["beatmapset"]["status"] == "graveyard" or discussions["beatmapset"]["status"] == "ranked":
            await ctx.send("i refuse to track graveyarded and ranked sets")
            return None

        await self.insert_mod_history_in_db(discussions, str(ctx.channel.id))
        await self.insert_nomination_history_in_db(discussions, str(ctx.channel.id))
        await self.bot.db.execute("INSERT INTO mod_tracking VALUES (?,?,?)",
                                  [str(mapset_id), str(ctx.channel.id), "veto"])
        try:
            result = await self.bot.osu.get_beatmapset(s=mapset_id)
            embed = await osuembed.beatmapset(result)

            await ctx.send("Tracked in veto mode", embed=embed)
        except:
            await ctx.send("tracked")
        await self.bot.db.commit()

    @commands.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode", description="")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def unveto(self, ctx, mapset_id):
        async with self.bot.db.execute("SELECT channel_id FROM channels WHERE setting = ? AND channel_id = ?",
                                       ["veto", str(ctx.channel.id)]) as cursor:
            is_veto_channel = await cursor.fetchall()

        if is_veto_channel:
            return None

        if not mapset_id.isdigit():
            await ctx.send("a mapset_id is supposed to be all numbers")
            return None

        await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                  [str(mapset_id), str(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",
                                  [str(mapset_id), str(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mapset_events WHERE mapset_id = ? AND channel_id = ?",
                                  [str(mapset_id), str(ctx.channel.id)])
        try:
            result = await self.bot.osu.get_beatmapset(s=mapset_id)
            embed = await osuembed.beatmapset(result)
            await ctx.send("I untracked this mapset in this channel", embed=embed)
        except:
            await ctx.send("done")
        await self.bot.db.commit()

    @commands.command(name="sublist", brief="List all tracked mapsets everywhere", description="")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def sublist(self, ctx):
        async with self.bot.db.execute("SELECT * FROM mod_tracking") as cursor:
            track_list = await cursor.fetchall()
        for mapset in track_list:
            try:
                result = await self.bot.osu.get_beatmapset(s=str(mapset[0]))
                embed = await osuembed.beatmapset(result)
            except:
                await ctx.send("Connection issues?")
                embed = None
            await ctx.send(content="mapset_id `%s` | channel <#%s> | tracking_mode `%s`" % mapset, embed=embed)

    @commands.command(name="veto_list", brief="List all vetoed mapsets everywhere", description="")
    @commands.check(permissions.is_not_ignored)
    async def veto_list(self, ctx):
        async with self.bot.db.execute("SELECT * FROM mod_tracking WHERE mode = ?", ["veto"]) as cursor:
            vetoed_sets = await cursor.fetchall()
        if len(vetoed_sets) == 0:
            await ctx.send("Nothing is tracked in veto mode at this moment")
            return None
        for mapset in vetoed_sets:
            try:
                result = await self.bot.osu.get_beatmapset(s=str(mapset[0]))
                embed = await osuembed.beatmapset(result)
            except:
                await ctx.send("Connection issues?")
                embed = None
            await ctx.send(content="mapset_id `%s` | channel <#%s> | tracking_mode `%s`" % mapset, embed=embed)

    async def mod_checker_background_loop(self):
        print("Mod checking Background Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)
            async with self.bot.db.execute("SELECT * FROM mod_tracking") as cursor:
                track_list = await cursor.fetchall()
            for track_entry in track_list:
                print(time.strftime("%X %x %Z") + " | " + track_entry[0])
                channel = self.bot.get_channel(int(track_entry[1]))

                if not channel:
                    print(f"channel {track_entry[1]} is deleted for mapset {track_entry[0]}")
                    await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [str(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mod_posts WHERE channel_id = ?", [str(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mapset_channels WHERE channel_id = ?", [str(track_entry[1])])
                    await self.bot.db.execute("DELETE FROM mapset_events WHERE channel_id = ?", [str(track_entry[1])])
                    await self.bot.db.commit()
                    continue

                mapset_id = str(track_entry[0])
                tracking_mode = str(track_entry[2])

                async with self.bot.db.execute("SELECT * FROM mod_tracking "
                                               "WHERE mapset_id = ? AND channel_id = ? AND mode = ?",
                                               [str(mapset_id), str(channel.id), str(tracking_mode)]) as cursor:
                    is_no_longer_tracked = await cursor.fetchall()
                if not is_no_longer_tracked:
                    continue

                try:
                    discussions = await self.bot.osuweb.get_beatmapset_discussions(mapset_id)
                    if not discussions:
                        continue
                except Exception as e:
                    print(e)
                    await asyncio.sleep(300)
                    continue

                if not await self.check_status(channel, mapset_id, discussions):
                    continue

                if tracking_mode == "veto" or tracking_mode == "timeline":
                    await self.timeline_mode_tracking(discussions, channel, mapset_id, tracking_mode)
                elif tracking_mode == "notification":
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
                            await self.bot.db.execute("INSERT INTO mod_posts VALUES (?,?,?)",
                                                      [str(post["id"]), str(mod["beatmapset_id"]), str(channel_id)])
        await self.bot.db.commit()

    async def insert_nomination_history_in_db(self, discussions, channel_id):
        mapset_id = discussions["beatmapset"]["id"]
        async with self.bot.db.execute("SELECT event_id FROM mapset_events WHERE channel_id = ? AND mapset_id = ?",
                                       [str(channel_id), str(mapset_id)]) as cursor:
            history = await cursor.fetchall()
        for event in discussions["beatmapset"]["events"]:
            if event:
                if self.get_icon(event["type"]):
                    if not wrappers.in_db_list(history, str(event["id"])):
                        await self.bot.db.execute("INSERT INTO mapset_events VALUES (?,?,?)",
                                                  [str(event["id"]), str(mapset_id), str(channel_id)])
        await self.bot.db.commit()

    async def check_status(self, channel, mapset_id, discussions):
        status = discussions["beatmapset"]["status"]
        if (status == "wip") or (status == "qualified") or (status == "pending"):
            return True
        elif status == "graveyard":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_events WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is graveyarded, so I am untracking it. "
                                       "I don't wanna track dead sets. "
                                       "You can track again after it's ungraveyarded "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            return None
        elif status == "deleted":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_events WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is deleted, so I am untracking it. "
                                       "why tho????????????? channel archived and will be nuked in a week "
                                       "along with it's role. "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                           ["mapset_archive", str(channel.guild.id)]) as cursor:
                guild_archive_category_id = await cursor.fetchall()
            if guild_archive_category_id:
                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await channel.edit(reason="mapset deleted!", category=archive_category)
            return None
        elif status == "ranked":
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.execute("DELETE FROM mapset_events WHERE mapset_id = ? AND channel_id = ?",
                                      [str(mapset_id), str(channel.id)])
            await self.bot.db.commit()
            await channel.send(content="This mapset is ranked, so I am untracking it. "
                                       "There is no point in continuing to do so. "
                                       "Channel archived! "
                                       f"https://osu.ppy.sh/beatmapsets/{mapset_id}")
            async with self.bot.db.execute("SELECT category_id FROM categories "
                                           "WHERE setting = ? AND guild_id = ?",
                                           ["mapset_archive", str(channel.guild.id)]) as cursor:
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
        async with self.bot.db.execute("SELECT post_id FROM mod_posts WHERE channel_id = ?",
                                       [str(channel.id)]) as cursor:
            history = await cursor.fetchall()
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if "posts" in mod:
                    for post in mod["posts"]:
                        if post:
                            if not wrappers.in_db_list(history, str(post["id"])):
                                #await self.bot.db.execute("INSERT INTO mod_posts VALUES (?,?,?)",
                                #                          [str(post["id"]), str(mapset_id), str(channel.id)])
                                #await self.bot.db.commit()
                                if ((not post["system"]) and
                                        (not post["message"] == "r") and
                                        (not post["message"] == "res") and
                                        (not post["message"] == "resolved")):
                                    post_to_post = await self.mod_post_embed(post, discussions, mod, tracking_mode)
                                    if post_to_post:
                                        try:
                                            await channel.send(embed=post_to_post)
                                        except Exception as e:
                                            print(e)

    async def notification_mode_tracking(self, discussions, channel, mapset_id):
        current_status = await self.check_if_resolved(discussions)  # 1 - we have new mods, 0 - no new mods
        async with self.bot.db.execute("SELECT status FROM mapset_notification_status "
                                       "WHERE mapset_id = ? AND channel_id = ?",
                                       [str(mapset_id), str(channel.id)]) as cursor:
            cached_status = await cursor.fetchall()
        if not cached_status:
            await self.bot.db.execute("INSERT INTO mapset_notification_status VALUES (?, ?, ?, ?)",
                                      [str(mapset_id), str(0), str(channel.id), str(current_status)])
            await self.bot.db.commit()
            return None

        cached_status = cached_status[0][0]
        if cached_status != current_status:
            await self.bot.db.execute("UPDATE mapset_notification_status SET status = ? "
                                      "WHERE mapset_id = ? AND channel_id = ?",
                                      [str(current_status), str(mapset_id), str(channel.id)])
            await self.bot.db.commit()
            if current_status == "1":
                unresolved_diffs = await self.get_unresolved_diffs(discussions)
                return_message = "new mods on: "
                for diff in unresolved_diffs:
                    return_message += f"\n> {self.get_diff_name(discussions['beatmapset']['beatmaps'], diff)}"
                return_message += "\nno further notifications until all mods are resolved"
                await channel.send(return_message.replace("@", ""))
        return None

    async def check_nomination_status(self, discussions, channel, mapset_id, tracking_mode):
        async with self.bot.db.execute("SELECT event_id FROM mapset_events WHERE channel_id = ?",
                                       [str(channel.id)]) as cursor:
            history = await cursor.fetchall()
        for event in discussions["beatmapset"]["events"]:
            if event:
                if self.get_icon(event["type"]):
                    if not wrappers.in_db_list(history, str(event["id"])):
                        await self.bot.db.execute("INSERT INTO mapset_events VALUES (?,?,?)",
                                                  [str(event["id"]), str(mapset_id), str(channel.id)])
                        await self.bot.db.commit()
                        event_to_post = await self.nomnom_embed(event, discussions, tracking_mode)
                        if event_to_post:
                            try:
                                await channel.send(embed=event_to_post)
                            except Exception as e:
                                print(e)

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
                    return "1"

    async def get_unresolved_diffs(self, discussions):
        return_list = []
        for mod in discussions["beatmapset"]["discussions"]:
            if mod:
                if not mod["resolved"]:
                    if not mod["beatmap_id"]:
                        if not False in return_list:
                            return_list.append(False)
                    else:
                        if not str(mod["beatmap_id"] in return_list):
                            return_list.append(str(mod["beatmap_id"]))
        return return_list

    async def nomnom_embed(self, event, discussions, tracking_mode):
        if not event:
            return None

        if tracking_mode == "veto":
            mapset_title = str(discussions["beatmapset"]["title"])
            title = mapset_title
        else:
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
        embed.set_footer(
            text=str(event["created_at"]),
        )
        return embed

    async def mod_post_embed(self, post, discussions, mod, tracking_mode):
        if not post:
            return None

        mapset_diff_name = str(self.get_diff_name(discussions["beatmapset"]["beatmaps"], mod["beatmap_id"]))
        if tracking_mode == "veto":
            if mod["message_type"] == "hype":
                return None
            elif mod["message_type"] == "praise":
                return None
            
            mapset_title = str(discussions["beatmapset"]["title"])
            title = f"{mapset_title} [{mapset_diff_name}]"
        else:
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
            except:
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
                    if str(discussion_id) == str(mod["id"]):
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
                if str(user_id) == str(user["id"]):
                    return user
        return None

    def get_diff_name(self, beatmaps, beatmap_id):
        for beatmap in beatmaps:
            if beatmap_id:
                if str(beatmap["id"]) == str(beatmap_id):
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
        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       [setting, str(guild.id)]) as cursor:
            category_id = await cursor.fetchall()
        if category_id:
            category = self.bot.get_channel(int(category_id[0][0]))
            if id_only:
                return category.id
            else:
                return category
        else:
            return False


def setup(bot):
    bot.add_cog(ModChecker(bot))
