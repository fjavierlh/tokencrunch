# Architecture Decision Records

## ¿Qué es un ADR?

Un ADR (Architecture Decision Record) documenta una decisión técnica importante
del proyecto. Cada ADR explica:

- **Contexto**: ¿Qué problema teníamos?
- **Decisión**: ¿Qué elegimos?
- **Alternativas**: ¿Qué otras opciones consideramos?
- **Consecuencias**: ¿Qué ganamos y qué sacrificamos?

## Índice

| ADR | Título | Estado |
|-----|--------|--------|
| [001](001-python-fastapi-stack.md) | Python + FastAPI como stack principal | Aceptado |
| [002](002-layered-pipeline-architecture.md) | Arquitectura de pipeline por capas | Aceptado |
| [003](003-transparent-proxy-pattern.md) | Patrón de proxy HTTP transparente | Aceptado |
| [004](004-toml-configuration.md) | TOML como formato de configuración | Aceptado |

## ¿Cuándo crear un nuevo ADR?

Cuando tomes una decisión que:
- Sea difícil de revertir
- Afecte a múltiples partes del código
- Otros desarrolladores puedan cuestionar legítimamente
