<div align="center">
<img src="https://i.imgur.com/ITwQN6H.png" width="300"></a>

# 🤖 Discloud Manager

![Status](https://img.shields.io/badge/Status-COMPLETO-green?logo=github&style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white&style=for-the-badge)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-5865F2?logo=discord&logoColor=white&style=for-the-badge)
![License: MIT](https://img.shields.io/badge/License-MIT-white?logo=opensourceinitiative&logoColor=white&style=for-the-badge)

**Gerencie suas aplicações Discloud direto do Discord.**
<br>
Um bot completo com painel interativo para controlar, monitorar e fazer deploy de suas aplicações hospedadas na Discloud.

[Reportar Bug](https://github.com/thekallum/discloud-dashboard/issues) • [Solicitar Feature](https://github.com/thekallum/discloud-dashboard/issues)

</div>

---

## 📸 Sobre o Projeto

O **Discloud Manager** é uma solução completa para gerenciar suas aplicações hospedadas na Discloud diretamente através do Discord. Com uma interface intuitiva baseada em menus e botões, você pode controlar as suas aplicações, visualizar logs em tempo real, gerenciar moderadores e muito mais.

### Principais Funcionalidades
* **🎮 Painel de Controle Completo:** Interface interativa com botões para iniciar, parar e reiniciar aplicações.
* **📊 Monitoramento em Tempo Real:** Visualize CPU, RAM, rede, SSD e uptime das suas aplicações.
* **📜 Logs Dinâmicos:** Acesse os logs do terminal diretamente no Discord com atualização em tempo real.
* **🛠️ Ferramentas Avançadas:** Backup de código-fonte, alteração de RAM e upload de atualizações.
* **🛡️ Gerenciamento de Moderadores:** Adicione, edite e remova moderadores com controle de permissões.
* **📦 Deploy Rápido:** Faça upload de novas aplicações ou atualize existentes com arquivos .zip.
* **🎨 Interface Moderna:** Design limpo com emojis customizados e barras de progresso visuais.

---

## 🛠️ Tecnologias Utilizadas

Este projeto foi desenvolvido utilizando as seguintes tecnologias:

* **Linguagem:** [Python 3.10+](https://www.python.org/)
* **Framework:** [Discord.py 2.0+](https://discordpy.readthedocs.io/)
* **API:** [Discloud Python](https://github.com/discloud/python-discloud-status)
* **Hospedagem:** Compatível com Discloud, Render, Railway, etc.

---

## 💻 Pré-requisitos

Antes de começar, certifique-se de ter na sua máquina:
* [Git](https://git-scm.com)
* [Python 3.10+](https://www.python.org/downloads/)
* Uma conta na [Discord Developer Portal](https://discord.com/developers/applications)
* Uma conta na [Discloud](https://discloud.com) com API Token

---

## 🚀 Como Rodar o Projeto Localmente

Siga este passo a passo para configurar uma cópia do projeto no seu computador.

### 1. Clone o repositório
```bash
git clone https://github.com/thekallum/discloud-dashboard.git
cd discloud-dashboard
```

### 2. Crie um Ambiente Virtual

Isso isola as dependências do projeto do seu sistema principal.

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

### 4. Configuração de Variáveis de Ambiente (.env)

O bot precisa de tokens para funcionar corretamente.

1. Crie um arquivo chamado `.env` na raiz do projeto.

2. Copie o conteúdo abaixo e ajuste os valores:
```env
# Token do Bot Discord
DISCORD_TOKEN=seu_token_do_bot_discord_aqui

# Token da API Discloud
DISCLOUD_TOKEN=seu_token_da_api_discloud_aqui
```

> [!CAUTION]
> O arquivo **`.env`** contém dados extremamente sensíveis (tokens de autenticação).
>
> **NUNCA** faça *commit* ou exponha este arquivo publicamente em locais como GitHub, GitLab ou quaisquer repositórios abertos. O `.env` já está listado no `.gitignore` para ajudar a prevenir isso, mas **verifique sempre** antes de enviar suas alterações. O vazamento dessas informações pode comprometer a segurança do seu bot e das suas aplicações.

#### Como Obter os Tokens

**Discord Token:**
1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie uma nova aplicação ou selecione uma existente
3. Vá em "Bot" no menu lateral
4. Copie o Token (clique em "Reset Token" se necessário)
5. Ative as **Privileged Gateway Intents**: `MESSAGE CONTENT INTENT`

**Discloud Token:**
1. Acesse seu [Painel Discloud](https://discloud.com/dashboard)
2. Vá em API Key
3. Copie sua chave de API

### 5. Execute o Bot
```bash
python main.py
```

Você verá a mensagem: `✅ Painel Online: NomeDoBot`

---

## 📋 Comandos Disponíveis

### Comandos Slash (/)

| Comando | Descrição | Uso |
|---------|-----------|-----|
| `/painel` | Abre o painel principal de gerenciamento | Acesso completo às suas aplicações |
| `/commit` | Atualiza uma aplicação existente | `/commit app_id:<ID> file_attachment:<arquivo.zip>` |
| `/upload` | Faz upload de uma nova aplicação | `/upload file_attachment:<arquivo.zip>` |

## 🎮 Como Usar o Painel

### 1. Abrir o Painel
Digite `/painel` no Discord. Você verá a tela inicial com suas informações:
- 🆔 ID do usuário Discloud
- 💎 Plano atual
- 🗓️ Validade do plano
- 📊 Uso de RAM global
- 📂 Lista de aplicações

### 2. Selecionar uma Aplicação
Use o menu dropdown "📂 Selecione uma aplicação..." para escolher qual app gerenciar.

### 3. Navegar pelos Modos

**🏠 Início** - Visão geral da conta e aplicações

**📊 Status** - Monitoramento detalhado:
- Estado do container (Online/Offline)
- Uso de CPU e RAM (com barras visuais)
- Tráfego de rede
- Espaço em SSD
- Tempo de atividade (uptime)
- Status de Auto Restart e Git Deploy

**🎮 Controle** - Gerenciamento da aplicação:
- 🟢 Iniciar aplicação
- 🔄 Reiniciar aplicação
- 🔴 Parar aplicação

**📜 Logs** - Visualização do terminal em tempo real

**🛠️ Tools** - Ferramentas avançadas:
- 💾 Backup - Download do código-fonte
- 🖥️ RAM - Alterar quantidade de memória
- 🗑️ Deletar - Remover aplicação (requer confirmação)

**🛡️ Mods** - Gerenciamento de moderadores:
- ➕ Adicionar novo moderador
- ✏️ Editar permissões
- 🗑️ Remover moderador

---

## 🚀 Deploy em Produção

Este projeto está pré-configurado para ser implantado na **Discloud**.

### Discloud (Recomendado)

O arquivo de configuração essencial para o deploy na Discloud é o `discloud.config`.

#### 📝 Configurando o `discloud.config`

O arquivo atual está configurado como exemplo. Ajuste os seguintes campos:
```ini
TYPE=bot
MAIN=main.py
NAME=Discloud Dashboard
AVATAR=https://i.imgur.com/ITwQN6H.png
RAM=300
AUTORESTART=true
```

**Campos importantes:**
- `RAM`: Quantidade de memória alocada (mínimo 100MB recomendado: 256-512MB)
- `ID`: Será gerado automaticamente após o primeiro upload
- `AUTORESTART`: Mantém o bot sempre online

#### 🔑 Variáveis de Ambiente na Discloud

1. Acesse o painel da sua aplicação na Discloud
2. Vá em **Configurações** → **Variáveis de Ambiente**
3. Adicione as seguintes variáveis:

| Variável | Valor |
|----------|-------|
| `DISCORD_TOKEN` | Token do seu bot Discord |
| `DISCLOUD_TOKEN` | Token da API Discloud |

#### 📦 Fazendo Upload

**Pelo Site:**
1. Comprima seu projeto em um arquivo `.zip` (não inclua a pasta `venv`)
2. Acesse [Discloud Upload](https://discloud.com/upload)
3. Faça upload do arquivo `.zip`

**Pela CLI:**
```bash
discloud upload
```

**Pelo próprio Bot (após estar online):**
```
/upload file_attachment:seu-bot.zip
```

---

## 📂 Estrutura do Projeto
```
discloud-dashboard/
├── main.py              # Arquivo principal do bot
├── requirements.txt     # Dependências Python
├── discloud.config      # Configuração de deploy Discloud
├── .env                 # Variáveis de ambiente (NÃO COMITAR!)
├── .gitignore           # Arquivos ignorados pelo Git
└── README.md            # Documentação do projeto
```

---

## ❓ Perguntas Frequentes (FAQ)

### 🤖 O bot não está respondendo aos comandos
- Verifique se o bot está online no Discord
- Confirme que você executou o comando `!sync` no servidor
- Certifique-se de que o bot tem permissões adequadas no servidor

### 🔑 Erro de autenticação
- Verifique se os tokens no `.env` estão corretos
- Confirme que não há espaços extras antes ou depois dos tokens
- Para o Discord Token, certifique-se de que ativou o `MESSAGE CONTENT INTENT`

### 📦 Erro ao fazer upload/commit
- O arquivo deve ser um `.zip` válido
- Verifique se o `discloud.config` está incluído no arquivo
- Certifique-se de que seu plano Discloud tem espaço disponível

### 🛑 Como parar o bot localmente
Pressione `Ctrl + C` no terminal onde o bot está rodando.

---

## 🤝 Como Contribuir

Contribuições são sempre bem-vindas! Se você tem uma ideia de melhoria:

1. Faça um Fork do projeto.
2. Crie uma Branch para sua feature (`git checkout -b feature/NovaFeature`).
3. Faça o Commit das suas mudanças (`git commit -m 'Adiciona NovaFeature'`).
4. Faça o Push para a branch (`git push origin feature/NovaFeature`).
5. Abra um Pull Request.

---

## 📝 Changelog

### v1.0.0 (Atual)
- ✨ Painel interativo completo
- 📊 Monitoramento de recursos em tempo real
- 🎮 Controles da aplicação (start/stop/restart)
- 📜 Visualização de logs
- 🛠️ Ferramentas de backup e gestão de RAM
- 🛡️ Sistema de moderadores
- 📦 Upload e commit de aplicações
- 🎨 Design moderno com emojis customizados

---

## ⚖️ Licença

Este projeto está licenciado sob a licença **MIT**.

### O que isso significa?
* ✅ **Você pode:** Usar, modificar, distribuir e até vender este software.
* ✅ **Sem restrições:** Uso comercial é permitido.
* 📋 **Obrigatório:** Incluir a licença e aviso de copyright em cópias do software.

Para ler a licença completa, veja o arquivo [LICENSE](./LICENSE) neste repositório.

---

## 🙏 Agradecimentos

- [Discord.py](https://github.com/Rapptz/discord.py) - Framework incrível para bots Discord
- [Discloud](https://discloud.com) - Hospedagem confiável para bots e sites
- [Discloud Python](https://github.com/discloud/python-discloud-status) - Wrapper oficial da API

---

## 📞 Suporte

Encontrou um bug ou tem uma sugestão? 
- Abra uma [Issue](https://github.com/thekallum/discloud-dashboard/issues)

---

<div align="center">

Feito com 🧡 por [**Kallum**](https://github.com/thekallum)

⭐ Se este projeto te ajudou, considere dar uma estrela!

</div>