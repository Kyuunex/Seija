import json
import asyncio
import time
import aiohttp

baseurl = "https://osu.ppy.sh/"
#baseurl = "http://192.168.9.13/"


async def customparser(after, before, string):
    return ((string.split(after))[1].split(before)[0]).strip()


async def rawrequest(endpointcategory, endpoint, query):
    try:
        url = baseurl+endpointcategory+'/'+query+'/'+endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                httpcontents = (await response.text())
                if len(httpcontents) > 4:
                    return httpcontents
                else:
                    return None
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in osuwebapipreview.rawrequest")
        print(e)
        return None


async def discussion(mapset):
    httpcontents = await rawrequest('beatmapsets', 'discussion', mapset)
    if httpcontents:
        if "json-beatmapset-discussion" in httpcontents:
            result = await customparser('<script id="json-beatmapset-discussion" type="application/json">', '</script>', httpcontents)
            return json.loads(result)
        elif "<h1>Page Missing</h1>" in httpcontents:
            return {
                "beatmapset": {
                    "status": "deleted"
                }
            }
        else:
            return None
    else:
        return None


async def groups(groupid):
    httpcontents = await rawrequest('groups', '', groupid)
    if httpcontents:
        if "user-action-button user-action-button--message" in httpcontents:
            messyarray = httpcontents.split(
                "https://osu.ppy.sh/home/messages/users/")
            actuallist = []
            for i in messyarray:
                parsedmemberid = (i.split("\""))[0]
                if not "<!DOCTYPE html>" in parsedmemberid:
                    actuallist.append(str(int(parsedmemberid)))
            return list(actuallist)
        else:
            return None
    else:
        return None
