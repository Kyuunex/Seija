import discord
import asyncio
import pycountry
import time


async def mapset(beatmapsetobject, color = 0xbd3661):
    try:
        if beatmapsetobject:
            beatmapobject = beatmapsetobject[0]
            mapsetembed = discord.Embed(
                title=str(beatmapobject['title']),
                url="https://osu.ppy.sh/beatmapsets/%s" % (str(beatmapobject['beatmapset_id'])),
                description=str(beatmapobject['artist']),
                color=int(color)
            )
            mapsetembed.set_author(
                name=str(beatmapobject['creator']),
                url="https://osu.ppy.sh/users/%s" % (str(beatmapobject['creator_id'])),
                icon_url="https://a.ppy.sh/%s" % (str(beatmapobject['creator_id']))
            )
            mapsetembed.set_thumbnail(
                url="https://b.ppy.sh/thumb/%sl.jpg" % (str(beatmapobject['beatmapset_id']))
            )
            mapsetembed.set_footer(
                text=str(beatmapobject['source']),
                icon_url='https://raw.githubusercontent.com/ppy/osu-resources/51f2b9b37f38cd349a3dd728a78f8fffcb3a54f5/osu.Game.Resources/Textures/Menu/logo.png'
            )
            for onediff in beatmapsetobject:
                if onediff["mode"] == "0":
                    gamemode = "std"
                elif onediff["mode"] == "1":
                    gamemode = "Taiko"
                elif onediff["mode"] == "2":
                    gamemode = "CtB"
                elif onediff["mode"] == "3":
                    gamemode = "mania"
                if onediff["difficultyrating"]:
                    sr = "%s ☆ %s" % (str(round(float(onediff["difficultyrating"]), 2)), gamemode)
                else:
                    sr = gamemode
                mapsetembed.add_field(
                    name=onediff["version"], 
                    value=sr, 
                    inline=True
                )
            return mapsetembed
        else:
            return None
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in osuembed.mapset")
        print(e)
        return None

async def osuprofile(osuprofile):
    try:
        if osuprofile:
            body = ""
            
            if osuprofile['country']:
                try:
                    country = pycountry.countries.get(alpha_2=osuprofile['country'])
                    body += ":flag_%s: %s\n" % (osuprofile['country'].lower(), country.name)
                except:
                    pass

            if osuprofile['pp_raw']:
                body += "%spp (#%s)\n" % (str(osuprofile['pp_raw']), str(osuprofile['pp_rank']))

            body += "Joined osu on: %s\n" % (str(osuprofile['join_date']))

            osuprofileembed = discord.Embed(
                title=osuprofile['username'],
                url='https://osu.ppy.sh/users/%s' % (str(osuprofile['user_id'])),
                color=0xbd3661,
                description=body,
            )
            osuprofileembed.set_thumbnail(
                url='https://a.ppy.sh/%s' % (str(osuprofile['user_id']))
            )
            return osuprofileembed
        else:
            return None
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in osuembed.osuprofile")
        print(e)
        return None