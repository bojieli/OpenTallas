#!/bin/bash
# DIE-HBM-61/PLAN: build HBM d44v from DIE-HBM-60/PLAN v4 (d44t + d44w + d44u + FT moves).  Order: templates (d) ->
# RE-FORM slots (class 2 + part-2 lane outlines: MEM channel_fit, pin-spread growth) -> slot infra (a: core_pg_connect) ->
# part-2 pin moves (PIN-BOUND) -> keybuf macros -> part-3 hcol_h1 mesh-island ft pins -> part-4 ep/cp_rxs right-width macros -> centre entries off macros -> hard-type core reset trees (q_sm) -> first-hop relay bays on
# the 8 die lanes over the 405 hop -> centre clock-entry pins (LAST plan change) -> sidecars (reform census, core clock
# regions, SPLIT sub-block slots, MEM recipe delta).  usage: build_d44v.sh WORK OUT   (WORK = die-hbm-60-plan dir)
set -e
cd "$1"; OUT=$2; R=repo/results/die_hbm_1103/reform; T=repo/tools/die_plan
K="ot_hbm_idx_qctl_static ot_hbm_idx_tail_native__v9496b22d4b49 ot_hbm_idx_tail_native__vf56d1f72f3f3 ot_hbm_static_cfg_collar_idx256r ot_hfd_coll_q2_hard_v8g__ring_ag ot_hnx_fused_tnode ot_hbm_idx_score_hcol_h1 ot_hbm_su_static_pgslice_lg__pretree"
S0="q_su31/L5r0_1,q_su31__physical_v1/L5r0_1,q_su31/L34r0_1,q_su31__physical_v1/L34r0_1,q_su31/L6br0_1,q_su31__physical_v1/L6br0_1,q_su00/L730x1,q_su00__physical_v1/L730x1,q_su01/L730x4,q_su01__physical_v1/L730x4"
python3 $R/mk_tmpl.py p/d44v_v0 p/v4 p/b1
python3 $R/mk_reform.py p/b1 p/b2 $T reform_v4.json $R/p2_outlines.json | tail -1
python3 $R/mk_infra.py p/b2 p/b3 $T > /dev/null
python3 $R/mk_repin.py p/b3
python3 $R/mk_kbmac.py p/b3
python3 $R/mk_mpisl.py p/b3
python3 $R/mk_rwmac.py p/b3
python3 $R/mk_cefix.py p/b3
python3 $R/mk_smrst.py p/b3 $T | cut -c1-300
cp p/b3/die_plan.json /tmp/h61_lat_before.json
python3 $R/mk_bays.py p/b3 $S0
(cd p/b3 && python3 ../../$T/gen.py latency die_plan.json --inplace --out ../../lat_p2 | tail -1)
python3 - p/b3 <<'PY'
import json, sys
A = json.load(open('/tmp/h61_lat_before.json'))['latency']['lanes']; B = json.load(open(sys.argv[1] + '/die_plan.json'))['latency']['lanes']
old = json.load(open('latency_changes.json'))
ch = {k: dict(before=old.get(k, {}).get('before', A[k]), after=B[k]) for k in B if A.get(k) != B[k]}
old.update(ch); json.dump(old, open(sys.argv[1] + '/latency_changes_d44v.json', 'w'), indent=1)
print('lanes with plan latency change (p2):', {k: (v['before']['cycles'], v['after']['cycles']) for k, v in ch.items()})
PY
rm -rf p/b4cx; python3 $T/clock_entry_pins.py p/b3 --keep $K --write p/b4cx | tail -1
rm -rf p/$OUT; cp -al p/b3 p/$OUT; rm p/$OUT/die_plan.json; cp p/b4cx/die_plan.json p/b4cx/centry_event.json p/$OUT/
cp --update=none p/b4cx/cores/* p/$OUT/cores/
python3 $R/mk_census.py reform_v4.json p/b2/reform_event.json p/$OUT/reform_census.json | head -1
python3 $R/mk_clkreg.py p/$OUT h61_geomcoll.json --keep $K
python3 $R/mk_split_slots.py p/$OUT $R/split_spec.json reform_v4.json > /dev/null
git -C repo show 55c4a61894a:physical/die_plan/hbm/mem_reform_1103/recipe_delta.json > p/$OUT/mem_recipe_delta.json
sha256sum p/$OUT/die_plan.json | cut -c1-12
