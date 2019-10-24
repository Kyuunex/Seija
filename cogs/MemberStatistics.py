import discord
from discord.ext import commands
from modules import permissions
from modules import db
from collections import Counter
import operator
import pycountry


class MemberStatistics(commands.Cog, name="Member Statistics Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="demographics", brief="Send server demographics stats", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def demographics(self, ctx):
        async with ctx.channel.typing():
            masterlist = []
            for member in ctx.guild.members:
                if not member.bot:
                    query = db.query(["SELECT country FROM users WHERE user_id = ?", [str(member.id)]])
                    if query:  # [5]
                        masterlist.append(query[0][0])
            stats = await self.statscalc(masterlist)

            rank = 0
            contents = ""
            memberamount = len(masterlist)

            for oneentry in stats:
                rank += 1
                amount = str(oneentry[1]) + " Members"
                percentage = str(round(float(int(oneentry[1]) * 100 / memberamount), 2))
                try:
                    countryobject = pycountry.countries.get(alpha_2=oneentry[0])
                    countryname = countryobject.name
                    countryflag = ":flag_%s:" % (oneentry[0].lower())
                except:
                    countryflag = ":gay_pride_flag:"
                    countryname = oneentry[0]
                contents += "**[%s]** : %s **%s** : %s : %s %% \n" % (
                rank, countryflag, countryname, amount, percentage)
                if len(contents) > 1800:
                    statsembed = discord.Embed(description=contents, color=0xbd3661)
                    statsembed.set_author(name="Server Demographics")
                    await ctx.send(embed=statsembed)
                    contents = ""

            if contents == "":
                contents = "\n"
            statsembed = discord.Embed(description=contents, color=0xbd3661)
            statsembed.set_author(name="Server Demographics")
        await ctx.send(embed=statsembed)

    @commands.command(name="from", brief="Get a list of members from specified country",
                      description="Takes Alpha-2, Alpha-3 codes and full country names", pass_context=True)
    async def users_from(self, ctx, *, country_code="US"):
        async with ctx.channel.typing():
            try:
                if len(country_code) == 2:
                    countryobject = pycountry.countries.get(alpha_2=country_code.upper())
                elif len(country_code) == 3:
                    countryobject = pycountry.countries.get(alpha_3=country_code.upper())
                else:
                    countryobject = pycountry.countries.get(name=country_code)
                countryname = countryobject.name
                countryflag = ":flag_%s:" % (countryobject.alpha_2.lower())
            except:
                countryobject = None
                countryflag = "\n"
                countryname = ""

            masterlist = []
            if countryobject:
                for member in ctx.guild.members:
                    if not member.bot:
                        query = db.query(["SELECT osu_username, osu_id FROM users WHERE country = ? AND user_id = ?",
                                          [str(countryobject.alpha_2.upper()), str(member.id)]])
                        if query:
                            masterlist.append(query[0])
            memberamount = len(masterlist)
            masterlist.sort()
            contents = "%s members from %s %s\n" % (str(memberamount), countryflag, countryname)

            for one_member in masterlist:
                contents += "[%s](https://osu.ppy.sh/users/%s)\n" % (one_member[0], one_member[1])
                if len(contents) > 1800:
                    statsembed = discord.Embed(description=contents, color=0xbd3661)
                    statsembed.set_author(name="Country Demographics")
                    await ctx.send(embed=statsembed)
                    contents = ""

            if contents == "":
                contents = "\n"
            statsembed = discord.Embed(description=contents, color=0xbd3661)
            statsembed.set_author(name="Country Demographics")
        if countryobject:
            await ctx.send(embed=statsembed)
        else:
            await ctx.send(
                "Country not found. Keep in mind that full country names are case-sensetive.\nYou can also try searching with alpha 2 codes.")

    async def statscalc(self, data):
        results = dict(Counter(data))
        return reversed(sorted(results.items(), key=operator.itemgetter(1)))


def setup(bot):
    bot.add_cog(MemberStatistics(bot))
