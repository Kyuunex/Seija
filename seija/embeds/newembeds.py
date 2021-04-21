import discord
import dateutil.parser
from discord.utils import escape_markdown

default_embed_color = 0xffffff


async def beatmapset_array(mapset, color=default_embed_color):
    if mapset:
        body = f""

        sorted_diffs = sorted(mapset["beatmaps"], key=lambda k: k["difficulty_rating"])
        for beatmap in sorted_diffs:
            try:
                short_dec = str(beatmap["difficulty_rating"])
                body += f"{short_dec} ☆ {beatmap['version']} [{beatmap['mode']}] \n"
            except:
                pass
        if len(body) > 2048:
            body = ""
        embed = discord.Embed(
            title=f"{mapset['artist']} - {mapset['title']}",
            url=f"https://osu.ppy.sh/beatmapsets/{mapset['id']}",
            description=body,
            color=int(color)
        )
        embed.set_author(
            name=mapset['creator'],
            url=f"https://osu.ppy.sh/users/{mapset['user_id']}",
            icon_url=f"https://a.ppy.sh/{mapset['user_id']}",
        )
        embed.set_thumbnail(
            url=f"https://assets.ppy.sh/beatmaps/{mapset['id']}/covers/list@2x.jpg"
        )
        embed.set_footer(
            text=mapset["source"],
        )
        return embed
    else:
        return None


async def user_array(user, color=None, custom_footer=None):
    if user:
        body = ""
        if not color:
            if user["profile_colour"]:
                color = int(str(user['profile_colour']).replace("#", "0x"), 16)
            else:
                color = default_embed_color

        try:
            if user["title"]:
                body += f"**{user['title']}**\n"
        except KeyError:
            pass

        if user["country"]:
            try:
                country = user["country"]
                country_flag_emote = f":flag_{country['code'].lower()}:"
                body += f"{country_flag_emote} {country['name']}\n"
            except KeyError:
                pass

        if user["statistics"]["pp"]:
            body += f"{user['statistics']['pp']}pp (#{user['statistics']['global_rank']})\n"

        body += "\n"

        join_date = dateutil.parser.parse(user['join_date'])
        body += f"**Joined osu on:** {str(join_date.isoformat(' '))}\n"

        try:
            if user['last_visit']:
                last_visit = dateutil.parser.parse(user['last_visit'])
                body += f"**Last seen:** {str(last_visit.isoformat(' '))}\n"

            if user['discord']:
                body += f"**Discord:** {user['discord']}\n"

            if user['twitter']:
                body += f"**Twitter:** [{user['twitter']}](https://twitter.com/{user['twitter']})\n"
        except KeyError:
            pass


        body += f"**Follower count:** {user['follower_count']}\n"
        body += f"**Amount of ranked maps:** {user['ranked_and_approved_beatmapset_count']}\n"
        body += f"**Kudosu earned:** {user['kudosu']['total']}\n"

        if user['groups']:
            body += f"**Groups:** "
            for group in user['groups']:
                body += f"{group['name']}"
                if user['groups'][-1] != group:
                    body += ", "
            body += f"\n"

        if user['badges']:
            body += f"\n"
            body += f"**Badges:** \n"
            for badge in user['badges']:
                body += f"~ {badge['description']} ~"
                # body += f" ({badge['awarded_at']})"
                body += f"\n"
            body += f"\n"

        name = escape_markdown(user["username"])
        if user["is_supporter"]:
            name += f" :heart:"

        embed = discord.Embed(
            title=name,
            url=f"https://osu.ppy.sh/users/{user['id']}",
            color=color,
            description=body,
        )
        if "http" in user["avatar_url"]:
            embed.set_thumbnail(
                url=user["avatar_url"]
            )
        embed.set_image(
            url=user["cover_url"]
        )
        if custom_footer:
            embed.set_footer(
                text=custom_footer
            )
        return embed
    else:
        return None


async def small_user_array(user, color=None, custom_footer=None):
    if user:
        body = ""
        if not color:
            if user["profile_colour"]:
                color = int(str(user['profile_colour']).replace("#", "0x"), 16)
            else:
                color = default_embed_color
        try:
            if user["title"]:
                body += f"**{user['title']}**\n"
        except KeyError:
            pass

        if user["country"]:
            try:
                country = user["country"]
                country_flag_emote = f":flag_{country['code'].lower()}:"
                body += f"{country_flag_emote} {country['name']}\n"
            except KeyError:
                pass

        if user["statistics"]["pp"]:
            body += f"{user['statistics']['pp']}pp (#{user['statistics']['global_rank']})\n"

        body += "\n"

        join_date = dateutil.parser.parse(user['join_date'])
        body += f"**Joined osu on:** {str(join_date.isoformat(' '))}\n"

        try:
            if user['last_visit']:
                last_visit = dateutil.parser.parse(user['last_visit'])
                body += f"**Last seen:** {str(last_visit.isoformat(' '))}\n"

            if user['discord']:
                body += f"**Discord:** {user['discord']}\n"

            if user['twitter']:
                body += f"**Twitter:** [{user['twitter']}](https://twitter.com/{user['twitter']})\n"
        except KeyError:
            pass

        body += f"**Follower count:** {user['follower_count']}\n"
        body += f"**Amount of ranked maps:** {user['ranked_and_approved_beatmapset_count']}\n"
        body += f"**Kudosu earned:** {user['kudosu']['total']}\n"

        if user['groups']:
            body += f"**Groups:** "
            for group in user['groups']:
                body += f"{group['name']}"
                if user['groups'][-1] != group:
                    body += ", "
            body += f"\n"

        name = escape_markdown(user["username"])
        if user["is_supporter"]:
            name += f" :heart:"

        embed = discord.Embed(
            title=name,
            url=f"https://osu.ppy.sh/users/{user['id']}",
            color=color,
            description=body,
        )
        if "http" in user["avatar_url"]:
            # thanks peppy
            embed.set_thumbnail(
                url=user["avatar_url"]
            )
        if custom_footer:
            embed.set_footer(
                text=custom_footer
            )
        return embed
    else:
        return None
