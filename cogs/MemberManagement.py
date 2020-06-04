import discord
import asyncio
from discord.ext import commands
from modules import permissions
from modules import wrappers
import osuembed


class MemberManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="get_members_not_in_db", brief="Get a list of users who are not in db", description="")
    @commands.check(permissions.is_owner)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_members_not_in_db(self, ctx):
        for member in ctx.guild.members:
            if not member.bot:
                async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?",
                                               [str(member.id)]) as cursor:
                    in_db_check = await cursor.fetchall()
                if not in_db_check:
                    await ctx.send(member.mention)

    @commands.command(name="get_roleless_members", brief="Get a list of members without a role", description="")
    @commands.check(permissions.is_owner)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_roleless_members(self, ctx, lookup_in_db: str = None):
        for member in ctx.guild.members:
            if len(member.roles) < 2:
                await ctx.send(member.mention)
                if lookup_in_db:
                    async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?",
                                                   [str(member.id)]) as cursor:
                        query = await cursor.fetchall()
                    if query:
                        await ctx.send("person above is in my database "
                                       f"and linked to <https://osu.ppy.sh/users/{query[0][0]}>")

    @commands.command(name="get_member_osu_profile",
                      brief="Check which osu account is a discord account linked to", description="")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_member_osu_profile(self, ctx, *, user_id):
        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]) as cursor:
            osu_id = await cursor.fetchall()
        if osu_id:
            result = await self.bot.osu.get_user(u=osu_id[0][0])
            if result:
                embed = await osuembed.user(result)
                await ctx.send(result.url, embed=embed)
            else:
                await ctx.send(f"<https://osu.ppy.sh/users/{osu_id[0][0]}>")

    @commands.command(name="check_ranked", brief="Update member roles based on their ranking amount", description="")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def check_ranked(self, ctx):
        await self.check_ranked_amount_by_role(ctx, 10, "ranked_mapper", "experienced_mapper")
        await self.check_ranked_amount_by_role(ctx, 1, "mapper", "ranked_mapper")

    async def check_ranked_amount_by_role(self, ctx, amount, old_role_setting, new_role_setting):
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [old_role_setting, str(ctx.guild.id)]) as cursor:
            old_role_id = await cursor.fetchall()
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [new_role_setting, str(ctx.guild.id)]) as cursor:
            new_role_id = await cursor.fetchall()
        old_role = discord.utils.get(ctx.guild.roles, id=int(old_role_id[0][0]))
        new_role = discord.utils.get(ctx.guild.roles, id=int(new_role_id[0][0]))
        if not old_role:
            return
        if not new_role:
            return
        updated_members = ""
        async with ctx.channel.typing():
            for member in old_role.members:
                await asyncio.sleep(0.5)

                async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?",
                                               [str(member.id)]) as cursor:
                    osu_id = await cursor.fetchall()
                if not osu_id:
                    continue

                try:
                    mapsets = await self.bot.osu.get_beatmapsets(u=osu_id[0][0])
                except:
                    # await ctx.send(e)
                    mapsets = None

                if not mapsets:
                    continue

                ranked_amount = await self.count_ranked_beatmapsets(mapsets)

                if ranked_amount >= amount:
                    await member.add_roles(new_role, reason="reputation updated")
                    await member.remove_roles(old_role, reason="removed old reputation")
                    updated_members += f"{member.mention} : {member.display_name}\n"

        embed = discord.Embed(color=0xbd3661)

        if len(updated_members) > 0:
            embed.set_author(name=f"I gave {new_role_setting} to the following members:")
            await wrappers.send_large_embed(ctx.channel, embed, updated_members)
        else:
            embed.set_author(name=f"no new member updated with {new_role_setting}")
            await ctx.send(embed=embed)

    async def count_ranked_beatmapsets(self, mapsets):
        try:
            count = 0
            if mapsets:
                for mapset in mapsets:
                    if mapset.approved == "1" or mapset.approved == "2":
                        count += 1
            return count
        except Exception as e:
            print(e)
            return 0


def setup(bot):
    bot.add_cog(MemberManagement(bot))
