cd /srv/opentallas-scratch2/claude/kv-plan-q5-1027; ulimit -v 48000000; export PYTHONPATH=/srv/opentallas-scratch2/claude/kv-cores-pv3/pylib:/srv/opentallas-scratch2/claude/wt/kv-plan-q5-1027/tools/die_plan
C=/srv/opentallas-scratch2/claude/wt/kv-plan-q5-1027/tools/die_plan/check.py
rm -f g0.done
python3 $C pd/hm_r26q5.json --out g0_r26q5 --cells-evidence hm_cells_evidence.json > logs/g0_r26q5.log 2>&1; echo g0 rc=$? >> g0.done &
python3 $C pd/hm_r26q5.json --out g0c_r26q5 --completeness --cells-evidence hm_cells_evidence.json > logs/g0c_r26q5.log 2>&1; echo g0c rc=$? >> g0.done &
wait; echo ALL >> g0.done
