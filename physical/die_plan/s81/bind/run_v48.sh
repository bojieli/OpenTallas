#!/bin/bash
# ELEM-S81 bind48 10-24: S81 plan v4.8 as-built bind recipe (rebuild of BINDER4-S81 b3r8, whose run dir was lost).
# RUN = run dir with cap30/bind/bind (copy of the recovered cap30 gen-main receipt bind/bind + rtl_extra/e8561c9db
# svc_rs/dsdv_svc_rs_roles.svh from git) and cap30/src_gm (-> recovered gen-main src); WT = repo worktree (main).
# Steps: asb rewrite + map -> asbuilt json (off / r8) -> elab -> off bind -> r8 table (LANDED rule) -> r8 bind.
# Heavy steps ran under ot-run --hosts intel2 --mem 64/128 (elab 2.7 GB, bind 7.7 GB max RSS).
set -euo pipefail
RUN=$1; WT=$2; cd "$RUN"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH OT_BIND_YOSYS=$HOME/.local/opentallas-tools/bin/yosys
B=$WT/physical/die_plan/s81/bind; P=$WT/physical/die_plan/s81/die_plan.json
python3 $B/asbuilt_s81.py cap30/bind/bind/die.v $WT/physical/die_plan/s81/instance_map.json asb
python3 $B/mk_map_s81.py $WT/physical/die_plan/s81/instance_map.json asb/map.json
python3 $B/mk_asbuilt_v48.py $RUN $WT off asbuilt_v48_off.json
python3 $B/mk_asbuilt_v48.py $RUN $WT r8 asbuilt_v48_r8.json
python3 $WT/tools/die_plan/bind.py elab $P --out b48 --asbuilt asbuilt_v48_off.json --mem 64 > elab.log 2>&1
python3 $WT/tools/die_plan/bind.py bind $P --out b48 --asbuilt asbuilt_v48_off.json > bind_off.log 2>&1
mkdir -p r8 r8main tools847 b48r8
git -C $WT show 847f8568f3:tools/die_plan/r8.py > tools847/r8.py; cp $WT/tools/die_plan/schema.py tools847/
EX='(?i)(^|_)(fault|flt)(_o|_q)?$'
python3 $WT/tools/die_plan/r8.py pads $P b48/bus_groups.json --out r8main --replica type --bus leaf --exempt "$EX" > r8main.log
python3 -I tools847/r8.py pads $P b48/bus_groups.json --out r8 --replica type --bus leaf --exempt "$EX" \
    --landed '^(x|xo)_[WE][0-5]_' --landed '^xring__' --landed '^sid_s_' > r8.log
python3 -I tools847/r8.py check $P b48/bus_groups.json --landing r8/s81_r8_landing.json --replica type --bus leaf \
    --exempt "$EX" --landed '^(x|xo)_[WE][0-5]_' --landed '^xring__' --landed '^sid_s_' --json r8/check.json > r8_check.log || true
python3 $B/r8_landed_v48.py r8/s81_r8_landing.json r8/s81_r8_landing_v48.json
ln -sfn ../b48/asbuilt.json b48r8/asbuilt.json; cp b48/asbuilt_sources.json b48/asbuilt.ys b48r8/
python3 $WT/tools/die_plan/bind.py bind $P --out b48r8 --asbuilt asbuilt_v48_r8.json > bind_r8.log 2>&1
