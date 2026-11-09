#!/bin/bash
set -eu
Q=/srv/opentallas-scratch3/claude/type-safe-3b/qc
C=/srv/opentallas-scratch3/claude/codex-qc-compose-1113
cd $Q
R=$(readlink -f $C/src_fixed); test ! -L "$R"
[ -d src ] || cp -al "$R" src
find src -type d -exec chmod u+w {} +
[ -d plan ] || cp -al $(readlink -f $C/plan) plan
chmod u+w plan
rm -f plan/plan_qc53v4n_ts3.json plan/plan_qc53v4n.json
cp -p $C/plan/plan_qc53v4n.json plan/plan_qc53v4n.json   # base plan path kept as a real new inode copy for the miter check
cp plan_qc53v4n_ts3.json plan/plan_qc53v4n_ts3.json
A0=src/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json
A1=src/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3_ts3.json
python3 -I - <<P
import json
d=json.load(open("$A0"));e=json.load(open("event.json"))
d["internal_stations_types"]=sorted(set(d.get("internal_stations_types") or [])|set(e["native_out_types"]))
json.dump(d,open("$A1","w"),indent=1);print(len(d["internal_stations_types"]))
P
mkdir -p bind_new
for f in asbuilt.json asbuilt_sources.json asbuilt_lib_stubs.sv asbuilt.ys provenance_elab.json asbuilt.yosys.log die_r56.v bind_elab_keep.sv; do [ -e bind_new/$f ] || ln $C/bind_v4n_hc3_fixed2/$f bind_new/$f 2>/dev/null || cp -p $C/bind_v4n_hc3_fixed2/$f bind_new/$f; done
cd src
python3 -I -B tools/die_plan/bind.py bind ../plan/plan_qc53v4n_ts3.json --out ../bind_new --strict --all-gaps --asbuilt physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3_ts3.json > ../bind_new.log 2>&1
echo BIND rc=$?
tail -3 ../bind_new.log | cut -c1-300
cd ..
python3 -I -B tools/die_plan/ts_relay_miter.py plan/plan_qc53v4n_ts3.json event.json $C/bind_v4n_hc3_fixed2/rtl bind_new/rtl miter.json; echo MITER rc=$?
