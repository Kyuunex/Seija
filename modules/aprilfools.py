from modules import dbhandler
import upsidedown
import aiohttp
import io
from PIL import Image

async def apply_channels(client, ctx):
    guild = ctx.guild
    for channel in guild.channels:
        results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(channel.id)]])
        if not results:
            await dbhandler.query(["INSERT INTO namebackups VALUES (?, ?)", [str(channel.id), str(channel.name)]])
            await channel.edit(name=upsidedown.transform(channel.name))


async def restore_channels(client, ctx):
    guild = ctx.guild
    for channel in guild.channels:
        results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(channel.id)]])
        if results:
            await channel.edit(name=str(results[0][0]))
            await dbhandler.query(["DELETE FROM namebackups WHERE id = ?", [str(channel.id)]])


async def apply_roles(client, ctx):
    guild = ctx.guild
    for role in guild.roles:
        results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(role.id)]])
        if not results:
            await dbhandler.query(["INSERT INTO namebackups VALUES (?, ?)", [str(role.id), str(role.name)]])
            try:
                await role.edit(name=upsidedown.transform(role.name))
            except Exception as e:
                print(e)


async def restore_roles(client, ctx):
    guild = ctx.guild
    for role in guild.roles:
        results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(role.id)]])
        if results:
            try:
                await role.edit(name=str(results[0][0]))
            except Exception as e:
                print(e)
            await dbhandler.query(["DELETE FROM namebackups WHERE id = ?", [str(role.id)]])


async def apply_guild(client, ctx):
    guild = ctx.guild
    results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(guild.id)]])
    if not results:
        await dbhandler.query(["INSERT INTO namebackups VALUES (?, ?)", [str(guild.id), str(guild.name)]])
        try:
            await guild.edit(name=upsidedown.transform(guild.name))
        except Exception as e:
            print(e)


async def restore_guild(client, ctx):
    guild = ctx.guild
    results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(guild.id)]])
    if results:
        try:
            await guild.edit(name=str(results[0][0]))
        except Exception as e:
            print(e)
        await dbhandler.query(["DELETE FROM namebackups WHERE id = ?", [str(guild.id)]])


async def rotate_logo(client, ctx):
    guild = ctx.guild
    oldiconurl = guild.icon_url
    async with aiohttp.ClientSession() as session:
        async with session.get(oldiconurl) as imageresponse:
            buffer = (await imageresponse.read())
            im = Image.open(io.BytesIO(buffer))
            im = im.rotate(180)
            im = im.convert('RGBA')
            newbytes = io.BytesIO()
            im.save(newbytes, format='PNG')
            newbytes = newbytes.getvalue()
    try:
        await guild.edit(icon=newbytes)
    except Exception as e:
        print(e)
