import asyncio
import time
import datetime
import json
import discord
from modules import dbhandler
from modules import osuapi
from modules import osuembed
from modules import utils


async def comparelists(list2, list1):
    difference = []
    for i in list1:
        if not i in list2:
            difference.append(i)
    return difference


async def main(client):
    try:
        print(time.strftime('%X %x %Z')+' | manual loop')
        tracklist = await dbhandler.query("SELECT * FROM scoretrackingdata")
        if tracklist:
            for oneentry in tracklist:
                user_top_scores = await osuapi.get_user_best(oneentry[0])
                if user_top_scores:
                    localdata = json.loads(oneentry[3])
                    #await dbhandler.query(["UPDATE scoretrackingdata SET contents = ? WHERE osuid = ?", [json.dumps(user_top_scores), oneentry[0]]])
                    difference = await comparelists(localdata, user_top_scores)
                    for newscore in difference:
                        beatmap = await osuapi.get_beatmap(newscore['beatmap_id'], "b")
                        embed = await print_play(newscore, beatmap, oneentry[1])
                        for onechannel in oneentry[2].split(","):
                            tochannel = client.get_channel(int(onechannel))
                            await tochannel.send(embed=embed)
                else:
                    print("`%s` | `%s` | restricted or connection issues" % (str(oneentry[0])))
        await asyncio.sleep(1200)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in scoretracking")
        print(e)
        await asyncio.sleep(7200)


async def track(ctx, userid, channellist):
    user_top_scores = await osuapi.get_user_best(str(userid))
    if user_top_scores:
        trackinfo = await dbhandler.query(["SELECT * FROM scoretrackingdata WHERE osuid = ?", [str(user_top_scores[0]['user_id'])]])
        if not trackinfo:
            osuprofile = await osuapi.get_user(str(userid))
            await dbhandler.query(
                [
                    "INSERT INTO scoretrackingdata VALUES (?,?,?,?)", 
                    [
                        str(user_top_scores[0]['user_id']), 
                        str(osuprofile['username']), 
                        str(channellist), 
                        str(json.dumps(user_top_scores)),
                    ]
                ])
            await ctx.send(content='Tracked %s' % (userid))
        else:
            cl = trackinfo[0][2].split(",")
            for onenewchannel in str(channellist).split(","):
                cl.append(onenewchannel)
            await dbhandler.query(["UPDATE scoretrackingdata SET channels = ? WHERE osuid = ?", [",".join(cl), str(user_top_scores[0]['user_id'])]])
            await ctx.send(content='Tracked %s in here' % (userid))


async def untrack(ctx, userid, channellist):
    # TODO: actually implement this
    await dbhandler.query(["DELETE FROM scoretrackingdata WHERE osuid = ?", [str(userid)]])


async def tracklist(ctx):
    tracklist = await dbhandler.query("SELECT * FROM scoretrackingdata")
    if tracklist:
        for oneentry in tracklist:
            channellist = ""
            for onechannel in oneentry[2].split(","):
                channellist += "<#%s> " % (onechannel)
            await ctx.send(content='osu_id: `%s` | Username: `%s` | channels: %s' % (oneentry[0], oneentry[1], channellist))


async def print_play(play, beatmap, display_name):
    try:
        embed = discord.Embed(
            title=str(beatmap['title']), 
            description=str(beatmap['version']), 
            url='https://osu.ppy.sh/beatmapsets/%s' % (str(beatmap['beatmapset_id'])), 
            color=0xbd3661
        )
        embed.set_author(
            name="%s just made a new top play on:" % (display_name),
            url="https://osu.ppy.sh/users/%s" % (str(play['user_id'])),
            icon_url="https://a.ppy.sh/%s" % (str(play['user_id']))
        )
        embed.set_thumbnail(
            url="https://b.ppy.sh/thumb/%sl.jpg" % (str(beatmap['beatmapset_id']))
        )
        embed.add_field(
            name='PP', 
            value=str(play['pp']), 
            inline=True
        )
        embed.add_field(
            name='Rank', 
            value=str(play['rank']), 
            inline=True
        )
        embed.add_field(
            name='Accuracy', 
            value=str(await compute_acc(str(play['countmiss']), str(play['count50']), str(play['count100']), str(play['count300'])))+" %",
            inline=True
        )
        embed.add_field(
            name='Score', 
            value=str(play['score']), 
            inline=True
        )
        embed.add_field(
            name='Combo', 
            value='%s/%s' % (str(play['maxcombo']), str(beatmap['max_combo'])), 
            inline=True
        )
        embed.add_field(
            name='Mods', 
            value=str(await get_mods(int(play['enabled_mods']))), 
            inline=True
        )
        embed.add_field(
            name='Stars', 
            value="%s ☆" % (str(round(float(beatmap['difficultyrating']), 2))), 
            inline=True
        )
        embed.add_field(
            name='Miss', 
            value=str(play['countmiss']), 
            inline=True
        )
        embed.set_footer(
            text=str(play['date']), 
            icon_url='https://raw.githubusercontent.com/ppy/osu-resources/51f2b9b37f38cd349a3dd728a78f8fffcb3a54f5/osu.Game.Resources/Textures/Menu/logo.png'
        )
        return embed
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in scoretracking.print_play")
        print(e)
        return None


async def compute_acc(cmiss, c50, c100, c300):
    return str(round(float(((int(c50)*50 + int(c100)*100 + int(c300)*300) / ((int(cmiss)+int(c50)+int(c100)+int(c300))*300))*100), 2))


async def get_mods(number):
    # Thanks Ayato_k
    mod_list = ['NF', 'EZ', 'NV', 'HD', 'HR', 'SD', 'DT', '128', 'HT', 'NC', 'FL', 'AutoPlay', 'SO', 'AP', 'PF', '4K', '5K', '6K', '7K', '8K', 'KM', 'FI', 'RanD', 'LM', 'FM', '9K', '10K', '1K', '3K', '2K']
    if number <= 0:
        return 'None'
    bin_list = [int(x) for x in bin(number)[2:]]
    i=0
    mod_str = ''
    for y in reversed(bin_list):
        if y == 1:
            mod_str += mod_list[i]
        i+=1
    return mod_str