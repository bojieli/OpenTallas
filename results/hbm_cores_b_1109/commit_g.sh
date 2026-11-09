set -e
W=/srv/opentallas-scratch2/claude/kw36/wt
cd $W
python3 -I - <<'PY'
W="/srv/opentallas-scratch2/claude/kw36/wt/"
tip="/srv/opentallas-scratch3/claude/kw36/tip/"
PY
git add tools/die_plan/signoff.py tools/die_plan/eco_loop.py tools/die_plan/test_eco_loop.py tools/die_plan/test_signoff_port_hold.py tools/autopilot/auto_resign.py
git commit -q -m "KW-FIX-36 R4: ECO near-miss census follows sign-off's output-port hold classification

Sign-off assigns output-port hold endpoints to the parent (census oport),
but the near-miss split scored them as core endpoints.  signoff adds
core_n/core_wns (census without output-port endpoints), eco_loop.near_miss
and auto_resign.judge_eco score those.  Bounds unchanged: one iteration,
<=30 ps, <=100 of the remaining endpoints.  The ECO repair scope (nonport
keeps register-to-output) and the stop-rule score are unchanged.  Records
older than core_n keep the unsplit wns with the count bounded by other+reg.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true
git log -1 --format='%h %s' | cut -c1-90
