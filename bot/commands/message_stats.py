import asyncio
from datetime import datetime, timedelta
import discord

from cmdClient import cmd, checks
from utils import interactive  # noqa

from wards import timer_admin


guild_stat_table = {}


@cmd("genmessagestats",
     group="WYSC Custom",
     desc="Display message stats in the given timeframe.")
@checks.in_guild()
@timer_admin()
async def cmd_genmessagestats(ctx):
    """
    Usage``:
        genmessagestats
        genmessagestats <days>
    Description:
        Retrieves the specified number of days of message history from each channel
        for use with other stats commands.
    Parameters::
        days: The number of days to retrieve. Defaults to 30.
    Examples``:
        genmessagestats 30
    """
    arg = ctx.arg_str.strip()
    if arg and not arg.isdigit():
        return await ctx.error_reply("Please enter a numerical number of days.")

    PERIOD = int(arg) if arg else 30
    timestamp_limit = datetime.now() - timedelta(days=PERIOD)

    stats = {}
    channels_counted = 0
    total_channels = len(ctx.guild.text_channels)
    out_msg = await ctx.reply("```{}```".format(
        progress_bar(channels_counted, total_channels, "Channels processed")
    ))

    async def read_channel_stats(channel):
        channel_data = {}
        if channel.permissions_for(ctx.guild.me).read_message_history:
            async for message in channel.history(limit=None):
                if message.created_at < timestamp_limit:
                    break
                if message.author.id not in channel_data:
                    channel_data[message.author.id] = 0
                channel_data[message.author.id] += 1
        stats[channel.id] = channel_data

        nonlocal channels_counted
        channels_counted = channels_counted + 1
        if not channels_counted % 5:
            await out_msg.edit(content="```{}```".format(
                progress_bar(channels_counted, total_channels, "Channels processed")
            ))

    for channel_block in [list(ctx.guild.text_channels)[i:i+10] for i in range(0, total_channels, 10)]:
        await asyncio.gather(*(read_channel_stats(channel) for channel in channel_block))

    await out_msg.delete()

    guild_stat_table[ctx.guild.id] = stats
    await ctx.embedreply("The stored stats have been updated!")


@cmd("userstats",
     group="WYSC Custom",
     desc="Display per-channel user message stats.")
@checks.in_guild()
@timer_admin()
async def cmd_userstats(ctx):
    """
    Usage``:
        userstats [user]
    Description:
        Displays a list of channels and your message counts.
        Uses the output of `genmessagestats`
    Parameters::
        days: The number of days to retrieve. Defaults to 30.
    Examples``:
        userstats
    """
    if ctx.guild.id not in guild_stat_table:
        return await ctx.error_reply("Please run the `genmessagestats` command first.")

    user = await ctx.find_member(ctx.arg_str, interactive=True) if ctx.arg_str else ctx.author
    if user is None:
        return
    userid = user.id

    channel_map = {cid: stats[userid] for cid, stats in guild_stat_table[ctx.guild.id].items() if userid in stats}
    flat_channels = sorted(list(channel_map.items()), key=lambda pair: pair[1], reverse=True)

    total = sum(channel_map.values())

    channel_list = [
        "<#{}>\t\t`{:>5}`\t{:<4.0%}".format(channel, stats, stats/total)
        for channel, stats in flat_channels
    ]
    channel_blocks = ['\n'.join(channel_list[i:i+20]) for i in range(0, len(channel_list), 20)]

    embeds = [discord.Embed(
        title="Per-channel message counts",
        description=block,
        colour=discord.Colour.light_grey(),
    ) for block in channel_blocks]
    await ctx.pager(embeds, locked=False)


def progress_bar(current, total, prefix='Progress', suffix='Complete', fill='█', length=50):
    """
    Creates a progress bar from the current value and total value with ASCII blocks.
    Parameters
    ----------
    current: int
        The current value to measure the progress bar
    total: int
        The total value to measure the progress bar
    prefix: string
        Allows a custom prefix for the string
    suffix: string
        Allows a custom suffix for the string
    fill: string
        Change the bar character
    length: int
        Change the length of the progress bar
    """
    filled = int(length * current // total)
    bar = fill * filled + '-' * (length-filled)
    return "{prefix}: |{bar}| {current}/{total} {suffix}".format(
        prefix=prefix,
        bar=bar,
        current=current,
        total=total,
        suffix=suffix
    )
