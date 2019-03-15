import asyncio
import time
import datetime
import json
import re
from html import unescape
from modules import dbhandler
from modules import users
from modules import osuapi
from modules import osuembed
from modules import utils


async def comparelists(list2, list1):
    difference = []
    for i in list1:
        if not i in list2:
            difference.append(i)
    return difference


async def compare(result, osuid, table = "userevents"):
    if not await dbhandler.query(["SELECT osuid FROM %s WHERE osuid = ?" % (table), [osuid]]):
        await dbhandler.query(["INSERT INTO %s VALUES (?,?)" % (table), [osuid, json.dumps(result)]])
        return None
    else:
        localdata = json.loads((await dbhandler.query(["SELECT contents FROM %s WHERE osuid = ?" % (table), [osuid]]))[0][0])
        await dbhandler.query(["UPDATE %s SET contents = ? WHERE osuid = ?" % (table), [json.dumps(result), osuid]])
        if type(result) is None:
            print('usereventtracker connection problems?')
            await asyncio.sleep(120)
            return None
        else:
            difference = await comparelists(localdata, result)
            return difference


async def manual_loop(client):
    try:
        print(time.strftime('%X %x %Z')+' | manual loop')
        manualfeedenabled = await dbhandler.query(["SELECT * FROM config WHERE setting = ?", ["manualusereventtracker"]])
        if manualfeedenabled:
            for oneentry in await dbhandler.query("SELECT * FROM manualusereventtracking"):
                osuprofile = await osuapi.get_user(oneentry[0])
                if osuprofile: #
                    await usereventtrack(client, oneentry[1].split(","), osuprofile, "manualuserevents")
                else:
                    print("`%s` | `%s` | restricted" % (str(oneentry[0])))
        await asyncio.sleep(1200)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in membertrack")
        print(e)
        await asyncio.sleep(7200)
        

async def usereventtrack(client, channel, osuprofile, table = "userevents"):
    print("currently checking %s" % (osuprofile['username']))
    newevents = await compare(osuprofile['events'], str(osuprofile['user_id']), table)
    if newevents:
        for newevent in newevents:
            if newevent:
                eventcolor = await determineevent(newevent['display_html'])
                if eventcolor:
                    embed = await osuembed.mapset(await osuapi.get_beatmaps(newevent['beatmapset_id']), eventcolor)
                    if embed:
                        display_text = unescape(re.sub('<[^<]+?>', '', newevent['display_html']))
                        try:
                            print(display_text)
                        except:
                            print(osuprofile['username'])
                        if type(channel) is list:
                            for onechannel in channel:
                                tochannel = client.get_channel(int(onechannel))
                                await tochannel.send(display_text, embed=embed)
                        elif type(channel) is int:
                            tochannel = client.get_channel(int(channel))
                            await tochannel.send(display_text, embed=embed)
                        else:
                            await channel.send(display_text, embed=embed)


async def determineevent(string):
    if 'has submitted' in string:
        return 0x2a52b2
    elif 'has updated' in string:
        #return 0xb2532a
        return None
    elif 'qualified' in string:
        return 0x2ecc71
    elif 'has been revived' in string:
        return 0xff93c9
    elif 'has been deleted' in string:
        return 0xf2d7d5
    else:
        return None
