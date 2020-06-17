import discord
from discord.ext import commands
from discord.utils import escape_markdown
from modules import permissions
from modules import wrappers
from modules import cooldown
from collections import Counter
import operator
import pycountry


class MemberStatistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="demographics", brief="Send server demographics stats")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def demographics(self, ctx):
        """
        Returns all countries in the order of how many members each has.
        Some partially recognized countries also exist on this list.
        This is all based on the data pulled from osu and processed in pycountry module.
        I actually don't decide what country is recognized and what is not.
        """

        if not await cooldown.check(str(ctx.guild.id), "last_demographics_time", 140):
            if not await permissions.is_admin(ctx):
                await ctx.send("slow down bruh")
                return

        async with ctx.channel.typing():
            master_list = []
            async with self.bot.db.execute("SELECT country, user_id FROM users") as cursor:
                query = await cursor.fetchall()

            for member in ctx.guild.members:
                if member.bot:
                    continue

                for user_in_db in query:
                    if str(member.id) != user_in_db[1]:
                        continue
                    master_list.append(user_in_db[0])
            stats = await self.stats_calc(master_list)

            rank = 0
            buffer = ""
            member_amount = len(master_list)

            for stat in stats:
                rank += 1
                amount = str(stat[1]) + " Members"
                percentage = str(round(float(int(stat[1]) * 100 / member_amount), 2))
                try:
                    country_object = pycountry.countries.get(alpha_2=stat[0])
                    country_name = country_object.name
                    country_flag = f":flag_{stat[0].lower()}:"
                except:
                    country_flag = ":flag_white:"
                    country_name = "??" + stat[0]
                buffer += f"**[{rank}]** : {country_flag} **{country_name}** : {amount} : {percentage} % \n"

            embed = discord.Embed(color=0xbd3661)
            embed.set_author(name="Server Demographics")
        await wrappers.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="from", brief="Get a list of members from specified country")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def users_from(self, ctx, *, country_code="US"):
        """
        Get a list of members from specified country.
        Takes Alpha-2, Alpha-3 codes and full country names.
        If you are not sure what this means, have a look at this
        https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
        """

        if not await cooldown.check(str(ctx.author.id), "last_from_time", 10):
            if not await permissions.is_admin(ctx):
                await ctx.send("slow down bruh")
                return

        async with ctx.channel.typing():
            try:
                if len(country_code) == 2:
                    country_object = pycountry.countries.get(alpha_2=country_code.upper())
                elif len(country_code) == 3:
                    country_object = pycountry.countries.get(alpha_3=country_code.upper())
                else:
                    country_object = pycountry.countries.get(name=country_code)
                country_name = country_object.name
                country_flag = f":flag_{country_object.alpha_2.lower()}:"
            except:
                await ctx.send(f"{ctx.author.mention}, Country not found. "
                               "Keep in mind that full country names are case-sensitive. \n"
                               "You can also try searching with Alpha-2 and Alpha-3 codes. \n"
                               "If you are not sure what this means, have a look at this "
                               "<https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2>")
                return

            master_list = []
            async with self.bot.db.execute("SELECT osu_username, osu_id, user_id FROM users WHERE country = ? ",
                                           [str(country_object.alpha_2.upper())]) as cursor:
                query = await cursor.fetchall()

            for member in ctx.guild.members:
                if member.bot:
                    continue

                for db_user in query:
                    if str(member.id) != str(db_user[2]):
                        continue

                    master_list.append(db_user)

            member_amount = len(master_list)
            master_list.sort()
            contents = f"{member_amount} members from {country_flag} {country_name}\n"

            for one_member in master_list:
                contents += f"[{escape_markdown(one_member[0])}](https://osu.ppy.sh/users/{one_member[1]})\n"

            embed = discord.Embed(color=0xbd3661)
            embed.set_author(name="Country Demographics")
        await wrappers.send_large_embed(ctx.channel, embed, contents)

    async def stats_calc(self, data):
        results = dict(Counter(data))
        return reversed(sorted(results.items(), key=operator.itemgetter(1)))


def setup(bot):
    bot.add_cog(MemberStatistics(bot))
