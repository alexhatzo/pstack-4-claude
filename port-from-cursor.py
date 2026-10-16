#!/usr/bin/env python3
"""Rewrite Cursor-isms in a verbatim upstream pstack checkout for Claude Code.

Rules that no longer match print STALE and are harmless. The leftover scan at the end is the
gate: it exits 1 while any Cursor-only term survives, and each hit needs a new rule here.
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.home() / ".claude/skills/pstack"
MD = [p for p in list((ROOT / "skills").rglob("*.md")) + list((ROOT / "agents").rglob("*.md"))]
# Playbooks are read raw (no ${...} substitution), so they name poteto-mode's directory as <poteto-mode>,
# which poteto-mode's SKILL.md defines from ${CLAUDE_SKILL_DIR}. Works for clone and marketplace installs.
SCRIPTS = "<poteto-mode>/scripts/"
SLUG = 'slug = the working directory with each "/" turned into "-"'
CONTROL = "the Browser pane tools for web UIs, the `run` skill for CLIs and servers, the iOS Simulator tool for iOS"

# Sentence-level rewrites, matched against verbatim upstream text (before GLOBAL renames).
PRE = [
    (r"\*\*Match the model to the job\.\*\*[^\n]*",
     "**Match the model to the job.** Before each spawn, start from the role's line or default and pick the reasoning effort the job needs, passed as the Agent tool's `effort` parameter (`low`, `medium`, `high`, `xhigh`, `max`). The `# budget` line of the `/setup-pstack` rule sets each role's starting effort, xhigh by default. Raise it one step, up to max, for the hardest or subtlest work. Lower it one step for judgment and two or more steps for routine work. Verification is the exception and stays on the `swarm workers` model and starting effort. Change only the effort, and keep the model the role names, so a diverse panel stays diverse. A role on `auto` or `inherit-parent` stays on the parent model. If the Agent tool rejects the effort, spawn without `effort` and say so."),
    (r"reasoning level and fast or standard speed", "reasoning effort"),
    (r"Bundled skills live at `\.\./<name>/SKILL\.md` from this file, so put this file's absolute path in every `poteto-agent` prompt\.",
     "This skill's directory is `${CLAUDE_SKILL_DIR}`, written `<poteto-mode>` in the playbooks. If you read this file directly and see that placeholder unexpanded, `<poteto-mode>` is the directory this file is in. Bundled skills live at `<poteto-mode>/../<name>/SKILL.md`, so put this file's absolute path in every `poteto-agent` prompt."),
    (r"Families go by prefix: [^\n]*?With no family match, use ([^.\n]*)\.",
     r"Families are the model names `opus`, `sonnet`, `haiku`, and `fable`. With no family match, use \1."),
    (r"\*\*\(b\) Apply it\.\*\*[^\n]*",
     "**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by model, list, or alias (`inherit-parent`, `auto`). The budget changes no model name. It sets the starting reasoning effort that every spawn passes as the Agent tool's `effort` parameter. `unlimited` sets `max`, `large` sets `xhigh`, `medium` sets `high`, and `small` sets `medium`. `large` keeps the skill defaults."),
    (r"with `alwaysApply: true`, ", "(plain markdown, no frontmatter, so it loads into every session) with "),
    # readonly / agent mode -> Explore vs general-purpose
    (r"`subagent_type: generalPurpose`(,| and) `readonly: true`", r"`subagent_type: Explore`"),
    (r"Every spawn is `generalPurpose` with `readonly: false` \(agent mode\)\. \*\*Do not use readonly/Ask mode\.\*\* It strips MCP access, which disables",
     "Every spawn is `general-purpose`, not `Explore`. The `Explore` agent has no MCP tools, which would disable"),
    (r", agent mode \(`readonly: false`\)\. (Reviewers need MCP access[^.\n]*), and readonly strips MCPs\.",
     r", not `Explore`. \1, and `Explore` has no MCP tools."),
    (r", agent mode \(`readonly: false`\)\. It spot-verifies citations through MCP, and readonly strips MCPs\.",
     ", not `Explore`. It spot-verifies citations through MCP, which `Explore` lacks."),
    (r"`run_in_background: true`, agent mode \(readonly strips MCP\),",
     "`run_in_background: true`, `subagent_type: Explore` for read-only exploration and `general-purpose` when the agent must write or needs MCP tools,"),
    (r"Spawn one readonly judge subagent", "Spawn one `Explore` judge subagent"),
    # cloud agents -> local worktree subagents
    (r'`environment: "cloud"`, ', '`isolation: "worktree"` when they write code, '),
    (r' Use `environment: "local"` only when the worker needs access to something on the user\'s computer\.', ""),
    (r"When a worker must start from a non-default pushed branch, pass `cloud_base_branch`\.",
     "When a worker must start from a non-default pushed branch, tell it to check that branch out in its worktree first."),
    (r"\ba Cursor cloud agent\b", 'a local subagent in its own worktree (`isolation: "worktree"`)'),
    (r"Always `environment: \"cloud\"` unless the task needs this machine: [^\n]*?Cloud agents cannot read the local store, so their briefs inline what they need or point at repo paths\.",
     "Local subagents (`subagent_type: pstack:poteto-agent`, `isolation: \"worktree\"` for anything that writes code). Claude Code has no cloud workers unless `isolation: \"remote\"` is enabled for this account. Briefs inline what they need or point at repo paths."),
    (r"the cloud agent's status in the Cursor dashboard", "the subagent's task status"),
    # cursor-team-kit -> Claude Code equivalents
    (r" \(such as `control-ui` or `control-cli` from `cursor-team-kit`\)", f" ({CONTROL})"),
    (r"\*\*Control skill\.\*\* Pick it by surface\. Browser, Electron, and web UIs use `control-ui` from `cursor-team-kit`\. CLIs and TUIs use `control-cli` from `cursor-team-kit`\. Native mobile uses whatever simulator-driving skill the repo has\.",
     "**Control surface.** Pick it by surface. Browser, Electron, and web UIs use the Browser pane tools (`preview_start`, `read_page`, `computer`). CLIs and TUIs use the `run` skill. Native iOS uses the iOS Simulator tool."),
    (r"Each live lane runs on its own cloud VM at the PR head\. Drive through `control-ui` or `control-cli` from `cursor-team-kit`\.",
     "Each live lane runs in its own worktree at the PR head. Drive through the Browser pane tools, the `run` skill, or the iOS Simulator tool."),
    (r"- Before commit → the `deslop` skill from the `cursor-team-kit` plugin \(`/deslop`\)\.", "- Before commit → the `simplify` skill (`/simplify`)."),
    (r"the `deslop` skill from the `cursor-team-kit` plugin \(`/deslop`\)", "`/simplify`"),
    (r"`/deslop` from `cursor-team-kit`", "`/simplify`"),
    (r"- Shipping UI / IDE / CLI → the matching control skill\. `cursor-team-kit` publishes `control-cli` \(CLIs and TUIs\) and `control-ui` \(browser / Electron / web UIs\)\.",
     "- Shipping UI / IDE / CLI → drive the real surface yourself: the Browser pane tools (`preview_start`, `read_page`, `computer`) for web UIs, the iOS Simulator tool for iOS, the `run` skill for CLIs and servers."),
    # Cursor built-in babysit skill
    (r",? not Cursor's built-in babysit skill, whose description matches the same words\.", "."),
    (r" This playbook replaces Cursor's built-in babysit skill for these requests, so do not route there even though its description matches the same words\.", ""),
    # transcripts
    (r"in the `agent-transcripts/` directory the system prompt names", f"in `~/.claude/projects/<slug>/` ({SLUG})"),
    (r"<agent-transcripts>/\*\.jsonl <agent-transcripts>/\*/\*\.jsonl <agent-transcripts>/\*/subagents/\*\.jsonl",
     "~/.claude/projects/<slug>/*.jsonl ~/.claude/projects/<slug>/*/subagents/*.jsonl"),
    (r"the (?:active )?workspace's `agent-transcripts/` directory \(the system prompt names (?:the|this) path",
     f"the workspace's transcript directory `~/.claude/projects/<slug>/` ({SLUG}"),
    (r"The system prompt names the (?:active )?workspace's `agent-transcripts/` directory\. Use (only )?that path\.",
     rf"Transcripts live under `~/.claude/projects/<slug>/` ({SLUG}). Use \1that path."),
    (r"Transcripts live at `~/\.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>\.jsonl`, where `<slug>` is the workspace path with the leading slash dropped and each \"/\" turned into \"-\" \(so `/Users/you/proj` becomes `Users-you-proj`\)\.",
     "Transcripts live at `~/.claude/projects/<slug>/<uuid>.jsonl`, where `<slug>` is the workspace path with each \"/\" turned into \"-\" (so `/Users/you/proj` becomes `-Users-you-proj`)."),
    # MCP discovery
    (r"list the available MCPs from the Cursor environment\. Use the available-tools map when present\. Otherwise inspect the `mcps/` directory Cursor exposes for enabled MCP servers\.",
     "list the available MCP servers in this session (the `mcp__<server>__*` tool names, plus deferred tools findable with `ToolSearch`)."),
    # poteto-agent finding poteto-mode
    (r"search `~/\.cursor/plugins/` for a file whose path ends in `skills/poteto-mode/SKILL\.md`\. If more than one file matches, use the copy whose `\.cursor-plugin/plugin\.json` has the highest `version`\.",
     "read `${CLAUDE_PLUGIN_ROOT}/skills/poteto-mode/SKILL.md`. If that path still shows `${CLAUDE_PLUGIN_ROOT}` unexpanded, find the file with `ls ~/.claude/plugins/cache/*/pstack/*/skills/poteto-mode/SKILL.md ~/.claude/skills/*/skills/poteto-mode/SKILL.md`."),
    # setup-pstack model detection
    (r"Enumerate the model slugs you can pass to a `Task` subagent in this session\. That is the dependable source\. If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness\. If you cannot detect any, ask the user to paste the slugs they have access to\. Never write a real slug you have not confirmed is available\.",
     "The Agent tool's `model` parameter accepts exactly `sonnet`, `opus`, `haiku`, and `fable` (Claude Code runs only Claude models). Those four are the detected set. Never write any other real slug."),
    (r"```\n---\ndescription: pstack per-role model choices \(overrides skill defaults\)\nalwaysApply: true\n---\n", "```\n"),
    # poteto-help: skills load from the user's words here, since the port drops disable-model-invocation
    (r"Installing changes nothing until the user invokes a skill\. Only `/setup-pstack` loads from the user's words\.",
     "Installing changes nothing until a skill runs. Skills load when the user types them or when the request matches their description."),
    (r"\| A skill didn't load on its own \| Only `/setup-pstack` loads from the user's words\. The others load when the user types them or when `/poteto-mode` runs them, and it doesn't run every skill\. \|",
     "| A skill didn't load on its own | Type it, or start with `/poteto-mode`, which runs the skills its playbook steps need. It doesn't run every skill. |"),
    # poteto-help
    (r"mention once that a Custom Mode keeps it on\.", "mention once that starting each task with `/poteto-mode` keeps it on."),
    (r"1\. Install with `/add-plugin pstack` in chat, or from Customize in the sidebar\.",
     "1. Install it as a plugin with `/plugin marketplace add alexhatzo/pstack-4-claude` and then `/plugin install pstack@pstack-4-claude`, or clone the repo into `~/.claude/skills/pstack`. Either way every skill is namespaced `pstack:<name>` (`/pstack:poteto-mode`)."),
    (r"pstack is built for Cursor\. [^\n]*",
     "pstack comes from cursor/plugins. This is a Claude Code port. Subagents run through the Agent tool on Claude models (`opus`, `sonnet`, `haiku`, `fable`), and `/loop` is Claude Code's built-in."),
    (r"Whether `/poteto-mode` stays on depends on how the user starts it:\n\n(?:- [^\n]*\n)+\nLink \[Cursor's skills docs\]\([^)]*\) when this comes up\. ",
     "Claude Code has no Custom Modes, so `/poteto-mode` attaches to one message and fades as the chat moves on. Start each new task with `/poteto-mode`. "),
    (r"which saves tokens when the chat runs on Auto or a cheaper model", "which saves tokens when the chat runs on a cheaper model"),
    (r"race workers, as cloud agents", "race workers, as parallel subagents"),
    (r"- `/deslop`, `control-cli`, and `control-ui` ship in the `cursor-team-kit` plugin\.",
     "- `/simplify` and the `run` skill ship with Claude Code. The Browser pane tools and the iOS Simulator tool come from the Claude desktop app."),
    (r"- `/loop` and `/create-skill` are Cursor built-ins\.",
     "- `/loop` is a Claude Code built-in. `skill-creator` comes from the `anthropic-skills` plugin."),
    (r"can start Cursor's own skill for the same job instead", "can start another plugin's skill for the same job instead"),
    (r"Cursor's Plan Mode works alongside it", "Claude Code's plan mode works alongside it"),
    (r"It was started with Enter\. Start it as a Custom Mode, or start each task with `/poteto-mode`\.",
     "Claude Code has no Custom Modes. Start each task with `/poteto-mode`."),
    (r"Give each agent its own worktree, or run them as cloud agents, which each get their own machine\.",
     'Give each agent its own worktree (`isolation: "worktree"` on the Agent call).'),
    # other skills
    (r"Cursor's built-in `create-skill`( skill)?", "the `skill-creator` skill"),
    (r"\(Cursor's built-in for authoring SKILL\.md files\)", "(the `anthropic-skills` plugin's skill for authoring SKILL.md files)"),
    (r"Cursor's `/loop` command", "Claude Code's `/loop` command"),
    (r"a Cursor restart", "a Claude Code restart"),
]

# Renames across every file, after PRE.
GLOBAL = [
    # In Cursor this only hides a skill from auto-invocation; in Claude Code the Skill tool then refuses it,
    # which stops poteto-mode and every skill that routes to another one.
    (r"(?m)^disable-model-invocation: true\n", ""),
    (r"claude-opus-5-5-(?:max|xhigh|high|medium|low)", "opus"),
    (r"grok-4\.7-(?:xhigh|high|medium|low)-fast", "sonnet"),
    (r"(?<!User)\bAskQuestion\b", "AskUserQuestion"),
    (r"\bTask\b(?! as a verb)", "Agent"),
    (r"\ba (`?)Agent\b", r"an \1Agent"),
    (r"subagent_type: \"poteto-agent\"", 'subagent_type: "pstack:poteto-agent"'),
    (r"subagent_type: \"comment-sicko\"", 'subagent_type: "pstack:comment-sicko"'),
    (r"generalPurpose", "general-purpose"),
    (r"https://github\.com/cursor/plugins/blob/main/pstack/", "https://github.com/alexhatzo/pstack-4-claude/blob/ported/"),
    (r"~/\.cursor/rules/pstack-models\.mdc", "~/.claude/rules/pstack-models.md"),
    (r"`pstack-models\.mdc` rule", "`~/.claude/rules/pstack-models.md` rule"),
    (r"~/\.cursor/projects/\*/", "~/.claude/projects/*/"),
    (r"\.cursor/skills/", ".claude/skills/"),
    (r"~/\.cursor/plugins/", "~/.claude/plugins/"),
    (r"\.cursor/worktrees/", ".claude/worktrees/"),
    (r"create-skill", "skill-creator"),
    (r"(?<![/-])\bBugbot\b", "CodeRabbit"),
    (r"\bbugbot\b(?!-triage)", "coderabbit"),
    (r"(?<!\.claude/skills/)pstack/skills/poteto-mode/scripts/", SCRIPTS),
    (r"(?<![\w/~.])scripts/(watch-pr/watch-pr|worktree-audit\.sh|orch/orch\.ts)", SCRIPTS + r"\1"),
    (r"(?<!\()`/deslop`", "`/simplify`"),
]

# Frontmatter fixes, exact, after GLOBAL.
EXACT = [
    ("skills/poteto-mode/SKILL.md", "name: Poteto Mode\n", "name: poteto-mode\n"),
    ("skills/make-bot-ui/SKILL.md", "name: Make Bot UI\n", "name: make-bot-ui\n"),
    ("agents/poteto-agent.md", "is_background: true\n", "background: true\n"),
]

def sub_all(pattern, repl):
    total = 0
    for p in MD:
        s = p.read_text()
        s2, n = re.subn(pattern, repl, s)
        if n:
            p.write_text(s2); total += n
    print(f"{total:3d}  {pattern[:70]}" + ("  STALE" if total == 0 else ""))

for pat, rep in PRE + GLOBAL:
    sub_all(pat, rep)

for rel, old, new in EXACT:
    p = ROOT / rel
    s = p.read_text()
    n = s.count(old)
    assert n <= 1, f"{rel}: {old[:50]!r} matched {n}"
    p.write_text(s.replace(old, new))
    print(f"  {n}  {rel}: {old[:50]!r}" + ("  STALE" if n == 0 else ""))

sh = ROOT / "skills/poteto-mode/scripts/worktree-audit.sh"
s = sh.read_text()
s2 = re.sub(r"# Transcripts dir: ~/\.cursor/projects/<slugified-repo-path>/agent-transcripts\.\n"
            r"slug=\$\(printf '%s' \"\$main_wt\" \| sed 's#\^/##; s#/#-#g'\)\n"
            r"transcripts=\"\$HOME/\.cursor/projects/\$slug/agent-transcripts\"\n",
            "# Transcripts dir: ~/.claude/projects/<repo-path with / turned into ->.\n"
            "slug=$(printf '%s' \"$main_wt\" | sed 's#/#-#g')\n"
            "transcripts=\"$HOME/.claude/projects/$slug\"\n", s)
sh.write_text(s2); print(f"  {int(s != s2)}  worktree-audit.sh transcripts path")

# Claude Code plugin manifest from the Cursor one.
src = json.loads((ROOT / ".cursor-plugin/plugin.json").read_text())
# No "version": a pinned version stops marketplace installs from updating until it changes, and upstream
# bumps it less often than this port changes. Without it Claude Code versions installs by commit SHA.
manifest = {k: src[k] for k in ("name", "description", "author", "homepage", "repository", "license", "keywords") if k in src}
manifest["description"] += f" (Claude Code port of cursor/plugins/pstack {src['version']})"
(ROOT / ".claude-plugin").mkdir(exist_ok=True)
(ROOT / ".claude-plugin/plugin.json").write_text(json.dumps(manifest, indent=2) + "\n")
marketplace = {"name": "pstack-4-claude", "owner": {"name": "alexhatzo"},
               "plugins": [{"name": "pstack", "source": "./", "description": manifest["description"]}]}
(ROOT / ".claude-plugin/marketplace.json").write_text(json.dumps(marketplace, indent=2) + "\n")
print(f"  manifest + marketplace for upstream {src['version']}")

# Upstream's README describes Cursor (install, models, modes), so it moves aside and ours replaces it.
README_HEAD = "# pstack for Claude Code\n"
readme = ROOT / "README.md"
if not readme.read_text().startswith(README_HEAD):
    (ROOT / "UPSTREAM-README.md").write_text(readme.read_text())
readme.write_text(README_HEAD + f"""
A Claude Code port of [pstack](https://github.com/cursor/plugins/tree/main/pstack) {src['version']}, the agent engineering skills [poteto](https://github.com/poteto) built for Cursor. This repo tracks upstream and rewrites the Cursor-only parts. Upstream's own README, with the tour of every skill and playbook, is [UPSTREAM-README.md](UPSTREAM-README.md). Its install and model sections describe Cursor.

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
""")

LEFT = re.compile(r"\.cursor/|\.cursor-plugin|cursor-team-kit|control-ui|control-cli|deslop|generalPurpose|\bTask\b(?! as a verb)"
                  r"|readonly[:`/]|environment: |is_background|grok-|composer|gpt-5|\bBugbot\b|(?<!User)AskQuestion|(?<!Support/)\bCursor\b"
                  r"|agent-transcripts|[Cc]loud agent|fast mode|-fast\b|alwaysApply|Agents Window|add-plugin|mcps/|\.mdc\b|cloud_base_branch|cursor/plugins/blob|\.claude/skills/pstack/")
left = []
for p in MD:
    for i, line in enumerate(p.read_text().splitlines(), 1):
        for m in LEFT.finditer(line):
            left.append(f"{p.relative_to(ROOT)}:{i}: {m.group(0)}")
print("leftovers:", "\n".join(left) or "none")
sys.exit(1 if left else 0)
