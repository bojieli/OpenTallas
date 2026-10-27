cd /srv/opentallas-scratch2/claude/kv-kits-6-1027; ulimit -v 48000000; export PYTHONPATH=/srv/opentallas-scratch2/claude/kv-cores-pv3/pylib:/srv/opentallas-scratch2/claude/wt/kv-kits-6-1027/tools/die_plan
for p in r26 r26q2; do
 python3 /srv/opentallas-scratch2/claude/wt/kv-kits-6-1027/tools/die_plan/check.py pd/hm_$p.json --out g0_$p --cells-evidence hm_cells_evidence.json > logs/g0_$p.log 2>&1; echo g0 $p rc=$? >> g0.done &
 python3 /srv/opentallas-scratch2/claude/wt/kv-kits-6-1027/tools/die_plan/check.py pd/hm_$p.json --out g0c_$p --completeness --cells-evidence hm_cells_evidence.json > logs/g0c_$p.log 2>&1; echo g0c $p rc=$? >> g0.done &
done; wait
