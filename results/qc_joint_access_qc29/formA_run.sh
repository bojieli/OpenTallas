#!/bin/bash
# DIE-QC-29 form (a): native landings FIRST (grown M7 proxies, clock NDR 0.32) -> reserve -> clock-cell PG access replan -> full global census
set -euo pipefail
cd /srv/opentallas-scratch2/claude/die-qc29/formA
python3 -I - <<PY
import json
r=json.load(open("/srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/reserved_full_power.json")); a_len=2407806
json.dump(r[a_len:],open("bridges.json","w"));print("BRIDGES",len(r)-a_len)
j=json.load(open("/srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/joint_groups_actual/joint_clock_reserved.json"))+json.load(open("/srv/opentallas-scratch2/claude/die-qc29/census_grow/grown_pgonly/reserved.json"))
json.dump(j,open("joint_clock_plus_landings.json","w"),separators=(",",":"));print("JOINT",len(j))
PY
/srv/opentallas-scratch2/claude/codex-qc-pg-access-1029/venv/bin/python3 /srv/opentallas-scratch2/claude/die-qc29/../wt/die-qc29-1029/results/qc_pg_access_1029/plan_access.py --input /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800 --clock-seed /srv/opentallas-scratch2/claude/codex-qc-physical-1029/inputs/clock_base_access26_minarea.json --joint-clock-reserved joint_clock_plus_landings.json --reserved-power bridges.json --out pg > pg.log 2>&1
tail -n 1 pg.log
python3 -I - <<PY
import json
a=json.load(open("pg/reserved_access.json"));b=json.load(open("bridges.json"));json.dump(a+b,open("reserved_power_new.json","w"),separators=(",",":"))
PY
python3 /srv/opentallas-scratch2/claude/die-qc29/../wt/die-qc29-1029/results/qc_clock_physical_1029/native_landing_plan.py --endpoints /srv/opentallas-scratch2/claude/die-qc29/census_grow/endpoints_grown.json --clock-plan /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/joint_groups_actual/repair_plan.json --pg /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800/pg_rects.json --reserved-power reserved_power_new.json --spacing 0.32 --out census_full
