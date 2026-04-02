# ADR-004: TOML como formato de configuración

**Estado:** Aceptado
**Fecha:** 2026-04-02

## Contexto

tokencrunch necesita un archivo de configuración para controlar qué capas están
activas, sus parámetros, y la configuración del proxy.

## Decisión

Usamos **TOML** como formato de configuración (`tokencrunch.toml`).

## Alternativas consideradas

### YAML
- ✅ Muy popular en DevOps
- ❌ Sintaxis ambigua (Norway problem: `NO` se interpreta como `false`)
- ❌ Indentation-sensitive (propenso a errores)
- ❌ Requiere librería externa en Python (PyYAML)

### JSON
- ✅ Universal, sin librerías extra
- ❌ No soporta comentarios (crítico para config files)
- ❌ Verbose (llaves, comillas en keys)

### .env / environment variables
- ✅ Simple, sin archivos extra
- ❌ No soporta estructuras anidadas (layers.syntactic = true)
- ❌ Difícil de versionar configuraciones complejas

## Consecuencias

### Positivas
- TOML está en la stdlib de Python 3.11+ (`import tomllib`)
- Soporta comentarios, tipos claros, y anidamiento
- Es el estándar de facto para config en Python (pyproject.toml)
- Sintaxis simple y no ambigua

### Negativas
- Menos conocido que YAML/JSON para algunos desarrolladores
- No soporta esquemas de validación nativos (usamos pydantic para validar)
