# Architecture Decision Records

## What is an ADR?

An ADR (Architecture Decision Record) documents an important technical decision
in the project. Each ADR explains:

- **Context**: What problem did we have?
- **Decision**: What did we choose?
- **Alternatives**: What other options did we consider?
- **Consequences**: What did we gain and what did we trade off?

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-python-fastapi-stack.md) | Python + FastAPI as the main stack | Accepted |
| [002](002-layered-pipeline-architecture.md) | Layered pipeline architecture | Accepted |
| [003](003-transparent-proxy-pattern.md) | Transparent HTTP proxy pattern | Accepted |
| [004](004-toml-configuration.md) | TOML as configuration format | Accepted |

## When to create a new ADR?

When you make a decision that:
- Is hard to reverse
- Affects multiple parts of the codebase
- Other developers could legitimately question
