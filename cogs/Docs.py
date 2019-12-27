import discord
from discord.ext import commands
from modules import db


class Docs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_thumbnail = "https://i.imgur.com/JhL9PV8.png"
        self.author_icon = "https://i.imgur.com/1icHC5a.png"
        self.author_text = "Seija"
        self.footer_icon = "https://avatars0.githubusercontent.com/u/5400432"
        self.footer_text = "Made by Kyuunex"
        self.veto_channel_id_list = db.query(["SELECT channel_id FROM channels WHERE setting = ?", ["veto"]])

    @commands.command(name="docs", brief="Pretty help command", description="")
    async def docs(self, ctx, sub_help=None):
        if sub_help == "veto":
            if (str(ctx.channel.id),) in self.veto_channel_id_list:
                await ctx.send(embed=await self.veto())
        elif sub_help == "mapset_channel":
            await ctx.send(embed=await self.mapset_channel())
        elif sub_help == "queue":
            await ctx.send(embed=await self.queue(ctx.author))
        elif sub_help == "mapset_channel_management":
            await ctx.send(embed=await self.mapset_channel_management())
        elif sub_help == "queue_management":
            await ctx.send(embed=await self.queue_management())
        else:
            await ctx.send(embed=await self.main(ctx))

    async def main(self, ctx):
        embed = discord.Embed(title="Seija teaches you how to be a bot master.",
                              description="Any abuse will be dealt with punishment.", color=0xbd3661)
        embed.add_field(name="'docs mapset_channel", value="Show a help menu for requesting a mapset channel.",
                        inline=True)
        embed.add_field(name="'docs queue", value="Show a help menu for requesting a queue channel.",
                        inline=True)
        embed.add_field(name="'docs mapset_channel_management", value="Show mapset channel management commands.",
                        inline=True)
        embed.add_field(name="'docs queue_management", value="Show queue channel management commands.",
                        inline=True)
        if (str(ctx.channel.id),) in self.veto_channel_id_list:
            embed.add_field(name="'docs veto", value="Commands for tracking a mapset in veto mode.", inline=True)
        embed.add_field(name="'from (country_name)",
                        value="Retrieve a list of server members who are from the specified country. "
                              "Takes Alpha-2, Alpha-3 codes and full country names.",
                        inline=True)
        embed.add_field(name="'ts (mod)", value="Send a clickable timestamp for the osu! editor. The message must start with a timestamp.",
                        inline=True)
        embed.set_thumbnail(url=self.help_thumbnail)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed

    async def veto(self):
        embed = discord.Embed(title="~~BNS PLS MUTUAL ME~~", description="**Veto tracking commands:**",
                              color=0xbd3661)
        embed.add_field(name="'veto <mapset_id>", value="Track a mapset in this channel in veto mode.", inline=True)
        embed.add_field(name="'unveto <mapset_id>", value="Untrack a mapset in this channel in veto mode.", inline=True)
        embed.set_thumbnail(url=self.help_thumbnail)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed

    async def queue(self, author):
        channel_friendly_author = author.display_name.replace(" ", "_").lower()
        text = "**__Queue creation command:__**"
        text += "\n`'request_queue (queue type)` - Create a modding queue. By default, the queue will be closed."
        text += "\n`(queue type)` is an optional argument that specifies " \
                "what goes between your username and the word `queue` in the title of the channel. " \
                "If no argument is supplied, `std` will be filled automatically. Please follow our naming standards."
        text += "\n"
        text += "\n**__Examples:__**"
        text += f"\n`'request_queue` - This example will create `#{channel_friendly_author}-std-queue`"
        text += f"\n`'request_queue mania` - This example will create `#{channel_friendly_author}-mania-queue`"
        text += f"\n`'request_queue taiko-bn` - This example will create `#{channel_friendly_author}-taiko-bn-queue`"
        text += "\n"
        text += "\nFor queue management commands, type `'docs queue_management`"
        text += "\n"
        text += "\n**Remember:**"
        text += "\n**__Do not__ create a queue __only__ for GD requests.**"
        text += "\n**__It should__ be a modding queue, not a diary and not an image dump. " \
                "You can be creative and do other things but its primary purpose must be a modding queue.**"
        embed = discord.Embed(title="With this command you can create a queue channel.", description=text,
                              color=0xbd3661)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed

    async def mapset_channel(self):
        text = "**__Mapset channel creation command:__**: "
        text += "\n`'request_mapset_channel (mapset id) (song name)` - This is the general command to create a mapset channel."
        text += "\n`(song name)` is an optional argument that is not required. "
        text += "\nIf the mapset is not uploaded yet, `(mapset id)` can be set to `0` " \
                "but in that case, the `(song name)` argument is required."
        text += "\n"
        text += "\n**__Examples:__**"
        text += "\n`'request_mapset_channel 817793` - An example usage with mapset ID."
        text += "\n`'request_mapset_channel 0 Futanari Nari ni` - An example usage with just the song title."
        text += "\n"
        text += "\nFor mapset channel management commands, type `'docs mapset_channel_management`"
        text += "\n"
        text += "\n**Remember:**"
        text += "\n**__Do not__ create a mapset channel for single person sets. **"
        text += "\n**__Do not__ create a channel if you don't have GDers/collaborators ready.**"
        embed = discord.Embed(title="With this command you can create a mapset channel for collaborative purposes.",
                              description=text, color=0xbd3661)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed

    async def queue_management(self):
        embed = discord.Embed(title="Queue management commands",
                              description="**Please avoid manually editing channel permissions "
                                          "unless you want to ban a specific person or a role from your queue "
                                          "or the bot is down.**",
                              color=0xbd3661)
        embed.add_field(name="'open", value="Open the queue, everyone can see it and post in it.", inline=False)
        embed.add_field(name="'close",
                        value="Close the queue, everyone can see it but can't post in it. "
                              "You can also use this command to unhide the queue, "
                              "but again, nobody will be able to post in it.",
                        inline=False)
        embed.add_field(name="'hide",
                        value="Hide the queue, only admins can see the queue. Nobody else can see it and post in it.",
                        inline=False)
        embed.add_field(name="'archive",
                        value="Move the queue to the archive category, "
                              "only admins can see the queue. "
                              "Nobody else can see it and post in it.",
                        inline=False)
        embed.add_field(name="'recategorize",
                        value="Move the queue to the correct category "
                              "if you became a BN or have gotten enough kudosu to earn a spot in a higher category. "
                              "For now command only works if you became/left BN/NAT, will add kudosu checks when I can.",
                        inline=False)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed

    async def mapset_channel_management(self):
        embed = discord.Embed(title="Mapset channel management commands",
                              description="`(user)` can either be the name of the user or a discord account user ID. "
                                          "To get the user ID, you need to enable the developer mode in your discord settings, "
                                          "right click on the user and click \"Copy ID\". "
                                          "Using IDs is recommended rather than names.",
                              color=0xbd3661)
        embed.add_field(name="'add (user)", value="Add a user to the mapset channel.", inline=False)
        embed.add_field(name="'remove (user)", value="Remove a user from the mapset channel.", inline=False)
        embed.add_field(name="'abandon",
                        value="If you're abandoning the set, whether temporarily or permanently, "
                              "this will stop all tracking and move the channel to the archive category.",
                        inline=False)
        embed.add_field(name="'set_id (mapset_id)",
                        value="Set a mapset ID for this channel. "
                              "This is useful if you created this channel without setting an ID.",
                        inline=False)
        embed.add_field(name="'set_owner (user_id)",
                        value="Transfer the mapset ownership to another discord account. "
                              "user_id can only be that discord account's ID.",
                        inline=False)
        embed.add_field(name="'track (tracking_mode)",
                        value="Track the mapset in this channel. "
                              "For (tracking_mode), specify `timeline` for the discussion/timeline type "
                              "or `notification` for the notification type.",
                        inline=False)
        embed.add_field(name="'untrack", value="Untrack everything in this channel.", inline=False)
        embed.set_author(name=self.author_text, icon_url=self.author_icon)
        embed.set_footer(text=self.footer_text, icon_url=self.footer_icon)
        return embed


def setup(bot):
    bot.add_cog(Docs(bot))
