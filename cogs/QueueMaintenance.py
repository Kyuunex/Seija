from modules import permissions
from modules import wrappers
import discord
from discord.ext import commands


class QueueMaintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue_owner_default_permissions = discord.PermissionOverwrite(
            create_instant_invite=True,
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
        )

    @commands.command(name="restore_queue_permissions",
                      brief="Restore queue permissions",
                      aliases=['debug_queue_force_call_on_member_join'])
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def restore_queue_permissions(self, ctx, user_id):
        """
        Manually restore queue permissions to a member who left and came back and I didn't pick up on it
        or maybe when they came back with a new Dicsord account

        user_id: Discord account ID
        """

        member = wrappers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return

        await self.on_member_join(member)
        await ctx.send("done")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            await self.bot.db.execute("DELETE FROM queues WHERE channel_id = ?", [int(deleted_channel.id)])
            await self.bot.db.commit()
            print(f"channel {deleted_channel.name} is deleted. maybe not a queue")
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.db.execute("SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                                       [int(member.id), int(member.guild.id)]) as cursor:
            queue_id = await cursor.fetchone()
        if not queue_id:
            return

        queue_channel = self.bot.get_channel(int(queue_id[0]))
        if not queue_channel:
            return

        await queue_channel.set_permissions(target=member, overwrite=self.queue_owner_default_permissions)
        await queue_channel.send("the queue (co)owner has returned, so i have restored permissions.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # TODO: i don't trust this.

        async with self.bot.db.execute("SELECT channel_id FROM queues "
                                       "WHERE user_id = ? AND guild_id = ? AND is_creator = ?",
                                       [int(member.id), int(member.guild.id), 1]) as cursor:
            queue_id = await cursor.fetchone()
        if not queue_id:
            return

        queue_channel = self.bot.get_channel(int(queue_id[0]))
        if not queue_channel:
            return

        await queue_channel.send("the queue creator has left")

        async with self.bot.db.execute("SELECT user_id FROM queues "
                                       "WHERE channel_id = ? AND guild_id = ? AND is_creator = ?",
                                       [int(queue_channel.id), int(member.guild.id), 0]) as cursor:
            queue_co_owners = await cursor.fetchall()
        if queue_co_owners:
            new_creator = await self.choose_a_new_queue_creator(member.guild, queue_co_owners)
            if new_creator:
                await self.bot.db.execute("UPDATE queues SET is_creator = ? WHERE channel_id = ? AND user_id = ?",
                                          [1, int(queue_channel.id), int(new_creator.id)])
                await self.bot.db.execute("UPDATE queues SET is_creator = ? WHERE channel_id = ? AND user_id = ?",
                                          [0, int(queue_channel.id), int(member.id)])
                await queue_channel.send(f"i have chosen {new_creator.mention} as the queue creator")
            return

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["queue_archive", int(queue_channel.guild.id)]) as cursor:
            guild_archive_category_id = await cursor.fetchone()
        if not guild_archive_category_id:
            return

        archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))

        if queue_channel.category_id == archive_category.id:
            return

        await queue_channel.edit(reason=None, category=archive_category)
        await queue_channel.set_permissions(queue_channel.guild.default_role,
                                            read_messages=False,
                                            send_messages=False)

        await queue_channel.send("queue archived!")

    async def choose_a_new_queue_creator(self, guild, queue_co_owners):
        for co_owner in queue_co_owners:
            new_creator_profile = guild.get_member(int(co_owner[0]))
            if new_creator_profile:
                return new_creator_profile
        return None


def setup(bot):
    bot.add_cog(QueueMaintenance(bot))
