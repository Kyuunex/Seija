from modules import db
from modules import permissions
import upsidedown
import aiohttp
import io
import asyncio
import discord
from discord.ext import commands
from PIL import Image


class AprilFools(commands.Cog, name="April Fools Management Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="af_2019_apply", brief="Apply April fools 2019 commands", description="")
    @commands.check(permissions.is_owner)
    @commands.guild_only()
    async def af_2019_apply(self, ctx):
        await ctx.message.delete()
        await self.apply_guild(ctx)
        await self.apply_channels(ctx)
        await asyncio.sleep(10)
        await self.apply_roles(ctx)
        await self.rotate_logo(ctx)
        try:
            await ctx.send(file=discord.File("data/sorry.png"))
        except Exception as e:
            print(e)
            await ctx.send(":ok_hand:")

    @commands.command(name="af_2019_restore", brief="Restore from April fools 2019", description="")
    @commands.check(permissions.is_owner)
    @commands.guild_only()
    async def af_2019_restore(self, ctx):
        await ctx.message.delete()
        await self.restore_guild(ctx)
        await self.restore_channels(ctx)
        await asyncio.sleep(10)
        await self.restore_roles(ctx)
        await self.rotate_logo(ctx)
        await ctx.send(":ok_hand:")

    @commands.command(name="af_2020_apply", brief="Apply April fools 2020 commands", description="")
    @commands.check(permissions.is_owner)
    @commands.guild_only()
    async def af_2020_apply(self, ctx):
        pass

    @commands.command(name="af_2020_restore", brief="Restore from April fools 2020", description="")
    @commands.check(permissions.is_owner)
    @commands.guild_only()
    async def af_2020_apply(self, ctx):
        pass

    async def apply_channels(self, ctx):
        guild = ctx.guild
        for channel in guild.channels:
            await asyncio.sleep(1)
            results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]])
            if not results:
                try:
                    db.query(["INSERT INTO name_backups VALUES (?, ?)", [str(channel.id), str(channel.name)]])
                    await channel.edit(name=upsidedown.transform(channel.name))
                except Exception as e:
                    print(e)
                    print("in apply_channels / %s" % channel.name)
                    await asyncio.sleep(10)

    async def restore_channels(self, ctx):
        guild = ctx.guild
        for channel in guild.channels:
            await asyncio.sleep(1)
            results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]])
            if results:
                try:
                    await channel.edit(name=str(results[0][0]))
                    db.query(["DELETE FROM name_backups WHERE id = ?", [str(channel.id)]])
                except Exception as e:
                    print(e)
                    print("in restore_channels / %s" % (results[0][0]))
                    await asyncio.sleep(10)

    async def apply_roles(self, ctx):
        guild = ctx.guild
        for role in guild.roles:
            await asyncio.sleep(1)
            results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(role.id)]])
            if not results:
                db.query(["INSERT INTO name_backups VALUES (?, ?)", [str(role.id), str(role.name)]])
                try:
                    await role.edit(name=upsidedown.transform(role.name))
                except Exception as e:
                    print(e)
                    print("in apply_roles / %s" % role.name)
                    await asyncio.sleep(10)

    async def restore_roles(self, ctx):
        guild = ctx.guild
        for role in guild.roles:
            await asyncio.sleep(1)
            results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(role.id)]])
            if results:
                try:
                    await role.edit(name=str(results[0][0]))
                except Exception as e:
                    print(e)
                    print("in restore_roles / %s" % (results[0][0]))
                    await asyncio.sleep(10)
                db.query(["DELETE FROM name_backups WHERE id = ?", [str(role.id)]])

    async def apply_guild(self, ctx):
        guild = ctx.guild
        results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]])
        if not results:
            db.query(["INSERT INTO name_backups VALUES (?, ?)", [str(guild.id), str(guild.name)]])
            try:
                await guild.edit(name=upsidedown.transform(guild.name))
            except Exception as e:
                print(e)
                print("in apply_guild")
                await asyncio.sleep(10)

    async def restore_guild(self, ctx):
        guild = ctx.guild
        results = db.query(["SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]])
        if results:
            try:
                await guild.edit(name=str(results[0][0]))
            except Exception as e:
                print(e)
                print("in restore_guild")
                await asyncio.sleep(10)
            db.query(["DELETE FROM name_backups WHERE id = ?", [str(guild.id)]])

    async def rotate_logo(self, ctx):
        guild = ctx.guild
        old_icon_url = guild.icon_url
        if old_icon_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(old_icon_url) as image_response:
                    buffer = (await image_response.read())
                    im = Image.open(io.BytesIO(buffer))
                    im = im.rotate(180)
                    im = im.convert('RGBA')
                    new_bytes = io.BytesIO()
                    im.save(new_bytes, format='PNG')
                    new_bytes = new_bytes.getvalue()
            try:
                await guild.edit(icon=new_bytes)
            except Exception as e:
                print(e)
                print("in rotate_logo")
                await asyncio.sleep(10)


def setup(bot):
    bot.add_cog(AprilFools(bot))
