import time

import discord
from discord.ext import commands
from seija.modules import permissions
from seija.reusables import exceptions
from seija.reusables import send_large_message
from seija.embeds import newembeds as osuwebembed
from aioosuwebapi import exceptions as aioosuwebapi_exceptions


class MemberManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="get_members_not_in_db", brief="Get a list of users who are not in db")
    @commands.check(permissions.is_owner)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_members_not_in_db(self, ctx, has_a_role=""):
        """
        This command will return a list of members who are not in the bot's `users` table.
        """

        async with ctx.channel.typing():
            buffer = ""
            for member in ctx.guild.members:
                if member.bot:
                    continue

                if has_a_role:
                    if not len(member.roles) > 1:
                        # actually every member has @everyone role,
                        # so, if a user has 2 roles, it means he has 1 assigned role
                        continue

                async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?",
                                               [int(member.id)]) as cursor:
                    in_db_check = await cursor.fetchall()
                if in_db_check:
                    continue

                buffer += f"{member.mention}\n"

            embed = discord.Embed(color=0xbd3661)
            embed.set_author(name="Server Members who are not in the database")
        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="get_roleless_members", brief="Get a list of members without a role")
    @commands.check(permissions.is_owner)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_roleless_members(self, ctx, lookup_in_db=""):
        """
        This command will return a list of members who do not have any roles.
        :arg lookup_in_db: if this is not null, the bot will also see if the member is in the db
        """

        async with ctx.channel.typing():
            buffer = ""
            for member in ctx.guild.members:
                if len(member.roles) > 1:
                    # actually every member has @everyone role,
                    # so, if a user has 2 roles, it means he has 1 assigned role
                    continue

                buffer += f"{member.mention}\n"

                if not lookup_in_db:
                    continue

                async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?",
                                               [int(member.id)]) as cursor:
                    query = await cursor.fetchone()
                if not query:
                    continue

                buffer += f"    ^ <https://osu.ppy.sh/users/{query[0]}>"
            embed = discord.Embed(color=0xbd3661)
            embed.set_author(name="Server Members who do not have a role")
        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="get_member_osu_profile", brief="Check which osu account is a discord account linked to")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def get_member_osu_profile(self, ctx, *, user_id):
        """
        Return what osu account is a discord account linked to
        """

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [int(user_id)]) as cursor:
            osu_id = await cursor.fetchone()
        if not osu_id:
            await ctx.reply("the specified discord user id does not link with any osu accounts")
            return

        try:
            result = await self.bot.osuweb.get_user_array(osu_id[0])
        except aioosuwebapi_exceptions.HTTPException as e:
            print(time.strftime("%Y/%m/%d %H:%M:%S %Z"))
            print("in get_member_osu_profile, connection issues to osu api v2 servers")
            print(e)
            await ctx.reply(f"I found a record of this user's osu account in my database, "
                            f"but I seem to be having connection problems with osu api v2 servers. "
                            f"Their profile url should be <https://osu.ppy.sh/users/{osu_id[0]}>")
            return

        if not result:
            await ctx.reply(f"I found a record of this user's osu account in my database, "
                            f"but osu api v2 servers seem to not return anything about them. "
                            f"Their profile url should be <https://osu.ppy.sh/users/{osu_id[0]}>")
            return

        embed = await osuwebembed.user_array(result)
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(MemberManagement(bot))
