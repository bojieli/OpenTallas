#!/bin/bash
# PATH-KV: f7 + channel FT sites -> G2 table -> face budget -> G0C -> proto geom -> results dir
set -e
D=/srv/opentallas-scratch2/claude/path-kv; W=/srv/opentallas-scratch2/claude/wt/path-kv-1025
Q=$W/physical/die_plan/qwen_kvsys; R=$W/results/arch/kv_plan_0719/f7ch; mkdir -p $R
cd $Q
python3 g3/ft_bit_sites_chan.py die_plan.json kv3_hgi_v3,kv3_hgi,kv3_hgi_v6,kv3_hgi_v8,kv3_hub_Eo,kv3_hub_Wo,kv3_hgi_v5,kv3_pc_v3 $D/fin_plan.json --report $R/ft_bit_sites_chan.json --png-dir $R
cmp <(python3 -c "import json;print(json.dumps(json.load(open(\"$D/fin_plan.json\"))[\"partition_types\"],sort_keys=True))") <(python3 -c "import json;print(json.dumps(json.load(open(\"$D/chan6/plan_all.json\"))[\"partition_types\"],sort_keys=True))")
cp $D/fin_plan.json die_plan.json
python3 /srv/opentallas-scratch2/claude/path-kv/addtype.py $D/f7ch_g2
python3 g3/g2_table.py $D/f7ch_g2 --out $R/g2_f7ch.json
python3 $W/tools/die_plan/check.py die_plan.json --completeness --out $D/fin_g0a --quiet || true
python3 g3/face_budget.py die_plan.json --g0 $D/fin_g0a/g0_report.json --g2 $R/g2_f7ch.json --g2-ref results/arch/kv_plan_0719/f7ch/g2_f7ch.json > $R/face_budget.json
python3 $W/tools/die_plan/check.py die_plan.json --completeness --out $D/fin_g0c --quiet | tail -1 || true
cp $D/fin_g0c/g0_report.json $R/g0c_f7ch.json
cd ~/OpenTallas && python3 tools/die_plan/proto_geom_scan.py $Q/die_plan.json $R/proto_geom_f7ch.json | tail -1
