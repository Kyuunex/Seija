from modules import dbhandler
import upsidedown

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
            except:
                print("no perms")


async def restore_roles(client, ctx):
    guild = ctx.guild
    for role in guild.roles:
        results = await dbhandler.query(["SELECT name FROM namebackups WHERE id = ?", [str(role.id)]])
        if results:
            try:
                await role.edit(name=str(results[0][0]))
            except:
                print("no perms")
            await dbhandler.query(["DELETE FROM namebackups WHERE id = ?", [str(role.id)]])
