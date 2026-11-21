#!/bin/bash
# install_git_history_shim.sh [HOST...]  (FLOW-OPS-1000): put tools/fleet/git-history-shim at ~/.local/bin/git on each host (default: every
# gen host + the hub + this host).  ~/.local/bin is first on the non-login ssh PATH and on every autopilot / wave unit PATH, so lane and tool
# history searches get `timeout 600`.  Copy + rename (a running git keeps its inode).  Undo on a host: ot-delete ~/.local/bin/git there.
set -u
SRC=$(dirname "$(readlink -f "$0")")/git-history-shim
[ -x "$SRC" ] || { echo "no $SRC"; exit 2; }
HOSTS=${*:-"epyc2 epyc4 epyc7 epyc8 epyc9 epyc10 intel1 intel2 localhost"}
for h in $HOSTS; do
  cmd='mkdir -p ~/.local/bin && cat > ~/.local/bin/.git.shim.new && chmod 755 ~/.local/bin/.git.shim.new && mv -f ~/.local/bin/.git.shim.new ~/.local/bin/git && ~/.local/bin/git --version'
  if [ "$h" = localhost ]; then out=$(bash -c "$cmd" < "$SRC" 2>&1); else out=$(timeout 60 ssh -o ControlPath=none -o ConnectTimeout=10 -o BatchMode=yes "$h" "$cmd" < "$SRC" 2>&1); fi
  echo "$h: $(echo "$out" | tail -1)"
done
