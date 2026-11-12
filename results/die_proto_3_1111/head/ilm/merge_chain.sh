#!/bin/bash
# DIE-PROTO-1: HEAD-94 merge_parts (b96976f417) -> kit/GRT -> GRT spef -> die_ctree -> HEAD ILM nominal (hd_spn_end real)
set -u; B=/srv/opentallas-scratch2/claude/die-proto-3; WM=/srv/opentallas-scratch2/claude/wt/die-proto-3m; W=/srv/opentallas-scratch2/claude/wt/die-proto-3
I=$B/head/ilm; R=$B/head/fregm; L=$B/head/merge_chain.log
echo "START $(date)" > $L
PB=$B PW=$WM GM=48g OTCLK=$B/head/cfg/head_freg_merge.yaml bash $B/proto_die.sh head $WM/physical/die_plan/s81_head/plan_of_record/l48hp1/source_plan_freg.json fregm >> $L 2>&1
echo "PROTO rc=$? $(date)" >> $L; cat $R/CHAIN.log >> $L
bash $B/spef_grt.sh $R 48g >> $L 2>&1; echo "SPEF rc=$? $(date)" >> $L
[ -s $R/die_ctree/ctree.spef ] || { echo FAIL_CTREE >> $L; exit 2; }
mkdir -p $I/run_tree2nm && cp -a $I/run_tree2n/ilm $I/run_tree2nm/ 2>/dev/null
sed -e "s#run_tree2n#run_tree2nm#g" -e "s#io_hold_parent_tree2n#io_hold_parent_tree2nm#" -e "s#ihp_tree2n#ihp_tree2nm#" -e "s#ILM_tree2n.log#ILM_tree2nm.log#g" \
    -e "s#head/freg/die_ctree#head/fregm/die_ctree#" $I/ilm_head_tree2n.sh > $I/ilm_head_tree2nm.sh
grep -q "fregm/die_ctree" $I/ilm_head_tree2nm.sh || { echo FAIL_SED >> $L; exit 3; }
( cd $I && bash ilm_head_tree2nm.sh ) >> $L 2>&1; echo "ILM rc=$? $(date)" >> $L
echo MERGE_CHAIN_DONE >> $L
