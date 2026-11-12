#!/bin/bash
# HBM-GEOM-2 11-12: one compose chain onto t40w (5129a5aab081)
set -e
G=/srv/opentallas-scratch2/claude/hbm-geom-2; C=/srv/opentallas-scratch2/claude/hbm-cut-1111/bin; O=$G/t40c
B0=/srv/opentallas-scratch2/claude/hbm-cut-1111/compose/t_tapsplit/comb2; T40=/srv/opentallas-scratch2/claude/hbm-vsn-xtap-t40w/plan_t40w
mkdir -p $O/d $O/m2plan; cd $O
for e in $G/qb010d/plan/*; do b=$(basename $e); [ $b = die_plan.json ] || ln -sfn $(readlink -f $e) m2plan/$b; done
python3 -I $G/m2layer.py $G/qb010d/plan/die_plan.json m2plan/die_plan.json
python3 -I $C/typedelta.py $B0 $G/phyflip5/plan/die_plan.json hg2_1_phy_flip_mcb_resite d/hg2_1_phy_flip_mcb_resite.json PHY_NW,PHY_NC,q_mcb_nw
python3 -I $C/typedelta.py $G/phyflip5/plan $G/qb010d/plan/die_plan.json hg2_2_qb010_lift d/hg2_2_qb010_lift.json q_b010
python3 -I $C/typedelta.py $G/qb010d/plan m2plan/die_plan.json hg2_3_m2_face_layer d/hg2_3_m2_face_layer.json PHY_NW,q_mcb_nw
D=/srv/opentallas-scratch2/claude/hbm-cut-1111/deltas
python3 -I $C/compose.py conflicts d/hg2_1_phy_flip_mcb_resite.json d/hg2_2_qb010_lift.json d/hg2_3_m2_face_layer.json $D/d11_nwio_ep_w52.json $D/d12_neio_ep_e52r.json $D/l3011_dlhbm_1112.json > conflicts.log 2>&1; echo "conflicts rc $?"; tail -5 conflicts.log
rm -rf t40c
python3 -I $C/compose.py apply $T40 t40c apply.log d/hg2_1_phy_flip_mcb_resite.json d/hg2_2_qb010_lift.json d/hg2_3_m2_face_layer.json $D/d11_nwio_ep_w52.json $D/d12_neio_ep_e52r.json
tail -8 apply.log
sha256sum t40c/die_plan.json
