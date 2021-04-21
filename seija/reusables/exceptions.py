import discord
from discord.utils import escape_markdown


async def embed_exception(exception):
    embed = discord.Embed(title="Exception",
                          description=escape_markdown(str(exception)),
                          color=0xff0000)
    embed.set_footer(text="This error information is for staff, just ignore it.")
    return embed
