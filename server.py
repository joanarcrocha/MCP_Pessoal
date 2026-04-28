"""
MCP Server — Desktop Folder Explorer
=====================================
Um servidor MCP local que expõe o conteúdo de uma pasta do teu
ambiente de trabalho (Desktop) como **tools** e **resources**.

Arquitetura MCP:
  ┌─────────────┐   JSON-RPC (stdio)   ┌─────────────┐
  │  MCP Client │ ◄──────────────────► │  MCP Server  │
  │ (Claude, etc)│                      │ (este ficheiro)│
  └─────────────┘                      └──────┬──────┘
                                              │
                                         Sistema de
                                         Ficheiros
                                         (~/Desktop)

Primitivas MCP expostas:
  • Resources — leitura passiva de ficheiros (como GET)
  • Tools     — operações com efeitos secundários (como POST)
  • Prompts   — templates reutilizáveis para o LLM

Como correr:
  pip install "mcp[cli]"
  python server.py
"""

import os
import json
import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
# Configuração: pasta alvo
# ─────────────────────────────────────────────
# Muda este caminho para a pasta que quiseres explorar.
# Por defeito aponta para ~/Desktop (funciona em macOS, Linux e Windows)
DESKTOP_PATH = Path.home() / "Desktop"

# Se ~/Desktop não existir, cria uma pasta de demo
if not DESKTOP_PATH.exists():
    DEMO_MODE = True
    DESKTOP_PATH = Path.home() / "mcp-demo-desktop"
    DESKTOP_PATH.mkdir(exist_ok=True)
    # Criar ficheiros de exemplo para teste
    (DESKTOP_PATH / "notas.txt").write_text(
        "Estas são as minhas notas de exemplo.\nLinha 2 das notas.", encoding="utf-8"
    )
    (DESKTOP_PATH / "projeto").mkdir(exist_ok=True)
    (DESKTOP_PATH / "projeto" / "readme.md").write_text(
        "# Projeto Exemplo\nDescrição do projeto.", encoding="utf-8"
    )
    (DESKTOP_PATH / "dados.json").write_text(
        json.dumps({"nome": "Exemplo", "versao": 1}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[DEMO] Pasta de demo criada em: {DESKTOP_PATH}")
else:
    DEMO_MODE = False

# ─────────────────────────────────────────────
# Inicialização do servidor FastMCP
# ─────────────────────────────────────────────
mcp = FastMCP("desktop-explorer")

# ═════════════════════════════════════════════
# RESOURCES — Leitura passiva (como endpoints GET)
# ═════════════════════════════════════════════
# Resources permitem ao cliente LLM "puxar" dados para o contexto.
# Usam URIs no formato  desktop://caminho/do/ficheiro


@mcp.resource("desktop://listing")
def list_desktop() -> str:
    """
    Resource que devolve a listagem completa da pasta Desktop.
    URI: desktop://listing

    O cliente pode carregar este resource para ver o que existe
    na pasta sem executar nenhuma ferramenta.
    """
    items = []
    for entry in sorted(DESKTOP_PATH.iterdir()):
        tipo = "📁 pasta" if entry.is_dir() else "📄 ficheiro"
        tamanho = entry.stat().st_size if entry.is_file() else "-"
        items.append(f"  {tipo}  {entry.name}  ({tamanho} bytes)")

    header = f"📂 Conteúdo de: {DESKTOP_PATH}\n{'─' * 50}\n"
    return header + "\n".join(items) if items else header + "  (pasta vazia)"


@mcp.resource("desktop://info")
def desktop_info() -> str:
    """
    Resource com metadados da pasta Desktop.
    URI: desktop://info
    """
    total_files = sum(1 for f in DESKTOP_PATH.rglob("*") if f.is_file())
    total_dirs = sum(1 for d in DESKTOP_PATH.rglob("*") if d.is_dir())
    total_size = sum(f.stat().st_size for f in DESKTOP_PATH.rglob("*") if f.is_file())

    return json.dumps(
        {
            "caminho": str(DESKTOP_PATH),
            "total_ficheiros": total_files,
            "total_pastas": total_dirs,
            "tamanho_total_bytes": total_size,
            "modo_demo": DEMO_MODE,
        },
        indent=2,
        ensure_ascii=False,
    )


# ═════════════════════════════════════════════
# TOOLS — Operações executáveis (como endpoints POST)
# ═════════════════════════════════════════════
# Tools são funções que o LLM pode invocar.
# O FastMCP gera automaticamente o JSON Schema
# a partir dos type hints e docstrings.


@mcp.tool()
def listar_pasta(subpasta: str = "") -> str:
    """
    Lista os ficheiros e pastas dentro da Desktop (ou subpasta).

    Args:
        subpasta: Caminho relativo dentro da Desktop (ex: "projeto").
                  Deixar vazio para listar a raiz.
    """
    target = DESKTOP_PATH / subpasta
    target = target.resolve()

    # Segurança: impedir navegação para fora da Desktop
    if not str(target).startswith(str(DESKTOP_PATH.resolve())):
        return "❌ Erro: Não é permitido navegar para fora da pasta Desktop."

    if not target.exists():
        return f"❌ Pasta não encontrada: {subpasta}"
    if not target.is_dir():
        return f"❌ '{subpasta}' não é uma pasta."

    items = []
    for entry in sorted(target.iterdir()):
        if entry.is_dir():
            n_items = len(list(entry.iterdir()))
            items.append(f"  📁 {entry.name}/  ({n_items} itens)")
        else:
            size = entry.stat().st_size
            items.append(f"  📄 {entry.name}  ({size} bytes)")

    path_display = subpasta or "/"
    header = f"📂 {path_display}\n{'─' * 40}\n"
    return header + "\n".join(items) if items else header + "  (vazio)"


@mcp.tool()
def ler_ficheiro(caminho: str) -> str:
    """
    Lê e devolve o conteúdo de um ficheiro na Desktop.

    Args:
        caminho: Caminho relativo do ficheiro (ex: "notas.txt" ou "projeto/readme.md")
    """
    target = (DESKTOP_PATH / caminho).resolve()

    # Segurança
    if not str(target).startswith(str(DESKTOP_PATH.resolve())):
        return "❌ Erro: Não é permitido aceder ficheiros fora da Desktop."

    if not target.exists():
        return f"❌ Ficheiro não encontrado: {caminho}"
    if not target.is_file():
        return f"❌ '{caminho}' não é um ficheiro."

    # Limitar tamanho para segurança
    if target.stat().st_size > 1_000_000:  # 1MB
        return "❌ Ficheiro demasiado grande (>1MB). Usa outro método."

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"❌ Ficheiro binário — não é possível ler como texto: {caminho}"

    return f"📄 {caminho}\n{'─' * 40}\n{content}"


@mcp.tool()
def procurar_ficheiros(termo: str, extensao: str = "") -> str:
    """
    Procura ficheiros na Desktop por nome.

    Args:
        termo: Texto a procurar no nome do ficheiro.
        extensao: Filtrar por extensão (ex: ".txt", ".py"). Opcional.
    """
    resultados = []
    for filepath in DESKTOP_PATH.rglob("*"):
        if not filepath.is_file():
            continue
        if termo.lower() not in filepath.name.lower():
            continue
        if extensao and not filepath.name.lower().endswith(extensao.lower()):
            continue
        rel = filepath.relative_to(DESKTOP_PATH)
        resultados.append(f"  📄 {rel}  ({filepath.stat().st_size} bytes)")

    header = f"🔍 Procura: '{termo}'"
    if extensao:
        header += f" (extensão: {extensao})"
    header += f"\n{'─' * 40}\n"

    if resultados:
        return header + "\n".join(resultados)
    return header + "  Nenhum resultado encontrado."


@mcp.tool()
def info_ficheiro(caminho: str) -> str:
    """
    Devolve informações detalhadas sobre um ficheiro ou pasta.

    Args:
        caminho: Caminho relativo ao ficheiro/pasta.
    """
    target = (DESKTOP_PATH / caminho).resolve()

    if not str(target).startswith(str(DESKTOP_PATH.resolve())):
        return "❌ Erro: Caminho fora da Desktop."

    if not target.exists():
        return f"❌ Não encontrado: {caminho}"

    stat = target.stat()
    info = {
        "nome": target.name,
        "tipo": "pasta" if target.is_dir() else "ficheiro",
        "tamanho_bytes": stat.st_size,
        "modificado": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "criado": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "extensao": target.suffix if target.is_file() else None,
        "caminho_completo": str(target),
    }

    return json.dumps(info, indent=2, ensure_ascii=False)


@mcp.tool()
def criar_ficheiro(caminho: str, conteudo: str) -> str:
    """
    Cria um novo ficheiro de texto na Desktop.

    Args:
        caminho: Caminho relativo para o novo ficheiro (ex: "novo.txt")
        conteudo: Conteúdo de texto a escrever no ficheiro.
    """
    target = (DESKTOP_PATH / caminho).resolve()

    if not str(target).startswith(str(DESKTOP_PATH.resolve())):
        return "❌ Erro: Caminho fora da Desktop."

    if target.exists():
        return f"❌ Ficheiro já existe: {caminho}. Usa outro nome."

    # Criar directórios intermédios se necessário
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(conteudo, encoding="utf-8")

    return f"✅ Ficheiro criado: {caminho} ({len(conteudo)} caracteres)"


# ═════════════════════════════════════════════
# PROMPTS — Templates reutilizáveis para o LLM
# ═════════════════════════════════════════════
# Prompts são templates pré-definidos que ajudam o LLM
# a realizar tarefas específicas de forma consistente.


@mcp.prompt()
def resumir_ficheiro(caminho: str) -> str:
    """
    Prompt que pede ao LLM para resumir o conteúdo de um ficheiro.

    Args:
        caminho: Caminho relativo do ficheiro a resumir.
    """
    return f"""Por favor, usa a ferramenta 'ler_ficheiro' para ler o ficheiro "{caminho}"
da Desktop e faz um resumo conciso do seu conteúdo.

Inclui:
- Tipo de conteúdo (código, notas, dados, etc.)
- Pontos principais
- Tamanho aproximado"""


@mcp.prompt()
def organizar_desktop() -> str:
    """
    Prompt que pede ao LLM para analisar e sugerir organização da Desktop.
    """
    return """Por favor, usa a ferramenta 'listar_pasta' para ver o conteúdo
da Desktop e depois sugere uma organização melhor dos ficheiros.

Analisa:
- Tipos de ficheiros presentes
- Possíveis agrupamentos por tema/tipo
- Ficheiros que podem ser arquivados
- Sugestões de estrutura de pastas"""


# ═════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    # Em modo stdio, NÃO podemos usar print() — stdout é o canal JSON-RPC.
    # Usamos stderr para mensagens de diagnóstico.
    print(f"🚀 MCP Desktop Explorer", file=sys.stderr)
    print(f"📂 Pasta: {DESKTOP_PATH}", file=sys.stderr)
    print(f"🔌 Transporte: stdio (JSON-RPC 2.0)", file=sys.stderr)

    mcp.run(transport="stdio")