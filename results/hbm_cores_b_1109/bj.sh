cd /srv/opentallas-scratch2/claude/kw35/us
cat list.py | cut -c1-200
sed -n 30,80p scan.py | cut -c1-170
cd /srv/opentallas-scratch2/claude/kw36/wt_g/tools/autopilot
grep -n "supersede\|SUPERSEDE" kit_wave.py | cut -c1-170 | head -30
grep -n "def resume_source\|resume_from\b" kit_wave.py | cut -c1-150 | head -12
grep -n "\"cancel\"\|def cancel\|--cancel\|queue_cancel" kit_wave.py autopilot.py | cut -c1-170 | head
