import urllib.request
import json
import asyncio
import time
import aiohttp

osuapikey = open("data/osuapikey.txt", "r+").read()
baseurl = "https://osu.ppy.sh/api/"


async def request(endpoint, query):
    query['k'] = osuapikey
    try:
        url = baseurl+endpoint+'?'+urllib.parse.urlencode(query)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return (await response.json())
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in osuapi.request")
        print(e)
        return None


async def get_user(username):
    query = {
        'u': username,
        'event_days': '4',
    }
    requestobject = await request('get_user', query)
    if requestobject:
        return requestobject[0]
    else:
        return None


async def get_beatmaps(mapsetid):
    query = {
        's': mapsetid,
    }
    requestobject = await request('get_beatmaps', query)
    if requestobject:
        return requestobject
    else:
        return None


async def get_beatmap(mapsetid):
    query = {
        's': mapsetid,
    }
    requestobject = await request('get_beatmaps', query)
    if requestobject:
        return requestobject[0]
    else:
        return None
