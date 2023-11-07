import discord

async def checkDMs(user: discord.User) -> bool: 
    '''Unintrusively checks if we can DM someone by attempting to send an invalid message.'''
    try:
        await user.send()
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return True

def compareRoles(ctx:discord.ApplicationContext):
    member = ctx.author
    guild = ctx.guild
    botMember = ctx.guild.get_member(ctx.bot.user.id)
    '''For debugging potential permission related issues in a command. This typically only happens for the owner account as tange has the highest role in the server.'''
    print(f"- {member.display_name}'s top role: {member.top_role} ({member.top_role.position}) \n- Own top role: {botMember.top_role} ({botMember.top_role.position})")
    if guild.owner == member:
        print(f"- {member.display_name} is an owner.")