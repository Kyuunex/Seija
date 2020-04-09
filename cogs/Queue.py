from cogs.Docs import Docs
from modules import permissions
from modules import wrappers
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

    async def can_manage_queue(self, ctx):
        if await permissions.is_admin(ctx):
            return True
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    async def channel_is_a_queue(self, ctx):
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE channel_id = ?",
                                       [str(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    async def get_queue_owner(self, ctx):
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE channel_id = ?",
                                       [str(ctx.channel.id)]) as cursor:
            queue_owner_metadata = await cursor.fetchone()
            return ctx.guild.get_member(int(queue_owner_metadata[0]))

    @commands.command(name="queue_cleanup", brief="Queue cleanup")
    @commands.guild_only()
    async def queue_cleanup(self, ctx, amount=100):
        """
        Deletes messages that are not made by the queue owner or me or has no beatmap link.
        """

        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        queue_owner = await self.get_queue_owner(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        try:
            await ctx.message.delete()
            async with ctx.channel.typing():
                def the_check(m):
                    if "https://osu.ppy.sh/beatmapsets/" in m.content:
                        return False
                    if m.author == queue_owner:
                        return False
                    if m.author == ctx.guild.me:
                        return False
                    return True

                deleted = await ctx.channel.purge(limit=int(amount), check=the_check)
            await ctx.send(f"Deleted {len(deleted)} message(s)")
        except Exception as e:
            await ctx.send(str(e).replace("@", ""))

    @commands.command(name="debug_get_kudosu")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def debug_get_kudosu(self, ctx, user_id, osu_id="0"):
        if user_id:
            async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]) as cursor:
                osu_id = await cursor.fetchall()
            if osu_id:
                osu_id = osu_id[0][0]
        if osu_id:
            await ctx.send(await self.get_kudosu_int(osu_id))

    @commands.command(name="debug_queue_force_call_on_member_join")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def debug_queue_force_call_on_member_join(self, ctx, user_id):
        member = wrappers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return None

        await self.on_member_join(member)
        await ctx.send("done")

    @commands.command(name="request_queue", brief="Request a queue", aliases=["create_queue", "make_queue"])
    @commands.guild_only()
    async def make_queue_channel(self, ctx, *, queue_type="std"):
        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["beginner_queue", str(ctx.guild.id)]) as cursor:
            is_enabled_in_server = await cursor.fetchone()
        if not is_enabled_in_server:
            await ctx.send("Not enabled in this server yet.")
            return None

        async with self.bot.db.execute("SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                                       [str(ctx.author.id), str(ctx.guild.id)]) as cursor:
            member_already_has_a_queue = await cursor.fetchone()
        if member_already_has_a_queue:
            already_existing_queue = self.bot.get_channel(int(member_already_has_a_queue[0]))
            if already_existing_queue:
                await ctx.send(f"you already have one <#{already_existing_queue.id}>")
                return None
            else:
                await self.bot.db.execute("DELETE FROM queues WHERE channel_id = ?",
                                          [str(member_already_has_a_queue[0])])
                await self.bot.db.commit()

        try:
            await ctx.send("sure, gimme a moment")
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
            await self.bot.db.execute("INSERT INTO queues VALUES (?, ?, ?, ?)",
                                      [str(channel.id), str(ctx.author.id), str(ctx.guild.id), "1"])
            await self.bot.db.commit()
            await channel.send(f"{ctx.author.mention} done!", embed=await self.docs.queue_management())
        except Exception as e:
            await ctx.send(e)

    async def generate_queue_event_embed(self, ctx, args):
        if len(args) == 0:
            return None
        elif len(args) == 2:
            embed_title = args[0]
            embed_description = args[1]
        else:
            embed_title = "message"
            embed_description = " ".join(args)
        embed = discord.Embed(title=embed_title, description=embed_description, color=0xbd3661)
        embed.set_author(name=ctx.author.display_name,
                         icon_url=ctx.author.avatar_url_as(static_format="jpg", size=128))
        await ctx.message.delete()
        return embed

    @commands.command(name="open", brief="Open the queue", description="")
    @commands.guild_only()
    async def open(self, ctx, *args):
        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        queue_owner = await self.get_queue_owner(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        embed = await self.generate_queue_event_embed(ctx, args)

        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=True)
        await self.unarchive_queue(ctx, queue_owner)
        await ctx.send(content="queue open!", embed=embed)

    @commands.command(name="close", brief="Close the queue", aliases=["closed", "show"])
    @commands.guild_only()
    async def close(self, ctx, *args):
        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        queue_owner = await self.get_queue_owner(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        embed = await self.generate_queue_event_embed(ctx, args)

        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
        await self.unarchive_queue(ctx, queue_owner)
        await ctx.send(content="queue is now closed but visible!", embed=embed)

    @commands.command(name="hide", brief="Hide the queue", description="")
    @commands.guild_only()
    async def hide(self, ctx, *args):
        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        embed = await self.generate_queue_event_embed(ctx, args)

        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
        await ctx.send(content="queue hidden!", embed=embed)

    @commands.command(name="recategorize", brief="Recategorize the queue", description="")
    @commands.guild_only()
    async def recategorize(self, ctx):
        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        queue_owner = await self.get_queue_owner(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        old_category = self.bot.get_channel(ctx.channel.category_id)
        new_category = await self.get_queue_category(queue_owner)
        if old_category == new_category:
            await ctx.send(content="queue is already in the category it belongs in!")
            return None

        await ctx.channel.edit(reason=None, category=new_category)
        await ctx.send(content="queue recategorized!")

    @commands.command(name="archive", brief="Archive the queue", description="")
    @commands.guild_only()
    async def archive(self, ctx):
        if not await self.can_manage_queue(ctx):
            return None

        if not await self.channel_is_a_queue(ctx):
            return None

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["queue_archive", str(ctx.guild.id)]) as cursor:
            guild_archive_category_id = await cursor.fetchone()
        if not guild_archive_category_id:
            await ctx.send("can't unarchive, guild archive category is not set anywhere")
            return None

        archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))
        if not archive_category:
            await ctx.send("something's wrong. i can't find the guild archive category")
            return None

        if ctx.channel.category_id == archive_category.id:
            await ctx.send("queue is already archived!")
            return None

        await ctx.channel.edit(reason=None, category=archive_category)
        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
        await ctx.send("queue archived!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            await self.bot.db.execute("DELETE FROM queues WHERE channel_id = ?", [str(deleted_channel.id)])
            await self.bot.db.commit()
            print(f"channel {deleted_channel.name} is deleted. maybe not a queue")
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.db.execute("SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                                       [str(member.id), str(member.guild.id)]) as cursor:
            queue_id = await cursor.fetchone()
        if not queue_id:
            return None

        queue_channel = self.bot.get_channel(int(queue_id[0]))
        if not queue_channel:
            return None

        await queue_channel.set_permissions(target=member, overwrite=self.queue_owner_default_permissions)
        await queue_channel.send("the queue owner has returned, so i have restored permissions. "
                                 "next time this queue is open, it will be unarchived.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with self.bot.db.execute("SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                                       [str(member.id), str(member.guild.id)]) as cursor:
            queue_id = await cursor.fetchone()
        if not queue_id:
            return None

        queue_channel = self.bot.get_channel(int(queue_id[0]))
        if not queue_channel:
            return None

        await queue_channel.send("the queue owner has left")

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["queue_archive", str(queue_channel.guild.id)]) as cursor:
            guild_archive_category_id = await cursor.fetchone()
        if not guild_archive_category_id:
            return None

        archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))

        if queue_channel.category_id == archive_category.id:
            return None

        await queue_channel.edit(reason=None, category=archive_category)
        await queue_channel.set_permissions(queue_channel.guild.default_role,
                                            read_messages=False,
                                            send_messages=False)

        await queue_channel.send("queue archived!")

    async def get_category_id(self, guild, setting):
        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       [setting, str(guild.id)]) as cursor:
            category_id = await cursor.fetchone()
        if not category_id:
            return None

        return int(category_id[0])

    async def get_category_object(self, guild, setting):
        category_id = await self.get_category_id(guild, setting)
        if not category_id:
            return None

        category = self.bot.get_channel(category_id)
        return category

    async def get_role_object(self, guild, setting):
        async with self.bot.db.execute("SELECT role_id FROM roles WHERE setting = ? AND guild_id = ?",
                                       [setting, str(guild.id)]) as cursor:
            role_id = await cursor.fetchone()
        if not role_id:
            return None

        role = discord.utils.get(guild.roles, id=int(role_id[0]))
        return role

    async def unarchive_queue(self, ctx, member):
        category_id = await self.get_category_id(ctx.guild, "queue_archive")
        if int(ctx.channel.category_id) == int(category_id):
            print("im here")
            await ctx.channel.edit(reason=None, category=await self.get_queue_category(member))
            await ctx.send("Unarchived")

    async def get_queue_category(self, member):
        if (await self.get_role_object(member.guild, "nat")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")
        elif (await self.get_role_object(member.guild, "bn")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]) as cursor:
            osu_id = await cursor.fetchone()
        if osu_id:
            kudosu = await self.get_kudosu_int(osu_id[0])
        else:
            kudosu = 0

        if kudosu <= 199:
            return await self.get_category_object(member.guild, "beginner_queue")
        elif 200 <= kudosu <= 499:
            return await self.get_category_object(member.guild, "intermediate_queue")
        elif 500 <= kudosu <= 999:
            return await self.get_category_object(member.guild, "advanced_queue")
        elif kudosu >= 1000:
            return await self.get_category_object(member.guild, "experienced_queue")

        return await self.get_category_object(member.guild, "beginner_queue")

    async def get_kudosu_int(self, osu_id):
        try:
            user = await self.bot.osuweb.get_user(str(osu_id))
            return user["kudosu"]["total"]
        except:
            return 0


def setup(bot):
    bot.add_cog(Queue(bot))
