set -u
cd /srv/opentallas-scratch2/claude/wt/die-head-1; E=/srv/opentallas-scratch2/claude/die-head-3/part/event; mkdir -p $E
cp ../../die-head-3/part/compose/landed_plan.json $E/part_event.json
python3 tools/die_plan/gen.py latency $E/part_event.json --out $E/lat --inplace > $E/lat.log 2>&1; cat $E/lat.log
python3 tools/s81_head/fallback_land.py variant $E/part_event.json --out $E/part_fb1.json > $E/variant.log 2>&1
sha256sum $E/part_event.json | cut -c1-12
python3 tools/die_plan/check.py $E/part_event.json --out $E/g0c --completeness --png > $E/g0c.log 2>&1; tail -1 $E/g0c.log | cut -c1-200
