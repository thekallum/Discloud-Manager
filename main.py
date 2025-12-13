import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import Button, View, Select, Modal, TextInput
import io
import os
import asyncio
import aiohttp 
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
E_CPU = "<:cpu:1446905260659445831>"
E_RAM = "<:memoriaram:1445901548638048489>"
E_SSD = "<:ssd:1446905262324846764>"
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

# --- LISTA DE PERMISSÕES VÁLIDAS DA DISCLOUD ---
VALID_PERMISSIONS = [
    discord.SelectOption(label="Iniciar App", value="start_app", description="Permite iniciar a aplicação", emoji="🟢"),
    discord.SelectOption(label="Parar App", value="stop_app", description="Permite parar a aplicação", emoji="🔴"),
    discord.SelectOption(label="Reiniciar App", value="restart_app", description="Permite reiniciar a aplicação", emoji="🔄"),
    discord.SelectOption(label="Ver Logs", value="logs_app", description="Permite ver o terminal/logs", emoji="<:terminal:1446262228121686088>"),
    discord.SelectOption(label="Ver Status", value="status_app", description="Permite ver consumo de RAM/CPU", emoji="📊"),
    discord.SelectOption(label="Fazer Commit", value="commit_app", description="Permite atualizar o bot (zip)", emoji="📦"),
    discord.SelectOption(label="Editar RAM", value="edit_ram", description="Permite alterar a quantidade de RAM", emoji=E_RAM),
    discord.SelectOption(label="Backup", value="backup_app", description="Permite baixar o backup", emoji="<:backup:1446905215050842254>"),
]

# --- HELPER: BARRA DE PROGRESSO & PARSER ---
def parse_to_mb(value_str: str) -> float:
    try:
        clean = value_str.upper().strip()
        if "GB" in clean:
            return float(clean.replace("GB", "")) * 1024
        return float(clean.replace("MB", ""))
    except Exception:
        return 0.0

def create_emoji_bar(current_str: str, total_str: str, length=10) -> str:
    current = parse_to_mb(current_str)
    total = parse_to_mb(total_str)
    percent = min(1.0, current / total) if total > 0 else 0
    filled = int(length * percent)
    return "🟩" * filled + "⬛" * (length - filled)

# --- FUNÇÃO HELPER PARA API DE PERFIL ---
async def update_app_profile(app_id: str, name: str, avatar_url: str):
    url = f"https://api.discloud.app/v2/app/{app_id}/profile"
    headers = {
        "api-token": DISCLOUD_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "avatarURL": avatar_url
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=payload) as response:
            data = await response.json()
            if response.status == 200:
                return True, data.get("message", "Perfil atualizado.")
            else:
                return False, data.get("message", "Erro desconhecido na API.")

# --- VIEWS E SELECTS ESPECÍFICOS PARA MODS ---

class PermissionSelect(Select):
    def __init__(self, current_perms: Optional[List[str]] = None):
        current_perms = current_perms or []
        options = []
        for vp in VALID_PERMISSIONS:
            is_selected = vp.value in current_perms
            options.append(discord.SelectOption(
                label=vp.label,
                value=vp.value,
                description=vp.description,
                emoji=vp.emoji,
                default=is_selected
            ))

        super().__init__(
            placeholder="Selecione as permissões...",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

class ModRightsView(View):
    def __init__(self, app_id: str, mod_id: str, mode: str, dashboard_view, current_perms: List[str] = None):
        super().__init__(timeout=300)
        self.app_id = app_id
        self.mod_id = mod_id
        self.mode = mode 
        self.dashboard_view = dashboard_view
        
        self.perm_select = PermissionSelect(current_perms)
        self.add_item(self.perm_select)

    @discord.ui.button(label="Voltar", style=ButtonStyle.secondary, emoji="⬅️", row=2)
    async def cancel(self, interaction: Interaction, button: Button):
        await self.dashboard_view.update_dashboard(interaction)

    @discord.ui.button(label="Confirmar", style=ButtonStyle.success, emoji="✅", row=2)
    async def confirm(self, interaction: Interaction, button: Button):
        if not self.perm_select.values:
            return await interaction.response.send_message("❌ Selecione pelo menos uma permissão.", ephemeral=True)
        
        await interaction.response.defer()
        mod_manager = discloud.ModManager(discloud_client, self.app_id)
        
        try:
            perms_list = self.perm_select.values
            if self.mode == "add":
                result = await mod_manager.add_mod(mod_id=self.mod_id, perms=perms_list)
                title = "Novo Moderador Adicionado"
            else:
                result = await mod_manager.edit_mod_perms(mod_id=self.mod_id, new_perms=perms_list)
                title = "Permissões Editadas"
            
            self.dashboard_view.last_notification = {
                "title": f"{E_SUCCESS} {title}",
                "description": f"{result.message}\n**Mod:** `{self.mod_id}`\n**Permissões:** {len(perms_list)} selecionadas.",
                "color": C_GREEN
            }
            await self.dashboard_view.update_dashboard(interaction)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

class ModListSelect(Select):
    def __init__(self, mods: List[AppMod], mode: str, dashboard_view, app_id: str):
        self.mode = mode 
        self.dashboard_view = dashboard_view
        self.app_id = app_id
        self.mods = mods
        
        options = []
        for mod in mods:
            perms_count = len(mod.perms) if mod.perms else 0
            options.append(discord.SelectOption(
                label=f"Mod: {mod.id}", 
                value=str(mod.id), 
                description=f"{perms_count} permissões ativas",
                emoji="👤"
            ))
            
        max_v = len(options) if mode == "remove" else 1
        placeholder_text = "Selecione os moderadores para remover..." if mode == "remove" else "Selecione um moderador..."

        super().__init__(
            placeholder=placeholder_text,
            min_values=1,
            max_values=max_v,
            options=options
        )

    async def callback(self, interaction: Interaction):
        if self.mode == "remove":
            await interaction.response.defer()
            return

        if self.mode == "edit":
            mod_id = self.values[0]
            selected_mod = next((m for m in self.mods if str(m.id) == mod_id), None)
            current_perms = selected_mod.perms if selected_mod else []

            embed = discord.Embed(
                title=f"🛠️ Editando: {mod_id}",
                description="As permissões atuais já estão marcadas.\nModifique conforme necessário e clique em Confirmar.",
                color=C_BLUE
            )
            await interaction.response.edit_message(
                embed=embed,
                view=ModRightsView(self.app_id, mod_id, "edit", self.dashboard_view, current_perms=current_perms)
            )

class ModSelectionView(View):
    def __init__(self, mods, mode, dashboard_view, app_id):
        super().__init__(timeout=300)
        self.dashboard_view = dashboard_view
        self.mode = mode
        self.app_id = app_id
        
        self.select_menu = ModListSelect(mods, mode, dashboard_view, app_id)
        self.add_item(self.select_menu)
        
        btn_back = Button(label="Voltar", style=ButtonStyle.secondary, emoji="⬅️", row=2)
        btn_back.callback = self.cancel
        self.add_item(btn_back)

        if mode == "remove":
            btn_confirm = Button(label="Confirmar Exclusão", style=ButtonStyle.danger, emoji="🗑️", row=2)
            btn_confirm.callback = self.confirm_delete
            self.add_item(btn_confirm)

    async def cancel(self, interaction: Interaction):
        await self.dashboard_view.update_dashboard(interaction)

    async def confirm_delete(self, interaction: Interaction):
        selected_ids = self.select_menu.values
        if not selected_ids:
            return await interaction.response.send_message("❌ Selecione pelo menos um moderador na lista acima.", ephemeral=True)
        
        await self.dashboard_view.set_processing(interaction, f"Removendo {len(selected_ids)} moderadores")
        
        mod_manager = discloud.ModManager(discloud_client, self.app_id)
        results = []
        errors = 0
        
        for mod_id in selected_ids:
            try:
                res = await mod_manager.delete_mod(mod_id)
                results.append(f"✅ `{mod_id}`: Removido")
            except Exception as e:
                errors += 1
                results.append(f"❌ `{mod_id}`: {str(e)}")
        
        report = "\n".join(results)
        if len(report) > 1000: report = report[:1000] + "\n...(mais)"
        
        color = C_GREEN if errors == 0 else C_GOLD
        title = "🗑️ Relatório de Remoção"
        
        self.dashboard_view.last_notification = {
            "title": title,
            "description": report,
            "color": color
        }
        
        await self.dashboard_view.update_dashboard(interaction, silent_update=True)

# --- MODAIS GERAIS (TOOLS) ---

class ChangeNameModal(Modal, title="Alterar Nome da App"):
    new_name = TextInput(label="Novo Nome", placeholder="Digite o novo nome...", min_length=2, max_length=30, required=True)

    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent

    async def on_submit(self, interaction: Interaction):
        await self.view_parent.set_processing(interaction, f"Atualizando Perfil...")
        
        try:
            app = await discloud_client.app_info(self.app_id)
            current_avatar = app.avatarURL
            
            success, msg = await update_app_profile(self.app_id, self.new_name.value, current_avatar)
            
            if success:
                if self.app_id in self.view_parent.apps_info_map:
                    self.view_parent.apps_info_map[self.app_id].name = self.new_name.value
                
                # --- EMBED PADRONIZADO ---
                embed = discord.Embed(
                    title=f"{E_SUCCESS} Nome Alterado!",
                    description=f"O nome da aplicação foi atualizado para **{self.new_name.value}**.",
                    color=C_GREEN
                )
                embed.add_field(name="📝 Detalhes da API", value=f"```diff\n+ {msg}\n```", inline=False)
                embed.set_footer(text="Discloud Manager • Perfil atualizado", icon_url=interaction.client.user.display_avatar.url)
                embed.timestamp = datetime.now()
            else:
                embed = discord.Embed(title=f"{E_ERROR} Erro", description=f"Falha ao alterar nome: {msg}", color=C_RED)

            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro Crítico: {e}", ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)

class ChangeAvatarModal(Modal, title="Alterar Avatar da App"):
    avatar_url = TextInput(label="URL da Nova Imagem", placeholder="https://i.imgur.com/...", required=True)

    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent

    async def on_submit(self, interaction: Interaction):
        await self.view_parent.set_processing(interaction, f"Atualizando Avatar...")
        
        try:
            app = await discloud_client.app_info(self.app_id)
            current_name = app.name
            
            success, msg = await update_app_profile(self.app_id, current_name, self.avatar_url.value)
            
            if success:
                if self.app_id in self.view_parent.apps_info_map:
                    self.view_parent.apps_info_map[self.app_id].avatarURL = self.avatar_url.value

                # --- EMBED PADRONIZADO ---
                embed = discord.Embed(
                    title=f"{E_SUCCESS} Avatar Alterado!",
                    description=f"O avatar da aplicação foi atualizado com sucesso.",
                    color=C_GREEN
                )
                embed.set_thumbnail(url=self.avatar_url.value)
                embed.add_field(name="📝 Detalhes da API", value=f"```diff\n+ {msg}\n```", inline=False)
                embed.set_footer(text="Discloud Manager • Perfil atualizado", icon_url=interaction.client.user.display_avatar.url)
                embed.timestamp = datetime.now()
            else:
                embed = discord.Embed(title=f"{E_ERROR} Erro", description=f"Falha ao alterar avatar: {msg}", color=C_RED)

            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro Crítico: {e}", ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)

class AddModIdModal(Modal, title="Adicionar Moderador"):
    mod_id = TextInput(label="Discord ID do Usuário", min_length=15, max_length=20, required=True, placeholder="Ex: 123456789...")

    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent

    async def on_submit(self, interaction: Interaction):
        embed = discord.Embed(
            title=f"👤 Novo Mod: {self.mod_id.value}",
            description="Selecione as permissões iniciais e clique em Confirmar.",
            color=C_GREEN
        )
        await interaction.response.edit_message(
            embed=embed,
            view=ModRightsView(self.app_id, self.mod_id.value, "add", self.view_parent)
        )

class RamModal(Modal, title="Alterar Memória RAM"):
    ram_input = TextInput(label="Nova Quantidade (MB)", placeholder="Ex: 512, 1024...", min_length=2, max_length=5, required=True)
    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent

    async def on_submit(self, interaction: Interaction):
        try:
            amount = int(self.ram_input.value)
        except ValueError:
            return await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)

        await self.view_parent.set_processing(interaction, f"Alterando RAM para {amount}MB")
        
        try:
            result = await discloud_client.ram(app_id=self.app_id, new_ram=amount)
            start_msg = "A aplicação permaneceu desligada."
            
            if result.status == "ok":
                try:
                    await asyncio.sleep(2) 
                    await discloud_client.start(self.app_id)
                    start_msg = "Reiniciando aplicação automaticamente..."
                except: pass

            is_success = result.status == "ok"
            api_msg = result.message.replace('ramMB', 'RAM')
            
            # --- EMBED PADRONIZADO ---
            if is_success:
                embed = discord.Embed(
                    title=f"{E_SUCCESS} RAM Alterada!",
                    description=f"A quantidade de memória foi ajustada para **{amount}MB**.",
                    color=C_GREEN
                )
                # Garante que a mensagem tenha o "+" para ficar verde no diff
                clean_msg = api_msg if api_msg.startswith("+") else f"+ {api_msg}"
                
                embed.add_field(name="📝 Detalhes da API", value=f"```diff\n{clean_msg}\n```", inline=False)
                
                if "Reiniciando" in start_msg:
                    embed.add_field(name="🚀 Ação Adicional", value="O sistema tentou reiniciar a aplicação automaticamente.", inline=False)

                embed.set_footer(text="Discloud Manager • Configuração atualizada", icon_url=interaction.client.user.display_avatar.url)
                embed.timestamp = datetime.now()
            else:
                embed = discord.Embed(title=f"{E_ERROR} Erro ao alterar RAM", description=api_msg, color=C_RED)

            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)
            
        except Exception as e:
             await interaction.followup.send(f"❌ Erro ao alterar RAM: {e}", ephemeral=True)
             await self.view_parent.update_dashboard(interaction, silent_update=True)

class DeleteAppModal(Modal, title="DELETAR APLICAÇÃO"):
    confirm_input = TextInput(
        label="Carregando...", 
        placeholder="Digite o ID da aplicação aqui...", 
        style=discord.TextStyle.short, 
        required=True
    )

    def __init__(self, app_id: str, view_parent):
        super().__init__()
        self.app_id = app_id
        self.view_parent = view_parent
        
        self.confirm_input.label = f'Para confirmar, digite: {app_id}'
        if len(self.confirm_input.label) > 45:
            self.confirm_input.label = f"Digite: {app_id}"[:45]

    async def on_submit(self, interaction: Interaction):
        if self.confirm_input.value != self.app_id:
            return await interaction.response.send_message(
                f"❌ **Confirmação Incorreta.**\nVocê digitou `{self.confirm_input.value}`\nO ID correto é `{self.app_id}`.", 
                ephemeral=True
            )
        
        await self.view_parent.set_processing(interaction, f"Deletando App: {self.app_id}")
        
        try:
            url = f"https://api.discloud.app/v2/app/{self.app_id}/delete"
            headers = {
                "api-token": DISCLOUD_TOKEN,
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers) as response:
                    try:
                        data = await response.json()
                    except:
                        data = {}
                    
                    if response.status == 200 or data.get("status") == "ok":
                        msg = data.get("message", "Aplicação deletada com sucesso.")
                        
                        embed = discord.Embed(
                            title=f"{E_SUCCESS} Aplicação Deletada!",
                            description=f"A aplicação **{self.app_id}** foi removida permanentemente.",
                            color=C_GREEN # Verde conforme o check
                        )
                        embed.add_field(name="📝 Detalhes da API", value=f"```diff\n- {msg}\n```")
                        embed.set_footer(text="Discloud Manager • App removido", icon_url=interaction.client.user.display_avatar.url)
                        embed.timestamp = datetime.now()
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
                        self.view_parent.selected_app_id = None
                        self.view_parent.current_mode = "home"
                        await self.view_parent.update_dashboard(interaction, silent_update=True)
                        
                    else:
                        error_msg = data.get("message", await response.text())
                        raise Exception(f"API Error {response.status}: {error_msg}")

        except Exception as e:
            embed = discord.Embed(
                title=f"{E_ERROR} Falha ao Deletar",
                description=f"Não foi possível deletar a aplicação **{self.app_id}**.",
                color=C_RED
            )
            embed.add_field(name="Erro Técnico", value=f"```\n{str(e)}\n```")
            await interaction.followup.send(embed=embed, ephemeral=True)
            await self.view_parent.update_dashboard(interaction, silent_update=True)

# --- UI COMPONENTES ---

class AppSelect(Select):
    def __init__(self, apps: List[ApplicationInfo], selected_id: str = None):
        options = []
        for app in apps[:25]: 
            emoji = E_ONLINE if app.online else E_OFFLINE
            label = app.name
            desc = f"ID: {app.id} | {app.lang}"
            is_selected = str(app.id) == str(selected_id)
            options.append(discord.SelectOption(
                label=label, 
                value=str(app.id), 
                description=desc, 
                emoji=emoji,
                default=is_selected
            ))
            
        if not options:
            options.append(discord.SelectOption(label="Nenhuma aplicação encontrada", value="none", description="Use /upload para começar", emoji="📂"))

        super().__init__(placeholder="📂 Selecione uma aplicação ...", min_values=1, max_values=1, row=0, options=options)

    async def callback(self, interaction: Interaction):
        if self.values[0] == "none":
            return await interaction.response.defer()
            
        self.view.selected_app_id = self.values[0]
        self.view.current_mode = "status"
        await self.view.update_dashboard(interaction)

class DashboardView(View):
    def __init__(self, apps_info: List[ApplicationInfo]):
        super().__init__(timeout=600)
        self.apps_info_map = {app.id: app for app in apps_info}
        self.selected_app_id = None
        self.current_mode = "home"
        self.last_notification: Optional[Dict] = None 
        
        if apps_info: 
            self.add_item(AppSelect(apps_info))
        self.create_nav_buttons()

    @property
    def current_app_name(self):
        if self.selected_app_id and self.selected_app_id in self.apps_info_map:
            return self.apps_info_map[self.selected_app_id].name
        return "Desconhecido"

    def create_nav_buttons(self):
        self.add_item(Button(label="Início", emoji=E_HOME, style=ButtonStyle.secondary, custom_id="mode_home", row=1))
        self.add_item(Button(label="Status", emoji="📊", style=ButtonStyle.primary, custom_id="mode_status", row=1))
        self.add_item(Button(label="Controle", emoji="<:controle:1446905259191570464>", style=ButtonStyle.secondary, custom_id="mode_control", row=1))
        self.add_item(Button(label="Logs", emoji="<:terminal:1446262228121686088>", style=ButtonStyle.secondary, custom_id="mode_logs", row=1))
        self.add_item(Button(label="Tools", emoji="<:tools:1446905257417248818>", style=ButtonStyle.secondary, custom_id="mode_tools", row=2))
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
        for item in self.children: item.disabled = True
        embed = discord.Embed(
            title=f"{E_LOADING} Processando: {action_name}...", 
            description="Aguarde enquanto a Discloud processa sua solicitação...", 
            color=C_GOLD
        )
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except: pass

    async def show_error(self, interaction, error, action_name):
        for item in self.children: item.disabled = False
        embed = discord.Embed(title=f"{E_ERROR} Erro: {action_name}", description=f"```{error}```", color=C_RED)
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)
        except: pass

    async def update_dashboard(self, interaction: Interaction, silent_update: bool = False):
        try:
            try:
                apps = await discloud_client.app_info("all")
                apps = apps if isinstance(apps, list) else [apps] if apps else []
                self.apps_info_map = {app.id: app for app in apps}
            except Exception as e:
                print(f"Erro ao atualizar lista de apps: {e}")
                apps = list(self.apps_info_map.values())

            if self.selected_app_id and self.selected_app_id not in self.apps_info_map:
                self.selected_app_id = None
                self.current_mode = "home"
                if self.last_notification is None:
                    self.last_notification = {"title": "⚠️ Aviso", "description": "A aplicação selecionada não existe mais.", "color": C_GOLD}

            self.clear_items()
            self.add_item(AppSelect(apps, self.selected_app_id))
            self.create_nav_buttons()

            for item in self.children:
                item.disabled = False
                if isinstance(item, Button) and getattr(item, 'custom_id', '').startswith("mode_"):
                    if self.current_mode == "home":
                        if item.custom_id != "mode_home":
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

            embed = None
            if self.current_mode == "home" or self.selected_app_id is None:
                embed = await self.build_home_view(interaction.user)
            elif self.current_mode == "status":
                embed = await self.build_status_view()
                btn_ref = Button(label="Atualizar", emoji="🔄", style=ButtonStyle.gray, row=3)
                btn_ref.callback = self.refresh_click
                self.add_item(btn_ref)
            elif self.current_mode == "control":
                embed = discord.Embed(title=f"<:controle:1446905259191570464> Controle: {self.current_app_name}", color=C_GOLD, description="Gerencie a sua aplicação.")
                self.add_control_buttons()
            elif self.current_mode == "logs":
                embed = await self.build_logs_view()
                btn_ref = Button(label="Atualizar Logs", emoji="🔄", style=ButtonStyle.primary, row=3)
                btn_ref.callback = self.refresh_click
                self.add_item(btn_ref)
            elif self.current_mode == "tools":
                embed = await self.build_tools_view()
                self.add_tools_buttons()
            elif self.current_mode == "mods":
                embed = await self.build_mods_view()
                await self.add_mods_buttons(interaction)

            if self.last_notification:
                embed.insert_field_at(0, 
                    name=self.last_notification['title'], 
                    value=self.last_notification['description'], 
                    inline=False
                )
                embed.color = self.last_notification.get('color', embed.color)
                self.last_notification = None

            if silent_update:
                if interaction.message:
                    await interaction.message.edit(embed=embed, view=self)
                else:
                    await interaction.edit_original_response(embed=embed, view=self)
            elif interaction.response.is_done():
                try:
                    await interaction.edit_original_response(embed=embed, view=self)
                except discord.NotFound:
                    if interaction.message: await interaction.message.edit(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
                
        except Exception as e: 
            if not silent_update:
                await self.show_error(interaction, e, "Carregar Painel")
            else:
                print(f"Erro update silencioso: {e}")

    async def refresh_click(self, interaction: Interaction):
        await self.update_dashboard(interaction)

    def clear_dynamic_buttons(self):
        pass 
    
    async def build_home_view(self, user_discord):
        user = await discloud_client.user_info()
        apps = list(self.apps_info_map.values())
        
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
        
        app_list_lines = [f"• **{app.name}** (`{app.id}`)" for app in apps]
        if not app_list_lines:
            embed.add_field(name="📂 Minhas aplicações", value="Nenhuma aplicação encontrada.", inline=False)
        else:
            current_chunk = ""
            field_idx = 1
            for line in app_list_lines:
                if len(current_chunk) + len(line) + 2 >= 1000:
                    name = f"📂 Minhas aplicações" if field_idx == 1 else f"📂 Aplicações ({field_idx})"
                    embed.add_field(name=name, value=current_chunk, inline=False)
                    current_chunk = ""
                    field_idx += 1
                current_chunk += line + "\n"
            if current_chunk:
                name = "📂 Minhas aplicações" if field_idx == 1 else f"📂 Aplicações ({field_idx})"
                embed.add_field(name=name, value=current_chunk, inline=False)

        embed.set_footer(text="Selecione uma aplicação no menu abaixo.", icon_url=bot.user.display_avatar.url)
        return embed

    async def build_status_view(self):
        status = await discloud_client.app_status(target=self.selected_app_id)
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

        uptime = "🔴 Desligado"
        if status.status == "Online":
            if hasattr(status, 'start_date') and hasattr(status.start_date, 'date'):
                try:
                    ts = int(status.start_date.date.timestamp())
                    uptime = f"<t:{ts}:R>"
                except: uptime = str(status.online_since)
            else: uptime = str(status.online_since)
                 
        embed.add_field(name="🕒 Uptime", value=f"{uptime}", inline=True)
        git_msg = "Desativado ❌"
        if info and info.autoDeployGit and info.autoDeployGit.lower() != "no": git_msg = "Ativo ✅"
        embed.add_field(name="<:git:1445928668055474187> Integração Git", value=git_msg, inline=True)
        restart_msg = "Desativado ❌"
        if info and info.autoRestart: restart_msg = "Ativo ✅"
        embed.add_field(name="🔄 Auto Restart", value=restart_msg, inline=True)
        if info and info.ramKilled:
             embed.add_field(name=f"{E_WARN} Alerta Crítico", value="O bot foi reiniciado por falta de RAM.", inline=False)
        embed.set_footer(text="Discloud Manager", icon_url=bot.user.display_avatar.url)
        return embed

    async def build_tools_view(self):
        embed = discord.Embed(title=f"<:tools:1446905257417248818> Caixa de Ferramentas: {self.current_app_name}", color=C_BLUE)
        embed.description = "Utilitários avançados para manutenção."
        embed.add_field(name="<:backup:1446905215050842254> Backup", value="Baixar código-fonte.", inline=True)
        embed.add_field(name="<:memoriaram:1445901548638048489> RAM", value="Alterar memória RAM.", inline=True)
        embed.add_field(name="📦 Update", value="Use `/commit`.", inline=True)
        return embed

    async def build_logs_view(self):
        logs = await discloud_client.logs(target=self.selected_app_id)
        content = logs.small[:1000]
        embed = discord.Embed(title=f"<:terminal:1446262228121686088> Terminal: {self.current_app_name}", color=C_DARK, description=f"```bash\n{content}\n```")
        if len(content) >= 1000: embed.description += "\n*(Logs cortados)*"
        full_log_url = logs.url if logs.url else "https://discloudbot.com/dashboard"
        embed.add_field(name="🔗 Completo", value=f"[Ver logs completos no navegador]({full_log_url})")
        return embed

    async def build_mods_view(self):
        mods = await discloud.ModManager(discloud_client, self.selected_app_id).get_mods()
        mods = mods if isinstance(mods, list) else [mods] if mods else []
        self._current_mods_cache = mods 
        embed = discord.Embed(title=f"{E_MODS} Equipe: {self.current_app_name}", color=C_PURPLE)
        if not mods: embed.description = "Nenhum moderador extra configurado."
        for mod in mods:
            perms = ", ".join(mod.perms) if mod.perms else "Sem permissões"
            embed.add_field(name=f"👤 {mod.id}", value=f"Perms: `{perms}`", inline=False)
        return embed

    def add_control_buttons(self):
        self.make_btn("Iniciar", E_ONLINE, ButtonStyle.success, discloud_client.start)
        self.make_btn("Reiniciar", "🔄", ButtonStyle.primary, discloud_client.restart)
        self.make_btn("Parar", E_OFFLINE, ButtonStyle.danger, discloud_client.stop)
    
    def add_tools_buttons(self):
        # Backup 
        btn_bkp = Button(label="Baixar Backup", emoji="<:backup:1446905215050842254>", style=ButtonStyle.secondary, row=3)
        async def bkp_cb(i):
            await self.set_processing(i, "Gerando Backup")
            try:
                b = await discloud_client.backup(self.selected_app_id)
                url = b.url if not isinstance(b, list) else b[0].url
                link_button = Button(label="Baixar Backup", style=ButtonStyle.link, url=url, emoji="<:backup:1446905215050842254>")
                link_view = View()
                link_view.add_item(link_button)
                
                embed = discord.Embed(title=f"{E_SUCCESS} Backup Gerado!", description="Clique no botão abaixo para baixar.", color=C_GREEN)
                embed.set_footer(text="Discloud Manager", icon_url=i.client.user.display_avatar.url)
                embed.timestamp = datetime.now()
                
                await i.followup.send(embed=embed, view=link_view, ephemeral=True)
            except Exception as e: 
                await i.followup.send(f"❌ Erro: {e}", ephemeral=True)
            await self.update_dashboard(i, silent_update=True)
        btn_bkp.callback = bkp_cb
        self.add_item(btn_bkp)

        # RAM
        btn_ram = Button(label="Mudar RAM", emoji=E_RAM, style=ButtonStyle.secondary, row=3)
        async def ram_cb(i): await i.response.send_modal(RamModal(self.selected_app_id, self))
        btn_ram.callback = ram_cb
        self.add_item(btn_ram)
        
        # Nome
        btn_name = Button(label="Mudar Nome", emoji="✏️", style=ButtonStyle.secondary, row=3)
        async def name_cb(i): await i.response.send_modal(ChangeNameModal(self.selected_app_id, self))
        btn_name.callback = name_cb
        self.add_item(btn_name)

        # Avatar
        btn_avatar = Button(label="Mudar Avatar", emoji="🖼️", style=ButtonStyle.secondary, row=3)
        async def avatar_cb(i): await i.response.send_modal(ChangeAvatarModal(self.selected_app_id, self))
        btn_avatar.callback = avatar_cb
        self.add_item(btn_avatar)
        
        # Deletar
        btn_del = Button(label="Deletar App", emoji="🗑️", style=ButtonStyle.danger, row=3)
        async def del_cb(i): await i.response.send_modal(DeleteAppModal(self.selected_app_id, self))
        btn_del.callback = del_cb
        self.add_item(btn_del)

    async def add_mods_buttons(self, interaction):
        btn_add = Button(label="Adicionar", emoji="➕", style=ButtonStyle.success, row=3)
        async def add(i): await i.response.send_modal(AddModIdModal(self.selected_app_id, self))
        btn_add.callback = add
        self.add_item(btn_add)

        btn_edit = Button(label="Editar", emoji="✏️", style=ButtonStyle.primary, row=3)
        async def edit(i):
            if not getattr(self, '_current_mods_cache', []): return await i.response.send_message("❌ Sem mods.", ephemeral=True)
            embed = discord.Embed(title="✏️ Editar Moderador", description="Selecione abaixo:", color=C_BLUE)
            await i.response.edit_message(embed=embed, view=ModSelectionView(self._current_mods_cache, "edit", self, self.selected_app_id))
        btn_edit.callback = edit
        self.add_item(btn_edit)

        btn_rem = Button(label="Remover", emoji="🗑️", style=ButtonStyle.danger, row=3)
        async def rem(i):
            if not getattr(self, '_current_mods_cache', []): return await i.response.send_message("❌ Sem mods.", ephemeral=True)
            embed = discord.Embed(title="🗑️ Remover Moderador", description="Selecione abaixo:", color=C_RED)
            await i.response.edit_message(embed=embed, view=ModSelectionView(self._current_mods_cache, "remove", self, self.selected_app_id))
        btn_rem.callback = rem
        self.add_item(btn_rem)

    def make_btn(self, lbl, emj, style, func):
        btn = Button(label=lbl, emoji=emj, style=style, row=3)
        async def cb(i):
            await self.set_processing(i, lbl)
            try:
                res = await func(self.selected_app_id)
                
                # --- EMBED PADRONIZADO (Sucesso) ---
                action_map = {"Iniciar": "Iniciada", "Parar": "Parada", "Reiniciar": "Reiniciada"}
                past_tense = action_map.get(lbl, lbl + "do")
                
                embed = discord.Embed(
                    title=f"{E_SUCCESS} Aplicação {past_tense}!", 
                    description=f"O comando de **{lbl.lower()}** foi enviado com sucesso para a Discloud.",
                    color=C_GREEN
                )
                
                # Garante que a mensagem tenha o "+" para ficar verde no diff
                clean_msg = res.message if res.message.startswith("+") else f"+ {res.message}"
                
                embed.add_field(name="📝 Detalhes da API", value=f"```diff\n{clean_msg}\n```", inline=False)
                embed.set_footer(text=f"Discloud Manager • {lbl}", icon_url=i.client.user.display_avatar.url)
                embed.timestamp = datetime.now()

                await i.followup.send(embed=embed, ephemeral=True)
                
                self.current_mode="status"
                await self.update_dashboard(i, silent_update=True)
                
            except Exception as e:
                err_msg = str(e).lower()
                if any(x in err_msg for x in ["já está", "ja esta", "already"]):
                    friendly_text = "⚠️ O estado já corresponde ao solicitado."
                    if any(x in err_msg for x in ["desligado", "offline", "stop", "parado"]): friendly_text = "⚠️ A aplicação já está desligada."
                    elif any(x in err_msg for x in ["ligado", "online", "start", "rodando"]): friendly_text = "⚠️ A aplicação já está ligada."
                    
                    await i.followup.send(friendly_text, ephemeral=True)
                    await self.update_dashboard(i, silent_update=True)
                else:
                    await self.show_error(i, e, lbl)
        btn.callback = cb
        self.add_item(btn)

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f"✅ Painel Online: {bot.user}")
    activity = discord.Game(name="Discloud Dashboard • Meu Manager!") 
    await bot.change_presence(status=discord.Status.online, activity=activity)

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
        apps = await discloud_client.app_info("all")
        apps = apps if isinstance(apps, list) else [apps] if apps else []
        view = DashboardView(apps)
        embed = await view.build_home_view(interaction.user)
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e: await interaction.followup.send(f"❌ Erro ao abrir painel: {e}")

@bot.tree.command(name="commit", description="Fazer Upload/Update do Bot (.zip)")
@app_commands.describe(app_id="ID do App", file_attachment="Arquivo .zip")
async def commit(interaction: Interaction, app_id: str, file_attachment: discord.Attachment):
    if not file_attachment.filename.endswith(".zip"):
        return await interaction.response.send_message("❌ **Erro de Formato:** O arquivo precisa terminar em `.zip`.", ephemeral=True)

    await interaction.response.defer()

    loading_embed = discord.Embed(
        title=f"📦 Preparando Commit",
        description=f"Iniciando o envio dos arquivos para a Discloud...",
        color=C_GOLD
    )
    loading_embed.add_field(name="📂 Arquivo", value=f"`{file_attachment.filename}`", inline=True)
    loading_embed.add_field(name="🆔 Aplicação", value=f"`{app_id}`", inline=True)
    loading_embed.set_footer(text="Aguarde, processando upload...", icon_url="https://cdn.discordapp.com/emojis/1136665045474320455.gif")
    
    await interaction.followup.send(embed=loading_embed)

    try:
        file_bytes = io.BytesIO(await file_attachment.read())
        d_file = discloud.File(file_bytes)
        d_file.filename = file_attachment.filename

        res = await discloud_client.commit(app_id, d_file)

        if res.status == "ok":
            success_embed = discord.Embed(
                title=f"{E_SUCCESS} Atualização Concluída!",
                description=f"Os arquivos da aplicação **{app_id}** foram atualizados com sucesso na nuvem.",
                color=C_GREEN
            )
            msg_formatada = res.message
            if "The files of your app have been updated" in res.message:
                 msg_formatada = "Os arquivos foram sincronizados e o deploy iniciado."
            
            # --- PADRÃO DIFF ---
            success_embed.add_field(name="📝 Detalhes da API", value=f"```diff\n+ {msg_formatada}\n```", inline=False)
            success_embed.set_footer(text="Discloud Manager • Deploy realizado", icon_url=interaction.client.user.display_avatar.url)
            success_embed.timestamp = datetime.now()

            await interaction.edit_original_response(embed=success_embed)
        else:
            error_embed = discord.Embed(
                title=f"{E_ERROR} Falha na Atualização",
                description="Houve um problema ao processar seu commit na Discloud.",
                color=C_RED
            )
            error_embed.add_field(name="🔍 Detalhes do Erro", value=f"```yaml\n{res.message}\n```", inline=False)
            error_embed.set_footer(text="Verifique o ID da aplicação e o arquivo ZIP.")
            
            await interaction.edit_original_response(embed=error_embed)

    except Exception as e:
        fail_embed = discord.Embed(
            title=f"{E_WARN} Erro Interno",
            description="Não foi possível completar a solicitação devido a um erro no bot.",
            color=C_RED
        )
        fail_embed.add_field(name="🛑 Log de Erro", value=f"```python\n{str(e)}\n```", inline=False)
        await interaction.edit_original_response(embed=fail_embed)

@bot.tree.command(name="upload", description="Subir uma NOVA aplicação para a Discloud (.zip)")
@app_commands.describe(file_attachment="Arquivo .zip da aplicação")
async def upload(interaction: Interaction, file_attachment: discord.Attachment):
    if not file_attachment.filename.endswith(".zip"):
        return await interaction.response.send_message("❌ **Erro de Formato:** O arquivo precisa terminar em `.zip`.", ephemeral=True)

    await interaction.response.defer()

    loading_embed = discord.Embed(
        title=f"{E_UPLOAD} Iniciando Upload",
        description=f"Preparando o ambiente para hospedar sua nova aplicação...",
        color=C_GOLD
    )
    loading_embed.add_field(name="📂 Arquivo", value=f"`{file_attachment.filename}`", inline=True)
    loading_embed.set_footer(text="Enviando para a Discloud... Aguarde.", icon_url="https://cdn.discordapp.com/emojis/1136665045474320455.gif")
    
    await interaction.followup.send(embed=loading_embed)

    try:
        file_bytes = io.BytesIO(await file_attachment.read())
        d_file = discloud.File(file_bytes)
        d_file.filename = file_attachment.filename

        result = await discloud_client.upload_app(file=d_file)

        if result.status == "ok":
            success_embed = discord.Embed(
                title=f"{E_SUCCESS} Upload Realizado!",
                description=f"Sua aplicação foi enviada e está sendo processada pela Discloud.",
                color=C_GREEN
            )
            
            msg_content = result.message
            
            # --- PADRÃO DIFF ---
            success_embed.add_field(name="📝 Detalhes da API", value=f"```diff\n+ {msg_content}\n```", inline=False)
            success_embed.add_field(name="🚀 Próximos Passos", value="Use o comando `/painel` para gerenciar, iniciar e ver os logs da sua nova aplicação.", inline=False)
            
            success_embed.set_footer(text="Discloud Manager • Hospedagem iniciada", icon_url=interaction.client.user.display_avatar.url)
            success_embed.timestamp = datetime.now()

            await interaction.edit_original_response(embed=success_embed)
        else:
            error_embed = discord.Embed(
                title=f"{E_ERROR} Falha no Upload",
                description="A Discloud recusou o arquivo ou houve um erro de validação.",
                color=C_RED
            )
            error_embed.add_field(name="🔍 Motivo", value=f"```yaml\n{result.message}\n```", inline=False)
            error_embed.set_footer(text="Verifique se o arquivo contém o discloud.config correto.")
            
            await interaction.edit_original_response(embed=error_embed)

    except Exception as e:
        fail_embed = discord.Embed(
            title=f"{E_WARN} Erro Interno",
            description="Ocorreu um erro inesperado ao tentar enviar o arquivo.",
            color=C_RED
        )
        fail_embed.add_field(name="🛑 Log de Erro", value=f"```python\n{str(e)}\n```", inline=False)
        await interaction.edit_original_response(embed=fail_embed)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)