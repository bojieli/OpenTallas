#!/bin/bash
# DIE-KV-40: eB3b strict bind (DIE-KV-39 bindB3bG recipe) on event28w -> must be 0 errors and equal bindB3bG except q1/q2 geometry
set -u; W=/srv/opentallas-scratch2/claude/wt/die-kv-40; O=/srv/opentallas-scratch2/claude/die-kv-40-1029; cd $W; P=kv40/event28w/plan_c.json; R=$O/bindWc; A=$O/recipe_eB3b_wc.json
mkdir -p $R; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp /srv/opentallas-scratch2/claude/die-kv-35-1029/bindOld/$f $R/; done
/usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"; echo "BIND_RC $? $(date)"
tail -n 3 $R/bind.log
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound $R --out-json $R/regen_constants.json > $R/regen_constants.log 2>&1; echo "REGEN_RC $?"
echo DONE $(date)
