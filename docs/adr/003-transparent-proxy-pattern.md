# ADR-003: Patrón de proxy HTTP transparente

**Estado:** Aceptado
**Fecha:** 2026-04-02

## Contexto

Necesitamos decidir cómo se integra tokencrunch con los coding assistants
existentes (Claude Code, opencode, aider, etc.).

## Decisión

tokencrunch funciona como un **proxy HTTP transparente** en localhost. El usuario
solo necesita cambiar una variable de entorno:

```bash
export ANTHROPIC_BASE_URL=http://localhost:7420
```

El proxy recibe las requests tal cual, aplica compresión, las reenvía al
upstream real (api.anthropic.com), recibe la respuesta, la procesa, y la
devuelve al cliente.

## Alternativas consideradas

### SDK wrapper (librería que envuelve la API)
```python
from tokencrunch import CompressedClient
client = CompressedClient()  # wraps anthropic.Client
```
- ✅ Control fino por mensaje
- ❌ Requiere cambiar código del usuario
- ❌ Necesita implementación por lenguaje (Python, TS, Rust...)
- ❌ No funciona con herramientas CLI que no exponen su client

### Monkey-patching / import hook
- ✅ Zero config para apps Python
- ❌ Solo funciona con Python
- ❌ Frágil, se rompe con actualizaciones de las librerías

### MCP Server
- ✅ Integración nativa con Claude
- ❌ El agente debe invocar la herramienta explícitamente
- ❌ Añade tokens de overhead (tool definitions, tool calls)
- ❌ No comprime el tráfico existente, solo añade herramientas

## Consecuencias

### Positivas
- **Zero code changes**: funciona con CUALQUIER herramienta que soporte
  custom base URL (Claude Code, opencode, aider, API directa)
- Un solo proxy sirve para Python, TypeScript, Rust, curl, etc.
- El usuario puede inspeccionar el tráfico (útil para debugging)
- Fácil de desactivar: quitar la variable de entorno

### Negativas
- Complejidad de manejar SSE streaming (hay que parsear y reensamblar chunks)
- El proxy debe reenviar correctamente TODOS los headers de la API
  (anthropic-version, anthropic-beta, authorization, etc.)
- En localhost usamos HTTP plano (no HTTPS), lo cual es seguro pero puede
  confundir a algunas herramientas. Documentamos esto.
- No podemos comprimir lo que no pasa por HTTP (e.g., archivos locales que
  Claude Code lee directamente). Para eso sería necesario un hook CLI
  complementario (futuro).
