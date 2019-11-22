import discord
from discord.ext import commands
from modules import permissions
from modules import db
from collections import Counter
import operator
import pycountry


class MemberStatistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="demographics", brief="Send server demographics stats", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def demographics(self, ctx):
        async with ctx.channel.typing():
            master_list = []
            query = db.query("SELECT country, user_id FROM users")
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
                    country_flag = ":flag_%s:" % (stat[0].lower())
                except:
                    country_flag = ":gay_pride_flag:"
                    country_name = "??"+stat[0]
                contents += "**[%s]** : %s **%s** : %s : %s %% \n" % (
                    rank, country_flag, country_name, amount, percentage)
                if len(contents) > 1800:
                    embed = discord.Embed(description=contents, color=0xbd3661)
                    embed.set_author(name="Server Demographics")
                    await ctx.send(embed=embed)
                    contents = ""

            if contents == "":
                contents = "\n"
            embed = discord.Embed(description=contents, color=0xbd3661)
            embed.set_author(name="Server Demographics")
        await ctx.send(embed=embed)

    @commands.command(name="from", brief="Get a list of members from specified country",
                      description="Takes Alpha-2, Alpha-3 codes and full country names")
    @commands.guild_only()
    async def users_from(self, ctx, *, country_code="US"):
        async with ctx.channel.typing():
            try:
                if len(country_code) == 2:
                    country_object = pycountry.countries.get(alpha_2=country_code.upper())
                elif len(country_code) == 3:
                    country_object = pycountry.countries.get(alpha_3=country_code.upper())
                else:
                    country_object = pycountry.countries.get(name=country_code)
                country_name = country_object.name
                country_flag = ":flag_%s:" % (country_object.alpha_2.lower())
            except:
                await ctx.send("Country not found. "
                               "Keep in mind that full country names are case-sensitive. "
                               "\nYou can also try searching with Alpha-2 and Alpha-3 codes.")
                return None

            master_list = []
            query = db.query(["SELECT osu_username, osu_id, user_id FROM users "
                              "WHERE country = ? ",
                              [str(country_object.alpha_2.upper())]])
            for member in ctx.guild.members:
                if not member.bot:
                    for db_user in query:
                        if str(member.id) == str(db_user[2]):
                            master_list.append(db_user)

            member_amount = len(master_list)
            master_list.sort()
            contents = "%s members from %s %s\n" % (str(member_amount), country_flag, country_name)

            for one_member in master_list:
                contents += "[%s](https://osu.ppy.sh/users/%s)\n" % (one_member[0], one_member[1])
                if len(contents) > 1800:
                    embed = discord.Embed(description=contents, color=0xbd3661)
                    embed.set_author(name="Country Demographics")
                    await ctx.send(embed=embed)
                    contents = ""

            if contents == "":
                contents = "\n"
            embed = discord.Embed(description=contents, color=0xbd3661)
            embed.set_author(name="Country Demographics")
        await ctx.send(embed=embed)
        # TODO: add a send_professionally command to avoid implementing a way around 2000 char limit every time

    async def stats_calc(self, data):
        results = dict(Counter(data))
        return reversed(sorted(results.items(), key=operator.itemgetter(1)))


def setup(bot):
    bot.add_cog(MemberStatistics(bot))
