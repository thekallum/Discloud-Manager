import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import Button, View, Select, Modal, TextInput
import io
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional, Dict

# --- IMPORTAÇÕES DA DISCLOUD ---
import discloud
from discloud.errors import RequestError
from discloud.discloud import Action, Application, ApplicationInfo, AppMod

# --- CONFIGURAÇÃO ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCLOUD_TOKEN = os.getenv("DISCLOUD_TOKEN")

if not DISCORD_TOKEN or not DISCLOUD_TOKEN:
    print("❌ ERRO: Tokens não definidos no .env")
    exit()

discloud_client = discloud.Client(DISCLOUD_TOKEN)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CORES E EMOJIS ---
C_GREEN = 0x50F862
C_RED = 0xE74C3C
C_BLUE = 0x3498DB
C_GOLD = 0xF1C40F
C_DARK = 0x2B2D31
C_PURPLE = 0x9B59B6

E_ONLINE = "🟢"
E_OFFLINE = "🔴"
E_CPU = "🖥️"
E_RAM = "<:memoriaram:1445901548638048489>"
E_SSD = "💾"
E_NET = "🌐"
E_LOADING = "⏳"
E_SUCCESS = "✅"
E_ERROR = "❌"
E_MODS = "🛡️"
E_INFO = "ℹ️"
E_PLAN = "💎"
E_WARN = "⚠️"
E_HOME = "🏠"
E_UPLOAD = "🚀"

# --- HELPER: BARRA DE PROGRESSO & PARSER ---
def parse_to_mb(value_str: str) -> float:
    """Converte strings como '10.1MB', '1GB' ou '1024' para float em MB."""
    try:
        clean = value_str.upper().strip()
        if "GB" in clean:
            return float(clean.replace("GB", "")) * 1024
        return float(clean.replace("MB", ""))
    except Exception:
        return 0.0

def create_emoji_bar(current_str: str, total_str: str, length=10) -> str:
    """Cria uma barra de progresso com emojis quadrados (🟩⬛)."""
    current = parse_to_mb(current_str)
    total = parse_to_mb(total_str)
    
    percent = min(1.0, current / total) if total > 0 else 0
    filled = int(length * percent)
    
    fill_char = "🟩"
    empty_char = "⬛" 
    
    return fill_char * filled + empty_char * (length - filled)

# --- MODAIS ---
class RamModal(Modal, title="Alterar Memória RAM"):
    ram_input = TextInput(
        label="Nova Quantidade (MB)",
        placeholder="Ex: 512, 1024...",
        min_length=2,
        max_length=5,
        required=True
    )

    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent

    async def on_submit(self, interaction: Interaction):
        try:
            amount = int(self.ram_input.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valor inválido. A RAM deve ser um número inteiro (ex: 512).", ephemeral=True)

        # 1. Feedback visual imediato no Painel Principal
        await interaction.response.defer()
        await self.view_parent.set_processing(interaction, f"Alterando RAM para {amount}MB")
        
        try:
            result = await discloud_client.ram(app_id=self.app_id, new_ram=amount) #
            
            # Tenta reiniciar, ou informa que não reiniciou
            start_msg = "A aplicação permaneceu desligada."
            if result.status == "ok":
                try:
                    await asyncio.sleep(2) 
                    await discloud_client.start(self.app_id) #
                    start_msg = "Reiniciando aplicação automaticamente..."
                except: 
                    start_msg = "A aplicação permaneceu desligada (erro ao tentar reiniciar)."

            # --- NOVO FORMATO DE RESPOSTA MAIS LEGÍVEL ---
            is_success = result.status == "ok"
            title_emoji = E_SUCCESS if is_success else E_ERROR
            embed_color = C_GREEN if is_success else C_RED
            api_message = result.message.replace('ramMB', 'RAM') # Limpa o termo técnico
            
            embed = discord.Embed(
                title=f"{title_emoji} Memória RAM Alterada",
                description=f"**Nova RAM:** `{amount}MB`\n"
                            f"**Mensagem:** {api_message}\n\n"
                            f"ℹ️ *{start_msg}*",
                color=embed_color
            )
            # --------------------------------------------

            await interaction.followup.send(embed=embed, ephemeral=True)
            # Atualiza o Painel após o Followup
            await self.view_parent.update_dashboard(interaction)
            
        except Exception as e:
            await self.view_parent.show_error(interaction, e, "Alterar RAM")

class ModActionModal(Modal):
    def __init__(self, action_type: str, app_id: str, view_parent):
        super().__init__(title=f"{action_type} Moderador")
        self.action_type = action_type
        self.app_id = app_id
        self.view_parent = view_parent
        self.mod_id = TextInput(label="Discord ID", placeholder="Ex: 123456789...", min_length=15, max_length=20, required=True)
        self.add_item(self.mod_id)
        self.perms = TextInput(label="Permissões", placeholder="start_app, restart_app...", default="start_app, restart_app, stop_app, logs_app, status_app", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.perms)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        mod_manager = discloud.ModManager(discloud_client, self.app_id) #
        perms_list = [p.strip() for p in self.perms.value.split(",") if p.strip()]
        try:
            if self.action_type == "add":
                result = await mod_manager.add_mod(mod_id=self.mod_id.value, perms=perms_list) #
            else:
                result = await mod_manager.edit_mod_perms(mod_id=self.mod_id.value, new_perms=perms_list) #
            embed = discord.Embed(title=f"{E_MODS} Mod {self.action_type}", description=result.message, color=C_GREEN)
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.view_parent.update_dashboard(interaction)
        except Exception as e: await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class RemoveModModal(Modal, title="Remover Moderador"):
    mod_id = TextInput(label="ID do Usuário", required=True)
    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent
    async def on_submit(self, intx):
        await intx.response.defer(ephemeral=True)
        try:
            res = await discloud.ModManager(discloud_client, self.app_id).delete_mod(self.mod_id.value) #
            await intx.followup.send(embed=discord.Embed(title="🗑️ Removido", description=res.message, color=C_GREEN), ephemeral=True)
            await self.view_parent.update_dashboard(intx)
        except Exception as e: await intx.followup.send(f"❌ Erro: {e}", ephemeral=True)

class DeleteAppModal(Modal, title="DELETAR APLICAÇÃO"):
    confirm_id = TextInput(
        label="Confirme o ID da Aplicação",
        placeholder="Cole o ID aqui para confirmar a exclusão...",
        required=True
    )
    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent
        
    async def on_submit(self, interaction: Interaction):
        if self.confirm_id.value != self.app_id:
            return await interaction.response.send_message("❌ ID Incorreto. A exclusão foi cancelada.", ephemeral=True)
        
        # 1. Feedback visual imediato antes da operação longa
        await interaction.response.defer()
        await self.view_parent.set_processing(interaction, f"Deletando App: {self.app_id}")
        
        try:
            result = await discloud_client.delete_app(self.app_id) #
            
            embed = discord.Embed(
                title="🗑️ Aplicação Deletada",
                description=f"**Status:** {result.status}\n**Msg:** {result.message}",
                color=C_GREEN if result.status == "ok" else C_RED
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Reseta o painel para Home
            self.view_parent.selected_app_id = None
            self.view_parent.current_mode = "home"
            await self.view_parent.update_dashboard(interaction)
            
        except Exception as e:
            await self.view_parent.show_error(interaction, e, "Deletar App")

# --- UI COMPONENTES ---

class AppSelect(Select):
    def __init__(self, apps: List[ApplicationInfo]):
        options = []
        for app in apps[:25]:
            emoji = E_ONLINE if app.online else E_OFFLINE
            label = app.name
            desc = f"ID: {app.id} | {app.lang}"
            options.append(discord.SelectOption(label=label, value=str(app.id), description=desc, emoji=emoji))
        super().__init__(placeholder="📂 Selecione uma aplicação ...", min_values=1, max_values=1, row=0, options=options)

    async def callback(self, interaction: Interaction):
        self.view.selected_app_id = self.values[0]
        self.view.current_mode = "status"
        await self.view.update_dashboard(interaction)

class DashboardView(View):
    def __init__(self, apps_info: List[ApplicationInfo]):
        super().__init__(timeout=600)
        self.apps_info_map = {app.id: app for app in apps_info}
        self.selected_app_id = None
        self.current_mode = "home"
        if apps_info: self.add_item(AppSelect(apps_info))
        self.create_nav_buttons()

    @property
    def current_app_name(self):
        return self.apps_info_map[self.selected_app_id].name if self.selected_app_id else "Desconhecido"

    def create_nav_buttons(self):
        self.add_item(Button(label="Início", emoji=E_HOME, style=ButtonStyle.secondary, custom_id="mode_home", row=1))
        self.add_item(Button(label="Status", emoji="📊", style=ButtonStyle.primary, custom_id="mode_status", row=1))
        self.add_item(Button(label="Controle", emoji="🎮", style=ButtonStyle.secondary, custom_id="mode_control", row=1))
        self.add_item(Button(label="Logs", emoji="📜", style=ButtonStyle.secondary, custom_id="mode_logs", row=1))
        self.add_item(Button(label="Tools", emoji="🛠️", style=ButtonStyle.secondary, custom_id="mode_tools", row=2))
        self.add_item(Button(label="Mods", emoji="🛡️", style=ButtonStyle.secondary, custom_id="mode_mods", row=2))
        for child in self.children:
            if isinstance(child, Button) and getattr(child, 'custom_id', '').startswith("mode_"): 
                child.callback = self.nav_callback

    async def nav_callback(self, interaction: Interaction):
        mode = interaction.data["custom_id"].replace("mode_", "")
        if mode == "home":
            self.selected_app_id = None
            self.current_mode = "home"
        else:
            if not self.selected_app_id:
                return await interaction.response.send_message("⚠️ Selecione uma aplicação no menu primeiro.", ephemeral=True)
            self.current_mode = mode
        await self.update_dashboard(interaction)

    async def set_processing(self, interaction, action_name):
        # Desabilita botões para evitar cliques duplos
        for item in self.children: item.disabled = True
        embed = discord.Embed(title=f"{E_LOADING} Processando: {action_name}...", color=C_GOLD)
        try:
            # Edita a mensagem original do painel
            await interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            if interaction.message: await interaction.message.edit(embed=embed, view=self)
        except Exception: pass

    async def show_error(self, interaction, error, action_name):
        # Reabilita botões de navegação, exceto os de seleção
        for item in self.children: 
            if getattr(item, 'row', 0) in [0, 1, 2]: item.disabled = False
        embed = discord.Embed(title=f"{E_ERROR} Erro: {action_name}", description=f"```{error}```", color=C_RED)
        retry_btn = Button(label="Tentar Novamente", style=ButtonStyle.secondary, emoji="↩️", row=3)
        async def retry_cb(intx): await self.update_dashboard(intx)
        retry_btn.callback = retry_cb
        self.clear_dynamic_buttons()
        self.add_item(retry_btn)
        try:
            await interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            if interaction.message: await interaction.message.edit(embed=embed, view=self)

    async def update_dashboard(self, interaction: Interaction):
        self.clear_dynamic_buttons()
        for item in self.children:
            item.disabled = False
            if isinstance(item, Button) and getattr(item, 'custom_id', '').startswith("mode_"):
                if self.current_mode == "home":
                    if item.custom_id != "mode_home":
                        # REMOVIDA A LINHA: item.disabled = True (para evitar que todos os botões fiquem desabilitados)
                        item.style = ButtonStyle.secondary
                    else:
                        item.style = ButtonStyle.success
                        item.disabled = True
                else:
                    if item.custom_id == f"mode_{self.current_mode}":
                        item.style = ButtonStyle.success
                        item.disabled = True
                    else:
                        item.style = ButtonStyle.secondary
                        if item.custom_id == "mode_home": item.style = ButtonStyle.secondary

        try:
            embed = None
            if self.current_mode == "home" or self.selected_app_id is None:
                embed = await self.build_home_view(interaction.user)
            elif self.current_mode == "status":
                embed = await self.build_status_view()
                btn_ref = Button(label="Atualizar", emoji="🔄", style=ButtonStyle.gray, row=3)
                btn_ref.callback = self.update_dashboard
                self.add_item(btn_ref)
            elif self.current_mode == "control":
                embed = discord.Embed(title=f"🎮 Controle: {self.current_app_name}", color=C_GOLD, description="Gerencie o ciclo de vida da aplicação.")
                self.add_control_buttons()
            elif self.current_mode == "logs":
                embed = await self.build_logs_view()
                btn_ref = Button(label="Atualizar Logs", emoji="🔄", style=ButtonStyle.primary, row=3)
                btn_ref.callback = self.update_dashboard
                self.add_item(btn_ref)
            elif self.current_mode == "tools":
                embed = await self.build_tools_view()
                self.add_tools_buttons()
            elif self.current_mode == "mods":
                embed = await self.build_mods_view()
                self.add_mods_buttons()

            if interaction.response.is_done():
                try:
                    await interaction.edit_original_response(embed=embed, view=self)
                except discord.NotFound:
                    if interaction.message: await interaction.message.edit(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e: await self.show_error(interaction, e, "Carregar Painel")

    def clear_dynamic_buttons(self):
        items_to_keep = [item for item in self.children if getattr(item, 'row', 0) in [0, 1, 2]]
        self.clear_items()
        for item in items_to_keep: self.add_item(item)
    
    # --- BUILDERS (VIEWS) ---
    async def build_home_view(self, user_discord):
        user = await discloud_client.user_info() #
        apps = await discloud_client.app_info("all") #
        apps = apps if isinstance(apps, list) else [apps] if apps else []
        embed = discord.Embed(title=f"{E_PLAN} Olá, Disclouder!", color=C_PURPLE)
        embed.set_thumbnail(url=user_discord.display_avatar.url)
        embed.add_field(name="🆔 Usuário", value=f"`{user.id}`", inline=True)
        embed.add_field(name="💎 Plano", value=f"**{user.plan}**", inline=True)
        expire_str = "Vitalício"
        if hasattr(user.plan, 'expire_date') and user.plan.expire_date:
            try:
                ts = int(user.plan.expire_date.date.timestamp())
                expire_str = f"<t:{ts}:f>"
            except: expire_str = str(user.plan.expire_date)
        embed.add_field(name="🗓️ Validade", value=expire_str, inline=True)
        bar = create_emoji_bar(str(user.using_ram), str(user.total_ram))
        embed.add_field(name=f"{E_RAM} RAM Global ({user.using_ram}MB / {user.total_ram}MB)", value=f"{bar}", inline=False)
        app_list = "\n".join([f"• **{app.name}** (`{app.id}`)" for app in apps[:5]])
        if not app_list: app_list = "Nenhuma aplicação encontrada."
        embed.add_field(name="📂 Minhas aplicações", value=app_list, inline=False)
        embed.set_footer(
            text="Selecione uma aplicação no menu acima. | Discloud Manager",
            icon_url=bot.user.display_avatar.url
        )
        return embed

    async def build_status_view(self):
        status = await discloud_client.app_status(target=self.selected_app_id) #
        info = self.apps_info_map.get(self.selected_app_id)
        color = C_GREEN if status.status == "Online" else C_RED
        embed = discord.Embed(title=f"App: {self.current_app_name}", color=color)
        if info and hasattr(info, 'avatarURL') and info.avatarURL: embed.set_thumbnail(url=info.avatarURL)
        app_type = "Desconhecido"
        if info:
            if info.type == 0: app_type = "Bot"
            elif info.type == 1: app_type = "Site"
            else: app_type = str(info.type)
        desc_lines = [
            f"**🆔 ID:** `{status.id}`",
            f"**🤖 Tipo:** `{app_type}`",
            f"**<:linguagem:1445919040697794652> Linguagem:** `{info.lang if info else '?'}`",
            f"**📂 Arquivo Principal:** `{info.mainFile if info else '?'}`"
        ]
        embed.description = "\n".join(desc_lines)
        
        container_status = "🟢 Online" if status.status == "Online" else f"🔴 {status.status}"
        embed.add_field(name="<:container:1445920562298880011> Container", value=f"**{container_status}**", inline=True)
        embed.add_field(name=f"{E_CPU} CPU", value=f"`{status.cpu}`", inline=True)
        
        ram_bar = create_emoji_bar(status.memory.using, status.memory.available)
        embed.add_field(name=f"{E_RAM} RAM ({status.memory.using} / {status.memory.available})", value=f"{ram_bar}", inline=False)
        net = f"⬇️ {status.net_info.download} | ⬆️ {status.net_info.upload}"
        embed.add_field(name=f"{E_NET} Rede", value=f"`{net}`", inline=True)
        embed.add_field(name=f"{E_SSD} SSD", value=f"`{status.ssd}`", inline=True)

        # Uptime com Formatação Discord (Relative Time)
        uptime = "🔴 Desligado"
        if status.status == "Online":
            if hasattr(status, 'start_date') and hasattr(status.start_date, 'date'):
                try:
                    ts = int(status.start_date.date.timestamp())
                    uptime = f"<t:{ts}:R>"
                except:
                    uptime = str(status.online_since)
            else:
                uptime = str(status.online_since)
                 
        embed.add_field(name="🕒 Uptime", value=f"{uptime}", inline=True)
        
        git_msg = "Desativado ❌"
        if info and info.autoDeployGit and info.autoDeployGit.lower() != "no": git_msg = "Ativo ✅"
        embed.add_field(name="<:git:1445928668055474187> Integração Git", value=git_msg, inline=True)
        restart_msg = "Desativado ❌"
        if info and info.autoRestart: restart_msg = "Ativo ✅"
        embed.add_field(name="🔄 Auto Restart", value=restart_msg, inline=True)
        if info and info.ramKilled:
             embed.add_field(name=f"{E_WARN} Alerta Crítico", value="O bot foi reiniciado por falta de RAM.", inline=False)
        embed.set_footer(
            text="Discloud Manager",
            icon_url=bot.user.display_avatar.url
        )
        return embed

    async def build_tools_view(self):
        embed = discord.Embed(title=f"🛠️ Caixa de Ferramentas: {self.current_app_name}", color=C_BLUE)
        embed.description = "Utilitários avançados para manutenção."
        embed.add_field(name="💾 Backup", value="Baixar código-fonte.", inline=True)
        embed.add_field(name="<:memoriaram:1445901548638048489> RAM", value="Alterar memória RAM.", inline=True)
        embed.add_field(name="📦 Update", value="Use `/commit`.", inline=True)
        return embed

    async def build_logs_view(self):
        logs = await discloud_client.logs(target=self.selected_app_id) #
        content = logs.small[:1000]
        embed = discord.Embed(title=f"📜 Terminal: {self.current_app_name}", color=C_DARK, description=f"```bash\n{content}\n```")
        if len(content) >= 1000: embed.description += "\n*(Logs cortados)*"
        full_log_url = logs.url if logs.url else "https://discloudbot.com/dashboard"
        embed.add_field(name="🔗 Completo", value=f"[Ver logs completos no navegador]({full_log_url})")
        return embed

    async def build_mods_view(self):
        mods = await discloud.ModManager(discloud_client, self.selected_app_id).get_mods() #
        mods = mods if isinstance(mods, list) else [mods] if mods else []
        embed = discord.Embed(title=f"{E_MODS} Equipe: {self.current_app_name}", color=C_PURPLE)
        if not mods: embed.description = "Nenhum moderador foi adicionado para esta aplicação."
        for mod in mods:
            perms = ", ".join(mod.perms) if mod.perms else "Sem permissões"
            embed.add_field(name=f"👤 {mod.id}", value=f"Perms: `{perms}`", inline=False)
        return embed

    def add_control_buttons(self):
        self.make_btn("Iniciar", E_ONLINE, ButtonStyle.success, discloud_client.start) #
        self.make_btn("Reiniciar", "🔄", ButtonStyle.primary, discloud_client.restart) #
        self.make_btn("Parar", E_OFFLINE, ButtonStyle.danger, discloud_client.stop) #
    
    def add_tools_buttons(self):
        # 1. Backup
        btn_bkp = Button(label="Baixar Backup", emoji="💾", style=ButtonStyle.secondary, row=3)
        async def bkp_cb(i):
            await i.response.defer()
            await self.set_processing(i, "Backup") # <--- Feedback visual imediato
            try:
                b = await discloud_client.backup(self.selected_app_id) #
                url = b.url if not isinstance(b, list) else b[0].url
                await i.followup.send(f"{E_SUCCESS} 📦 [Backup Pronto]({url})", ephemeral=True)
                await self.update_dashboard(i)
            except Exception as e: await self.show_error(i, e, "Backup")
        btn_bkp.callback = bkp_cb
        self.add_item(btn_bkp)

        # 2. RAM
        btn_ram = Button(label="Mudar RAM", emoji=E_RAM, style=ButtonStyle.secondary, row=3)
        # O feedback de processamento está dentro do RamModal.on_submit
        async def ram_cb(i): await i.response.send_modal(RamModal(self.selected_app_id, self))
        btn_ram.callback = ram_cb
        self.add_item(btn_ram)
        
        # 3. DELETAR
        btn_del = Button(label="Deletar App", emoji="🗑️", style=ButtonStyle.danger, row=3)
        # O feedback de processamento está dentro do DeleteAppModal.on_submit
        async def del_cb(i): await i.response.send_modal(DeleteAppModal(self.selected_app_id, self))
        btn_del.callback = del_cb
        self.add_item(btn_del)

    def add_mods_buttons(self):
        btn_add = Button(label="Adicionar", emoji="➕", style=ButtonStyle.success, row=3)
        async def add(i): await i.response.send_modal(ModActionModal("add", self.selected_app_id, self))
        btn_add.callback = add; self.add_item(btn_add)
        btn_edit = Button(label="Editar", emoji="✏️", style=ButtonStyle.primary, row=3)
        async def edit(i): await i.response.send_modal(ModActionModal("edit", self.selected_app_id, self))
        btn_edit.callback = edit; self.add_item(btn_edit)
        btn_rem = Button(label="Deletar", emoji="🗑️", style=ButtonStyle.danger, row=3)
        async def rem(i): await i.response.send_modal(RemoveModModal(self.selected_app_id, self))
        btn_rem.callback = rem; self.add_item(btn_rem)

    def make_btn(self, lbl, emj, style, func):
        btn = Button(label=lbl, emoji=emj, style=style, row=3)
        async def cb(i):
            await i.response.defer()
            await self.set_processing(i, lbl)
            try:
                res = await func(self.selected_app_id)
                await i.followup.send(f"{E_SUCCESS} {lbl}: {res.message}", ephemeral=True)
                self.current_mode="status"
                await self.update_dashboard(i)
            except Exception as e: await self.show_error(i, e, lbl)
        btn.callback = cb
        self.add_item(btn)

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f"✅ Painel Online: {bot.user}")
    activity = discord.Game(name="Discloud Dashboard • Meu Manager!") 
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"Status definido para 'Jogando {activity.name}'")

@bot.command(name="sync")
async def sync(ctx):
    if not ctx.author.guild_permissions.administrator: return
    msg = await ctx.send("⏳ Sincronizando...")
    bot.tree.clear_commands(guild=ctx.guild)
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await msg.edit(content="✅ Painel sincronizado!")

@bot.tree.command(name="painel", description="Abre o painel de gerenciamento Discloud")
async def painel(interaction: Interaction):
    await interaction.response.defer()
    try:
        apps = await discloud_client.app_info("all") #
        apps = apps if isinstance(apps, list) else [apps] if apps else []
        view = DashboardView(apps)
        embed = await view.build_home_view(interaction.user)
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e: await interaction.followup.send(f"❌ Erro ao abrir painel: {e}")

@bot.tree.command(name="commit", description="Fazer Upload/Update do Bot (.zip)")
@app_commands.describe(app_id="ID do App", file_attachment="Arquivo .zip")
async def commit(interaction: Interaction, app_id: str, file_attachment: discord.Attachment):
    await interaction.response.defer()
    if not file_attachment.filename.endswith(".zip"): return await interaction.followup.send("❌ Deve ser .zip")
    try:
        d_file = discloud.File(io.BytesIO(await file_attachment.read()))
        d_file.filename = file_attachment.filename
        res = await discloud_client.commit(app_id, d_file) #
        await interaction.followup.send(embed=discord.Embed(title="📦 Commit OK", description=res.message, color=C_GREEN))
    except Exception as e: await interaction.followup.send(f"❌ Erro: {e}")

@bot.tree.command(name="upload", description="Subir uma NOVA aplicação para a Discloud (.zip)")
@app_commands.describe(file_attachment="Arquivo .zip da aplicação")
async def upload(interaction: Interaction, file_attachment: discord.Attachment):
    if not file_attachment.filename.endswith(".zip"):
        return await interaction.response.send_message("❌ O arquivo deve ser um .zip!", ephemeral=True)
    await interaction.response.defer()
    loading_embed = discord.Embed(
        title=f"{E_UPLOAD} Iniciando Upload...",
        description=f"Carregando `{file_attachment.filename}` para a Discloud.\nAguarde um momento...",
        color=C_GOLD
    )
    await interaction.followup.send(embed=loading_embed)
    try:
        file_bytes = io.BytesIO(await file_attachment.read())
        d_file = discloud.File(file_bytes)
        d_file.filename = file_attachment.filename
        result = await discloud_client.upload_app(file=d_file) #
        if result.status == "ok":
            success_embed = discord.Embed(
                title=f"{E_SUCCESS} Upload Concluído!",
                description=f"**Status:** {result.status}\n**Mensagem:** {result.message}\n\nUse `/painel` para gerenciar seu novo app.",
                color=C_GREEN
            )
            await interaction.edit_original_response(embed=success_embed)
        else:
            error_embed = discord.Embed(
                title=f"{E_ERROR} Falha no Upload",
                description=f"**Status:** {result.status}\n**Erro:** {result.message}",
                color=C_RED
            )
            await interaction.edit_original_response(embed=error_embed)
    except Exception as e:
        fail_embed = discord.Embed(title=f"{E_ERROR} Erro Crítico", description=f"```{str(e)}```", color=C_RED)
        await interaction.edit_original_response(embed=fail_embed)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)