import json
import time
import asyncio
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import osuwebapipreview
from modules import utils


async def comparelists(list1, list2, reverse):
    difference = []
    if reverse:
        comparelist1 = list2
        comparelist2 = list1
    else:
        comparelist1 = list1
        comparelist2 = list2
    for i in comparelist1:
        if not i in comparelist2:
            difference.append(i)
    return difference


async def compare(result, lookupvalue, tablename, lookupkey, updatedb, reverse):
    if not await dbhandler.select(tablename, lookupkey, [[lookupkey, lookupvalue]]):
        await dbhandler.insert(tablename, (lookupvalue, json.dumps(result)))
        return None
    else:
        if result:
            if updatedb:
                await dbhandler.update(tablename, 'contents', json.dumps(result), lookupkey, lookupvalue)
                print("db is updating for sure %s" % (lookupvalue))
            localdata = json.loads((await dbhandler.select(tablename, 'contents', [[lookupkey, lookupvalue]]))[0][0])
            comparison = await comparelists(result, localdata, reverse)
            if comparison:
                print("comparison if block %s and %s" %
                      (lookupvalue, str(updatedb)))
                return comparison
            else:
                return None
        else:
            print('connection problems?')
            return None


async def groupmain(client, user, groupname, groupurl, description, groupfeedchannellist, color):
    osuprofile = await osuapi.get_user(user)
    if not osuprofile:
        osuprofile = {}
        osuprofile['username'] = "restricted user"
        osuprofile['user_id'] = user
    embed = await osuembed.groupmember(
        osuprofile,
        groupname,
        groupurl,
        description % ("[%s](https://osu.ppy.sh/users/%s)" % (osuprofile['username'],
                                                              str(osuprofile['user_id'])), "[%s](%s)" % (groupname, groupurl)),
        color
    )
    for groupfeedchannelid in groupfeedchannellist:
        channel = await utils.get_channel(client.get_all_channels(), int(groupfeedchannelid[0]))
        await channel.send(embed=embed)


async def groupcheck(client, groupfeedchannellist, groupid, groupname):
    userlist = await osuwebapipreview.groups(groupid)
    checkadditions = await compare(userlist, groupid, 'feedjsondata', 'feedtype', False, False)
    checkremovals = await compare(userlist, groupid, 'feedjsondata', 'feedtype', True, True)
    if checkadditions:
        for newuser in checkadditions:
            print("groupfeed | %s | added %s" % (groupname, newuser))
            await groupmain(client, newuser, groupname, "https://osu.ppy.sh/groups/%s" % (groupid), "**%s** \nhas been added to \nthe **%s**", groupfeedchannellist, 0xffbd0e)
    if checkremovals:
        for removeduser in checkremovals:
            print("groupfeed | %s | removed %s" % (groupname, removeduser))
            await groupmain(client, removeduser, groupname, "https://osu.ppy.sh/groups/%s" % (groupid), "**%s** \nhas been removed from \nthe **%s**", groupfeedchannellist, 0x2c0e6c)


async def main(client):
    try:
        await asyncio.sleep(120)
        print(time.strftime('%X %x %Z')+' | groupfeed')
        groupfeedchannellist = await dbhandler.query("SELECT channelid FROM groupfeedchannels")
        if groupfeedchannellist:
            await groupcheck(client, groupfeedchannellist, "7", "Quality Assurance Team")
            await asyncio.sleep(5)
            await groupcheck(client, groupfeedchannellist, "28", "Beatmap Nomination Group")
            await asyncio.sleep(120)
            await groupcheck(client, groupfeedchannellist, "4", "Global Moderation Team")
            await asyncio.sleep(120)
            await groupcheck(client, groupfeedchannellist, "11", "Developers")
            await asyncio.sleep(120)
            await groupcheck(client, groupfeedchannellist, "16", "osu! Alumni")
            await asyncio.sleep(120)
            await groupcheck(client, groupfeedchannellist, "22", "Support Team Redux")
        await asyncio.sleep(1600)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in groupfeed_background_loop")
        print(e)
        await asyncio.sleep(3600)