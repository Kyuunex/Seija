import discord
import asyncio
from modules import modelements


async def mapset(beatmapobject):
    if beatmapobject:
        mapsetembed = discord.Embed(
            title=str(beatmapobject['title']),
            url="https://osu.ppy.sh/beatmapsets/%s" % (
                str(beatmapobject['beatmapset_id'])),
            description=str(beatmapobject['artist']),
            color=0xbd3661
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
        return mapsetembed
    else:
        return None


async def osuprofile(osuprofile):
    if osuprofile:
        osuprofileembed = discord.Embed(
            title=osuprofile['username'],
            url='https://osu.ppy.sh/users/%s' % (str(osuprofile['user_id'])),
            color=0xbd3661
        )
        osuprofileembed.set_thumbnail(
            url='https://a.ppy.sh/%s' % (str(osuprofile['user_id']))
        )
        osuprofileembed.add_field(
            name="Country",
            value=':flag_%s: %s' % (
                osuprofile['country'].lower(), osuprofile['country']),
            inline=True
        )
        osuprofileembed.add_field(
            name="PP",
            value=osuprofile['pp_raw'],
            inline=True
        )
        osuprofileembed.add_field(
            name="Rank",
            value=osuprofile['pp_rank'],
            inline=True
        )
        osuprofileembed.add_field(
            name="Join Date",
            value=osuprofile['join_date'],
            inline=True
        )
        return osuprofileembed
    else:
        return None


async def modpost(subpostobject, beatmapsetdiscussionobject, newevent, trackingtype):
    if subpostobject:
        if trackingtype == "0":
            title = str(await modelements.diffname(beatmapsetdiscussionobject, newevent))
        elif trackingtype == "1":
            title = "%s / %s" % (str(beatmapsetdiscussionobject["beatmapset"]["title"]), str(await modelements.diffname(beatmapsetdiscussionobject, newevent)))
            if newevent['message_type'] == "hype":
                return None
            elif newevent['message_type'] == "praise":
                return None

        footer = await modelements.modtype(newevent)
        modpost = discord.Embed(
            title=title,
            url="https://osu.ppy.sh/beatmapsets/%s/discussion#/%s" % (
                str(beatmapsetdiscussionobject["beatmapset"]["id"]), str(newevent['id'])),
            description=str(subpostobject['message']),
            color=footer['color']
        )
        modpost.set_author(
            name=str(await modelements.username(beatmapsetdiscussionobject, subpostobject)),
            url="https://osu.ppy.sh/users/%s" % (
                str(subpostobject['user_id'])),
            icon_url="https://a.ppy.sh/%s" % (str(subpostobject['user_id']))
        )
        modpost.set_thumbnail(
            url="https://b.ppy.sh/thumb/%sl.jpg" % (
                str(beatmapsetdiscussionobject["beatmapset"]["id"]))
        )
        modpost.set_footer(
            text=str(footer['text']),
            icon_url=str(footer['icon'])
        )
        return modpost
    else:
        return None


async def groupmember(osuprofile, groupname, groupurl, description, color):
    if osuprofile:
        osuprofileembed = discord.Embed(
            # title=groupname,
            # url=groupurl,
            description=description,
            color=color
        )
        # osuprofileembed.set_author(
        #	name=osuprofile['username'],
        #	url='https://osu.ppy.sh/users/%s' % (str(osuprofile['user_id'])),
        #	icon_url='https://a.ppy.sh/%s' % (str(osuprofile['user_id']))
        #	)
        osuprofileembed.set_thumbnail(
            url='https://a.ppy.sh/%s' % (str(osuprofile['user_id']))
        )
        return osuprofileembed
    else:
        return None
