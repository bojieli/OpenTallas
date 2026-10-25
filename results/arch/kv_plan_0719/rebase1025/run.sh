#!/usr/bin/env bash
# PATH-KV-REBASE 10-25: f7ch plan on main 183f0b03b9 -> content-obstacle clearance + latency + R8 (run from repo root).
set -euo pipefail
D=physical/die_plan/qwen_kvsys; T=tools/die_plan; O=${1:?scratch dir}; FAMILY=kv3_hg,kv3_hg_v1,kv3_hg_v3
python3 $T/ft_sites_unblock.py $D/die_plan.json $O/plan_u1.json kv3_pv_v2,kv3_pv_v4,kv3_pv_v5,kv3_pv_v6,kv3_pv_v7,kv3_pv_v12 --report $O/unblock_pv.json
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));open(sys.argv[2],w).write(json.dumps(d,indent=1)+n)" $O/plan_u1.json $D/die_plan.json
python3 $T/gen.py latency $D/die_plan.json --inplace --out $O/lat
mkdir -p $O/r8; gzip -dc $D/r8/kv44_bus_groups.json.gz > $O/r8/bg_kv44.json
python3 $D/r8/r8_fault_exempt.py $O/r8/bg_kv44.json $O/r8/bg_fx.json
python3 $D/r8/r8_invariant_split.py $D/die_plan.json $O/r8/bg_fx.json $O/r8/bg_split.json
python3 $D/r8/r8_row_publish.py $D/die_plan.json $O/r8/bg_split.json $O/r8/bg_pub.json --family $FAMILY
python3 $D/r8/r8_rebase.py $D/die_plan.json $O/r8/bg_pub.json $D/r8/kv44_bind_latency.json.gz $O/r8/bus_groups.json
python3 $T/gen.py latency $D/die_plan.json --inplace --out $O/lat --groups $O/r8/bus_groups.json --bus leaf --replica type --fold-r8
cp $O/r8/bus_groups.json $O/lat/qwen_kvsys_r8_landing.json $D/r8/; mkdir -p $D/lat_v39r; cp $O/lat/qwen_kvsys_lat_pkg.sv $O/lat/qwen_kvsys_latency.json $D/lat_v39r/
python3 $T/check.py $D/die_plan.json --landing $D/r8/qwen_kvsys_r8_landing.json --out $O/g0 || true
python3 $T/check.py $D/die_plan.json --completeness --landing $D/r8/qwen_kvsys_r8_landing.json --out $O/g0c || true
python3 $T/proto_geom_scan.py $D/die_plan.json $O/proto_geom.json
python3 $T/reset_tree.py offsets $D/die_plan.json --out $D/reset_offsets_v39r.json > /dev/null
