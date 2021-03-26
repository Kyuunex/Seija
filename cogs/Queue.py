from cogs.Docs import Docs
from modules import permissions
from reusables import exceptions
from reusables import send_large_message
from reusables import get_member_helpers
import discord
from discord.ext import commands


class Queue(commands.Cog):
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
        self.queue_bot_default_permissions = discord.PermissionOverwrite(
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True
        )

    async def is_queue_creator(self, ctx):
        if await permissions.is_admin(ctx):
            return True
        async with self.bot.db.execute("SELECT user_id FROM queues "
                                       "WHERE user_id = ? AND channel_id = ? AND is_creator = ?",
                                       [int(ctx.author.id), int(ctx.channel.id), 1]) as cursor:
            return bool(await cursor.fetchone())

    async def can_manage_queue(self, ctx):
        if await permissions.is_admin(ctx):
            return True
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    async def channel_is_a_queue(self, ctx):
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            return bool(await cursor.fetchone())

    async def get_queue_creator(self, ctx):
        async with self.bot.db.execute("SELECT user_id FROM queues WHERE channel_id = ? AND is_creator = ?",
                                       [int(ctx.channel.id), 1]) as cursor:
            queue_creator_id = await cursor.fetchone()
        return ctx.guild.get_member(int(queue_creator_id[0]))

    @commands.command(name="queue_cleanup", brief="Purges messages that are offtopic for a modding queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def queue_cleanup(self, ctx, amount=100):
        """
        Cycles through [amount] of messages and deletes any that:
        1. is not made by me
        2. has no beatmap link
        3. not made by the queue owner
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        queue_owner = await self.get_queue_creator(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        try:
            await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} I don't seem to have permissions to purge this queue",
                           embed=await exceptions.embed_exception(e))
            return

        async with ctx.channel.typing():
            def is_message_offtopic(message):
                if "https://osu.ppy.sh/beatmapsets/" in message.content:
                    return False
                if message.author == queue_owner:
                    return False
                if message.author == ctx.guild.me:
                    return False
                return True

            try:
                deleted = await ctx.channel.purge(limit=int(amount), check=is_message_offtopic)
            except Exception as e:
                await ctx.send(f"{ctx.author.mention} something went wrong while attempting to purge messages", 
                               embed=await exceptions.embed_exception(e))
                return

        await ctx.send(f"Deleted {len(deleted)} message(s)")

    @commands.command(name="debug_get_kudosu", brief="Print how much kudosu a user has")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def debug_get_kudosu(self, ctx, user_id, osu_id):
        """
        Debug command for managers to print how much kudosu a member has.

        user_id: Discord account ID
        osu_id: osu! account ID
        """

        # TODO: maybe use argparser here

        if user_id:
            async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [int(user_id)]) as cursor:
                osu_id_db = await cursor.fetchone()
            if osu_id:
                osu_id = osu_id_db[0]

        if osu_id:
            await ctx.send(await self.get_kudosu_int(osu_id))

    @commands.command(name="request_queue", brief="Request a queue", aliases=["create_queue", "make_queue"])
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def make_queue_channel(self, ctx, *, queue_type="std"):
        """
        This command creates a queue style channel for the person executing the command

        queue_type: This specifies the type of the queue, for example std, mania, or whatever you want
        """

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["beginner_queue", int(ctx.guild.id)]) as cursor:
            is_enabled_in_server = await cursor.fetchone()
        if not is_enabled_in_server:
            await ctx.send("Not enabled in this server yet.")
            return

        await ctx.send("sure, gimme a moment")

        async with self.bot.db.execute("SELECT channel_id FROM queues "
                                       "WHERE user_id = ? AND guild_id = ? AND is_creator = ?",
                                       [int(ctx.author.id), int(ctx.guild.id), 1]) as cursor:
            member_already_has_a_queue = await cursor.fetchone()
        if member_already_has_a_queue:
            already_existing_queue = self.bot.get_channel(int(member_already_has_a_queue[0]))
            if already_existing_queue:
                await ctx.send(f"{ctx.author.mention} you already have one <#{already_existing_queue.id}>")
                return
            else:
                await ctx.send(f"{ctx.author.mention} it seems you already had a queue "
                               f"but it was deleted without me noticing. "
                               f"oh well, new one it is then")
                await self.bot.db.execute("DELETE FROM queues WHERE channel_id = ?",
                                          [int(member_already_has_a_queue[0])])
                await self.bot.db.commit()

        guild = ctx.guild

        channel_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.message.author: self.queue_owner_default_permissions,
            guild.me: self.queue_bot_default_permissions
        }

        underscored_name = ctx.author.display_name.replace(" ", "_").lower()
        channel_name = f"{underscored_name}-{queue_type}-queue"

        category = await self.get_queue_category(ctx.author)
        try:
            channel = await guild.create_text_channel(channel_name,
                                                      overwrites=channel_overwrites, category=category)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} i am unable to create the channel, idk why, maybe no perms. "
                           f"managers will have to look into this", embed=await exceptions.embed_exception(e))
            return

        await self.bot.db.execute("INSERT INTO queues VALUES (?, ?, ?, ?)",
                                  [int(channel.id), int(ctx.author.id), int(ctx.guild.id), 1])
        await self.bot.db.commit()

        await channel.send(f"{ctx.author.mention} done!", embed=await Docs.queue_management())

    @commands.command(name="add_co_modder", brief="Add a co-modder to your queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def add_co_modder(self, ctx, user_id):
        """
        Turns a modding queue into a joint one.
        This command allows you to add a co-owner to your queue.
        They will be able to open/close/hide/archive the queue.
        Using this command will not prevent them from creating their own separate queue or
        from being added to someone else's queue.
        They will not be able to remove you from the queue.
        You, being the creator of the queue, will still not be able to make a new queue,
        however you can still be a co-owner of someone else's queue.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.is_queue_creator(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        member = get_member_helpers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return

        if member.id == (await self.get_queue_creator(ctx)).id:
            await ctx.send(f"{ctx.author.mention} the member you're trying to add is the owner of this queue")
            return

        await self.bot.db.execute("INSERT INTO queues VALUES (?, ?, ?, ?)",
                                  [int(ctx.channel.id), int(member.id), int(ctx.guild.id), 0])
        await self.bot.db.commit()

        try:
            await ctx.channel.set_permissions(member, overwrite=self.queue_owner_default_permissions)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} i am unable to edit the channel permissions, "
                           f"idk why, maybe permissions error",
                           embed=await exceptions.embed_exception(e))
            return

        await ctx.send(f"{member.mention} is now the co-owner of this queue!")

    @commands.command(name="remove_co_modder", brief="Remove a co-modder from your queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def remove_co_modder(self, ctx, user_id):
        """
        This command allows you to remove a co-modder that you added to your queue

        user_id: Discord account ID
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.is_queue_creator(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        member = get_member_helpers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return

        if member.id == (await self.get_queue_creator(ctx)).id:
            await ctx.send(f"{ctx.author.mention} the member you're trying to remove is the owner of this queue")
            return

        await self.bot.db.execute("DELETE FROM queues "
                                  "WHERE channel_id = ? AND user_id = ? AND guild_id = ? AND is_creator = ?",
                                  [int(ctx.channel.id), int(member.id), int(ctx.guild.id), 0])
        await self.bot.db.commit()

        try:
            await ctx.channel.set_permissions(member, overwrite=None)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} i am unable to edit the channel permissions, "
                           f"idk why, maybe permissions error", 
                           embed=await exceptions.embed_exception(e))
            return

        await ctx.send(f"{member.mention} is no longer a co-owner of this queue!")

    @commands.command(name="get_queue_owner_list", brief="List all the owners of this queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def get_queue_owner_list(self, ctx):
        """
        Prints a list of modders who own the particular queue.
        The queue creator will have a crown icon next to them.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        async with self.bot.db.execute("SELECT user_id, is_creator FROM queues WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            queue_owner_list = await cursor.fetchall()

        if not queue_owner_list:
            await ctx.send("queue_owner_list is empty. this should not happen")
            return

        buffer = ":notepad_spiral: **Owners of this queue**\n\n"
        for one_owner in queue_owner_list:
            one_owner_profile = ctx.guild.get_member(int(one_owner[0]))
            if one_owner_profile:
                buffer += f"{one_owner_profile.display_name}"
            else:
                buffer += f"{one_owner[0]}"
            if int(one_owner[1]) == 1:
                buffer += " :crown:"
            buffer += "\n"
        embed = discord.Embed(color=0xff6781)

        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="give_queue", brief="Give your creator permissions of the queue to someone.")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def give_queue(self, ctx, user_id):
        """
        Give your creator permissions of the queue to someone.
        I had to make this clear all co-modders from the queue too because it was buggy.
        So, the new creator will have to add all co-modders back again.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.is_queue_creator(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        member = get_member_helpers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return

        await self.bot.db.execute("DELETE FROM queues WHERE channel_id = ? AND guild_id = ?",
                                  [int(ctx.channel.id), int(ctx.guild.id)])
        await self.bot.db.execute("INSERT INTO queues VALUES (?, ?, ?, ?)",
                                  [int(ctx.channel.id), int(member.id), int(ctx.guild.id), 1])
        await self.bot.db.commit()

        try:
            await ctx.channel.set_permissions(member, overwrite=self.queue_owner_default_permissions)
        except Exception as e:
            await ctx.send(f"{ctx.author.mention} i am unable to edit the channel permissions, "
                           f"idk why, maybe permissions error, although i made the change in the database already", 
                           embed=await exceptions.embed_exception(e))
            return

        await ctx.send(f"You have given the queue creator permissions to {member.mention}")

    @commands.command(name="open", brief="Open the queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def open(self, ctx, *args):
        """
        This command will "open" the queue. It will change channel permissions, so that,
        anyone who is not explicitly blacklisted from the queue, can post it in.

        args: A message you want the bot to post after opening the queue.
              If you use this, the message you call the command in in will be deleted.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        queue_owner = await self.get_queue_creator(ctx)
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
    @commands.check(permissions.is_not_ignored)
    async def close(self, ctx, *args):
        """
        This command will "close" the queue. It will change channel permissions, so that,
        anyone (who is not explicitly banned from seeing the queue) will see it but cannot send any message in it.

        args: A message you want the bot to post after closing the queue.
              If you use this, the message you call the command in in will be deleted.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        queue_owner = await self.get_queue_creator(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        embed = await self.generate_queue_event_embed(ctx, args)

        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
        await self.unarchive_queue(ctx, queue_owner)
        await ctx.send(content="queue is now closed but visible!", embed=embed)

    @commands.command(name="hide", brief="Hide the queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def hide(self, ctx, *args):
        """
        This command will "hide" the queue. It will change channel permissions, so that,
        other than server administrators, nobody can see it.

        args: A message you want the bot to post after hiding the queue.
              If you use this, the message you call the command in in will be deleted.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        embed = await self.generate_queue_event_embed(ctx, args)

        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
        await ctx.send(content="queue hidden!", embed=embed)

    @commands.command(name="recategorize", brief="Recategorize the queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def recategorize(self, ctx):
        """
        This command will recategorize the queue manually.
        This is usually needed if the queue creator obtained more kudosu and qualifies in a higher category or
        has obtained a BN/NAT role.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        queue_owner = await self.get_queue_creator(ctx)
        if not queue_owner:
            queue_owner = ctx.author
            await ctx.send("warning, unable to find the queue owner in this server. "
                           "so, i will treat the person typing the command "
                           "as the queue owner during the execution of this command.")

        old_category = self.bot.get_channel(ctx.channel.category_id)
        new_category = await self.get_queue_category(queue_owner)
        if old_category == new_category:
            await ctx.send(content="queue is already in the category it belongs in!")
            return

        await ctx.channel.edit(reason=None, category=new_category)
        await ctx.send(content="queue recategorized!")

    @commands.command(name="archive", brief="Archive the queue")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def archive(self, ctx):
        """
        This command will "archive" the queue. It will change channel permissions, so that,
        other than server administrators, nobody can see it.
        Additionally, it will move the channel to an archive category.
        """

        if not await self.channel_is_a_queue(ctx):
            await ctx.send(f"{ctx.author.mention} this channel is not a queue")
            return

        if not await self.can_manage_queue(ctx):
            await ctx.send(f"{ctx.author.mention} you are not allowed to manage this queue")
            return

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["queue_archive", int(ctx.guild.id)]) as cursor:
            guild_archive_category_id = await cursor.fetchone()
        if not guild_archive_category_id:
            await ctx.send("can't unarchive, guild archive category is not set anywhere")
            return

        archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))
        if not archive_category:
            await ctx.send("something's wrong. i can't find the guild archive category")
            return

        if ctx.channel.category_id == archive_category.id:
            await ctx.send("queue is already archived!")
            return
        try:
            await ctx.channel.edit(reason=None, category=archive_category)
            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
            await ctx.send("queue archived!")
        except Exception as e:
            await ctx.send(embed=await exceptions.embed_exception(e))

    @commands.command(name="list_open_queues", brief="List open queues", aliases=['loq'])
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def list_open_queues(self, ctx):
        queue_categories = [await self.get_category_object(ctx.guild, "bn_nat_queue"),
                            await self.get_category_object(ctx.guild, "experienced_queue"),
                            await self.get_category_object(ctx.guild, "advanced_queue"),
                            await self.get_category_object(ctx.guild, "intermediate_queue"),
                            await self.get_category_object(ctx.guild, "beginner_queue")]

        buffer = ":page_with_curl: **Open queues**\n\n"
        for queue_category in queue_categories:
            buffer += f"**{queue_category.name}:**\n"
            for text_channel in queue_category.text_channels:
                # perms = text_channel.permissions_for(ctx.author)
                role = ctx.guild.default_role
                perms = text_channel.overwrites_for(role)
                for perm in perms:
                    if perm[0] == "send_messages":
                        if perm[1]:
                            buffer += f"{text_channel.mention}\n"
            buffer += "\n"

        embed = discord.Embed(color=0xff6781)
        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    async def get_category_id(self, guild, setting):
        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       [setting, int(guild.id)]) as cursor:
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
                                       [setting, int(guild.id)]) as cursor:
            role_id = await cursor.fetchone()
        if not role_id:
            return None

        role = discord.utils.get(guild.roles, id=int(role_id[0]))
        return role

    async def unarchive_queue(self, ctx, member):
        category_id = await self.get_category_id(ctx.guild, "queue_archive")
        if int(ctx.channel.category_id) == int(category_id):
            await ctx.channel.edit(reason=None, category=await self.get_queue_category(member))
            await ctx.send("Unarchived")

    async def get_queue_category(self, member):
        if (await self.get_role_object(member.guild, "nat")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")
        elif (await self.get_role_object(member.guild, "bn")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")

        async with self.bot.db.execute("SELECT osu_id FROM users WHERE user_id = ?", [int(member.id)]) as cursor:
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
            user = await self.bot.osuweb.get_user_array(str(osu_id))
            return user["kudosu"]["total"]
        except:
            return 0

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


def setup(bot):
    bot.add_cog(Queue(bot))
