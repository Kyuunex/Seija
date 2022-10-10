import discord


async def get_role_based_on_reputation(self, guild, ranked_amount):
    if ranked_amount >= 10:
        return await get_role_from_db(self, "experienced_mapper", guild)
    elif ranked_amount >= 1:
        return await get_role_from_db(self, "ranked_mapper", guild)
    else:
        return await get_role_from_db(self, "mapper", guild)


async def get_role_from_db(self, setting, guild):
    async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                   [setting, int(guild.id)]) as cursor:
        role_id = await cursor.fetchone()
    return guild.get_role(int(role_id[0]))
