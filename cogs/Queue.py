from modules import db
from cogs.Docs import Docs
from modules import permissions
import discord
from discord.ext import commands

from modules.connections import osuweb as osuweb

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

    @commands.command(name="debug_get_kudosu")
    @commands.check(permissions.is_admin)
    @commands.guild_only()
    async def debug_get_kudosu(self, ctx, user_id, osu_id="0"):
        if user_id:
            osu_id = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(user_id)]])
            if osu_id:
                osu_id = osu_id[0][0]
        if osu_id:
            await ctx.send(await self.get_kudosu_int(osu_id))

    @commands.command(name="request_queue", brief="Request a queue", description="")
    @commands.guild_only()
    async def make_queue_channel(self, ctx, *, queue_type="std"):
        if not db.query(["SELECT category_id FROM categories "
                         "WHERE setting = ? AND guild_id = ?",
                         ["beginner_queue", str(ctx.guild.id)]]):
            await ctx.send("Not enabled in this server yet.")
            return None

        member_already_has_a_queue = db.query(["SELECT channel_id FROM queues "
                                               "WHERE user_id = ? AND guild_id = ?",
                                               [str(ctx.author.id), str(ctx.guild.id)]])
        if member_already_has_a_queue:
            already_existing_queue = self.bot.get_channel(int(member_already_has_a_queue[0][0]))
            if already_existing_queue:
                await ctx.send(f"you already have one <#{already_existing_queue.id}>")
                return None
            else:
                db.query(["DELETE FROM queues WHERE channel_id = ?", [str(member_already_has_a_queue[0][0])]])

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
            db.query(["INSERT INTO queues VALUES (?, ?, ?)",
                      [str(channel.id), str(ctx.author.id), str(ctx.guild.id)]])
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
        # TODO: fix if a manager opens a queue of someone, use that someone's kds
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            embed = await self.generate_queue_event_embed(ctx, args)

            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=True)
            await self.unarchive_queue(ctx, ctx.author)
            await ctx.send(content="queue open!", embed=embed)

    @commands.command(name="close", brief="Close the queue", description="")
    @commands.guild_only()
    async def close(self, ctx, *args):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            embed = await self.generate_queue_event_embed(ctx, args)

            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send(content="queue closed!", embed=embed)

    @commands.command(name="show", brief="Show the queue", description="")
    @commands.guild_only()
    async def show(self, ctx, *args):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            embed = await self.generate_queue_event_embed(ctx, args)

            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=None, send_messages=False)
            await ctx.send(content="queue is visible to everyone, but it's still closed. "
                           "use `'open` command if you want people to post in it.", embed=embed)

    @commands.command(name="hide", brief="Hide the queue", description="")
    @commands.guild_only()
    async def hide(self, ctx, *args):
        queue_owner_check = db.query(["SELECT user_id FROM queues "
                                      "WHERE user_id = ? AND channel_id = ?",
                                      [str(ctx.author.id), str(ctx.channel.id)]])
        is_queue_channel = db.query(["SELECT user_id FROM queues "
                                     "WHERE channel_id = ?",
                                     [str(ctx.channel.id)]])
        if (queue_owner_check or await permissions.is_admin(ctx)) and is_queue_channel:
            embed = await self.generate_queue_event_embed(ctx, args)

            await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
            await ctx.send(content="queue hidden!", embed=embed)

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
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                             [str(member.id), str(member.guild.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.set_permissions(target=member, overwrite=self.queue_owner_default_permissions)
                await queue_channel.send("the queue owner has returned. "
                                         "next time you open the queue, it will be unarchived.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ? AND guild_id = ?",
                             [str(member.id), str(member.guild.id)]])
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
        if int(ctx.channel.category_id) == int(
                await self.get_category_object(ctx.guild, "queue_archive", id_only=True)):
            await ctx.channel.edit(reason=None, category=await self.get_queue_category(member))
            await ctx.send("Unarchived")

    async def get_queue_category(self, member):
        if (await self.get_role_object(member.guild, "nat")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")
        elif (await self.get_role_object(member.guild, "bn")) in member.roles:
            return await self.get_category_object(member.guild, "bn_nat_queue")

        osu_id = db.query(["SELECT osu_id FROM users WHERE user_id = ?", [str(member.id)]])
        if osu_id:
            kudosu = await self.get_kudosu_int(osu_id[0][0])
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
            user = await osuweb.get_user(str(osu_id))
            return user["kudosu"]["total"]
        except:
            return 0


def setup(bot):
    bot.add_cog(Queue(bot))
