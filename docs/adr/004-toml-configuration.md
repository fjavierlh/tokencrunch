# ADR-004: TOML as configuration format

**Status:** Accepted
**Date:** 2026-04-02

## Context

tokencrunch needs a configuration file to control which layers are active,
their parameters, and the proxy settings.

## Decision

We use **TOML** as the configuration format (`tokencrunch.toml`).

## Alternatives considered

### YAML
- ✅ Very popular in DevOps
- ❌ Ambiguous syntax (Norway problem: `NO` is interpreted as `false`)
- ❌ Indentation-sensitive (error-prone)
- ❌ Requires an external library in Python (PyYAML)

### JSON
- ✅ Universal, no extra libraries
- ❌ Does not support comments (critical for config files)
- ❌ Verbose (braces, quoted keys)

### .env / environment variables
- ✅ Simple, no extra files
- ❌ Does not support nested structures (layers.syntactic = true)
- ❌ Hard to version complex configurations

## Consequences

### Positive
- TOML is in the Python 3.11+ stdlib (`import tomllib`)
- Supports comments, clear types, and nesting
- De facto standard for config in Python (pyproject.toml)
- Simple and unambiguous syntax

### Negative
- Less known than YAML/JSON for some developers
- No native schema validation (we use pydantic to validate)
