import discord
from discord.ext import commands, tasks
import datetime
from src.ritV import ritV
import aiohttp
import time
from rich.console import Console
from src.errors import *
import utils
from src import styles
from mcrcon import MCRcon
import requests
import os
import pickle
from rich.prompt import Prompt

console= Console()


verif = ritV(console)
if os.path.exists('bot.token'):
    with open('bot.token', 'rb') as token_file:
        token = pickle.load(token_file)
else:
    token = Prompt.ask("[bold]Initial bot setup:[not bold]\n↳ Please enter a Discord token")
    with open('bot.token', 'wb') as token_file:
        pickle.dump(token, token_file)
bot = commands.Bot(intents=discord.Intents.all())
console.print('↳ Loading configuration...')
guilds=["1151963835515813890"]
invites = {}

def check_minecraft_username(username):
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    response = requests.get(url)
    if response.status_code == 200:
        return True
    elif response.status_code == 204:
        return False
    else:
        response.raise_for_status()

async def apply_verification(user:discord.User,first = False):
    await user.add_roles(role_verified,role_not_whitelisted)
    embed = discord.Embed(title="You've been verified!",description="Be sure to check out https://discord.com/channels/1151963835515813890/1170861611653812244 to be whitelisted on the Minecraft Server.",color=discord.Color.nitro_pink())
#     if first:
#         embed.add_field(name='You\'ve also been granted access to:',value='''
# - [RIT Freshmen Discord](https://discord.gg/P9qd46x9B4)
# ''')
    credits = discord.Embed(title="⟶ keeping communities safer.",description="a  verification solution developed, hosted, and maintained by [mae.red](https://mae.red). please consider **[donating](https://www.buymeacoffee.com/maedotred)** to support my efforts :)",color=discord.Color.from_rgb(255,255,255))
    try:
        await user.add_roles(role_verified,role_not_whitelisted)
    except:
        console.log('Ignoring permission error when assigning role.',style=styles.critical_error)
    dmsopen = await utils.checkDMs(user)
    if dmsopen:
        await user.send(embeds=[embed,credits])
    console.print(f"Successfully verified {user.display_name}. ({user.name}, {user.id})")

# ------------------------------------------------------------------------------
# Lambdas
# ------------------------------------------------------------------------------
roleByName = lambda roleName: discord.utils.get(guild.roles, name=roleName)
roleByID = lambda roleID: discord.utils.get(guild.roles, id=roleID)
# channelByID does not exist, because you should use bot.fetch_channel(ID)
# ----------------------------------------------------------------------------
console.print('↳ Registering commands...')
@bot.event
async def on_connect():
    console.print('↳ Connected to Discord.')

@bot.event
async def on_ready():
    global guild # Used by lambdas, but can only be retrieved once the bot is initialized
    guild = bot.get_guild(1151963835515813890)
    global botMember
    botMember = guild.get_member(bot.user.id) #workaround to bot.me
    # ----------------------------------------------------------------------------
    # Shorthands - be extra careful when setting IDs here!
    console.print('↳ Fetching roles and channels...')
    # ----------------------------------------------------------------------------
    global channel_mod 
    channel_mod = await bot.fetch_channel(1152437009453953155)
    global channel_hooks
    channel_hooks = await bot.fetch_channel(1154882083827744778)
    global role_verified
    role_verified = roleByID(1153773046973337620)
    global role_not_whitelisted
    role_not_whitelisted = roleByID(1170869083189809243)
    global channel_verify
    channel_verify=await bot.fetch_channel(1169808832344641616)
    # ----------------------------------------------------------------------------
    console.print('↳ Fetching invites...')
    guild_invs = await guild.invites()
    for i in guild_invs:
        i:discord.Invite
        invites[i.code] = i.uses
    console.print(f'  ↳ {len(invites)} invites loaded.')
    refreshInvites.start()
    
    console.print('  ↳ Invite refresh timer started.')
    # console.print(invites)
    console.print('↳ Adding views...')
    bot.add_view(VerificationMenu())
    bot.add_view(WhitelistMenu())
    console.print(f'  ↳ {len(bot.persistent_views)} views loaded.')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Gravitron MC"))

    console.print('↳ Testing RCON connection...')
    try:
        with MCRcon("51.222.254.78", "Grav1rattat") as mcr:
            resp = mcr.command("/list").split(' of')[0].split('are ')[1]
            console.print(f'↳ Connected to server! {resp} players online.')
    except Exception as e:
        console.print('↳ Failed to connect to RCON.',style=styles.critical_error)
        console.print(e)
    console.print(f'↳ Completed self setup![bold][orange] Bot is ready.[/orange][not bold]')

@tasks.loop(seconds=15)
async def refreshInvites():
    guild_invs = await guild.invites()
    for i in guild_invs:
        i:discord.Invite
        invites[i.code] = i.uses

# ==============================================================================
# User commands
# ==============================================================================

# Verification Modals and Views

class VerificationEmailModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:

        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="ab1234@rit.edu", min_length=6, max_length=20))

    async def callback(self, interaction: discord.Interaction):
        ritemail = self.children[0].value
        console.print(f'Verification session started for {interaction.user.name}.')
        v_status=False
        try: 
            v_status = verif.verify_email(interaction.user.id,ritemail)
        except AlreadyVerifiedException:
            await apply_verification(interaction.user)
            await interaction.response.defer()
        except DuplicateEmailException:
            embed = discord.Embed(title="That email didn't work.")
            embed.description = "This email has already been bound to another account."
            console.print(f'{interaction.user.name} attempted an existing email.')
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
        except BannedEmailException:
            await interaction.user.ban()
            await memberAlert('WARNING: A banned email was blocked from verification. The user was banned.', interaction.user)
            return
        except EmailFormatException:
            await interaction.response.send_message('Something went wrong. Please use your RIT email, such as `ab1234@rit.edu`, or `abc1234@g.rit.edu`.', ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message("**Yikes!**\nSomething went wrong when sending an email. We're still ironing out some issues that arise with high usage. The developers have been notified.",ephemeral=True)
            console.print(e)
            return
        if v_status:
            await interaction.response.defer()
            await interaction.followup.send(embed=discord.Embed(color=discord.Colour.green(),title="An email has been sent!",description="Check your email for a six-digit code, then click below or type `/readytoverify` when you're ready. \n *Please don\'t close this message!*"),view=AwaitingVerificationView(),ephemeral=True)


class VerificationMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout of the view must be set to None    
    @discord.ui.button(label="Verify my RIT Email", style=discord.ButtonStyle.green, emoji="✅",custom_id="VerifyButton") 
    async def button_callback(self, button, interaction:discord.Interaction):
        if verif.is_verified(interaction.user.id):
            await apply_verification(interaction.user)
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(modal= VerificationEmailModal(title="Please enter your RIT Email."))

class AwaitingVerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="I received an email.", style=discord.ButtonStyle.green, emoji="📨") 
    async def button_callback(self, button, interaction:discord.Interaction):
        await interaction.response.send_modal(modal = VerificationCodeModal(title="Please enter your verification code."))

class VerificationCodeModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Your 6-digit ID", min_length=6, max_length=6))

    async def callback(self, interaction: discord.Interaction):
        try:    
            console.print(self.children[0].value)
            if verif.complete_verification(str(interaction.user.id),self.children[0].value):
                await apply_verification(interaction.user,first=True)
                await interaction.response.defer()
            else:                
                embed = discord.Embed(title="Incorrect verification code. Please try again.")
                console.print(f'Verification code for {interaction.user.name} was incorrect.')
                await interaction.response.send_message(embeds=[embed], ephemeral=True)
        except InactiveSessionException:
            console.print('Invalid session exception')

# ==============================================================================
# Developer Utilities
# ==============================================================================

# ------------------------------------------------------------------------------
# Extension Management
# ------------------------------------------------------------------------------

@bot.slash_command(guild_ids=guilds)
@commands.has_role('Server Management')
async def testdm(ctx,member:discord.Option(discord.Member)):
    await ctx.respond(str(await utils.checkDMs(member)),ephemeral=True)
    

async def memberAlert(title:str, member:discord.Member):
    '''Warn the mod chat with information about a member.'''
    warn = discord.Embed(title=title,color=discord.Colour.red(),timestamp=datetime.datetime.now())
    warn.set_thumbnail(url=member.avatar.url) 
    warn.add_field(name='Name',value=member.name)
    warn.add_field(name='Member Since',value=member.joined_at.strftime("%m/%d/%Y, %I:%M:%S %p"))
    warn.add_field(name='Mention',value=f'<@{member.id}>')
    
    await channel_mod.send(embed=warn)

class WhitelistMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  
    @discord.ui.button(label="Enter Your IGN", style=discord.ButtonStyle.primary, emoji="✅",custom_id="WhitelistButton") 
    async def button_callback(self, button, interaction:discord.Interaction):
        await interaction.response.send_modal(modal= WhitelistModal(title="Please enter your Minecraft IGN."))

class WhitelistModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:

        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="ab1234@rit.edu", min_length=3, max_length=16))

    async def callback(self, interaction: discord.Interaction):
        ign = self.children[0].value
        if check_minecraft_username(ign):
            with MCRcon("51.222.254.78", "Grav1rattat") as mcr:
                mcr.command(f"/whitelist add {ign}")
                mcr.command(f"/whitelist reload")
                console.print(f'Sueccessfully whitelisted `{ign}`!',style=styles.success)
            embed = discord.Embed(title=f'`{ign}` has been added to the whitelist.')
            await interaction.user.send(embeds=[embed])
            await interaction.response.defer()

            await interaction.user.remove_roles(role_not_whitelisted)
            await channel_hooks.send(f'Whitelisted <@{interaction.user.id}> : `{ign}`')
        else:
            interaction.response.send_message(f'### Woah there.\nYou entered an invalid Minecraft username. Please double check the spelling of **`{ign}`** and try again.', ephemeral=True)

@bot.slash_command(guild_ids=guilds)
@commands.has_role('Admin')
async def getchannelmembers(ctx: discord.ApplicationContext, channel: discord.Option(discord.TextChannel)):
    msg = ""
    for i in channel.members:
        msg += f"<@{i.id}>"
    console.print(msg)
    await ctx.respond(msg,ephemeral=True)
# ------------------------------------------------------------------------------
# Killswitch
# ------------------------------------------------------------------------------
@bot.slash_command(guild_ids=guilds)
@commands.has_role('Server Management')
async def kill(ctx):
    exit()

# ==============================================================================
# Events
# ==============================================================================

@bot.event
async def on_member_join(member: discord.Member):
    newinvites = await member.guild.invites()
    for i in newinvites:
        if invites[i.code] < i.uses:
            donotping=channel_mod.members
            if i.inviter not in donotping:
                inviter_id = f'<@{i.inviter.id}>'
            else:
                inviter_id = i.inviter.name
            embed = discord.Embed(title=f"{member.name} joined the server.",color=discord.Colour.blurple(),timestamp=datetime.datetime.now())
            embed.set_thumbnail(url=member.avatar.url) 
            embed.add_field(name='Name',value=member.name)
            embed.add_field(name='Member Since',value=member.joined_at.strftime("%m/%d/%Y, %I:%M:%S %p"))
            embed.add_field(name='Account Creation Date', value=member.created_at.strftime("%m/%d/%Y, %I:%M:%S %p"))
            embed.add_field(name='Mention',value=f'<@{member.id}>')
            embed.add_field(name='Invited by:', value=f'<@{inviter_id}>')
            embed.add_field(name='Invite code:', value=f'`{i.code}`')
            try:
                await channel_hooks.send(embed=embed)
            except:
                console.print('Failed to send invite log to hooks.')
            console.print(f'({member.id}) invited by {i.inviter.name} ({i.inviter.id}) through invite: {i.code}')
            break
    for i in newinvites:
        invites[i.code] = i.approximate_member_count
    if verif.check_banlist(member.id):
        await member.ban()
        await memberAlert('A user on the ban list was removed.', member)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(f'This command is on cooldown. Please retry in {round(error.retry_after, 2)}.\n## Are you still waiting for an email?\nDue to the large volume of emails being sent and restrictions on rit.edu, it may take upwards of two hours to receive this email.',ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.id==275318661647171584:
        if "!sendVerifModal" in message.content: # mf slash commands won't sync    
            embed = discord.Embed(title="This won't take long!",description="We keep our server safe by checking that members have an RIT email. Once you verify, you'll gain access to the rest of the server.",colour=discord.Color.green())
            # embed.add_field(name="How does verification work?",value="Transparency is our priority! You can learn more about our process here: https://discord.com/channels/1060637647862767726/1149385591230845139")
            await message.channel.send("# Welcome!",embed=embed,view=VerificationMenu())
            await message.delete()
        if "!sendWhitelistModal" in message.content: # mf slash commands won't sync    
            embed = discord.Embed(title="Get access!",description="Thank you for verifying. Click below to enter your minecraft IGN and get access to the server.",colour=discord.Color.from_rgb(255,255,255))
            await message.channel.send("# Welcome to __Gravitron MC__!",embed=embed,view=WhitelistMenu())
            await message.delete()

console.print('↳ Starting bot instance!')

while True:
    try:
        bot.run(token)
    except aiohttp.client_exceptions.ClientConnectorError:
        console.print("↳ Failed to connect. Retrying in a few seconds.")
        time.sleep(5)
