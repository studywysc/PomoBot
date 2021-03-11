import asyncio
from datetime import datetime, timedelta
import discord

from cmdClient import cmd, checks
from utils import interactive  # noqa

from wards import timer_admin


@cmd("emojistats",
     group="WYSC Custom",
     desc="Display emoji usage stats in the given timeframe.")
@checks.in_guild()
@timer_admin()
async def cmd_emojistats(ctx):
    """
    Usage``:
        emojistats
        emojistats <days>
    Description:
        Shows you a sorted list of guild custom emojis with their recent usages.
    Parameters::
        days: The number of days to check the usage for. Defaults to 30.
    Examples``:
        emojistats 30
    """
    arg = ctx.arg_str.strip()
    if arg and not arg.isdigit():
        return await ctx.error_reply("Please enter a numerical number of days.")

    PERIOD = int(arg) if arg else 30
    timestamp_limit = datetime.now() - timedelta(days=PERIOD)

    emoji_map = {emoji: [0, 0] for emoji in ctx.guild.emojis}

    channels_counted = 0
    total_channels = len(ctx.guild.text_channels)
    out_msg = await ctx.reply("```{}```".format(
        progress_bar(channels_counted, total_channels, "Channels processed")
    ))

    async def read_channel_stats(channel, map):
        if channel.permissions_for(ctx.guild.me).read_message_history:
            async for message in channel.history(limit=None):
                if message.created_at < timestamp_limit:
                    break
                for emoji, efreq in emoji_map.items():
                    if str(emoji) in message.content:
                        efreq[0] += 1
                for emoji in [r.emoji for r in message.reactions]:
                    if emoji in emoji_map:
                        emoji_map[emoji][1] += 1

        nonlocal channels_counted
        channels_counted = channels_counted + 1
        if not channels_counted % 5:
            await out_msg.edit(content="```{}```".format(
                progress_bar(channels_counted, total_channels, "Channels processed")
            ))

    for channel_block in [list(ctx.guild.text_channels)[i:i+50] for i in range(0, total_channels, 50)]:
        await asyncio.gather(*(read_channel_stats(channel, emoji_map) for channel in channel_block))

    await out_msg.delete()

    results = [(emoji, efreq[0], efreq[1], efreq[0] + efreq[1]) for emoji, efreq in emoji_map.items()]
    results.sort(key=lambda item: item[-1], reverse=True)

    emoji_list = ["{}\t\t`{:>4}`\t`{:<4}`\t`{:<4}`".format(*result) for result in results]
    emoji_blocks = ['\n'.join(emoji_list[i:i+20]) for i in range(0, len(emoji_list), 20)]

    embeds = [discord.Embed(
        title="Custom emoji usage counts for the last {} days".format(PERIOD),
        description="<emoji>  <messages>  <reactions>  <total>\n"+block,
        colour=discord.Colour.light_grey(),
    ) for block in emoji_blocks]
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
