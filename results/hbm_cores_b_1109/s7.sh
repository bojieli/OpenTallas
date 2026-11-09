cd /
K=/srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py
grep -nE 'epyc[0-9]|HOSTS|host_list|"hosts"|--hosts' $K | cut -c1-180 | head -30
echo ==env; for p in $(pgrep -f 'kit_wave.py (loop|daemon|drain|serve|run )' | head -3); do tr '\0' '\n' < /proc/$p/cmdline | tr '\n' ' ' | cut -c1-200; echo; done
ls ~/coord/autopilot/kit_wave/*.json 2>/dev/null | head; grep -lE 'epyc6' ~/coord/autopilot/*.json ~/coord/autopilot/kit_wave/*.json 2>/dev/null | head
echo ==autoclean; grep -lE 'epyc6' ~/.config/systemd/user/* ~/.local/bin/ot-* 2>/dev/null | grep -v '\.bak' | head
grep -n 'epyc6' ~/coord/bin/near_close.py | cut -c1-140 | head -5
