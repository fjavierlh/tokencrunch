# Roadmap

## Fase 1 — Proxy funcional (MVP)
> El proxy arranca, reenvía requests a la API, y mide tokens.

- [x] Estructura del proyecto y documentación base
- [ ] Proxy HTTP con FastAPI que reenvía requests a upstream
- [ ] Soporte SSE streaming passthrough
- [ ] Token counting (antes/después) con métricas en logs
- [ ] CLI: `tokencrunch start` / `tokencrunch stop`

## Fase 2 — Capas lossless
> Compresión sin riesgo de pérdida de calidad.

- [ ] **Syntactic layer**: strip whitespace, comments, empty lines
- [ ] **Serialization layer**: JSON minification, TOON conversion
- [ ] **Dedup layer**: LTSC-style repeated sequence replacement
- [ ] Config TOML con toggle por capa
- [ ] Dashboard de métricas por capa (terminal)

## Fase 3 — Capas avanzadas
> Compresión con ML y caché inteligente.

- [ ] **Semantic layer**: integración LLMLingua-2
- [ ] **Cache layer**: embedding-based semantic cache
- [ ] Rate limiting configurable por capa
- [ ] Tests de regresión de calidad

## Fase 4 — Producción
> Listo para uso diario.

- [ ] Publicar en PyPI
- [ ] Documentación completa
- [ ] Benchmarks reproducibles
- [ ] Integración probada con Claude Code, opencode, aider
- [ ] GitHub Actions CI/CD
