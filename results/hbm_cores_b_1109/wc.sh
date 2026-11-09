cd /srv/opentallas-scratch2/claude/kw36/wt
B=origin/codex/wave-claims-1113
git show $B:results/flow/wave_claims_1113/actual_replay.json | head -30 | cut -c1-160
git diff origin/main...$B -- tools/autopilot/kit_wave.py | cut -c1-170
for f in tools/autopilot/kit_wave.py tools/autopilot/geom_continue.py tools/autopilot/test_geom_resume.py tools/autopilot/test_wave_claims.py; do
  ssh -n -o ControlPath=none epyc2 "mkdir -p /srv/opentallas-scratch3/claude/kw36/wc/tools/autopilot; rm -f /srv/opentallas-scratch3/claude/kw36/wc/$f"
  git show $B:$f | ssh -o ControlPath=none epyc2 "cat > /srv/opentallas-scratch3/claude/kw36/wc/$f"
done
