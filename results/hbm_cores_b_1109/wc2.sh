set -e
R=/srv/opentallas-scratch2/claude/kw35/repo
W=/srv/opentallas-scratch2/claude/kw36/wt_w
cd $R; git fetch -q origin 2>/dev/null || true
if [ ! -d $W ]; then
  git worktree add -q --no-checkout -b claude/kw-fix-36-wave-claims-1108 $W 5382e2a0ad0
  git -C $W sparse-checkout init --cone
  git -C $W sparse-checkout set tools physical/common_flow
  git -C $W checkout -q claude/kw-fix-36-wave-claims-1108
fi
cd $W/tools/autopilot
grep -n "test_second_attempt_keeps_first_output_and_identity" -B3 -A34 test_kit_wave_source.py | cut -c1-190
