import time
import asyncio
import discord
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview


async def populatedb(discussions, channelid):
    modposts = discussions["beatmapset"]["discussions"]
    allposts = []
    for onemod in modposts:
        try:
            if onemod:
                for subpost in onemod["posts"]:
                    if subpost:
                        allposts.append(
                            [
                                "INSERT INTO modposts VALUES (?,?,?)", 
                                [
                                    str(subpost["id"]), 
                                    str(onemod["beatmapset_id"]), 
                                    str(channelid)
                                ]
                            ]
                        )
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in modchecker.populatedb")
            print(e)
            print(onemod)
    await dbhandler.massquery(allposts)


async def track(mapsetid, channelid, tracking_mode = "0"):
    if not await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(channelid)]]):
        beatmapset_discussions = await osuwebapipreview.discussion(str(mapsetid))
        if beatmapset_discussions:
            await populatedb(beatmapset_discussions, str(channelid))
            await dbhandler.query(["INSERT INTO modtracking VALUES (?,?,?)", [str(mapsetid), str(channelid), tracking_mode]])
            return True
        else:
            return False
    else:
        return False


async def untrack(mapsetid, channelid, untrackall = False):
    if untrackall:
        if await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE mapsetid = ?", [str(mapsetid)]]):
            await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ?", [str(mapsetid)]])
            await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ?", [str(mapsetid)]])
            return True
        else:
            return False
    else:
        if await dbhandler.query(["SELECT mapsetid FROM modtracking WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(channelid)]]):
            await dbhandler.query(["DELETE FROM modtracking WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(channelid)]])
            await dbhandler.query(["DELETE FROM modposts WHERE mapsetid = ? AND channelid = ?", [str(mapsetid), str(channelid)]])
            return True
        else:
            return False


async def check_status(channel, mapsetid, beatmapset_discussions):
    status = beatmapset_discussions["beatmapset"]["status"]
    if (status == "wip") or (status == "qualified") or (status == "pending"):
        discussions = beatmapset_discussions["beatmapset"]["discussions"]
    elif status == "ranked":
        discussions = None
        if await untrack(mapsetid, channel.id):
            await channel.send(content='I detected that this map is ranked now. Since the modding stage is finished, and the map is moved to the ranked section, I will no longer be checking for mods on this mapset.', embed=await osuembed.mapset(await osuapi.get_beatmaps(mapsetid)))
    elif status == "graveyard":
        discussions = None
        if await untrack(mapsetid, channel.id):
            await channel.send(content='I detected that this map is graveyarded now and so, I am untracking it. Ping a manager when this set is back in pending section. Please understand that we don\'t wanna track dead sets.', embed=await osuembed.mapset(await osuapi.get_beatmaps(mapsetid)))
    elif status == "deleted":
        discussions = None
        if await untrack(mapsetid, channel.id):
            await channel.send(content='I detected that the mapset with the id %s has been deleted, so I am untracking.' % (str(mapsetid)))
    else:
        discussions = None
        await channel.send(content='<@155976140073205761> something went wrong, please check the console output.')
        print("%s / %s" % (status, mapsetid))
    return discussions


async def main(client):
    try:
        await asyncio.sleep(120)
        for oneentry in await dbhandler.query("SELECT * FROM modtracking"):
            channel = client.get_channel(int(oneentry[1]))
            mapsetid = str(oneentry[0])
            tracking_mode = str(oneentry[2])
            print(time.strftime('%X %x %Z')+' | '+oneentry[0])

            beatmapset_discussions = await osuwebapipreview.discussion(mapsetid)

            if beatmapset_discussions:
                discussions = await check_status(channel, mapsetid, beatmapset_discussions)
                if discussions:
                    for discussion in discussions:
                        try:
                            if discussion:
                                for subpostobject in discussion['posts']:
                                    if subpostobject:
                                        if not await dbhandler.query(["SELECT postid FROM modposts WHERE postid = ? AND channelid = ?", [str(subpostobject['id']), str(channel.id)]]):
                                            await dbhandler.query(
                                                [
                                                    "INSERT INTO modposts VALUES (?,?,?)", 
                                                    [
                                                        str(subpostobject["id"]), 
                                                        str(mapsetid), 
                                                        str(channel.id)
                                                    ]
                                                ]
                                            )
                                            if (not subpostobject['system']) and (not subpostobject["message"] == "r") and (not subpostobject["message"] == "res") and (not subpostobject["message"] == "resolved"):
                                                modtopost = await modpost(subpostobject, beatmapset_discussions, discussion, tracking_mode)
                                                if modtopost:
                                                    try:
                                                        await channel.send(embed=modtopost)
                                                    except Exception as e:
                                                        print(e)
                        except Exception as e:
                            print(time.strftime('%X %x %Z'))
                            print("while looping through discussions")
                            print(e)
                            print(discussion)
                else:
                    print("No actual discussions found at %s or mapset untracked automatically" % (mapsetid))
            else:
                print("%s | modchecker connection issues" % (time.strftime('%X %x %Z')))
                await asyncio.sleep(300)
            await asyncio.sleep(120)
        await asyncio.sleep(1800)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in modchecker.main")
        print(e)
        await asyncio.sleep(300)


async def get_username(beatmapset_discussions, subpostobject):
    for oneuser in beatmapset_discussions["beatmapset"]["related_users"]:
        if subpostobject['user_id'] == oneuser['id']:
            if "bng" in oneuser['groups']:
                return oneuser['username']+" [BN]"
            elif "qat" in oneuser['groups']:
                return oneuser['username']+" [QAT]"
            else:
                return oneuser['username']


async def get_diffname(beatmapset_discussions, newevent):
    for onediff in beatmapset_discussions["beatmapset"]["beatmaps"]:
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


async def modpost(subpostobject, beatmapset_discussions, newevent, tracking_mode):
    if subpostobject:
        if tracking_mode == "0":
            title = str(await get_diffname(beatmapset_discussions, newevent))
        elif tracking_mode == "1":
            title = "%s / %s" % (str(beatmapset_discussions["beatmapset"]["title"]), str(await get_diffname(beatmapset_discussions, newevent)))
            if newevent['message_type'] == "hype":
                return None
            elif newevent['message_type'] == "praise":
                return None

        footer = await get_modtype(newevent)
        modpost = discord.Embed(
            title=title,
            url="https://osu.ppy.sh/beatmapsets/%s/discussion#/%s" % (
                str(beatmapset_discussions["beatmapset"]["id"]), str(newevent['id'])),
            description=str(subpostobject['message']),
            color=footer['color']
        )
        modpost.set_author(
            name=str(await get_username(beatmapset_discussions, subpostobject)),
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