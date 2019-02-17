from modules import dbhandler

async def get_channel(channels, channel_id):  # client.get_all_channels()
    for channel in channels:
        if channel.id == channel_id:
            return channel
    return None


async def send_notice(notice, channel, now):
    if not await dbhandler.query(["SELECT notice FROM notices WHERE notice = ?", [notice]]):
        await channel.send(notice)
        await dbhandler.query(["INSERT INTO notices VALUES (?, ?)", [str(now.isoformat()), notice]])


# TODO: make a message parser that parses profiles
