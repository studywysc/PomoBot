import asyncio
import discord

from cmdClient import cmd
from cmdClient.lib import ResponseTimedOut, UserCancelled
from cmdClient.checks import in_guild

from wards import timer_admin
from utils import seekers, ctx_addons, timer_utils  # noqa
# from Timer import create_timer


@cmd("createfocus",
     group="WYSC Custom",
     desc="Set up the focus role system.")
@in_guild()
@timer_admin()
async def cmd_createfocus(ctx):
    """
    Usage``:
        createfocus
    Description:
        Prompts for the focus role and channels to hide.

        When the `focus` command is run, the user will be given the focus role,
        and in addition the specified channels will be hidden.
        When the `focus` command is run again, the focus role will be removed,
        and the channels will be shown to them.
    """
    role = None
    channels = []
    try:
        while role is None:
            role_str = await ctx.input(
                "Please enter the focus role.\n"
                "This role is given when a user runs `focus`, and removed when `focus` is run again.\n"
                "(Accepted input: Role name or partial name, role id, or role mention.)"
            )
            role = await ctx.find_role(role_str.strip(), interactive=True)

        while not channels:
            channel_strs = await ctx.input(
                "Please enter the channels to explicitly hide from focused users, or `None`.\n"
                "(Accepted input: None, or Comma separated list of channel names "
                "or partial names, channel ids or channel mentions.)"
            )
            if channel_strs.lower() == "none":
                break
            for channel_str in channel_strs.split(','):
                channel = await ctx.find_channel(channel_str.strip(), interactive=True)
                if channel is None:
                    await ctx.error_reply("Couldn't find channel `{}`.".format(channel_str))
                    channels = []
                    break
                channels.append(channel)
    except UserCancelled:
        raise UserCancelled(
            "User cancelled focus system setup!"
        ) from None
    except ResponseTimedOut:
        raise ResponseTimedOut(
            "Timed out waiting for a response during focus system setup!"
        ) from None

    ctx.client.config.guilds.set(ctx.guild.id, 'focus_role', role.id)
    ctx.client.config.guilds.set(ctx.guild.id, 'focus_channels', [c.id for c in channels])
    await ctx.embedreply("Focus system set up!")


@cmd("focus",
     group="WYSC Custom",
     desc="Enter or leave focus mode.")
@in_guild()
async def cmd_focus(ctx):
    """
    Usage``:
        focus
    Description:
        Enter or leave focus mode to remove distractions.
        This requires focus setup to have been completed via the `createfocus` command.
    """
    roleid = ctx.client.config.guilds.get(ctx.guild.id, 'focus_role')
    channelids = ctx.client.config.guilds.get(ctx.guild.id, 'focus_channels') or []

    if roleid is None or channelids is None:
        return await ctx.error_reply("The focus system has not been setup! Set it up via the `createfocus` command.")

    focus_role = ctx.guild.get_role(roleid)
    channels = [ctx.guild.get_channel(chid) for chid in channelids]

    if focus_role is None:
        return await ctx.error_reply("The focus role doesn't exist, please set up the focus system again.")

    if focus_role in ctx.author.roles:
        # Remove focus
        try:
            await ctx.author.remove_roles(focus_role, reason="Removing focus role.")
        except discord.Forbidden:
            return await ctx.error_reply("Didn't have permission to remove the focus role from you.")

        focus_overwrite = discord.PermissionOverwrite(read_messages=None)
        failed_channels = []

        async def remove_focus_in(channel):
            if channel is not None:
                try:
                    await channel.set_permissions(ctx.author, overwrite=focus_overwrite, reason="Disabling focus mode.")
                except discord.Forbidden:
                    failed_channels.append(channel)

        await asyncio.gather(*[remove_focus_in(channel) for channel in channels])

        await ctx.embedreply("You have left **Focus** mode!", title="Relax")
    else:
        # Add focus
        try:
            await ctx.author.add_roles(focus_role, reason="Adding focus role.")
        except discord.Forbidden:
            return await ctx.error_reply("Didn't have permission to add the focus role to you.")

        focus_overwrite = discord.PermissionOverwrite(read_messages=False)
        failed_channels = []

        async def create_focus_in(channel):
            if channel is not None:
                try:
                    await channel.set_permissions(ctx.author, overwrite=focus_overwrite, reason="Enabling focus mode.")
                except discord.Forbidden:
                    failed_channels.append(channel)

        await asyncio.gather(*[create_focus_in(channel) for channel in channels])

        await ctx.embedreply(("You have entered **Focus** mode!\n"
                              "Some distracting channels have been hidden to help you focus.\n"
                              "Type the command again to leave focus mode!"),
                             title="Focus!")
