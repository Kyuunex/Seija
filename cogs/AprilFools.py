from modules import db
from modules import permissions
import upsidedown
import aiohttp
import io
import asyncio
import discord
from discord.ext import commands
#from PIL import Image


class AprilFools(commands.Cog, name="April Fools Management Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="af_2018_apply", brief="Apply April fools commands", description="", pass_context=True, hidden=True)
    @commands.check(permissions.is_owner)
    async def af_apply(self, ctx, action):
        await ctx.message.delete()
        await self.apply_guild(ctx)
        await self.apply_channels(ctx)
        await asyncio.sleep(10)
        await self.apply_roles(ctx)
        await self.rotate_logo(ctx)
        try:
            await ctx.send(file=discord.File("data/imsorry.png"))
        except:
            await ctx.send(":ok_hand:")

    @commands.command(name="af_2018_restore", brief="Restore from April fools", description="", pass_context=True, hidden=True)
    @commands.check(permissions.is_owner)
    async def af_restore(self, ctx, action):
        await ctx.message.delete()
        await self.restore_guild(ctx)
        await self.restore_channels(ctx)
        await asyncio.sleep(10)
        await self.restore_roles(ctx)
        await self.rotate_logo(ctx)
        await ctx.send(":ok_hand:")

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
                    print("in apply_channels / %s" % (channel.name))
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
                    print("in apply_roles / %s" % (role.name))
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
            pass
            # async with aiohttp.ClientSession() as session:
            #     async with session.get(old_icon_url) as imageresponse:
            #         buffer = (await imageresponse.read())
            #         im = Image.open(io.BytesIO(buffer))
            #         im = im.rotate(180)
            #         im = im.convert('RGBA')
            #         newbytes = io.BytesIO()
            #         im.save(newbytes, format='PNG')
            #         newbytes = newbytes.getvalue()
            # try:
            #     await guild.edit(icon=newbytes)
            # except Exception as e:
            #     print(e)
            #     print("in rotate_logo")
            #     await asyncio.sleep(10)

def setup(bot):
    bot.add_cog(AprilFools(bot))
