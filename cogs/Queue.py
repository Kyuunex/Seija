from modules import db
from cogs.Docs import Docs
from modules import permissions
import discord
from discord.ext import commands


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.docs = Docs(bot)
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
        self.queue_bot_default_permissions = discord.PermissionOverwrite(
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True
        )

    @commands.command(name="request_queue", brief="Request a queue", description="")
    @commands.guild_only()
    async def make_queue_channel(self, ctx, queue_type=None):
        guild_queue_category = db.query(["SELECT category_id FROM categories "
                                         "WHERE setting = ? AND guild_id = ?",
                                         ["mapper_queue", str(ctx.guild.id)]])
        if guild_queue_category:
            member_already_has_a_queue = db.query(["SELECT channel_id FROM queues "
                                                   "WHERE user_id = ? AND guild_id = ?",
                                                   [str(ctx.author.id), str(ctx.guild.id)]])
            if member_already_has_a_queue:
                already_existing_queue = self.bot.get_channel(int(member_already_has_a_queue[0][0]))
                if already_existing_queue:
                    await ctx.send(f"you already have one <#{already_existing_queue.id}>")
                    return
                else:
                    db.query(["DELETE FROM queues WHERE channel_id = ?", [str(member_already_has_a_queue[0][0])]])

            try:
                await ctx.send("sure, gimme a moment")
                if not queue_type:
                    queue_type = "std"
                guild = ctx.guild
                channel_overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: self.queue_owner_default_permissions,
                    guild.me: self.queue_bot_default_permissions
                }
                underscored_name = ctx.author.display_name.replace(" ", "_").lower()
                channel_name = f"{underscored_name}-{queue_type}-queue"
                category = await self.get_queue_category(ctx.author)
                channel = await guild.create_text_channel(channel_name,
                                                          overwrites=channel_overwrites, category=category)
                db.query(["INSERT INTO queues VALUES (?, ?, ?)",
                          [str(channel.id), str(ctx.author.id), str(ctx.guild.id)]])
                await channel.send(f"{ctx.author.mention} done!", embed=await self.docs.queue_management())
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("Not enabled in this server yet.")

    @commands.command(name="open", brief="Open the queue", description="")
    @commands.guild_only()
    async def open(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=True)
            await self.unarchive_queue(ctx, ctx.author)
            await ctx.send("queue open!")

    @commands.command(name="close", brief="Close the queue", description="")
    @commands.guild_only()
    async def close(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send("queue closed!")

    @commands.command(name="show", brief="Show the queue", description="")
    @commands.guild_only()
    async def show(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send("queue is visible to everyone, but it's still closed. "
                           "use `'open` command if you want people to post in it.")

    @commands.command(name="hide", brief="Hide the queue", description="")
    @commands.guild_only()
    async def hide(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
            await ctx.send("queue hidden!")

    @commands.command(name="recategorize", brief="Recategorize the queue", description="")
    @commands.guild_only()
    async def recategorize(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if queue_owner_check and is_queue_channel:
            await ctx.channel.edit(reason=None, category=await self.get_queue_category(ctx.author))

    @commands.command(name="archive", brief="Archive the queue", description="")
    @commands.guild_only()
    async def archive(self, ctx):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            guild_archive_category_id = db.query(["SELECT category_id FROM categories "
                                                  "WHERE setting = ? AND guild_id = ?",
                                                  ["queue_archive", str(ctx.guild.id)]])
            if guild_archive_category_id:
                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await ctx.channel.edit(reason=None, category=archive_category)
                await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue archived!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            db.query(["DELETE FROM queues WHERE channel_id = ?", [str(deleted_channel.id)]])
            print(f"channel {deleted_channel.name} is deleted. maybe not a queue")
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.set_permissions(target=member, overwrite=self.queue_owner_default_permissions)
                await queue_channel.send("the queue owner has returned. "
                                         "next time you open the queue, it will be unarchived.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.send("the queue owner has left")
                guild_archive_category_id = db.query(["SELECT category_id FROM categories "
                                                      "WHERE setting = ? AND guild_id = ?",
                                                      ["queue_archive", str(queue_channel.guild.id)]])
                if guild_archive_category_id:
                    archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                    await queue_channel.edit(reason=None, category=archive_category)
                    await queue_channel.set_permissions(queue_channel.guild.default_role,
                                                        read_messages=False,
                                                        send_messages=False)
                    await queue_channel.send("queue archived!")

    async def get_category_object(self, guild, setting, id_only=None):
        category_id = db.query(["SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                [setting, str(guild.id)]])
        if category_id:
            category = self.bot.get_channel(int(category_id[0][0]))
            if id_only:
                return category.id
            else:
                return category
        else:
            return False

    async def get_role_object(self, guild, setting, id_only=None):
        role_id = db.query(["SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?", [setting, str(guild.id)]])
        if role_id:
            role = discord.utils.get(guild.roles, id=int(role_id[0][0]))
            if id_only:
                return role.id
            else:
                return role
        else:
            return False

    async def unarchive_queue(self, ctx, member):
        if int(ctx.channel.category_id) == int(await self.get_category_object(ctx.guild, "queue_archive", id_only=True)):
            await ctx.channel.edit(reason=None, category=await self.get_queue_category(member))
            await ctx.send("Unarchived")

    async def get_queue_category(self, member):
        if (await self.get_role_object(member.guild, "nat")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")
        elif (await self.get_role_object(member.guild, "bn")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")
        elif (await self.get_role_object(member.guild, "experienced_mapper")) in member.roles:
            return await self.get_category_object(member.guild, "ranked_mapper_queue")
        elif (await self.get_role_object(member.guild, "ranked_mapper")) in member.roles:
            return await self.get_category_object(member.guild, "ranked_mapper_queue")
        elif (await self.get_role_object(member.guild, "mapper")) in member.roles:
            return await self.get_category_object(member.guild, "mapper_queue")
        else:
            return None


def setup(bot):
    bot.add_cog(Queue(bot))
