#!/bin/bash
# DIE-KV-37 KV-023: strict bind of event28b with recipe eB3 (= eB2 + PV column pad table pv_col_pads_28b + kv_pv_col_regen hook)
set -u
S=/srv/opentallas-scratch2/claude/die-kv-37-1029; cd /srv/opentallas-scratch2/claude/die-kv-35-1029/bindroot
P=kv36/event28b/plan.json; R=$S/bindB3; A=$S/recipe_kv27f_eB3.json
mkdir -p $R; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json die_bound_native_mission_lc.v elab.log; do cp /srv/opentallas-scratch2/claude/die-kv-35-1029/bindOld/$f $R/; done
/usr/bin/time -v python3 tools/die_plan/bind.py bind "$P" --out "$R" --asbuilt "$A" --strict > "$R/bind.log" 2> "$R/bind.time"; echo "BIND_RC $? $(date)"
tail -n 3 $R/bind.log
python3 /srv/opentallas-scratch2/claude/wt/die-kv-37-hg/tools/die_plan/regen_constants.py --help >/dev/null 2>&1 && echo regen_tool_ok
echo DONE $(date)
