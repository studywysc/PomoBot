import discord

from cmdClient import cmd, checks
from utils import interactive  # noqa


@cmd("permcheck",
     group="WYSC Custom",
     desc="List the channels visible to a user.")
@checks.in_guild()
async def cmd_permchek(ctx):
    """
    Usage``:
        permcheck <userid>
    Description:
        Displays a list of channels visible to the given user.
    Parameters::
        userid: The userid of the user you want to check.
    """
    arg = ctx.arg_str.strip()
    if not arg.isdigit():
        return await ctx.error_reply("**Usage:** `permcheck <userid>`")

    try:
        member = await ctx.guild.fetch_member(int(arg))
    except discord.HTTPException:
        member = None
    if member is None:
        return await ctx.error_reply("No member with id `{}` found.".format(arg))

    all_channels = []
    for cat, channels in ctx.guild.by_category():
        if cat is not None and cat not in all_channels:
            all_channels.append(cat)
        all_channels += channels

    channels = [channel for channel in all_channels if channel.permissions_for(member).read_messages]
    channels = [channel.mention if channel.type == discord.ChannelType.text else channel.name for channel in channels]
    channel_blocks = ['\n'.join(channels[i:i+20]) for i in range(0, len(channels), 20)]

    embeds = [discord.Embed(
        title="Channels visible to {}".format(member.name),
        description=block,
        colour=discord.Colour.light_grey(),
    ).set_footer(text="Page {}/{}".format(i+1, len(channel_blocks))) for i, block in enumerate(channel_blocks)]
    await ctx.pager(embeds, locked=False)
