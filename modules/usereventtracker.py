import asyncio
import time
import datetime
from jsondiff import diff
import jsondiff
import json
import re
from html import unescape
from modules import dbhandler
from modules import users
from modules import osuapi
from modules import osuembed
from modules import utils


async def compare(result, osuid):
    if not await dbhandler.query(["SELECT osuid FROM userevents WHERE osuid = ?", [osuid]]):
        await dbhandler.query(["INSERT INTO userevents VALUES (?,?)", [osuid, json.dumps(result)]])
        return None
    else:
        localdata = json.loads((await dbhandler.query(["SELECT contents FROM userevents WHERE osuid = ?", [osuid]]))[0][0])
        await dbhandler.query(["UPDATE userevents SET contents = ? WHERE osuid = ?", [json.dumps(result), osuid]])
        if type(result) is None:
            print('connection problems?')
            await asyncio.sleep(120)
            return None
        else:
            difference = diff(list(localdata), list(result))
            if jsondiff.insert in difference:
                return dict(difference[jsondiff.insert])


async def main(client):
    try:
        print(time.strftime('%X %x %Z')+' | tracking members')
        memberfeedchannellist = await dbhandler.query(["SELECT * FROM config WHERE setting = ?", ["usereventtracker"]])
        if memberfeedchannellist:
            now = datetime.datetime.now()
            for onechannel in memberfeedchannellist:
                auditchannel = client.get_channel(int(onechannel[3]))
                feedchannel = client.get_channel(int(onechannel[2]))
                guild = client.get_guild(int(onechannel[1]))
                for member in guild.members:
                    if not member.bot:
                        query = await dbhandler.query(["SELECT * FROM users WHERE discordid = ?", [str(member.id)]])
                        if query:
                            osuprofile = await osuapi.get_user(query[0][1])
                            if osuprofile:
                                await users.one_guild_member_sync(auditchannel, query, now, member, osuprofile)
                                await usereventtrack(feedchannel, osuprofile)
                            else:
                                await utils.send_notice("%s | `%s` | `%s` | restricted" % (member.mention, str(query[0][2]), str(query[0][1])), auditchannel, now)
                        else:
                            await utils.send_notice("%s | not in db" % (member.mention), auditchannel, now)
        await asyncio.sleep(7200)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in membertrack")
        print(e)
        await asyncio.sleep(7200)


async def usereventtrack(channel, osuprofile):
    print("currently checking %s" % (osuprofile['username']))
    newevents = await compare(osuprofile['events'], str(osuprofile['user_id']))
    if newevents:
        for newevent in newevents:
            newevent = newevents[newevent]
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