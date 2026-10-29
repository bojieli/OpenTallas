#!/bin/bash
# DIE-HEAD-17 start-stage pass N at hd_tile insertion LT/LF (copy of DIE-HEAD-15 iter.sh; run_ca17.sh instead of run_ca15.sh):
# emit(N) from the previous CA bind -> combo GRT TT/FF with the emitted stages -> CA chain -> emit(N+1) compare.
# usage: iter17.sh TAG N PREV_G LT LF   (PREV_G = clk dir whose ca/bind.json + proof_t seed emit N)
set -u
D=/srv/opentallas-scratch2/claude/die-head-17; TAG=$1; N=$2; PG=$3; LT=$4; LF=$5
E=$D/st_${TAG}_$N; G=$D/clk17_${TAG}_$N; K=/srv/opentallas-scratch2/claude/die-head-5/r2/grt/kit
MT=/srv/opentallas-scratch2/claude/wt/die-head-17/tools/die_plan
cd $MT && python3 start_stage_emit.py emit $PG/ca/bind.json $PG/proof_t --ctree /srv/opentallas-scratch2/claude/die-head-11/inv/g5_r200/clk --plan $PG/die_plan_root_sp5_lat${LT}.json --out $E | tail -1
mkdir -p $G; cp -r /srv/opentallas-scratch2/claude/die-head-15/clk15/clk $G/
for C in TT FF; do mkdir -p $G/out_$C; python3 /srv/opentallas-scratch2/claude/die-head-15/swap_st.py /srv/opentallas-scratch2/claude/die-head-14/clk14/out_$C $E $G/out_$C
 docker run --rm --name h17-combo-$TAG$N-$C --cpus=8 --memory=32g -v $K:/work:ro -v $G/out_$C:/out -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out" & done; wait
grep -h "^Total \|EXIT" $G/out_*/combo_*.log
sed -e "s#/srv/opentallas-scratch2/claude/die-head-15/st_emit/start_stages.json#$E/start_stages.json#" $D/run_ca17.sh > $D/run_ca17_${TAG}_$N.sh
bash $D/run_ca17_${TAG}_$N.sh $G $LT $LF > $D/run_ca17_${TAG}_$N.log 2>&1; grep -E "^PLAN |^START |^MC |COUNT-ALIGN (TT|FF)|FAIL" $D/run_ca17_${TAG}_$N.log | cut -c1-300
cd $MT && python3 start_stage_emit.py emit $G/ca/bind.json $G/proof_t --ctree /srv/opentallas-scratch2/claude/die-head-11/inv/g5_r200/clk --plan $G/die_plan_root_sp5_lat${LT}.json --out $D/st_${TAG}_$((N+1)) | tail -1
python3 - $E $D/st_${TAG}_$((N+1)) <<'P'
import json,sys
a={s["tree_path_id"]:s for s in json.load(open(sys.argv[1]+"/start_stages.json"))["stages"]};b={s["tree_path_id"]:s for s in json.load(open(sys.argv[2]+"/start_stages.json"))["stages"]}
diff=[k for k in set(a)|set(b) if k not in a or k not in b or any(a[k][f]!=b[k][f] for f in ("node_cell","flops","pad","edge_fall"))]
print("CONVERGE",sys.argv[1],"stages",len(a),len(b),"diffs",len(diff),"identical" if not diff else "")
P
