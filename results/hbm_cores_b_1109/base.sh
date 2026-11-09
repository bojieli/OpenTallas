cd /srv/opentallas-scratch2/claude/kw36/wt
for f in tools/die_plan/signoff.py tools/die_plan/eco_loop.py tools/die_plan/test_eco_loop.py tools/die_plan/test_signoff_port_hold.py tools/autopilot/auto_resign.py tools/autopilot/test_auto_resign.py; do
  git show origin/main:$f | ssh -o ControlPath=none epyc2 "cat > /srv/opentallas-scratch3/claude/kw36/base/$f" || echo FAIL $f
done
echo copied
