import discord
import pycountry

from discord.utils import escape_markdown

default_embed_color = 0xffffff


async def beatmapset(mapset, color=default_embed_color):
    if mapset:
        body = f""

        for beatmap in sorted(mapset.beatmaps, key=lambda x: x.difficulty_rating, reverse=False):
            try:
                short_dec = str(round(float(beatmap.difficultyrating), 2))
                body += f"{short_dec} ☆ {beatmap.version} [{beatmap.gamemode}] \n"
            except:
                pass
        if len(body) > 2048:
            body = ""
        escaped_body = escape_markdown(body)
        embed = discord.Embed(
            title=escape_markdown(f"{mapset.artist} - {mapset.title}"),
            url=mapset.url,
            description=escaped_body,
            color=int(color)
        )
        embed.set_author(
            name=mapset.creator,
            url=f"https://osu.ppy.sh/users/{mapset.creator_id}",
            icon_url=f"https://a.ppy.sh/{mapset.creator_id}",
        )
        embed.set_thumbnail(
            url=mapset.thumb
        )
        embed.set_footer(
            text=mapset.source,
        )
        return embed
    else:
        return None


async def user(user, color=default_embed_color, custom_footer=""):
    if user:
        body = ""

        if user.country:
            try:
                country = pycountry.countries.get(alpha_2=user.country.upper())
                country_flag_emote = f":flag_{country.alpha_2.lower()}:"
                body += f"{country_flag_emote} {country.name}\n"
            except:
                pass

        if user.pp:
            body += f"{user.pp}pp (#{user.rank})\n"

        body += f"Joined osu on: {user.join_date}\n"

        embed = discord.Embed(
            title=escape_markdown(user.username),
            url=user.url,
            color=color,
            description=body,
        )
        embed.set_thumbnail(
            url=user.avatar
        )
        embed.set_footer(
            text=custom_footer
        )
        return embed
    else:
        return None
