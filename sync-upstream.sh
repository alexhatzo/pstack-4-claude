#!/usr/bin/env bash
# Sync this Claude Code port with cursor/plugins/pstack.
#   sync-upstream.sh            fetch upstream; if it moved: snapshot, port, replay local commits, go live
#   sync-upstream.sh port DIR   rerun the port in DIR/wt after editing DIR/wt/port-from-cursor.py
#   sync-upstream.sh live DIR   go live after resolving a cherry-pick conflict in DIR/wt
# Branches: `upstream` = verbatim snapshots, `ported` = upstream + one port commit (public),
# `live` = ported + your own commits (checked out, never pushed).
# The port commit carries port-from-cursor.py and sync-upstream.sh as they are on `live`, so commits
# that only touch those two files are not replayed. Keep tooling edits in their own commits.
# With an origin remote, every successful run pushes `upstream` and `ported`.
# Exit 0 = up to date or synced. Exit 2 = stopped for a fix; the message says what to do next.
set -euo pipefail
REPO=${PSTACK_DIR:-$HOME/.claude/skills/pstack}
TOOLS='^(port-from-cursor\.py|sync-upstream\.sh)$'
g() { git -c user.email=46765087+alexhatzo@users.noreply.github.com -c user.name=alexhatzo "$@"; }
# ported is rebuilt each sync, so the push forces (with lease against the last fetched state).
publish() { git remote get-url origin >/dev/null 2>&1 || return 0; g push -q --force-with-lease origin upstream ported; echo "PUSHED to $(git remote get-url origin)"; }

port() {
  cd "$1/wt"
  [[ $(git log -1 --format=%s) == *"verbatim from cursor/plugins@"* ]] || { echo "HEAD is not the upstream snapshot"; exit 2; }
  git checkout -q HEAD -- skills agents README.md && rm -rf .claude-plugin
  if ! python3 port-from-cursor.py "$PWD"; then
    echo "PORT LEFTOVERS: add rules to $1/wt/port-from-cursor.py, then run: $0 port $1"; exit 2
  fi
  g add -A && g commit -q --allow-empty -m "Port pstack $(jq -r .version .cursor-plugin/plugin.json) to Claude Code"
  g branch -q -f sync-ported HEAD
  local mine=()
  for c in $(git rev-list --reverse --no-merges ported..live); do
    git diff-tree --no-commit-id --name-only -r "$c" | grep -vE "$TOOLS" >/dev/null && mine+=("$c")
  done
  if [ ${#mine[@]} -gt 0 ] && ! g cherry-pick "${mine[@]}" >/dev/null; then
    echo "CONFLICT replaying local commits in $1/wt: resolve, git cherry-pick --continue (repeat), then run: $0 live $1"; exit 2
  fi
  live "$1"
}

live() {
  cd "$1/wt"
  [ ! -e "$(git rev-parse --git-path CHERRY_PICK_HEAD)" ] || { echo "cherry-pick still in progress"; exit 2; }
  claude plugin validate . >/dev/null || { echo "plugin manifest invalid"; exit 2; }
  local head; head=$(git rev-parse HEAD)
  cd "$REPO"
  g branch -q -f upstream sync-upstream
  g branch -q -f ported sync-ported
  g worktree remove --force "$1/wt"
  g reset -q --hard "$head"
  g branch -q -D sync sync-upstream sync-ported
  rm -rf "$1"
  echo "LIVE at $(git log -1 --format='%h %s')"
  publish
}

case "${1:-}" in
  port) port "$2"; exit ;;
  live) live "$2"; exit ;;
esac

cd "$REPO"
[ "$(git branch --show-current)" = live ] || { echo "$REPO is not on branch live"; exit 2; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "$REPO has uncommitted changes; commit them to live first"; exit 2; }
WORK=$(mktemp -d)
git clone -q --filter=blob:none --sparse https://github.com/cursor/plugins "$WORK/up"
git -C "$WORK/up" sparse-checkout set pstack
new=$(git -C "$WORK/up" log -1 --format=%H -- pstack)
old=$(git log -1 --format=%s upstream | grep -o 'cursor/plugins@[0-9a-f]*' | cut -d@ -f2 || true)
if [ -n "$old" ] && [[ $new == "$old"* ]]; then echo "UP TO DATE at cursor/plugins@$new"; rm -rf "$WORK"; publish; exit 0; fi
echo "UPSTREAM $old -> $new:"
git -C "$WORK/up" log -n 100 --format='  %h %ad %s' --date=short ${old:+"$old.."}"$new" -- pstack

g worktree add -q -b sync "$WORK/wt" upstream
cd "$WORK/wt"
rsync -a --checksum --delete --exclude .git "$WORK/up/pstack/" ./
g add -A && g commit -q --allow-empty -m "pstack $(jq -r .version .cursor-plugin/plugin.json) verbatim from cursor/plugins@$new"
g branch -q -f sync-upstream HEAD
for f in port-from-cursor.py sync-upstream.sh; do git -C "$REPO" show "live:$f" > "$f"; done
chmod +x sync-upstream.sh
port "$WORK"
