import time
import asyncio
import discord
from discord.ext import commands
from modules import db
from modules import permissions
from osuembed import osuembed

from modules.connections import osuweb as osuweb
from modules.connections import osu as osu

class ModChecker(commands.Cog, name="Mod Checker"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.modchecker_background_loop())

    @commands.command(name="track", brief="Track the mapset in this channel", description="", pass_context=True)
    async def track_command(self, ctx, tracking_mode = "classic"):
        if (db.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            try:
                if db.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                    db.query(["DELETE FROM mod_tracking WHERE channel_id = ?",[str(ctx.message.channel.id)]])
                    db.query(["DELETE FROM mod_posts WHERE channel_id = ?",[str(ctx.message.channel.id)]])
                    await ctx.send("Deleted all previously existing tracking records in this channel")
                    await asyncio.sleep(1)

                mapset_id = db.query(["SELECT mapset_id FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]])
                if mapset_id:
                    if str(mapset_id[0][0]) != "0":
                        if await self.track(str(mapset_id[0][0]), ctx.message.channel.id):
                            try:
                                beatmap_object = await osu.get_beatmapset(s=str(mapset_id[0][0]))
                                tracked_embed = await osuembed.beatmapset(beatmap_object)

                                await ctx.send("Tracked", embed=tracked_embed)
                                try:
                                    await reputation.unarchive_channel(client, ctx, "guild_mapset_category")
                                except:
                                    pass
                            except:
                                print("Connection issues?")
                                await ctx.send("Connection issues? try again")
                        else:
                            await ctx.send("Error")
                    else:
                        await ctx.send("Set a mapset id for this channel first, using the `'setid (mapset_id)` command.")
                else:
                    await ctx.send("Set a mapset id for this channel first, using the `'setid (mapset_id)` command.")
            except Exception as e:
                await ctx.send(e)

    @commands.command(name="untrack", brief="Untrack everything in this channel", description="", pass_context=True)
    async def untrack_command(self, ctx):
        if (db.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            try:
                if db.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                    db.query(["DELETE FROM mod_tracking WHERE channel_id = ?",[str(ctx.message.channel.id)]])
                    db.query(["DELETE FROM mod_posts WHERE channel_id = ?",[str(ctx.message.channel.id)]])
                    await ctx.send("Untracked everything in this channel")
            except Exception as e:
                await ctx.send(e)

    @commands.command(name="forcetrack", brief="Force Track a mapset in the current channel", description="", pass_context=True, hidden=True)
    async def forcetrack(self, ctx, mapset_id: str):
        if permissions.check(ctx.message.author.id):
            if await self.track(mapset_id, ctx.message.channel.id):
                try:
                    result = await osu.get_beatmapset(s=mapset_id)
                    embed = await osuembed.beatmapset(result)
                    await ctx.send("Tracked", embed=embed)
                except:
                    print("Connection issues?")
                    await ctx.send("Connection issues?")
            else:
                await ctx.send("Error")
        else:
            await ctx.send(embed=permissions.error())


    @commands.command(name="forceuntrack", brief="Force untrack a mapset in the current channel", description="", pass_context=True, hidden=True)
    async def forceuntrack(self, ctx, mapset_id: str):
        if permissions.check(ctx.message.author.id):
            if await self.untrack(mapset_id, ctx.message.channel.id):
                await ctx.send("Untracked")
            else:
                await ctx.send("No tracking record found")
        else:
            await ctx.send(embed=permissions.error())


    @commands.command(name="veto", brief="Track a mapset in the current channel in veto mode", description="", pass_context=True)
    async def veto(self, ctx, mapset_id: int):
        if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):
            if await self.track(mapset_id, ctx.message.channel.id, "veto"):
                try:
                    result = await osu.get_beatmapset(s=mapset_id)
                    embed = await osuembed.beatmapset(result)
                    await ctx.send("Tracked in veto mode", embed=embed)
                except:
                    print("Connection issues?")
                    await ctx.send("Connection issues?")
            else:
                await ctx.send("Error")
        else:
            await ctx.send(embed=permissions.error())


    @commands.command(name="unveto", brief="Untrack a mapset in the current channel in veto mode", description="", pass_context=True)
    async def unveto(self, ctx, mapset_id: int):
        if db.query(["SELECT value FROM config WHERE setting = ? AND parent = ? AND value = ?", ["guild_veto_channel", str(ctx.guild.id), str(ctx.message.channel.id)]]):   
            if await self.untrack(mapset_id, ctx.message.channel.id):
                try:
                    result = await osu.get_beatmapset(s=mapset_id)
                    embed = await osuembed.beatmapset(result)
                    await ctx.send("Untracked this", embed=embed)
                except:
                    print("Connection issues?")
                    await ctx.send("Connection issues?")
            else:
                await ctx.send("No tracking record found")
        else:
            await ctx.send(embed=permissions.error())


    @commands.command(name="sublist", brief="List all tracked mapsets everywhere", description="", pass_context=True)
    async def sublist(self, ctx):
        if permissions.check(ctx.message.author.id):
            for oneentry in db.query("SELECT * FROM mod_tracking"):
                try:
                    result = await osu.get_beatmapset(s=str(oneentry[0]))
                    embed = await osuembed.beatmapset(result)
                    await ctx.send(content="mapset_id %s | channel <#%s> | tracking_mode %s" % (oneentry), embed=embed)
                except:
                    print("Connection issues?")
                    await ctx.send("Connection issues?")
        else:
            await ctx.send(embed=permissions.error())

    async def modchecker_background_loop(self):
        print("Mod checking Background Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(120)
            for oneentry in db.query("SELECT * FROM mod_tracking"):
                channel = self.bot.get_channel(int(oneentry[1]))
                if channel:
                    mapset_id = str(oneentry[0])
                    tracking_mode = str(oneentry[2])
                    print(time.strftime('%X %x %Z')+' | '+oneentry[0])

                    beatmapset_discussions = await osuweb.discussion(mapset_id)

                    if beatmapset_discussions:
                        status = await self.check_status(channel, mapset_id, beatmapset_discussions)
                        if status:
                            if tracking_mode == "veto" or tracking_mode == "classic":
                                await self.timeline_mode_tracking(beatmapset_discussions, channel, mapset_id, tracking_mode)
                            elif tracking_mode == "notification":
                                await self.notification_mode_tracking(beatmapset_discussions, channel, mapset_id, tracking_mode)
                        else:
                            print("No actual discussions found at %s or mapset untracked automatically" % (mapset_id))
                    else:
                        print("%s | modchecker connection issues" % (time.strftime('%X %x %Z')))
                        await asyncio.sleep(300)
                else:
                    print("someone manually removed the channel with id %s and mapset id %s" % (oneentry[1], oneentry[0]))
                await asyncio.sleep(120)
            await asyncio.sleep(1800)

    async def populatedb(self, discussions, channel_id):
        mod_posts = discussions["beatmapset"]["discussions"]
        allposts = []
        for onemod in mod_posts:
            try:
                if onemod:
                    if 'posts' in onemod:
                        for subpost in onemod["posts"]:
                            if subpost:
                                allposts.append(["INSERT INTO mod_posts VALUES (?,?,?)", [str(subpost["id"]), str(onemod["beatmapset_id"]), str(channel_id)]])
            except Exception as e:
                print(time.strftime('%X %x %Z'))
                print("in modchecker.populatedb")
                print(e)
                print(onemod)
        db.mass_query(allposts)

    async def track(self, mapset_id, channel_id, tracking_mode = "classic"):
        if not db.query(["SELECT mapset_id FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id), str(channel_id)]]):
            beatmapset_discussions = await osuweb.discussion(str(mapset_id))
            if beatmapset_discussions:
                await self.populatedb(beatmapset_discussions, str(channel_id))
                db.query(["INSERT INTO mod_tracking VALUES (?,?,?)", [str(mapset_id), str(channel_id), tracking_mode]])
                return True
            else:
                return False
        else:
            return False

    async def untrack(self, mapset_id, channel_id):
        if db.query(["SELECT mapset_id FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id), str(channel_id)]]):
            db.query(["DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id), str(channel_id)]])
            db.query(["DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id), str(channel_id)]])
            return True
        else:
            return False

    async def check_status(self, channel, mapset_id, beatmapset_discussions):
        status = beatmapset_discussions["beatmapset"]["status"]
        if (status == "wip") or (status == "qualified") or (status == "pending"):
            discussions = True
        elif status == "ranked":
            discussions = None
            if await self.untrack(mapset_id, channel.id):
                try:
                    mapset_object = await osu.get_beatmapset(s=mapset_id)
                    embedthis = await osuembed.beatmapset(mapset_object)
                except:
                    print("Connection issues?")
                    embedthis = None
                await channel.send(content='I detected that this map is ranked now. Since the modding stage is finished, and the map is moved to the ranked section, I will no longer be checking for mods on this mapset.', embed=embedthis)
        elif status == "graveyard":
            discussions = None
            if await self.untrack(mapset_id, channel.id):
                try:
                    mapset_object = await osu.get_beatmapset(s=mapset_id)
                    embedthis = await osuembed.beatmapset(mapset_object)
                except:
                    print("Connection issues?")
                    embedthis = None
                await channel.send(content="I detected that this map is graveyarded now and so, I am untracking it. Type `'track` after you ungraveyard it, to continue tracking it. Please understand that we don't wanna track dead sets.", embed=embedthis)
        elif status == "deleted":
            discussions = None
            if await self.untrack(mapset_id, channel.id):
                await channel.send(content='I detected that the mapset with the id %s has been deleted, so I am untracking.' % (str(mapset_id)))
        else:
            discussions = None
            await channel.send(content='<@155976140073205761> something went wrong, please check the console output.')
            print("%s / %s" % (status, mapset_id))
        return discussions

    async def timeline_mode_tracking(self, beatmapset_discussions, channel, mapset_id, tracking_mode):
        if db.query(["SELECT * FROM mod_tracking WHERE mapset_id = ? AND channel_id = ? AND mode = ?", [str(mapset_id), str(channel.id), str(tracking_mode)]]):
            for discussion in beatmapset_discussions["beatmapset"]["discussions"]:
                if discussion:
                    if 'posts' in discussion:
                        for subpostobject in discussion['posts']:
                            if subpostobject:
                                if not db.query(["SELECT post_id FROM mod_posts WHERE post_id = ? AND channel_id = ?", [str(subpostobject['id']), str(channel.id)]]):
                                    db.query(["INSERT INTO mod_posts VALUES (?,?,?)", [str(subpostobject["id"]), str(mapset_id), str(channel.id)]])
                                    if (not subpostobject['system']) and (not subpostobject["message"] == "r") and (not subpostobject["message"] == "res") and (not subpostobject["message"] == "resolved"):
                                        modtopost = await self.modpost(subpostobject, beatmapset_discussions, discussion, tracking_mode)
                                        if modtopost:
                                            try:
                                                await channel.send(embed=modtopost)
                                            except Exception as e:
                                                print(e)

    async def notification_mode_tracking(self, beatmapset_discussions, channel, mapset_id, tracking_mode): # channel is important
        if db.query(["SELECT * FROM mod_tracking WHERE mapset_id = ? AND channel_id = ? AND mode = ?", [str(mapset_id), str(channel.id), str(tracking_mode)]]):
            return None
        # cachedstatus = dbhandler.query(["SELECT unresolved FROM mapset_status WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id), str(channel.id)]])
        # for discussion in beatmapset_discussions["beatmapset"]["discussions"]:
        #     try:
        #         if discussion:
        #             discussion['resolved'] == False
                    
        #     except Exception as e:
        #         print(time.strftime('%X %x %Z'))
        #         print("while looping through discussions")
        #         print(e)
        #         print(discussion)

    async def get_username(self, related_users, user_id):
        for user in related_users:
            if str(user_id) == str(user['id']):
                if user['default_group'] == "bng":
                    return user['username']+" [BN]"
                elif user['default_group'] == "bng_limited":
                    return user['username']+" [BN]"
                elif user['default_group'] == "nat":
                    return user['username']+" [NAT]"
                else:
                    return user['username']

    async def get_diffname(self, beatmaps, beatmap_id):
        for beatmap in beatmaps:
            if beatmap_id:
                if beatmap['id'] == beatmap_id:
                    return beatmap['version']
            else:
                return "All difficulties"

    async def get_modtype(self, newevent):
        if newevent['resolved']:
            footer = {
                'icon': "https://i.imgur.com/jjxrPpu.png",
                'text': "RESOLVED",
                'color': 0x77b255,
            }
        else:
            if newevent['message_type'] == "praise":
                footer = {
                    'icon': "https://i.imgur.com/2kFPL8m.png",
                    'text': "Praise",
                    'color': 0x44aadd,
                }
            elif newevent['message_type'] == "hype":
                footer = {
                    'icon': "https://i.imgur.com/fkJmW44.png",
                    'text': "Hype",
                    'color': 0x44aadd,
                }
            elif newevent['message_type'] == "mapper_note":
                footer = {
                    'icon': "https://i.imgur.com/HdmJ9i5.png",
                    'text': "Note",
                    'color': 0x8866ee,
                }
            elif newevent['message_type'] == "problem":
                footer = {
                    'icon': "https://i.imgur.com/qxyuJFF.png",
                    'text': "Problem",
                    'color': 0xcc5288,
                }
            elif newevent['message_type'] == "suggestion":
                footer = {
                    'icon': "https://i.imgur.com/Newgp6L.png",
                    'text': "Suggestion",
                    'color': 0xeeb02a,
                }
            else:
                footer = {
                    'icon': "",
                    'text': newevent['message_type'],
                    'color': 0xbd3661,
                }
        return footer

    async def modpost(self, subpostobject, beatmapset_discussions, newevent, tracking_mode):
        if subpostobject:
            if tracking_mode == "classic":
                title = str(await self.get_diffname(beatmapset_discussions["beatmapset"]["beatmaps"], newevent['beatmap_id']))
            elif tracking_mode == "veto":
                title = "%s / %s" % (str(beatmapset_discussions["beatmapset"]["title"]), str(await self.get_diffname(beatmapset_discussions["beatmapset"]["beatmaps"], newevent['beatmap_id'])))
                if newevent['message_type'] == "hype":
                    return None
                elif newevent['message_type'] == "praise":
                    return None

            footer = await self.get_modtype(newevent)
            modpost = discord.Embed(
                title=title,
                url="https://osu.ppy.sh/beatmapsets/%s/discussion#/%s" % (
                    str(beatmapset_discussions["beatmapset"]["id"]), str(newevent['id'])),
                description=str(subpostobject['message']),
                color=footer['color']
            )
            modpost.set_author(
                name=str(await self.get_username(beatmapset_discussions["beatmapset"]["related_users"], str(subpostobject['user_id']))),
                url="https://osu.ppy.sh/users/%s" % (
                    str(subpostobject['user_id'])),
                icon_url="https://a.ppy.sh/%s" % (str(subpostobject['user_id']))
            )
            modpost.set_thumbnail(
                url="https://b.ppy.sh/thumb/%sl.jpg" % (
                    str(beatmapset_discussions["beatmapset"]["id"]))
            )
            modpost.set_footer(
                text=str(footer['text']),
                icon_url=str(footer['icon'])
            )
            return modpost
        else:
            return None

def setup(bot):
    bot.add_cog(ModChecker(bot))
