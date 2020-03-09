import discord
from discord.ext import commands
from modules import permissions
from modules import wrappers
from modules import cooldown
from collections import Counter
import operator
import pycountry


class MemberStatistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="demographics", brief="Send server demographics stats", description="")
    @commands.guild_only()
    async def demographics(self, ctx):
        if not await cooldown.check(str(ctx.guild.id), "last_demographics_time", 40):
            if not await permissions.is_admin(ctx):
                await ctx.send("slow down bruh")
                return None

        async with ctx.channel.typing():
            master_list = []
            async with self.bot.db.execute("SELECT country, user_id FROM users") as cursor:
                query = await cursor.fetchall()
            for member in ctx.guild.members:
                if not member.bot:
                    for user_in_db in query:
                        if str(member.id) == user_in_db[1]:
                            master_list.append(user_in_db[0])
            stats = await self.stats_calc(master_list)

            rank = 0
            contents = ""
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
                contents += f"**[{rank}]** : {country_flag} **{country_name}** : {amount} : {percentage} % \n"

            embed = discord.Embed(description=contents, color=0xbd3661)
            embed.set_author(name="Server Demographics")
        await wrappers.send_large_embed(ctx.channel, embed, contents)

    @commands.command(name="from", brief="Get a list of members from specified country",
                      description="Takes Alpha-2, Alpha-3 codes and full country names")
    @commands.guild_only()
    async def users_from(self, ctx, *, country_code="US"):
        if not await cooldown.check(str(ctx.author.id), "last_from_time", 10):
            if not await permissions.is_admin(ctx):
                await ctx.send("slow down bruh")
                return None

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
                await ctx.send("Country not found. "
                               "Keep in mind that full country names are case-sensitive. "
                               "\nYou can also try searching with Alpha-2 and Alpha-3 codes.")
                return None

            master_list = []
            async with self.bot.db.execute("SELECT osu_username, osu_id, user_id FROM users WHERE country = ? ",
                                           [str(country_object.alpha_2.upper())]) as cursor:
                query = await cursor.fetchall()
            for member in ctx.guild.members:
                if not member.bot:
                    for db_user in query:
                        if str(member.id) == str(db_user[2]):
                            master_list.append(db_user)

            member_amount = len(master_list)
            master_list.sort()
            contents = f"{member_amount} members from {country_flag} {country_name}\n"

            for one_member in master_list:
                contents += f"[{one_member[0]}](https://osu.ppy.sh/users/{one_member[1]})\n"

            embed = discord.Embed(description=contents, color=0xbd3661)
            embed.set_author(name="Country Demographics")
        await wrappers.send_large_embed(ctx.channel, embed, contents)

    async def stats_calc(self, data):
        results = dict(Counter(data))
        return reversed(sorted(results.items(), key=operator.itemgetter(1)))


def setup(bot):
    bot.add_cog(MemberStatistics(bot))
