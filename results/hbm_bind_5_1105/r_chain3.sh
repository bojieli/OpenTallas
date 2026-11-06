#!/bin/bash
# tail of the t1 chain after elab PID $2 ends (fresh copy; r_t1.sh had no yosys path)
set -u
TAG=$1
W=/srv/opentallas-scratch2/claude/hbm-bind-5; R=/srv/opentallas-scratch2/claude/hbm-bind-4; T=$R/tip; O=$W/e_$TAG
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $O/dce $O/norm $O/fus $W/g_$TAG; D=$T/physical/die_plan/hbm/bind/d44v
cp $W/$TAG/top.sv $D/inputs/${TAG}_top.sv; cp $W/$TAG/map.json $D/inputs/${TAG}_map.json
python3 -I - <<P
import json
for src,dst in (("asbuilt_e2.json","asbuilt_${TAG}_e.json"),("asbuilt.json","asbuilt_${TAG}.json")):
    a=json.load(open("$D/"+src))
    a["netlist"]=["physical/die_plan/hbm/bind/d44v/inputs/${TAG}_top.sv"]; a["map_file"]="inputs/${TAG}_map.json"
    a["declared_ties"]=json.load(open("$W/$TAG/declared_ties.json"))
    a["straps"]=list(a["straps"])+[".*\\.pad_[kb]"]
    a["note"]="HBM-BIND-5 ${TAG} candidate: kb_ctl + S emission + pad straps + candidate ties, unproven | "+a["note"]
    json.dump(a,open("$D/"+dst,"w"),indent=1)
P
cd $T; python3 -I tools/die_plan/bind.py elab $W/b0b/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_${TAG}_e.json --out $O/out --mem 48 > $O/elab.log 2>&1; echo ELAB $? $(date) | tee $O/elab.rc
[ -s $O/out/asbuilt.json ] || { echo ELAB_FAILED $(date); grep -n ERROR $O/elab.log | head -5 | cut -c1-400; exit 1; }
echo ELAB done $(date)
cd $T
python3 -I tools/hbm_b2/dead_scorer_loop_index.py $O/out/asbuilt.json --out $O/dce/asbuilt.json --receipt $O/dce/receipt.json 2>&1 | tail -2 | cut -c1-200; echo DCE ${PIPESTATUS[0]}
printf 'read_json "%s"\nmemory_collect\nmemory_map\nwrite_json "%s"\n' $O/dce/asbuilt.json $O/norm/asbuilt.json > $O/norm/asbuilt.ys
docker run --rm --name hb5-norm-$TAG --memory=48g --memory-swap=48g --cpus=4 --user $(id -u):$(id -g) -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/norm/asbuilt.yosys.log -s $O/norm/asbuilt.ys; echo NORM $?
python3 -I tools/hbm_b2/fused_lower_tree_splice.py splice $O/norm/asbuilt.json $O/fus/asbuilt.json $O/fus/receipt.json 2>&1 | tail -2 | cut -c1-200; echo FUS ${PIPESTATUS[0]}
python3 -I $W/patch_pads.py $O/fus/asbuilt.json $O/fus/pads.json $W/pads.json $O/fus/pads_receipt.json; echo PADS $?
python3 -I $R/rename.py $R/g3/asbuilt.json $O/fus/pads.json $O/tj.json $O/rename_receipt.json 2>&1 | cut -c1-220 | head -40
mkdir -p $W/g_$TAG; cp -al $O/tj.json $W/g_$TAG/asbuilt.json; S=$O/out/asbuilt_sources.json; [ -s $S ] || S=$R/g4/asbuilt_sources.json; cp -al $S $W/g_$TAG/
bash $W/rb.sh $W/b0b/die_plan.json $W/g_$TAG asbuilt_${TAG}.json; cat $W/g_$TAG.rc; echo CHAIN_END $(date)
