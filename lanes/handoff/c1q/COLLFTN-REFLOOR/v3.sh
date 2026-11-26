#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude
W=$D/QC-COLLFTN-REFLOOR
F=$W/tree
O=$D/kw45/snap_qwen_compute/qwen_compute_c1p_r6_1125
V=$D/kw45/snap_qwen_compute/qwen_compute_v4c4
R=$D/rt/afdd397cad26/tools
Q=physical/die_plan/qwen_compute
BASE=$O/$Q/plan_of_record/zz_c1p_colla_sitemacro_1125.json
SB=$Q/plan_of_record/sink_bins/hf1c/coll_ftn_c1q_refloor.json
P=$F/$Q/plan_of_record/zz_c1q_collftn_refloor_1125.json
python3 -I $W/collftn_v3.py $W/zz_c1q_collftn_refloor_1125.json $W/v3_pre_retap.json $O/$Q/plan_of_record/sink_bins/hf1c/coll_ftn_s4q9l2d.json $F/$SB $SB > $W/v3_edit.log 2>&1; echo "EDIT rc=$?"; tail -1 $W/v3_edit.log
export OT_REPO_ROOT=$F OT_PLAN_ROOT=$F/$Q OT_LANE=QC-COLLFTN-REFLOOR PYTHONDONTWRITEBYTECODE=1
cd $F
python3 -I $R/die_plan/retap.py $BASE $W/v3_pre_retap.json $W/v3.json --types coll_ftn --republish-reset --report $W/retap_report.json > $W/retap.log 2>&1; echo "RETAP rc=$?"; tail -5 $W/retap.log
cp $W/v3.json $P; sha256sum $P
export OT_RESETPUB_SOLVE=1
python3 -I $R/die_plan/compose_drop_guard.py $BASE $P --json $W/guard_v3.json > $W/guard_v3.log 2>&1; echo "GUARD rc=$?"; tail -1 $W/guard_v3.log
python3 -I $R/die_plan/plan_gate_pre.py check --tree $F --plan $P --asbuilt $F/$Q/qc_start_1106/runtime/asbuilt_c1p_1125.json --remap-base $V/$Q/plan_of_record/zz_s29_qc103_s4q9n46r4_final_preview.json --rows-proof $F/$Q/plan_of_record/rows_proofs/qc_c1p_sc_rows_proof_1125.json --json $W/pre_v3.json > $W/pre_v3.log 2>&1
echo "PRE rc=$?"; grep -F 'PLAN-GATE-PRE' $W/pre_v3.log | tail -1
mkdir -p $W/g0_v3; python3 -I $R/die_plan/check.py $P --out $W/g0_v3 --repo-root $F > $W/g0_v3.log 2>&1; echo "G0 v3 rc=$?"; grep "G0 PASS\|G0 FAIL" $W/g0_v3.log | tail -1 | cut -c1-200
