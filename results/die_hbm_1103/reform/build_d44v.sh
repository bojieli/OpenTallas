#!/bin/bash
# DIE-HBM-61/PLAN: build HBM d44v from DIE-HBM-60/PLAN v4 (d44t + d44w + d44u + FT moves).  Order: templates (d) ->
# RE-FORM slots (class 2) -> slot infra (a: core_pg_connect) -> centre clock-entry pins (LAST plan change) -> sidecars
# (reform census, core clock regions).  usage: build_d44v.sh WORK OUT   (WORK = die-hbm-60-plan dir with p/v4, p/d44v_v0)
set -e
cd "$1"; OUT=$2; R=repo/results/die_hbm_1103/reform
K="ot_hbm_idx_qctl_static ot_hbm_idx_tail_native__v9496b22d4b49 ot_hbm_idx_tail_native__vf56d1f72f3f3 ot_hbm_static_cfg_collar_idx256r ot_hfd_coll_q2_hard_v8g__ring_ag ot_hnx_fused_tnode ot_hbm_idx_score_hcol_h1 ot_hbm_su_static_pgslice_lg__pretree"
python3 $R/mk_tmpl.py p/d44v_v0 p/v4 p/b1
python3 $R/mk_reform.py p/b1 p/b2 repo/tools/die_plan reform_v4.json | tail -1
python3 $R/mk_infra.py p/b2 p/b3 repo/tools/die_plan > /dev/null
rm -rf p/b4cx; python3 repo/tools/die_plan/clock_entry_pins.py p/b3 --keep $K --write p/b4cx | tail -1
rm -rf p/$OUT; cp -al p/b3 p/$OUT; rm p/$OUT/die_plan.json; cp p/b4cx/die_plan.json p/b4cx/centry_event.json p/$OUT/
cp --update=none p/b4cx/cores/* p/$OUT/cores/
python3 $R/mk_census.py reform_v4.json p/b2/reform_event.json p/$OUT/reform_census.json | head -1
python3 $R/mk_clkreg.py p/$OUT h61_geomcoll.json --keep $K
sha256sum p/$OUT/die_plan.json | cut -c1-12
