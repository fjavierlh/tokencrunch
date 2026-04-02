# ADR-001: Python + FastAPI como stack principal

**Estado:** Aceptado
**Fecha:** 2026-04-02

## Contexto

Necesitamos elegir el lenguaje y framework para construir un proxy HTTP que
intercepte llamadas a APIs de LLM y aplique compresión en tiempo real.

Los requisitos clave son:
- Baja latencia añadida (el proxy no debe ralentizar notablemente las llamadas)
- Soporte para streaming SSE (Server-Sent Events), que es como Claude envía respuestas
- Integración directa con LLMLingua-2 (librería Python de Microsoft)
- Facilidad de contribución para la comunidad open-source

## Decisión

Usamos **Python 3.12+** con **FastAPI** y **uvicorn** como servidor ASGI.

## Alternativas consideradas

### Rust (como lessloss y RTK)
- ✅ Máximo rendimiento, binario único sin dependencias
- ❌ LLMLingua-2 es Python → requeriría FFI o subprocess, añadiendo complejidad
- ❌ Barrera de entrada alta para contribuidores
- ❌ Desarrollo más lento para un prototipo

### TypeScript/Bun
- ✅ Buen rendimiento, ecosistema npm rico
- ❌ Mismo problema con LLMLingua-2 (necesitaría child process Python)
- ❌ Ecosistema de ML/NLP mucho más débil que Python

### Go
- ✅ Buen rendimiento, binario único, bueno para proxies HTTP
- ❌ Mismo problema con LLMLingua-2
- ❌ Ecosistema ML limitado

## Consecuencias

### Positivas
- Integración nativa con LLMLingua-2, tree-sitter, y todo el ecosistema ML de Python
- Baja barrera de contribución (Python es el lenguaje más popular)
- FastAPI genera documentación OpenAPI automática para el proxy
- uvicorn es async, manejando bien conexiones concurrentes y streaming

### Negativas
- Mayor consumo de memoria que Rust/Go (~50-100MB vs ~10MB)
- Latencia ligeramente mayor (~5-20ms por request vs ~1ms en Rust)
- Requiere Python instalado (no es un binario autocontenido)
- El GIL de Python limita el paralelismo CPU-bound (mitigable con ProcessPoolExecutor)

### Mitigaciones
- La latencia del proxy (~10ms) es despreciable vs la latencia del LLM (~1-5s)
- Podemos empaquetar con PyInstaller o similar para distribución
- Las capas CPU-intensivas (tree-sitter, LLMLingua) se ejecutan en process pool
