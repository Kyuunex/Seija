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

    @commands.command(name="af_apply", brief="Apply April fools commands", description="", pass_context=True, hidden=True)
    async def af_apply(self, ctx, action):
        if permissions.check_owner(ctx.message.author.id):
            await ctx.message.delete()
            await apply_guild(self.bot, ctx)
            await apply_channels(self.bot, ctx)
            await asyncio.sleep(10)
            await apply_roles(self.bot, ctx)
            #await rotate_logo(self.bot, ctx)
            try:
                await ctx.send(file=discord.File("data/imsorry.png"))
            except:
                await ctx.send(":ok_hand:")
        else:
            await ctx.send(embed=permissions.error_owner())

    @commands.command(name="af_restore", brief="Restore from April fools", description="", pass_context=True, hidden=True)
    async def af_restore(self, ctx, action):
        if permissions.check_owner(ctx.message.author.id):
            await ctx.message.delete()
            await restore_guild(self.bot, ctx)
            await restore_channels(self.bot, ctx)
            await asyncio.sleep(10)
            await restore_roles(self.bot, ctx)
            #await rotate_logo(self.bot, ctx)
            await ctx.send(":ok_hand:")
        else:
            await ctx.send(embed=permissions.error_owner())


async def apply_channels(client, ctx):
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


async def restore_channels(client, ctx):
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


async def apply_roles(client, ctx):
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


async def restore_roles(client, ctx):
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


async def apply_guild(client, ctx):
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


async def restore_guild(client, ctx):
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


# async def rotate_logo(client, ctx):
#     guild = ctx.guild
#     oldiconurl = guild.icon_url
#     if oldiconurl:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(oldiconurl) as imageresponse:
#                 buffer = (await imageresponse.read())
#                 im = Image.open(io.BytesIO(buffer))
#                 im = im.rotate(180)
#                 im = im.convert('RGBA')
#                 newbytes = io.BytesIO()
#                 im.save(newbytes, format='PNG')
#                 newbytes = newbytes.getvalue()
#         try:
#             await guild.edit(icon=newbytes)
#         except Exception as e:
#             print(e)
#             print("in rotate_logo")
#             await asyncio.sleep(10)



#TODO: reverse channel
#TODO: rotate all emotes

def setup(bot):
    bot.add_cog(AprilFools(bot))
