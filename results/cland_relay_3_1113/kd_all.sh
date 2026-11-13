#!/bin/bash
# CLAND-RELAY-3: K / boot / RSTH-1 copy counts per die against the current plans (branch tools)
cd /srv/opentallas-scratch2/claude/cland-relay-3; T=wt/tools/die_plan; M=wt/physical/die_plan; mkdir -p kd
python3 -I kdelta_list.py $T rp18r2.json /srv/opentallas-scratch2/claude/kit-ops-1/head_rp18c/prep/source_sidecar.json > kd/head.txt 2>&1
python3 -I kdelta_list.py $T $M/qwen_kvsys/plan_of_record/plan_c.json $M/qwen_kvsys/plan_of_record/eW_sidecar.json > kd/kv.txt 2>&1
python3 -I kdelta_list.py $T $M/qwen_compute/plan_of_record/plan_qc99_s28.json /srv/opentallas-scratch2/claude/kw45/qcs28in/sidecar_pv_s28.json > kd/qc.txt 2>&1
python3 -I kdelta_list.py $T $M/s81/plan_h2_2249.json $M/s81/h2_2249/landed_sidecar_h2_psplit_all.json > kd/s81.txt 2>&1
for f in kd/*.txt; do echo "== $f"; sed -n 2,3p $f | cut -c1-300; done
