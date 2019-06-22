import discord
import asyncio

from modules import dbhandler


async def get_category_object(client, guild, setting, id_only=None):
    category_id = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", [setting, str(guild.id)]])
    if category_id:
        category = client.get_channel(int(category_id[0][0]))
        if id_only:
            return category.id
        else:
            return category
    else:
        return False

async def get_role_object(client, guild, setting, id_only=None):
    role_id = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", [setting, str(guild.id)]])
    if role_id:
        role = discord.utils.get(guild.roles, id=int(role_id[0][0]))
        if id_only:
            return role.id
        else:
            return role
    else:
        return False


async def unarchive_channel(client, ctx, setting):
    if int(ctx.channel.category_id) == int(await get_category_object(client, ctx.guild, "guild_archive_category", id_only=True)):
        await ctx.message.channel.edit(reason=None, category=await get_category_object(client, ctx.guild, setting))
        await ctx.send("Unarchived")


async def unarchive_queue(client, ctx, member):
    if int(ctx.channel.category_id) == int(await get_category_object(client, ctx.guild, "guild_archive_category", id_only=True)):
        await ctx.message.channel.edit(reason=None, category=await validate_reputation_queues(client, member))
        await ctx.send("Unarchived")


async def validate_reputation_queues(client, member):
    if (await get_role_object(client, member.guild, "guild_nat_role")) in member.roles:
        return (await get_category_object(client, member.guild, "guild_bn_nat_queue_category"))
    elif (await get_role_object(client, member.guild, "guild_bn_role")) in member.roles:
        return (await get_category_object(client, member.guild, "guild_bn_nat_queue_category"))
    elif (await get_role_object(client, member.guild, "guild_experienced_mapper_role")) in member.roles:
        return (await get_category_object(client, member.guild, "guild_ranked_queue_category"))
    elif (await get_role_object(client, member.guild, "guild_ranked_mapper_role")) in member.roles:
        return (await get_category_object(client, member.guild, "guild_ranked_queue_category"))
    elif (await get_role_object(client, member.guild, "guild_verify_role")) in member.roles:
        return (await get_category_object(client, member.guild, "guild_queue_category"))
    else:
        return None