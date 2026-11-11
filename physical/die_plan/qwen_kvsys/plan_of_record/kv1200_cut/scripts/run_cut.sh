#!/bin/bash
# DIE-KV-98 12:00 KV cut, ONE plan event. usage: run_cut.sh REPO OUTDIR   (REPO = checkout with tools/die_plan + this dir; run on epyc4 under nice -n 19)
# base = kw43/kvr2 (92370701) + overlays (e2s2, kvfix1, kvrs) + sreg + ringhold + phyrev (compose_cut.py) -> step0
# step1 CPL-KV-PV pv_S -> step2 CPL-KV-PV hub_Wi -> tapfix (clk_t70) -> step3 VIS-TRIAGE-KVHEAD hg + hgi -> step4 hgi_v6
set -euo pipefail
R=$1; OUT=$2; D=$R/physical/die_plan/qwen_kvsys; K=$D/plan_of_record/kv1200_cut; CS=$D/cleanslate_cplkvpv; VT=$K/cleanslate_vtkvhead
S=/srv/opentallas-scratch2/claude; B=$(readlink -f $S/kw43/kvr2); P=$D/plan_of_record/plan_c.json   # P = event28w_c, base of the CPL deltas
rm -rf $OUT; cp -al $B $OUT; rm $OUT/plan_c.json; cd $R
nice -n 19 python3 -I $K/scripts/compose_cut.py $B/plan_c.json $OUT/step0.json $K/scripts/ev \
  --types-from $S/kv-plan-2/plan_e2s2/plan_c.json=* --types-from $S/kv-plan-2/plan_kvfix1/plan_c.json=* --types-from $S/kw43/kvrs/plan_c.json=*
python3 -I $K/scripts/rebase_delta.py $P $OUT/step0.json $CS/delta_kv_pv_S.json $OUT/rb_1.json
(cd $OUT && python3 -I $CS/apply_delta.py $OUT/step0.json $OUT/rb_1.json $OUT/step1.json)
python3 -I $K/scripts/rebase_delta.py $P $OUT/step1.json $CS/delta_kv_hub_Wi.json $OUT/rb_2.json
(cd $OUT && python3 -I $CS/apply_delta.py $OUT/step1.json $OUT/rb_2.json $OUT/step2.json)
python3 -I $K/scripts/tapfix.py $OUT/step2.json $OUT/step2c.json
python3 -I $K/scripts/apply_cs.py $OUT/step2c.json $OUT/step3.json $VT/hg/delta_kv3_hg.json $VT/hgi_light/delta_kv3_hgi.json
python3 -I $K/scripts/apply_cs.py $OUT/step3.json $OUT/step4.json $VT/hgi_ft/delta_kv3_hgi_v6.json
cp $OUT/step4.json $OUT/plan_c.json
python3 -I $K/scripts/eq_diff.py $OUT/step0.json $OUT/plan_c.json || true
nice -n 19 python3 -I tools/die_plan/check.py $OUT/plan_c.json --out $OUT/g0 > $OUT/g0.log 2>&1 || true
python3 -I $K/scripts/g0_new.py $S/dkv98/g0_base_kvr2 $OUT/g0   # compare slot-level: see README
md5sum $OUT/plan_c.json; sha256sum $OUT/plan_c.json
