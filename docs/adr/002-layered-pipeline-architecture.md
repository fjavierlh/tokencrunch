# ADR-002: Arquitectura de pipeline por capas

**Estado:** Aceptado
**Fecha:** 2026-04-02

## Contexto

Existen múltiples técnicas de compresión de tokens (sintáctica, serialización,
deduplicación, semántica, caché). Necesitamos decidir cómo combinarlas.

## Decisión

Cada técnica de compresión es una **capa independiente** con una interfaz común.
Las capas se ejecutan en orden secuencial formando un pipeline. Cada capa puede
activarse/desactivarse individualmente.

```
Request → [Syntactic] → [Serialize] → [Dedup] → [Semantic] → [Cache] → API
Response ← [Syntactic] ← [Serialize] ← [Dedup] ←            ← [Cache] ← API
```

### Interfaz de cada capa

```python
class CompressionLayer(Protocol):
    name: str
    def compress_request(self, messages: list[dict]) -> list[dict]: ...
    def compress_response(self, response: dict) -> dict: ...
    def get_stats(self) -> LayerStats: ...
```

### Orden de ejecución

El orden importa y está fijado por diseño:

1. **Syntactic** primero: transforma código/texto a forma mínima. Esto hace que
   las capas posteriores trabajen con menos texto.
2. **Serialize**: convierte estructuras de datos a formatos compactos.
3. **Dedup**: detecta secuencias repetidas (más efectivo después de normalizar).
4. **Semantic**: compresión ML (la más costosa en tiempo, se aplica al final).
5. **Cache**: si todo el request ya se vio antes, se salta la API completamente.

## Alternativas consideradas

### Monolito (todo en una función)
- ❌ Imposible desactivar técnicas individuales
- ❌ Difícil de testear y debuggear
- ❌ No permite que el usuario ajuste el nivel de riesgo

### Plugin system dinámico (carga de plugins en runtime)
- ✅ Máxima extensibilidad
- ❌ Sobreingeniería para 5 capas conocidas
- ❌ Añade complejidad de discovery, ordering, dependency resolution

## Consecuencias

### Positivas
- El usuario controla exactamente qué capas usar (risk management)
- Cada capa se testea de forma aislada
- Las métricas por capa permiten saber qué técnica aporta más ahorro
- Fácil añadir nuevas capas sin tocar las existentes

### Negativas
- Overhead de pasar datos entre capas (copias de mensajes). Mitigable con
  referencias/views.
- El orden fijo puede no ser óptimo para todos los casos. Aceptamos esto como
  trade-off por simplicidad.
