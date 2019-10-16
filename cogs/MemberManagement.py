import discord
import asyncio
import time
import datetime
from discord.ext import commands
from modules import permissions
from modules import db
import osuembed
import pycountry
import upsidedown

from modules.connections import osu as osu


class MemberManagement(commands.Cog, name="Member Management"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="print_all", brief="Print all users and their profiles from db", description="", pass_context=True)
    @commands.check(permissions.is_owner)
    async def print_all(self, ctx, mention_users: str = None):
        try:
            if mention_users == "m":
                tag = "<@%s> / %s"
            else:
                tag = "%s / %s"
            for one_user in db.query("SELECT * FROM users"):
                try:
                    userprofile = await osu.get_user(u=one_user[1])
                    embed = await osuembed.user(userprofile)
                except:
                    print("Connection issues?")
                    await ctx.send("Connection issues?")
                    await asyncio.sleep(10)
                    embed = None
                if embed:
                    await ctx.send(content=tag % (one_user[0], one_user[2]), embed=embed)
                await asyncio.sleep(1)
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in userdb")
            print(e)

    @commands.command(name="get_users_not_in_db", brief="Get a list of users who are not in db", description="", pass_context=True)
    @commands.check(permissions.is_owner)
    async def get_users_not_in_db(self, ctx, mention_users: str = None):
        try:
            responce = "These users are not in my database:\n"
            count = 0
            for member in ctx.guild.members:
                if not member.bot:
                    if not db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]]):
                        count += 1
                        if mention_users == "m":
                            responce += ("<@%s>\n" % (str(member.id)))
                        else:
                            responce += ("\"%s\" %s\n" % (str(member.display_name), str(member.id)))
                        if count > 40:
                            count = 0
                            responce += ""
                            await ctx.send(responce)
                            responce = "\n"
            responce += ""
            await ctx.send(responce)
        except Exception as e:
            print(time.strftime('%X %x %Z'))
            print("in userdb")
            print(e)

    @commands.command(name="check_ranked", brief="Return ranked mappers who don't have the role", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def check_ranked(self, ctx):
        await self.check_ranked_amount_by_role(ctx, 1, "guild_mapper_role")

    @commands.command(name="check_experienced", brief="Return experienced mappers who don't have the role", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def check_experienced(self, ctx):
        await self.check_ranked_amount_by_role(ctx, 10, "guild_ranked_mapper_role")

    @commands.command(name="roleless", brief="Get a list of members without a role", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def roleless(self, ctx, lookup_in_db: str = None):
        for member in ctx.guild.members:
            if len(member.roles) < 2:
                await ctx.send(member.mention)
                if lookup_in_db:
                    try:
                        query = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]])
                        if query:
                            await ctx.send("person above is in my database and linked to <https://osu.ppy.sh/users/%s>" % (query[0][0]))
                    except Exception as e:
                        await ctx.send(e)

    @commands.command(name="cv", brief="Check which osu account is a discord account linked to", description="", pass_context=True)
    @commands.check(permissions.is_admin)
    async def cv(self, ctx, *, user_id):
        osu_profile = (db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]]))
        if osu_profile:
            osu_id = osu_profile[0][0]
            result = await osu.get_user(u=osu_id)
            embed = await osuembed.user(result)
            await ctx.send("https://osu.ppy.sh/users/%s" % (osu_id), embed=embed)


    async def check_ranked_amount_by_role(self, ctx, amount = 1, role_name = "guild_mapper_role"):
        role = discord.utils.get(ctx.guild.roles, id=int((db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", [role_name, str(ctx.guild.id)]]))[0][0]))
        if role:
            output = "These fella's are the result of this check:\n"
            async with ctx.channel.typing():
                for member in role.members:
                    lookupuser = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id), ]])
                    if lookupuser:
                        try:
                            mapsbythisguy = await osu.get_beatmapsets(u=str(lookupuser[0][0]))
                            if mapsbythisguy:
                                try:
                                    ranked_amount = await self.count_ranked_beatmapsets(mapsbythisguy)
                                except Exception as e:
                                    print(e)
                                    print("Connection issues?")
                                    ranked_amount = 0
                                if ranked_amount >= amount:
                                    output += "%s\n" % (member.mention)
                            else:
                                print("problem with %s" % (member.display_name))
                        except Exception as e:
                            print(e)
                            print(str(lookupuser[0][0]))
                    await asyncio.sleep(0.5)
            await ctx.send(output)
        else:
            await ctx.send("Nope")

    async def count_ranked_beatmapsets(self, beatmapsets):
        try:
            count = 0
            if beatmapsets:
                for beatmapset in beatmapsets:
                    if beatmapset.approved == "1" or beatmapset.approved == "2":
                        count += 1
            return count
        except Exception as e:
            print(e)
            return 0

def setup(bot):
    bot.add_cog(MemberManagement(bot))
