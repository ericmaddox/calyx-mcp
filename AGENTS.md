# Calyx MCP Agent Directives

When interacting with this codebase or when Calyx MCP is active in your environment, follow the bio-inspired code reflex loop below.

## Calyx Associative Memory Policy

You have access to the Calyx Mushroom Body code reflex server over MCP. Use the following 2-step verification and learning loop:

### 1. Pre-Flight Reflex Check (Before Modifying or Generating Code)
- Before writing, replacing, or proposing significant code diffs, call `check_code_reflex(code=...)`.
- **Interpreting Reflex Outcomes**:
  - `status: "avoid"`: **Do NOT proceed** with that implementation. The code has high structural resemblance to a previously punished bug pattern or negative synaptic valence. Inspect the `warning` and `recommendation` to choose an alternative approach.
  - `status: "safe"`: Proceed with confidence. The code matches previously rewarded implementations.
  - `status: "neutral"`: Novel or unverified code pattern. Proceed normally.

### 2. Post-Execution Synaptic Learning (After Testing Code)
- After executing tests, build scripts, or terminal verification:
  - If a test fails or a runtime error occurs, call `remember_code_outcome(code=..., outcome="failure", error_message=...)` with the failing snippet and error reason.
  - If tests pass and the implementation is verified, call `remember_code_outcome(code=..., outcome="success")` to reinforce the active synapses.

### 3. Associative Retrieval
- Use `query_associative_memory(query_code=..., top_k=5, compact=True)` when searching for past related bug patterns or past lessons in the repository.
