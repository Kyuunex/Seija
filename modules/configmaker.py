from modules import db
from modules import docs
from modules import permissions
from modules import reputation
import discord
import asyncio

async def role_setup(client, ctx, setting, role_name):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        db.query(["INSERT INTO config VALUES (?, ?, ?, ?)", [str(setting), str(ctx.guild.id), str(role.id), "0"]])
        await ctx.send("%s added" % (role.name))


async def cfg_setup(client, ctx, setting, an_id):
    db.query(["INSERT INTO config VALUES (?, ?, ?, ?)", [str(setting), str(ctx.guild.id), str(an_id), "0"]])
    await ctx.send("don")