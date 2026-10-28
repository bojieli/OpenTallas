# keep loop: d9b_event (re-window, keep K) -> d9c_event (chain re-site) -> failed chain ports added to K -> repeat; then G0C
cd /srv/opentallas-scratch2/claude/kv-plan-d9c-1027; W=/srv/opentallas-scratch2/claude/wt/kv-plan-d9b; B=../kv-plan-d9b-1027
export PYTHONPATH=/srv/opentallas-scratch2/claude/kv-plan-d5-1027/pylib
cp p2/keep0.txt p2/keep.txt
for it in 1 2 3 4 5 6; do
  timeout 900 python3 $B/d9b_event.py $B/rt ../kv-plan-d9-1027/pd9/hm_r26q9.json p2/pd/kb.json p2/led_b.json --keep p2/keep.txt > p2/b.log 2>&1
  python3 d9c_event.py $W p2/pd/kb.json p2/pd/kc.json p2/led_c.json > p2/c.log 2>&1
  F=$(python3 failports.py $W p2/pd/kb.json p2/led_c.json p2/led_b.json)
  echo "it $it keep $(wc -w < p2/keep.txt) $(grep PORTS p2/b.log) | $(tail -2 p2/c.log | head -1 | cut -c1-80) | add: $F"
  [ -z "$F" ] && break
  echo $F >> p2/keep.txt
done
python3 $W/tools/die_plan/check.py p2/pd/kc.json --out p2/g0c --completeness > p2/g0c.log 2>&1; tail -n1 p2/g0c.log | cut -c1-120; date
