import asyncio
import discord

from cmdClient import cmd
from cmdClient.checks import in_guild

from wards import timer_admin, guild_admin
from utils import seekers, ctx_addons, timer_utils  # noqa
from data.data import Table

from settings import Setting, GuildSettings
from settings.base import ColumnData
from settings.setting_types import SettingType, Channel, Role, UserInputError

# from Timer import create_timer


class ListData:
    _table_interface = None
    _id_column = None
    _data_column = None

    @classmethod
    def _reader(cls, id, **kwargs):
        table = cls._table_interface

        rows = table.select_where(**cls._params(id, **kwargs))
        return [row[cls._data_column] for row in rows]

    @classmethod
    def _writer(cls, id, data, **kwargs):
        table = cls._table_interface
        params = cls._params(id, **kwargs)

        if not data:
            # Remove all rows
            table.delete_where(**params)
        else:
            old = cls._reader(id)
            to_remove = [item for item in old if item not in data]
            to_add = [item for item in data if item not in old]
            if to_remove:
                remove_params = {
                    **params,
                    cls._data_column: to_remove
                }
                table.delete_where(**remove_params)
            if to_add:
                value_tuples = (
                    (*params.values(), item)
                    for item in to_add
                )
                insert_keys = (*params.keys(), cls._data_column)
                table.insert_many(
                    *value_tuples,
                    insert_keys=insert_keys
                )

    @classmethod
    def _params(cls, id, **kwargs):
        if isinstance(cls._id_column, (tuple, list)):
            if not isinstance(id, (tuple, list)) or len(id) != len(cls._id_column):
                raise ValueError("Invalid `id` passed to multi-column ListData.")
            return {
                col: value for col, value in zip(cls._id_column, id)
            }
        else:
            return {
                cls._id_column: id
            }


class ChannelList(SettingType):
    accepts = "Comma separated list of channel mentions/ids/names, or `None` to unset."

    @classmethod
    def _data_from_value(cls, id, values, **kwargs):
        return [Channel._data_from_value(id, value) for value in values] if values else None

    @classmethod
    def _data_to_value(cls, id, data, **kwargs):
        return [Channel._data_to_value(id, item) for item in data] if data else []

    @classmethod
    async def _parse_userstr(cls, ctx, id, userstr, **kwargs):
        if userstr.lower() == 'none':
            data = []
        else:
            items = userstr.split(',')
            items = [item.strip() for item in items]
            data = [await Channel._parse_userstr(ctx, id, item, **kwargs) for item in items]
            data = [item for item in data if item is not None]
        return data

    @classmethod
    def _format_data(cls, id, data, **kwargs):
        if data is None or not data:
            return None
        else:
            return ', '.join(Channel._format_data(id, item, **kwargs) for item in data)


@GuildSettings.attach_setting
class focus_role(Role, ColumnData, Setting):
    attr_name = 'focus_role'

    _table_interface = Table('guild_focus_roles')
    _id_column = 'guildid'
    _data_column = 'focus_roleid'

    write_ward = guild_admin

    display_name = 'focus_role'
    desc = 'Role giving a distraction-free server view.'
    long_desc = (
        "Role given when a member goes into `focus` mode (see the `focus` command). "
        "The role is intended to hide as many distractions as possible. "
        "Further channels may be hidden using the `focushides` system.\n"
        "*This role must be under PomoBot's top role.*"
    )

    @property
    def success_response(self):
        if self.value:
            return "The focus role is now {}.".format(self.formatted)
        else:
            return "The focus role has been unset and the focus system is disabled."

    @classmethod
    def _writer(cls, id, data, **kwargs):
        if data is None:
            table = cls._table_interface
            table.delete_where(**{cls._id_column: id})
        else:
            super()._writer(id, data, **kwargs)


@GuildSettings.attach_setting
class focus_channels(ChannelList, ListData, Setting):
    attr_name = 'focus_channels'

    _table_interface = Table('guild_focus_channels')
    _id_column = 'guildid'
    _data_column = 'channelid'

    write_ward = timer_admin

    display_name = 'focus_channels'
    desc = "Channels manually hidden in focus mode."
    long_desc = (
        "List of channels to manually hide when a user goes into focus mode, "
        "in addition to those hidden by the `focusrole`.\n"
        "The channels are hidden using per-channel member permission overrides, "
        "and allow for more complex permission setups than the role itself.\n"
        "*PomoBot must have the `manage_permissions` and `view_channel` permissions in each channel.*"
    )

    @property
    def success_response(self):
        if self.value:
            return "The focus channels are now:\n{}.".format(self.formatted)
        else:
            return "All focus channels have been removed from the focus system."


@GuildSettings.attach_setting
class focus_channels_extra(ChannelList, ListData, Setting):
    attr_name = 'focus_channels_extra'

    _table_interface = Table('guild_focus_channels_extra')
    _id_column = 'guildid'
    _data_column = 'channelid'

    write_ward = timer_admin

    display_name = 'focus_extra'
    desc = "Extra channels that may optionally be hidden in focus mode."
    long_desc = (
        "List of channels that may be additionally hidden in focus mode. "
        "Members may add these channels to their `myfocushides` list, "
        "and they will be hidden when the member next goes into focus mode.\n"
        "*PomoBot must have the `manage_permissions` and `view_channel` permissions in each channel.*"
    )

    @property
    def success_response(self):
        if self.value:
            return "The possible extra focus channels are now:\n{}.".format(self.formatted)
        else:
            return "All extra focus channels have been removed from the focus system."


class member_focus_extra(ChannelList, ListData, Setting):
    attr_name = 'member_focus_extra'

    _table_interface = Table('member_focus_extra')
    _id_column = ('guildid', 'userid')
    _data_column = 'channelid'

    write_ward = None

    display_name = 'focus_extra'
    desc = "Extra channels to hide in focus mode."
    long_desc = (
        "List of channels that will be additionally hidden in focus mode. "
        "The channels must be in the `focusextra` list."
    )
    accepts = "Comma-separated list of channels from the below list, or `None` to unset."

    @property
    def embed(self):
        embed = super().embed
        embed.add_field(
            name="Available Extra Channels",
            value=GuildSettings.settings.focus_channels_extra.get(self.id[0]).formatted
        )
        return embed

    @property
    def success_response(self):
        if self.value:
            return (
                "The following channels will additionally be hidden from you in focus mode:\n{}.".format(self.formatted)
            )
        else:
            return "No extra channels will be hidden from you in focus mode."

    @classmethod
    async def _parse_userstr(cls, ctx, id, userstr, **kwargs):
        data = await super()._parse_userstr(ctx, id, userstr, **kwargs)
        if data:
            valid_choices = set(ctx.guild_settings.focus_channels_extra.data or [])
            invalid = next((chid for chid in data if chid not in valid_choices), None)
            if invalid:
                raise UserInputError(
                    "Channel <#{}> cannot be added to your focus mode. "
                    "Check `{}myfocushides` to see a list of available extra channels.".format(
                        invalid,
                        ctx.best_prefix
                    )
                )
        return data


@cmd(
    "focusrole",
    group="Wysc Admin",
    short_help=("The focus system role. "
                "(Currently {ctx.guild_settings.focus_role.formatted})")
)
@in_guild()
async def cmd_focusrole(ctx):
    """
    Usage``:
        {prefix}focusrole
        {prefix}focusrole <new-role>
    Setting Description:
        {ctx.guild_settings.settings.focus_role.long_desc}
    """
    await GuildSettings.settings.focus_role.command(ctx, ctx.guild.id)


@cmd(
    "focushides",
    group="Wysc Admin",
    short_help=("Channels hidden in focus mode.")
)
@in_guild()
async def cmd_focushides(ctx):
    """
    Usage``:
        {prefix}focushides
        {prefix}focushides channel1, channel2, ...
    Setting Description:
        {ctx.guild_settings.settings.focus_channels.long_desc}
    """
    await GuildSettings.settings.focus_channels.command(ctx, ctx.guild.id)


@cmd(
    "focusextra",
    group="Wysc Admin",
    short_help=("Extra channels that may be hidden in focus mode.")
)
@in_guild()
async def cmd_focusextra(ctx):
    """
    Usage``:
        {prefix}focusextra
        {prefix}focusextra channel1, channel2, ...
    Setting Description:
        {ctx.guild_settings.settings.focus_channels_extra.long_desc}
    """
    await GuildSettings.settings.focus_channels_extra.command(ctx, ctx.guild.id)


@cmd(
    "myfocushides",
    group="Personal Settings",
    short_help=("Extra channels hidden in focus mode.")
)
@in_guild()
async def cmd_myfocushides(ctx):
    """
    Usage``:
        {prefix}myfocushides
        {prefix}myfocushides channel1, channel2, ...
    Setting Description:
        A list of channels that will be additionally hidden when you enter focus mode.
        The channels must be in the list below.
    Available Channels:
        {ctx.guild_settings.focus_channels_extra.formatted}
    """
    await member_focus_extra.command(ctx, (ctx.guild.id, ctx.author.id))


@cmd("focus",
     group="Wysc",
     desc="Enter or leave focus mode.")
@in_guild()
async def cmd_focus(ctx):
    """
    Usage``:
        {prefix}focus
    Description:
        Enter or leave focus mode to remove distractions.
    Configuration:
        *For server admins*
        To setup the focus role and additional hidden channels see\
            `{prefix}focusrole`, `{prefix}focushides` and `{prefix}focusextra`.

        *For members*
        See `{prefix}myfocushides` for further configuration of your focus mode.
    """
    role = ctx.guild_settings.focus_role.value
    if not role:
        return await ctx.error_reply(
            "No focus role (`{}focusrole`) has been set! "
            "The focus system is disabled.".format(ctx.best_prefix)
        )

    channels = ctx.guild_settings.focus_channels.value + member_focus_extra.get((ctx.guild.id, ctx.author.id)).value

    if role in ctx.author.roles:
        # Leave focus mode
        try:
            await ctx.author.remove_roles(role, reason="Removing focus role.")
        except discord.Forbidden:
            return await ctx.error_reply("I don't have permission to remove the focus role from you!")

        focus_overwrite = discord.PermissionOverwrite(read_messages=None)
        failed_channels = []

        async def remove_focus_in(channel):
            if channel is not None:
                try:
                    await channel.set_permissions(ctx.author, overwrite=focus_overwrite, reason="Disabling focus mode.")
                except discord.Forbidden:
                    failed_channels.append(channel)

        await asyncio.gather(*[remove_focus_in(channel) for channel in channels])

        await ctx.embed_reply("You have left **Focus** mode!", title="Relax")
    else:
        # Enter focus mode
        try:
            await ctx.author.add_roles(role, reason="Adding focus role.")
        except discord.Forbidden:
            return await ctx.error_reply("I don't have permission to add the focus role to you!")

        focus_overwrite = discord.PermissionOverwrite(read_messages=False)
        failed_channels = []

        async def create_focus_in(channel):
            if channel is not None:
                try:
                    await channel.set_permissions(ctx.author, overwrite=focus_overwrite, reason="Enabling focus mode.")
                except discord.Forbidden:
                    failed_channels.append(channel)

        await asyncio.gather(*[create_focus_in(channel) for channel in channels])

        await ctx.embed_reply(("You have entered **Focus** mode!\n"
                               "Some distracting channels have been hidden to help you focus.\n"
                               "Type the command again to leave focus mode!"),
                              title="Focus!")
