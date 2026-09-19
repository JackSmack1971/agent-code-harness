# Claude Code → Codex CLI Conversion Matrix

| Claude artifact | Codex artifact | Conversion status | Notes |
|---|---|---|---|
| `CLAUDE.md` | `AGENTS.md` | Converted | Persistent behavioral policy; authority language preserved. |
| `.claude/settings.json` | `.codex/config.toml` + hooks + rules | Converted semantically | Codex separates sandbox, approvals, hooks, and execpolicy. |
| `.claude/settings.local.json` | user `~/.codex/config.toml` if desired | Not packaged | Machine/user-specific overrides should not be committed as portable project policy. |
| `.claude/agents/*.md` | `.codex/agents/*.toml` | Converted | Role body becomes `developer_instructions`; sandbox/model mapped to Codex fields. |
| `.claude/skills/*` | `.agents/skills/*` | Converted | Portable frontmatter retained; Claude-only metadata removed. |
| `disable-model-invocation` | `agents/openai.yaml` `allow_implicit_invocation` | Converted | Explicit `$skill` use remains available. |
| `context: fork` / `agent:` | skill delegation instructions | Converted | Fresh named Codex subagent requested by workflow. |
| `isolation: worktree` | orchestration precondition | Converted without false equivalence | Native subagent config does not create Git worktree isolation. |
| `.claude/hooks/*` | `.codex/hooks/*` + `[hooks]` | Converted | Uses Codex hook `cwd`, `tool_name`, `tool_input.command`, and supported decisions. |
| `.claude/rules/*.md` | `AGENTS.md` trigger index + `.codex/references/path-policies/*` | Converted behaviorally | Codex AGENTS scoping is directory-based, not Claude glob-frontmatter based. |
| Claude Bash deny list | PreToolUse guard + `.codex/rules/default.rules` | Converted | Hook guards all supported Bash tool calls; execpolicy governs outside-sandbox escalation. |
| `.claude/evidence` | `.codex/evidence` | Converted | Local hints only; Git/runtime journal remains authoritative. |
| `.claude/scheduled_tasks.lock` | none | Omitted | No equivalent portable Codex project-control-plane primitive. |
