import json
import time
import asyncio
from jsondiff import diff
import jsondiff
from modules import utils
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview
from modules import osuwebapipreview


async def compare(result, mapsetid):
    if not await dbhandler.select('jsondata', 'mapsetid', [['mapsetid', mapsetid]]):
        # await dbhandler.insert('jsondata', (mapsetid, json.dumps(result, indent=4, sort_keys=True)))
        await dbhandler.insert('jsondata', (mapsetid, json.dumps(result)))
        return None
    else:
        localdata = json.loads((await dbhandler.select('jsondata', 'contents', [['mapsetid', mapsetid]]))[0][0])
        if result != localdata:
            await dbhandler.update('jsondata', 'contents', json.dumps(result), 'mapsetid', mapsetid)
            if result:
                difference = diff(localdata, result)
                if jsondiff.insert in difference:
                    return dict(difference[jsondiff.insert])
            else:
                print('connection problems?')
                return None


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
    if not await dbhandler.select('modtracking', 'mapsetid', [['mapsetid', str(mapsetid)]]):
        mapsetmetadata = await osuapi.get_beatmap(str(mapsetid))
        embed = await osuembed.mapset(mapsetmetadata)
        if embed:
            beatmapsetdiscussionobject = await osuwebapipreview.discussion(str(mapsetid))
            if beatmapsetdiscussionobject:
                await dbhandler.insert('modtracking', (str(mapsetid), str(ctx.message.channel.id), mapsethostdiscordid, roleid, str(mapsetmetadata['creator_id']), trackingtype))
                await compare(beatmapsetdiscussionobject["beatmapset"]["discussions"], str(mapsetid))
                await populatedb(beatmapsetdiscussionobject)
                if trackingtype == 1:
                    await ctx.send(content='This mapset is now being tracked in this channel in veto mode', embed=embed)
                else:
                    await ctx.send(content='This mapset is now being tracked in this channel', embed=embed)
            else:
                await ctx.send(content='`No mapset found with that ID / Mapset has no modding v2 / Connection issues`')
        else:
            await ctx.send(content='`No mapset found with that ID`')


async def untrack(ctx, mapsetid, embed, ranked):
    where = [
            ['mapsetid', str(mapsetid)],
            ['channelid', str(ctx.message.channel.id)]
    ]
    if await dbhandler.select('modtracking', 'mapsetid', where):
        await dbhandler.delete('modtracking', where)

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
            channel = await utils.get_channel(client.get_all_channels(), int(oneentry[1]))
            mapsetid = oneentry[0]
            trackingtype = str(oneentry[5])
            print(time.strftime('%X %x %Z')+' | '+oneentry[0])

            beatmapsetdiscussionobject = await osuwebapipreview.discussion(mapsetid)
            if beatmapsetdiscussionobject:
                newevents = await compare(beatmapsetdiscussionobject["beatmapset"]["discussions"], mapsetid)

                if newevents:
                    for newevent in newevents:
                        newevent = newevents[newevent]
                        if newevent:
                            for subpostobject in newevent['posts']:
                                if not subpostobject['system']:
                                    if not await dbhandler.query(["SELECT postid FROM modposts WHERE postid = ?", [str(subpostobject['id']), ]]):
                                        await dbhandler.query(
                                            [
                                                "INSERT INTO modposts VALUES (?,?,?,?,?)", 
                                                [
                                                    str(subpostobject["id"]), 
                                                    str(mapsetid), 
                                                    str(newevent["beatmap_id"]), 
                                                    str(subpostobject["user_id"]), 
                                                    str(subpostobject["message"])
                                                ]
                                            ]
                                        )
                                        modtopost = await osuembed.modpost(subpostobject, beatmapsetdiscussionobject, newevent, trackingtype)
                                        if modtopost:
                                            await channel.send(embed=modtopost)
            else:
                print(time.strftime('%X %x %Z') +
                        " | Possible connection issues")
                await asyncio.sleep(300)
            await asyncio.sleep(120)
        await asyncio.sleep(1800)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in background_loop")
        print(e)
        print(newevent)
        await asyncio.sleep(300)