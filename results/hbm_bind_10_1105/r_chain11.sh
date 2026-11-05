#!/bin/bash
# HBM-BIND-10 t11: t7 elab chain (r_chain7.sh steps) on top t11_top.sv (obs re-home candidate), then strict bind of k13 with asbuilt_t11.json.
set -u
TAG=t11
W=/srv/opentallas-scratch2/claude/hbm-bind-6; H=/srv/opentallas-scratch2/claude/hbm-bind-5; R=/srv/opentallas-scratch2/claude/hbm-bind-4; T=$W/tip2
M=/srv/opentallas-scratch2/claude/hbm-bind-9; O=$M/e_$TAG; PL=$W/p7
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $O/dce $O/norm $O/fus
cd $T; python3 -I tools/die_plan/bind.py elab $PL/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_${TAG}_e.json --out $O/out --mem 48 > $O/elab.log 2>&1; echo ELAB $? $(date) | tee $O/elab.rc
[ -s $O/out/asbuilt.json ] || { echo ELAB_FAILED; grep -n ERROR $O/elab.log | head -5 | cut -c1-500; exit 1; }
python3 -I tools/hbm_b2/dead_scorer_loop_index.py $O/out/asbuilt.json --out $O/dce/asbuilt.json --receipt $O/dce/receipt.json 2>&1 | tail -2 | cut -c1-200; echo DCE ${PIPESTATUS[0]}
printf 'read_json "%s"\nmemory_collect\nmemory_map\nwrite_json "%s"\n' $O/dce/asbuilt.json $O/norm/asbuilt.json > $O/norm/asbuilt.ys
docker run --rm --name hb10-norm-$TAG --memory=48g --memory-swap=48g --cpus=4 --user $(id -u):$(id -g) -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/norm/asbuilt.yosys.log -s $O/norm/asbuilt.ys; echo NORM $?
python3 -I tools/hbm_b2/fused_lower_tree_splice.py splice $O/norm/asbuilt.json $O/fus/asbuilt.json $O/fus/receipt.json 2>&1 | tail -2 | cut -c1-200; echo FUS ${PIPESTATUS[0]}
python3 -I $H/pad_straps.py $PL/die_plan.json $O/pads_plan.json | tail -1 | cut -c1-200
python3 -I $H/patch_pads.py $O/fus/asbuilt.json $O/fus/pads.json $O/pads_plan.json $O/fus/pads_receipt.json; echo PADS $?
python3 -I $H/patch_c2.py $O/fus/pads.json $O/fus/c2.json $O/fus/c2_receipt.json; echo C2 $?
python3 -I $H/a/rename.py $R/g3/asbuilt.json $O/fus/c2.json $O/tj.json $O/rename_receipt.json 2>&1 | cut -c1-220 | tail -8
G=$M/g_${TAG}k13; mkdir -p $G
cp -al $O/tj.json $G/asbuilt.json; cp -al $O/out/asbuilt_sources.json $G/
cd $T; /usr/bin/time -v prlimit --as=120000000000 python3 -I tools/die_plan/bind.py bind $M/k13p/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_$TAG.json --out $G --strict --all-gaps --mem 48 > $M/g_${TAG}k13.bind.log 2>&1; echo RC $? $(date) | tee $M/g_${TAG}k13.rc
