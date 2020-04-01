from modules import permissions
import upsidedown
# import aiohttp
# import io
import asyncio
import discord
from discord.ext import commands
# from PIL import Image


class AprilFools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="af_2019_apply", brief="Apply April fools 2019 commands", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def af_2019_apply(self, ctx):
        await ctx.message.delete()
        await self.apply_guild(ctx)
        await self.apply_channels(ctx)
        await asyncio.sleep(10)
        await self.apply_nicknames(ctx)
        await asyncio.sleep(10)
        await self.apply_roles(ctx)
        # await self.rotate_logo(ctx)
        try:
            await ctx.send(file=discord.File("data/sorry.png"))
        except Exception as e:
            print(e)
            await ctx.send(":ok_hand:")

    @commands.command(name="af_2019_restore", brief="Restore from April fools 2019", description="")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def af_2019_restore(self, ctx):
        await ctx.message.delete()
        await self.restore_guild(ctx)
        await self.restore_channels(ctx)
        await asyncio.sleep(10)
        await self.restore_roles(ctx)
        # await self.rotate_logo(ctx)
        await ctx.send(":ok_hand:")

    async def apply_nicknames(self, ctx):
        for member in ctx.guild.members:
            try:
                await member.edit(nick=upsidedown.transform(member.display_name))
            except:
                pass

    async def apply_channels(self, ctx):
        guild = ctx.guild
        for channel in guild.channels:
            await asyncio.sleep(1)
            async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]) as cursor:
                results = await cursor.fetchall()
            if not results:
                try:
                    await self.bot.db.execute("INSERT INTO name_backups VALUES (?, ?)",
                                              [str(channel.id), str(channel.name)])
                    await channel.edit(name=upsidedown.transform(channel.name))
                except Exception as e:
                    print(e)
                    print(f"in apply_channels / {channel.name}")
                    await asyncio.sleep(10)
        await self.bot.db.commit()

    async def restore_channels(self, ctx):
        guild = ctx.guild
        for channel in guild.channels:
            await asyncio.sleep(1)
            async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]) as cursor:
                results = await cursor.fetchall()
            if results:
                try:
                    await channel.edit(name=str(results[0][0]))
                    await self.bot.db.execute("DELETE FROM name_backups WHERE id = ?", [str(channel.id)])
                except Exception as e:
                    print(e)
                    print(f"in restore_channels / {results[0][0]}")
                    await asyncio.sleep(10)
        await self.bot.db.commit()

    async def apply_roles(self, ctx):
        guild = ctx.guild
        for role in guild.roles:
            await asyncio.sleep(1)
            async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(role.id)]) as cursor:
                results = await cursor.fetchall()
            if not results:
                await self.bot.db.execute("INSERT INTO name_backups VALUES (?, ?)", [str(role.id), str(role.name)])
                try:
                    await role.edit(name=upsidedown.transform(role.name))
                except Exception as e:
                    print(e)
                    print(f"in apply_roles / {role.name}")
                    await asyncio.sleep(10)
        await self.bot.db.commit()

    async def restore_roles(self, ctx):
        guild = ctx.guild
        for role in guild.roles:
            await asyncio.sleep(1)
            async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(role.id)]) as cursor:
                results = await cursor.fetchall()
            if results:
                try:
                    await role.edit(name=str(results[0][0]))
                except Exception as e:
                    print(e)
                    print(f"in restore_roles / {results[0][0]}")
                    await asyncio.sleep(10)
                await self.bot.db.execute("DELETE FROM name_backups WHERE id = ?", [str(role.id)])
        await self.bot.db.commit()

    async def apply_guild(self, ctx):
        guild = ctx.guild
        async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]) as cursor:
            results = await cursor.fetchall()
        if not results:
            await self.bot.db.execute("INSERT INTO name_backups VALUES (?, ?)", [str(guild.id), str(guild.name)])
            try:
                await guild.edit(name=upsidedown.transform(guild.name))
            except Exception as e:
                print(e)
                print("in apply_guild")
                await asyncio.sleep(10)
        await self.bot.db.commit()

    async def restore_guild(self, ctx):
        guild = ctx.guild
        async with self.bot.db.execute("SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]) as cursor:
            results = await cursor.fetchall()
        if results:
            try:
                await guild.edit(name=str(results[0][0]))
            except Exception as e:
                print(e)
                print("in restore_guild")
                await asyncio.sleep(10)
            await self.bot.db.execute("DELETE FROM name_backups WHERE id = ?", [str(guild.id)])
        await self.bot.db.commit()

    # async def rotate_logo(self, ctx):
    #     guild = ctx.guild
    #     old_icon_url = guild.icon_url
    #     if old_icon_url:
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(old_icon_url) as image_response:
    #                 buffer = (await image_response.read())
    #                 im = Image.open(io.BytesIO(buffer))
    #                 im = im.rotate(180)
    #                 im = im.convert("RGBA")
    #                 new_bytes = io.BytesIO()
    #                 im.save(new_bytes, format="PNG")
    #                 new_bytes = new_bytes.getvalue()
    #         try:
    #             await guild.edit(icon=new_bytes)
    #         except Exception as e:
    #             print(e)
    #             print("in rotate_logo")
    #             await asyncio.sleep(10)


def setup(bot):
    bot.add_cog(AprilFools(bot))
