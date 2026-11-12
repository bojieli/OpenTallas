#!/bin/bash
# DIE-PROTO-3 (ADVISORY, DO_NOT_COUNT): HEAD FREG die STA ILM (17 signed real views + 9 budget stand-ins) + io_hold_parent
set -u; B=/srv/opentallas-scratch2/claude/die-proto-3; W=/srv/opentallas-scratch2/claude/wt/die-proto-3; I=$B/head/ilm
PLAN=$W/physical/die_plan/s81_head/plan_of_record/l48hp1/source_plan_freg.json; TL=$W/tools/die_plan
SI=ot_s81hd_ctl,ot_s81hd_host_e_ep,ot_s81hd_host_w_ep,ot_s81hd_lep0N,ot_s81hd_mesh_ep,ot_s81hd_serdes,ot_s81hd_spn_end_strip,ot_s81hd_spn_strip,ot_s81hd_spn_wshim_rx
cd $I; echo "START $(date)" > ILM_tree.log
( cd $TL && prlimit --as=96000000000 nice python3 -s die_sta.py run --top $I/die_top.v --parts $I/parts --out $I/run_tree --mode ilm \
    --corner TT --corner FF --spine-tree /srv/opentallas-scratch2/claude/die-proto-3/head/freg/die_ctree --crpr-pairs 400 --threads 16 ) > $I/run_tree.log 2>&1
echo "RUN rc=$? $(date)" >> ILM_tree.log
( cd $TL && nice python3 -s io_hold_parent.py $PLAN $I/run_tree/die_sta.json --all-seams --standin-types $SI --out $I/io_hold_parent_tree.json ) > $I/ihp_tree.log 2>&1
echo "IHP rc=$? $(date)" >> ILM_tree.log; echo ILM_DONE >> ILM_tree.log
