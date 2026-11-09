cd /srv/opentallas-scratch2/claude/kw36/wt
B=origin/codex/eco-prerouted-clock-1113
git diff --name-only origin/main...$B | grep -E '^tools/' | while read f; do
  ssh -n -o ControlPath=none epyc2 "rm -f /srv/opentallas-scratch3/claude/kw36/ceco/$f"
  git show $B:$f | ssh -o ControlPath=none epyc2 "cat > /srv/opentallas-scratch3/claude/kw36/ceco/$f" && echo ok $f
done
