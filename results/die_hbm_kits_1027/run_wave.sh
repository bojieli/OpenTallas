#!/bin/bash
# DIE-HBM-3/KITS: kit wave on any HBM plan (generalises run_c20.sh + run_fixes_c20.sh).
#   run_wave.sh PLANDIR WAVE TAG "EXCL_REGEX"   (on intel2)
# views -> mk_c20 (4 batches) -> 6 HBM-local fixed types -> kit_preflight (shared, plan = PLANDIR)
set -u
P=$1; WAVE=$2; TAG=$3; EXCL=$4
W=/srv/opentallas-scratch2/claude/wt/die-hbm-kits-1027; F=/srv/opentallas-scratch2/claude/die-hbm-1027/kits/fixes
D=/srv/opentallas-scratch2/claude/die-hbm-1027/kits/$WAVE; mkdir -p $D; cd $D
echo "$(date) start plan $(cut -c1-12 $P/die_plan.sha256) src $(git -C $W rev-parse --short=10 HEAD) excl $EXCL"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views.json ) > $D/views.log 2>&1
tail -n +2 /srv/opentallas-scratch2/claude/hbm-streets3-1027/kits/native_view_kits.tsv | cut -f1 \
  | grep -v -E "tailx_sk_steady|topk_link_static" | grep -v -E "$EXCL" | sort -u > $D/mods.txt
grep -E "$EXCL" <(tail -n +2 /srv/opentallas-scratch2/claude/hbm-streets3-1027/kits/native_view_kits.tsv | cut -f1) | sort -u > $D/wait_c20f.txt
split -n r/4 -d $D/mods.txt $D/batch_
for b in batch_00 batch_01 batch_02 batch_03; do
  MKTAG=_$b python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views.json $D/slices_$b $D/kits $W $(paste -sd, $b) --tag $TAG > $D/mk_$b.log 2>&1 &
done
wait; echo "$(date) gen done"
V=$D/views.json; K=$D/kits_fix; mkdir -p $K; G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
sdir() { dirname $(ls $D/slices_batch_0*/$1.json | head -1); }
view() { python3 -c "import json;print([v[\"view\"] for v in json.load(open(\"$V\"))[\"view_list\"] if v[\"module\"]==\"$1\"][0])"; }
cd $W/physical/die_plan/hbm_arch_cores
for m in ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691 ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77 ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526; do
  python3 $F/run_canon_kit.py $W $F --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag ${TAG}fix > $K/gen_$m.log 2>&1; echo "$m rc=$?"
done
for m in ot_hfd_coll_q2_hard_v8g__reduce ot_hfd_coll_q2_hard_v8g__ring_ag; do
  python3 $G --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag ${TAG}fix --wrapper $F/q2_oneclk_wrappers/$m.sv > $K/gen_$m.log 2>&1; echo "$m rc=$?"
done
m=ot_hbm_su_static_pgslice_lg__lane_exp0
python3 $G --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag ${TAG}fix --macro-placement $F/B2n_inputs/exp_lane.json --macro-inst-fmt "u_core.u_bank.u_data.g_read[{k}].u_m" > $K/gen_$m.log 2>&1; echo "$m rc=$?"
echo "$(date) fixes done"
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $D/kits $D/preflight $W > $D/pf_all.log 2>&1
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $K $D/preflight_fix $W > $D/pf_fix.log 2>&1
echo "$(date) preflight done"; touch $D/RUN_DONE
