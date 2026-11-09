cd ~/coord/autopilot
echo "--- last tick wave lines (non disk/src)"
tail -n 300 log.txt | grep -a 'KIT-WAVE' | grep -a -v -E 'GEN-DISK-LOW|SRC-INCOMPLETE|SUBSTEP' | tail -14 | cut -c1-240
echo "--- counts since 16:30 by first words"
awk '/^2026-11-08 1[67]:/' log.txt | grep -a 'KIT-WAVE' | sed -E 's/^.*KIT-WAVE //' | awk '{print $1,$2}' | sed -E 's/[a-z0-9_]+\/[^ ]*//' | sort | uniq -c | sort -rn | head -20
grep -a -E 'LOAD-HOLD|load_hold|INFLIGHT|inflight' log.txt | tail -5 | cut -c1-300
ls -la kit_wave_pending.tsv; wc -l kit_wave_pending.tsv; tail -n 5 kit_wave_pending.tsv | cut -c1-260
/home/ubuntu/.local/bin/ot-run --status </dev/null 2>/dev/null | head -14 | cut -c1-200
cd /srv/opentallas-scratch2/claude/kw36/wt_e/tools/autopilot
grep -n 'max_inflight\|def inflight\|max_launch_per_tick' kit_wave.py | cut -c1-170 | head -14
grep -n -E 'scratch.*(floor|FLOOR|< *50|GB)' /home/ubuntu/.local/bin/ot-run | cut -c1-180 | head -20
