channel_role_map = {
    319655206029885442: 486481145630949376, // vc-cafe: voice
    748180533959327795: 486481145630949376, // yoga: voice
    953199599567384596: 633128594071355403, // studycam: studyspace
    621534062133379132: 633128594071355403, // studyspace: studyspace
    640109668072423424: 633125625053315089, // studyradio: studyradio
}


async def manage_vc_role(client, member, before, after):
    if before.channel != after.channel:
        guild = member.guild

        to_add = guild.get_role(channel_role_map.get(after.channel.id, None)) if after.channel else None
        to_remove = guild.get_role(channel_role_map.get(before.channel.id, None)) if before.channel else None

        if to_add != to_remove or to_add not in member.roles:
            if to_remove is not None:
                await member.remove_roles(to_remove, reason="Removing voice auto-role")
            if to_add is not None:
                await member.add_roles(to_add, reason="Adding voice auto-role")


def load_into(client):
    client.add_after_event('voice_state_update', manage_vc_role)
