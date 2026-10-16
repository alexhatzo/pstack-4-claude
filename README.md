# pstack for Claude Code

A Claude Code port of [pstack](https://github.com/cursor/plugins/tree/main/pstack) 0.15.25, the agent engineering skills [poteto](https://github.com/poteto) built for Cursor. This repo tracks upstream and rewrites the Cursor-only parts. Upstream's own README, with the tour of every skill and playbook, is [UPSTREAM-README.md](UPSTREAM-README.md). Its install and model sections describe Cursor.

## Install

As a plugin, inside Claude Code:

```
/plugin marketplace add alexhatzo/pstack-4-claude
/plugin install pstack@pstack-4-claude
```

To update, open `/plugin`, go to Marketplaces, pick `pstack-4-claude` and choose Update marketplace. Turning on auto-update for it there keeps it current.

Or as a plain clone, which Claude Code loads in place as the `pstack@skills-dir` plugin:

```bash
git clone https://github.com/alexhatzo/pstack-4-claude ~/.claude/skills/pstack
```

The `ported` branch is rebuilt on every upstream sync, so update a clone with a reset, not a pull:

```bash
git -C ~/.claude/skills/pstack fetch origin && git -C ~/.claude/skills/pstack reset --hard origin/ported
```

Use one install, not both: they register the same `pstack:<name>` skills.

## Start

Start a new Claude Code session. Every skill is namespaced `pstack:<name>`. Run `/pstack:setup-pstack` to pick models, then start any task that needs rigor with `/pstack:poteto-mode`. `/pstack:poteto-help` answers questions about the rest.

## What the port changes

- Subagents use the Agent tool. Read-only spawns use `subagent_type: Explore`, and spawns that write or need MCP tools use `general-purpose`.
- Cursor model slugs become `opus` for judgment, prose, and the hardest work, and `sonnet` for fast code. Reasoning levels and the `/setup-pstack` budget become the Agent tool's `effort` parameter.
- `~/.cursor` paths become `~/.claude`. The model rule lives at `~/.claude/rules/pstack-models.md`, and transcripts live under `~/.claude/projects/`.
- `cursor-team-kit` skills map to Claude Code. `/deslop` becomes `/simplify`, and `control-ui` and `control-cli` become the Browser pane tools, the `run` skill, and the iOS Simulator tool.
- Cloud agents become local subagents in their own worktrees, Bugbot becomes CodeRabbit, and `create-skill` becomes `skill-creator`.
- `docs/` and `automations/` are verbatim upstream and still describe Cursor.

## How it stays in sync

The `upstream` branch holds verbatim snapshots of cursor/plugins. `ported` is `upstream` plus one commit made by [`port-from-cursor.py`](port-from-cursor.py). [`sync-upstream.sh`](sync-upstream.sh) repeats both when upstream moves.

## License

MIT, same as upstream. pstack is by Lauren Tan ([poteto](https://github.com/poteto)). See [LICENSE](LICENSE).
