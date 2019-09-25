from modules import db
from cogs.Docs import queuemanagement
from modules import permissions
from modules import reputation
import discord
from discord.ext import commands
import asyncio

queue_owner_default_permissions = discord.PermissionOverwrite(
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

class Queue(commands.Cog, name="Queue Management Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="request_queue", brief="Request a queue", description="", pass_context=True)
    async def make_queue_channel(self, ctx, queuetype = None):
        guildqueuecategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_mapper_queue_category", str(ctx.guild.id)]])
        if guildqueuecategory:
            if not db.query(["SELECT user_id FROM queues WHERE user_id = ? AND guild_id = ?", [str(ctx.message.author.id), str(ctx.guild.id)]]):
                try:
                    await ctx.send("sure, gimme a moment")
                    if not queuetype:
                        queuetype = "std"
                    guild = ctx.message.guild
                    channeloverwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        ctx.message.author: queue_owner_default_permissions,
                        guild.me: discord.PermissionOverwrite(
                            manage_channels=True,
                            manage_roles=True,
                            read_messages=True,
                            send_messages=True,
                            embed_links=True
                        )
                    }
                    discordfriendlychannelname = "%s-%s-queue" % (
                        ctx.message.author.display_name.replace(" ", "_").lower(), queuetype)
                    category = await reputation.validate_reputation_queues(self.bot, ctx.message.author)
                    channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                    db.query(["INSERT INTO queues VALUES (?, ?, ?)", [str(channel.id), str(ctx.message.author.id), str(ctx.guild.id)]])
                    await channel.send("%s done!" % (ctx.message.author.mention), embed=await queuemanagement())
                except Exception as e:
                    await ctx.send(e)
            else:
                await ctx.send("you already have a queue though. or it was deleted when i was offline, in this case, ping kyuunex")
        else:
            await ctx.send("Not enabled in this server yet.")

    @commands.command(name="open", brief="Open the queue", description="", pass_context=True)
    async def openq(self, ctx):
        if (db.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            if db.query(["SELECT user_id FROM queues WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=True)
                await reputation.unarchive_queue(self.bot, ctx, ctx.message.author)
                await ctx.send("queue open!")

    @commands.command(name="close", brief="Close the queue", description="", pass_context=True)
    async def closeq(self, ctx):
        if (db.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            if db.query(["SELECT user_id FROM queues WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue closed!")

    @commands.command(name="show", brief="Show the queue", description="", pass_context=True)
    async def showq(self, ctx):
        if (db.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            if db.query(["SELECT user_id FROM queues WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue is visible to everyone, but it's still closed. use 'open command if you want people to post in it.")

    @commands.command(name="hide", brief="Hide the queue", description="", pass_context=True)
    async def hideq(self, ctx):
        if (db.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            if db.query(["SELECT user_id FROM queues WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue hidden!")

    @commands.command(name="archive", brief="Archive the queue", description="", pass_context=True)
    async def archiveq(self, ctx):
        if (db.query(["SELECT user_id FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            if db.query(["SELECT user_id FROM queues WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                guildarchivecategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_archive_category", str(ctx.guild.id)]])
                if guildarchivecategory:
                    archivecategory = self.bot.get_channel(int(guildarchivecategory[0][0]))
                    await ctx.message.channel.edit(reason=None, category=archivecategory)
                    await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=False, send_messages=False)
                    await ctx.send("queue archived!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            db.query(["DELETE FROM queues WHERE channel_id = ?",[str(deleted_channel.id)]])
            print("channel %s is deleted. maybe not a queue" % (deleted_channel.name))
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.set_permissions(target=member, overwrite=queue_owner_default_permissions)
                await queue_channel.send("the queue owner has returned. next time you open the queue, it will be unarchived.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        queue_id = db.query(["SELECT channel_id FROM queues WHERE user_id = ?", [str(member.id)]])
        if queue_id:
            queue_channel = self.bot.get_channel(int(queue_id[0][0]))
            if queue_channel:
                await queue_channel.send("the queue owner has left")
                guildarchivecategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_archive_category", str(queue_channel.guild.id)]])
                if guildarchivecategory:
                    archivecategory = self.bot.get_channel(int(guildarchivecategory[0][0]))
                    await queue_channel.edit(reason=None, category=archivecategory)
                    await queue_channel.set_permissions(queue_channel.guild.default_role, read_messages=False, send_messages=False)
                    await queue_channel.send("queue archived!")


def setup(bot):
    bot.add_cog(Queue(bot))
