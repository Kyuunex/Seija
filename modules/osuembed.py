import discord
import asyncio
import pycountry


async def mapset(beatmapsetobject, color = 0xbd3661):
    if beatmapsetobject:
        beatmapobject = beatmapsetobject[0]
        mapsetembed = discord.Embed(
            title=str(beatmapobject['title']),
            url="https://osu.ppy.sh/beatmapsets/%s" % (
                str(beatmapobject['beatmapset_id'])),
            description=str(beatmapobject['artist']),
            color=int(color)
        )
        mapsetembed.set_author(
            name=str(beatmapobject['creator']),
            url="https://osu.ppy.sh/users/%s" % (
                str(beatmapobject['creator_id'])),
            icon_url="https://a.ppy.sh/%s" % (str(beatmapobject['creator_id']))
        )
        mapsetembed.set_thumbnail(
            url="https://b.ppy.sh/thumb/%sl.jpg" % (
                str(beatmapobject['beatmapset_id']))
        )
        mapsetembed.set_footer(
            text=str(beatmapobject['source']),
            icon_url='https://raw.githubusercontent.com/ppy/osu-resources/51f2b9b37f38cd349a3dd728a78f8fffcb3a54f5/osu.Game.Resources/Textures/Menu/logo.png'
        )
        for onediff in beatmapsetobject:
            if onediff["mode"] == "0":
                gamemode = "osu!"
            elif onediff["mode"] == "1":
                gamemode = "Taiko"
            elif onediff["mode"] == "2":
                gamemode = "CtB"
            elif onediff["mode"] == "3":
                gamemode = "osu!mania"
            mapsetembed.add_field(
                name=onediff["version"], 
                value="%s [%s]" % (str(round(float(onediff["difficultyrating"]), 2)), gamemode), 
                inline=True
            )
        return mapsetembed
    else:
        return None


async def osuprofile(osuprofile):
    if osuprofile:
        try:
            usercountry = pycountry.countries.get(
                alpha_2=osuprofile['country'])
            flag = ":flag_%s: %s\n" % (
                osuprofile['country'].lower(), usercountry.name)
        except:
            flag = ""
        if osuprofile['pp_raw']:
            performance = "%spp (#%s)\n" % (
                str(osuprofile['pp_raw']), str(osuprofile['pp_rank']))
        else:
            performance = ""
        osuprofileembed = discord.Embed(
            title=osuprofile['username'],
            url='https://osu.ppy.sh/users/%s' % (str(osuprofile['user_id'])),
            color=0xbd3661,
            description=str("%s%sJoined osu on: %s" %
                            (flag, performance, str(osuprofile['join_date'])))
        )
        osuprofileembed.set_thumbnail(
            url='https://a.ppy.sh/%s' % (str(osuprofile['user_id']))
        )
        return osuprofileembed
    else:
        return None
