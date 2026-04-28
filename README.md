# 🖥️ MCP Desktop Explorer

Um servidor MCP local em Python que expõe a pasta Desktop como ferramentas para um LLM.

Criado como exercício prático para perceber a arquitectura do Model Context Protocol.

## O que é o MCP?

O **Model Context Protocol** é um protocolo aberto (JSON-RPC 2.0) que padroniza a forma como LLMs acedem a dados e ferramentas externas. Pensa nele como uma "USB-C para IA" — um servidor MCP que escrevas uma vez funciona com o Claude Desktop, Cursor, VS Code Copilot, e qualquer cliente compatível.

## Arquitectura

```
┌────────────────────┐         JSON-RPC 2.0          ┌──────────────────────┐
│    MCP CLIENT      │ ◄──────── (stdio) ──────────► │    MCP SERVER        │
│                    │                                │                      │
│  • Claude Desktop  │   initialize ──────────►       │  server.py           │
│  • Cursor          │   ◄────── capabilities         │                      │
│  • VS Code         │                                │  Primitivas:         │
│  • client.py       │   list_tools ──────────►       │  ├─ Resources (GET)  │
│    (teste)         │   ◄────── [5 tools]            │  ├─ Tools (POST)     │
│                    │                                │  └─ Prompts (TPL)    │
│                    │   call_tool ──────────►         │                      │
│                    │   ◄────── resultado             │         │            │
└────────────────────┘                                └─────────┼────────────┘
                                                                │
                                                         Sistema de Ficheiros
                                                           ~/Desktop
```

### As 3 primitivas MCP

| Primitiva    | Analogia   | Descrição                                          |
|-------------|------------|-----------------------------------------------------|
| **Resource** | GET        | Dados passivos que o LLM pode puxar para o contexto |
| **Tool**     | POST       | Funções executáveis com efeitos secundários          |
| **Prompt**   | Template   | Templates reutilizáveis que guiam o LLM             |

## Instalação

### Pré-requisitos

- Python 3.10+ ([python.org/downloads](https://www.python.org/downloads/))
- Claude Desktop ([claude.ai/download](https://claude.ai/download))

### Setup (Windows PowerShell)

```powershell
# Clonar o repositório
git clone https://github.com/<teu-user>/MCP_Pessoal.git
cd MCP_Pessoal

# Criar ambiente virtual e instalar dependências
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install "mcp[cli]"
```

> **Nota:** Se `.venv\Scripts\Activate.ps1` der erro de permissão, corre primeiro:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### Setup (macOS / Linux)

```bash
git clone https://github.com/<teu-user>/MCP_Pessoal.git
cd MCP_Pessoal

python3 -m venv .venv
source .venv/bin/activate
pip install "mcp[cli]"
```

## Testar

```powershell
# Testar o servidor directamente (Ctrl+C para parar)
python server.py

# Testar com o cliente Python (handshake + invoca todas as primitivas)
python client.py

# Testar com o MCP Inspector (UI visual no browser)
mcp dev server.py
```

## Ligar ao Claude Desktop

### Windows

1. Abrir o Claude Desktop → **Configurações** → **Desenvolvedor** → **Editar Config**

2. Adicionar o bloco `mcpServers` ao JSON (manter as `preferences` que já existirem):

```json
{
  "mcpServers": {
    "desktop-explorer": {
      "command": "C:\\Users\\<teu-user>\\MCP_Pessoal\\MCP_Pessoal\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\<teu-user>\\MCP_Pessoal\\MCP_Pessoal\\server.py"]
    }
  }
}
```

3. Guardar, fechar completamente o Claude Desktop e reabrir

4. Em **Configurações → Desenvolvedor** deves ver `desktop-explorer` com estado **running**

### macOS

1. Abrir o ficheiro `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Adicionar:

```json
{
  "mcpServers": {
    "desktop-explorer": {
      "command": "/caminho/para/.venv/bin/python",
      "args": ["/caminho/para/server.py"]
    }
  }
}
```

3. Reiniciar o Claude Desktop

## Estrutura do projecto

```
MCP_Pessoal/
├── server.py      # Servidor MCP (o coração do projecto)
├── client.py      # Cliente de teste que exercita todas as primitivas
├── README.md
└── .venv/         # Ambiente virtual Python (não fazer commit)
```

## Tools disponíveis

| Tool | Descrição | Exemplo de uso no Claude |
|------|-----------|--------------------------|
| `listar_pasta` | Lista ficheiros e pastas | "Lista o que tenho no Desktop" |
| `ler_ficheiro` | Lê conteúdo de ficheiros de texto | "Lê o ficheiro notas.txt" |
| `procurar_ficheiros` | Procura por nome/extensão | "Procura ficheiros .pdf" |
| `info_ficheiro` | Metadados detalhados | "Dá-me info sobre a pasta JR" |
| `criar_ficheiro` | Cria novos ficheiros de texto | "Cria um ficheiro lista.txt" |

## Resources disponíveis

| URI | Descrição |
|-----|-----------|
| `desktop://listing` | Listagem completa da Desktop |
| `desktop://info` | Metadados da pasta (total de ficheiros, tamanho, etc.) |

## Prompts disponíveis

| Prompt | Descrição |
|--------|-----------|
| `resumir_ficheiro` | Pede ao LLM para resumir o conteúdo de um ficheiro |
| `organizar_desktop` | Pede sugestões de organização da Desktop |

## Segurança

O servidor implementa várias camadas de protecção:

- **Path traversal prevention** — impede acesso a ficheiros fora da Desktop via `../`
- **Limite de tamanho** — recusa ler ficheiros maiores que 1MB
- **Protecção binária** — detecta e recusa ficheiros não-texto
- **Prevenção de sobrescrita** — não permite escrever sobre ficheiros existentes
- **Transporte stdio** — sem porta de rede exposta, comunicação local apenas

## Conceitos aprendidos

- Como funciona o protocolo MCP (JSON-RPC 2.0 sobre stdio)
- As 3 primitivas: Resources, Tools e Prompts
- Como o FastMCP gera JSON Schemas automaticamente a partir de type hints
- Como o transporte stdio funciona (stdin/stdout entre processos)
- Como configurar o Claude Desktop para usar servidores MCP locais
- Boas práticas de segurança no acesso ao sistema de ficheiros
