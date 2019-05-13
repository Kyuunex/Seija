from modules import dbhandler
import upsidedown
import aiohttp
import io
import asyncio
#from PIL import Image

async def apply_channels(client, ctx):
    guild = ctx.guild
    for channel in guild.channels:
        await asyncio.sleep(1)
        results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]])
        if not results:
            try:
                await dbhandler.query(["INSERT INTO name_backups VALUES (?, ?)", [str(channel.id), str(channel.name)]])
                await channel.edit(name=upsidedown.transform(channel.name))
            except Exception as e:
                print(e)
                print("in apply_channels / %s" % (channel.name))
                await asyncio.sleep(10)


async def restore_channels(client, ctx):
    guild = ctx.guild
    for channel in guild.channels:
        await asyncio.sleep(1)
        results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(channel.id)]])
        if results:
            try:
                await channel.edit(name=str(results[0][0]))
                await dbhandler.query(["DELETE FROM name_backups WHERE id = ?", [str(channel.id)]])
            except Exception as e:
                print(e)
                print("in restore_channels / %s" % (results[0][0]))
                await asyncio.sleep(10)


async def apply_roles(client, ctx):
    guild = ctx.guild
    for role in guild.roles:
        await asyncio.sleep(1)
        results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(role.id)]])
        if not results:
            await dbhandler.query(["INSERT INTO name_backups VALUES (?, ?)", [str(role.id), str(role.name)]])
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
        results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(role.id)]])
        if results:
            try:
                await role.edit(name=str(results[0][0]))
            except Exception as e:
                print(e)
                print("in restore_roles / %s" % (results[0][0]))
                await asyncio.sleep(10)
            await dbhandler.query(["DELETE FROM name_backups WHERE id = ?", [str(role.id)]])


async def apply_guild(client, ctx):
    guild = ctx.guild
    results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]])
    if not results:
        await dbhandler.query(["INSERT INTO name_backups VALUES (?, ?)", [str(guild.id), str(guild.name)]])
        try:
            await guild.edit(name=upsidedown.transform(guild.name))
        except Exception as e:
            print(e)
            print("in apply_guild")
            await asyncio.sleep(10)


async def restore_guild(client, ctx):
    guild = ctx.guild
    results = await dbhandler.query(["SELECT name FROM name_backups WHERE id = ?", [str(guild.id)]])
    if results:
        try:
            await guild.edit(name=str(results[0][0]))
        except Exception as e:
            print(e)
            print("in restore_guild")
            await asyncio.sleep(10)
        await dbhandler.query(["DELETE FROM name_backups WHERE id = ?", [str(guild.id)]])


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