import json
import time
import asyncio
import discord
from modules import utils
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview
from modules import osuwebapipreview


async def populatedb(discussions):
    modposts = discussions["beatmapset"]["discussions"]
    allposts = []
    for onemod in modposts:
        try:
            if onemod:
                for subpost in onemod["posts"]:
                    if subpost:
                        if not subpost["system"]:
                            allposts.append(
                                [
                                    "INSERT INTO modposts VALUES (?,?,?,?,?)", 
                                    [
                                        str(subpost["id"]), 
                                        str(onemod["beatmapset_id"]), 
                                        str(onemod["beatmap_id"]), 
                                        str(subpost["user_id"]), 
                                        str(subpost["message"])
                                    ]
                                ]
                            )
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in modchecker.populatedb")
            print(e)
            print(onemod)
    await dbhandler.massquery(allposts)


async def track(ctx, mapsetid, mapsethostdiscordid, trackingtype):
    roleid = None  # TODO: actually implement roleid
    if not await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE mapsetid = ?", [str(mapsetid)]]):
        mapsetmetadata = await osuapi.get_beatmap(str(mapsetid))
        embed = await osuembed.mapsetold(mapsetmetadata)
        if embed:
            beatmapsetdiscussionobject = await osuwebapipreview.discussion(str(mapsetid))
            if beatmapsetdiscussionobject:
                await populatedb(beatmapsetdiscussionobject)
                await dbhandler.query(["INSERT INTO modtracking VALUES (?,?,?,?,?,?)", [str(mapsetid), str(ctx.message.channel.id), mapsethostdiscordid, roleid, str(mapsetmetadata['creator_id']), trackingtype]])
                if trackingtype == 1:
                    await ctx.send(content='This mapset is now being tracked in this channel in veto mode', embed=embed)
                else:
                    await ctx.send(content='This mapset is now being tracked in this channel', embed=embed)
            else:
                await ctx.send(content='`No mapset found with that ID / Mapset has no modding v2 / Connection issues`')
        else:
            await ctx.send(content='`No mapset found with that ID`')


async def untrack(ctx, mapsetid, embed, ranked):
    if await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(ctx.message.channel.id)]]):
        await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(ctx.message.channel.id)]])
        #await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ?",[str(mapsetid),]])

        if embed:
            if ranked:
                await ctx.send(content='Congratulations on ranking your mapset. Since the modding stage is finished, and the map is moved to the ranked section, I will no longer be checking for mods on this mapset.', embed=embed)
            else:
                await ctx.send(content='This Mapset is no longer being tracked in this channel', embed=embed)
        else:
            await ctx.send(content='`Mapset with that ID is no longer being tracked in this channel`')
    else:
        await ctx.send(content='`No tracking record was found in the database with this mapsetid for this channel`')


async def main(client):
    try:
        await asyncio.sleep(120)
        for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
            channel = client.get_channel(int(oneentry[1]))
            mapsetid = str(oneentry[0])
            trackingtype = str(oneentry[5])
            print(time.strftime('%X %x %Z')+' | '+oneentry[0])

            beatmapsetdiscussionobject = await osuwebapipreview.discussion(mapsetid)

            if beatmapsetdiscussionobject:
                discussions = beatmapsetdiscussionobject["beatmapset"]["discussions"]

                if discussions:
                    for discussion in discussions:
                        try:
                            if discussion:
                                for subpostobject in discussion['posts']:
                                    if not await dbhandler.query(["SELECT postid FROM modposts WHERE postid = ?", [str(subpostobject['id']), ]]):
                                        await dbhandler.query(
                                            [
                                                "INSERT INTO modposts VALUES (?,?,?,?,?)", 
                                                [
                                                    str(subpostobject["id"]), 
                                                    str(mapsetid), 
                                                    str(discussion["beatmap_id"]), 
                                                    str(subpostobject["user_id"]), 
                                                    str(subpostobject["message"])
                                                ]
                                            ]
                                        )
                                        if (not subpostobject['system']) and (not subpostobject["message"] == "res") and (not subpostobject["message"] == "resolved"):
                                            modtopost = await modpost(subpostobject, beatmapsetdiscussionobject, discussion, trackingtype)
                                            if modtopost:
                                                await channel.send(embed=modtopost)
                        except Exception as e:
                            print(time.strftime('%X %x %Z'))
                            print("while looping through discussions")
                            print(e)
                            print(discussion)
                else:
                    print("No actual discussions found at %s" % (mapsetid))
            else:
                print("%s | Possible connection issues" % (time.strftime('%X %x %Z')))
                await asyncio.sleep(300)
            await asyncio.sleep(120)
        await asyncio.sleep(1800)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in modchecker.main")
        print(e)
        await asyncio.sleep(300)


async def get_username(beatmapsetdiscussionobject, subpostobject):
    for oneuser in beatmapsetdiscussionobject["beatmapset"]["related_users"]:
        if subpostobject['user_id'] == oneuser['id']:
            if "bng" in oneuser['groups']:
                return oneuser['username']+" [BN]"
            elif "qat" in oneuser['groups']:
                return oneuser['username']+" [QAT]"
            else:
                return oneuser['username']


async def get_diffname(beatmapsetdiscussionobject, newevent):
    for onediff in beatmapsetdiscussionobject["beatmapset"]["beatmaps"]:
        if newevent['beatmap_id']:
            if onediff['id'] == newevent['beatmap_id']:
                diffname = onediff['version']
        else:
            diffname = "All difficulties"
    return diffname


async def get_modtype(newevent):
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


async def modpost(subpostobject, beatmapsetdiscussionobject, newevent, trackingtype):
    if subpostobject:
        if trackingtype == "0":
            title = str(await get_diffname(beatmapsetdiscussionobject, newevent))
        elif trackingtype == "1":
            title = "%s / %s" % (str(beatmapsetdiscussionobject["beatmapset"]["title"]), str(await get_diffname(beatmapsetdiscussionobject, newevent)))
            if newevent['message_type'] == "hype":
                return None
            elif newevent['message_type'] == "praise":
                return None

        footer = await get_modtype(newevent)
        modpost = discord.Embed(
            title=title,
            url="https://osu.ppy.sh/beatmapsets/%s/discussion#/%s" % (
                str(beatmapsetdiscussionobject["beatmapset"]["id"]), str(newevent['id'])),
            description=str(subpostobject['message']),
            color=footer['color']
        )
        modpost.set_author(
            name=str(await get_username(beatmapsetdiscussionobject, subpostobject)),
            url="https://osu.ppy.sh/users/%s" % (
                str(subpostobject['user_id'])),
            icon_url="https://a.ppy.sh/%s" % (str(subpostobject['user_id']))
        )
        modpost.set_thumbnail(
            url="https://b.ppy.sh/thumb/%sl.jpg" % (
                str(beatmapsetdiscussionobject["beatmapset"]["id"]))
        )
        modpost.set_footer(
            text=str(footer['text']),
            icon_url=str(footer['icon'])
        )
        return modpost
    else:
        return None