import discord

from modules import db


async def get_category_object(client, guild, setting, id_only=None):
    category_id = db.query(["SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                            [setting, str(guild.id)]])
    if category_id:
        category = client.get_channel(int(category_id[0][0]))
        if id_only:
            return category.id
        else:
            return category
    else:
        return False


async def get_role_object(client, guild, setting, id_only=None):
    role_id = db.query(["SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?", [setting, str(guild.id)]])
    if role_id:
        role = discord.utils.get(guild.roles, id=int(role_id[0][0]))
        if id_only:
            return role.id
        else:
            return role
    else:
        return False


async def unarchive_channel(client, ctx, setting):
    if int(ctx.channel.category_id) == int(await get_category_object(client, ctx.guild, "archive", id_only=True)):
        await ctx.channel.edit(reason=None, category=await get_category_object(client, ctx.guild, setting))
        await ctx.send("Unarchived")


async def unarchive_queue(client, ctx, member):
    if int(ctx.channel.category_id) == int(await get_category_object(client, ctx.guild, "archive", id_only=True)):
        await ctx.channel.edit(reason=None, category=await get_queue_category(client, member))
        await ctx.send("Unarchived")


async def get_queue_category(client, member):
    if (await get_role_object(client, member.guild, "nat")) in member.roles:
        return await get_category_object(client, member.guild, "bn_nat_queue")
    elif (await get_role_object(client, member.guild, "bn")) in member.roles:
        return await get_category_object(client, member.guild, "bn_nat_queue")
    elif (await get_role_object(client, member.guild, "experienced_mapper")) in member.roles:
        return await get_category_object(client, member.guild, "ranked_mapper_queue")
    elif (await get_role_object(client, member.guild, "ranked_mapper")) in member.roles:
        return await get_category_object(client, member.guild, "ranked_mapper_queue")
    elif (await get_role_object(client, member.guild, "mapper")) in member.roles:
        return await get_category_object(client, member.guild, "mapper_queue")
    else:
        return None
