import discord
from discord.ext import commands
import osuembed
from modules import permissions
from reusables import exceptions
import osuwebembed


class Osu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mapset", brief="Show mapset info")
    @commands.check(permissions.is_not_ignored)
    async def mapset(self, ctx, mapset_id: str):
        try:
            result = await self.bot.osu.get_beatmapset(s=mapset_id)
        except Exception as e:
            await ctx.send("Connection problems?",
                           embed=await exceptions.embed_exception(e))
            return

        embed = await osuembed.beatmapset(result)
        if not embed:
            await ctx.send(content="`No mapset found with that ID`")
            return

        await ctx.send(embed=embed)

    @commands.command(name="user", brief="Show osu user info")
    @commands.check(permissions.is_not_ignored)
    async def user(self, ctx, *, username):
        try:
            result = await self.bot.osuweb.get_user_array(username)
        except Exception as e:
            await ctx.send("Connection problems?", 
                           embed=await exceptions.embed_exception(e))
            return

        if not result:
            await ctx.send(content="`No user found with that username`")
            return

        embed = await osuwebembed.user_array(result)

        await ctx.send(embed=embed)

    @commands.command(name="ts", brief="Send an osu editor clickable timestamp")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def ts(self, ctx, *, string):
        """
        Send an osu editor clickable timestamp
        Must start with a timestamp
        This command needs a proper solution, this is half-assed.
        """

        if "-" in string:
            timestamp_data = string.split("-")
            timestamp_link = (timestamp_data[0]).strip().replace(" ", "_")
            try:
                timestamp_desc = "- " + timestamp_data[1]
            except:
                timestamp_desc = ""
        else:
            timestamp_link = string.strip().replace(" ", "_")
            timestamp_desc = ""
        embed = discord.Embed(
            description=f"<osu://edit/{timestamp_link}> {timestamp_desc}",
            color=ctx.author.colour
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.avatar_url
        )
        try:
            await ctx.send(embed=embed)
            await ctx.message.delete()
        except Exception as e:
            print(e)


def setup(bot):
    bot.add_cog(Osu(bot))
