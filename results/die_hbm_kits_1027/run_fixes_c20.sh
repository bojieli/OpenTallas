#!/bin/bash
# DIE-HBM/KITS: C20 kits for the 6 HBM-local fixed types (canon wrappers x3, q2 oneclk wrappers x2, lane_exp0 macro placement)
W=/srv/opentallas-scratch2/claude/wt/die-hbm-kits-1027; F=/srv/opentallas-scratch2/claude/die-hbm-1027/kits/fixes
D=/srv/opentallas-scratch2/claude/die-hbm-1027/kits/c20b; V=$D/views_c20.json; K=$D/kits_fix; mkdir -p $K
G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
sdir() { dirname $(ls $D/slices_batch_0*/$1.json | head -1); }
view() { python3 -c "import json,sys;print([v['view'] for v in json.load(open('$V'))['view_list'] if v['module']=='$1'][0])"; }
cd $W/physical/die_plan/hbm_arch_cores
for m in ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691 ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77 ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526; do
  python3 $F/run_canon_kit.py $W $F --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag _c20fix > $K/gen_$m.log 2>&1; echo "$m rc=$?"
done
for m in ot_hfd_coll_q2_hard_v8g__reduce ot_hfd_coll_q2_hard_v8g__ring_ag; do
  python3 $G --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag _c20fix --wrapper $F/q2_oneclk_wrappers/$m.sv > $K/gen_$m.log 2>&1; echo "$m rc=$?"
done
m=ot_hbm_su_static_pgslice_lg__lane_exp0
python3 $G --views $V --view $(view $m) --out $K --master-slice $(sdir $m) --trial --tag _c20fix --macro-placement $F/B2n_inputs/exp_lane.json --macro-inst-fmt 'u_core.u_bank.u_data.g_read[{k}].u_m' > $K/gen_$m.log 2>&1; echo "$m rc=$?"
bash $W/results/die_hbm_kits_1027/pf_all.sh /srv/opentallas-scratch2/claude/die-hbm-1027/c20 $K $D/preflight_fix $W
