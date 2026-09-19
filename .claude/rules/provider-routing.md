---
paths:
  - "src/**/providers/**"
  - "src/**/routing/**"
  - "src/**/models/**"
  - "tests/**/*provider*"
---
# Provider and Routing Rules

Initial adapters: OpenAI, Anthropic, OpenRouter, plus optional generic OpenAI-compatible adapters.

Routes:
- Route A -> routes.primary
- Route B -> routes.low_cost_candidates[]
- Route C -> routes.stronger_candidates[]
- Route D -> routes.reviewer

- Configuration alone does not qualify a model.
- Capabilities, limits, continuation semantics, and token accounting come from adapter capability contracts and current research.
- Preserve provider-native continuation state opaquely and losslessly.
- If a required route has no eligible model, block; do not silently substitute different semantics.
- Never parse hidden chain of thought.
