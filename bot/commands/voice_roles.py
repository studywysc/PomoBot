channel_role_map = {
    319655206029885442: 486481145630949376,
    748180533959327795: 486481145630949376,
    621534062133379132: 633128594071355403,
    640109668072423424: 633125625053315089
}


async def add_vc_role(client, member, before, after):
    if after.channel is not None and before.channel != after.channel:
        roleid = channel_role_map.get(after.channel.id, None)
        if roleid is not None:
            role = member.guild.get_role(roleid)
            if role is not None:
                await member.add_roles(role, reason="Adding voice auto-role")


async def rm_vc_role(client, member, before, after):
    if before.channel is not None and before.channel != after.channel:
        roleid = channel_role_map.get(before.channel.id, None)
        if roleid is not None:
            role = member.guild.get_role(roleid)
            if role is not None:
                await member.remove_roles(role, reason="Removing voice auto-role")


def load_into(client):
    client.add_after_event('voice_state_update', add_vc_role)
    client.add_after_event('voice_state_update', rm_vc_role)
