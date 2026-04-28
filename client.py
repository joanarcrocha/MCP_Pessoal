"""
MCP Client de Teste
====================
Este cliente liga-se ao server.py via stdio e testa
todas as primitivas MCP: tools, resources e prompts.
"""

import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_test_client():
    """Executa o cliente MCP de teste."""

    print("=" * 60)
    print("🧪 MCP Client de Teste — Desktop Explorer")
    print("=" * 60)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
    )

    print("\n📡 A conectar ao servidor via stdio...")

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            # PASSO 1: Inicialização (handshake)
            result = await session.initialize()

            # Compatibilidade: serverInfo (novo) vs server_info (antigo)
            info = getattr(result, 'serverInfo', None) or getattr(result, 'server_info', None)
            if info:
                name = getattr(info, 'name', 'desconhecido')
                version = getattr(info, 'version', '?')
                print(f"✅ Conectado ao servidor: {name} v{version}")
            else:
                print(f"✅ Conectado ao servidor")

            print(f"   Protocolo: {getattr(result, 'protocolVersion', getattr(result, 'protocol_version', '?'))}")

            # PASSO 2: Descobrir Resources
            print(f"\n{'─' * 60}")
            print("📚 RESOURCES (dados passivos)")
            print(f"{'─' * 60}")

            resources = await session.list_resources()
            for r in resources.resources:
                print(f"\n  URI: {r.uri}")
                print(f"  Nome: {r.name}")

            # Ler um resource
            print(f"\n  → A ler resource 'desktop://listing'...")
            listing = await session.read_resource("desktop://listing")
            for content in listing.contents:
                print(f"\n{content.text}")

            # PASSO 3: Descobrir Tools
            print(f"\n{'─' * 60}")
            print("🔧 TOOLS (operações executáveis)")
            print(f"{'─' * 60}")

            tools = await session.list_tools()
            for t in tools.tools:
                print(f"\n  🔧 {t.name}")
                print(f"     {t.description}")

            # Invocar tools
            print(f"\n  → A invocar tool 'listar_pasta'...")
            result = await session.call_tool("listar_pasta", {"subpasta": ""})
            for content in result.content:
                print(f"\n{content.text}")

            print(f"\n  → A invocar tool 'procurar_ficheiros' (termo='txt')...")
            result = await session.call_tool("procurar_ficheiros", {"termo": "txt"})
            for content in result.content:
                print(f"\n{content.text}")

            # PASSO 4: Descobrir Prompts
            print(f"\n{'─' * 60}")
            print("💬 PROMPTS (templates para o LLM)")
            print(f"{'─' * 60}")

            prompts = await session.list_prompts()
            for p in prompts.prompts:
                print(f"\n  💬 {p.name}")
                if p.description:
                    print(f"     {p.description}")

            # Resumo final
            print(f"\n{'=' * 60}")
            print("✅ Teste completo!")
            print(f"   Resources: {len(resources.resources)}")
            print(f"   Tools:     {len(tools.tools)}")
            print(f"   Prompts:   {len(prompts.prompts)}")
            print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(run_test_client())
