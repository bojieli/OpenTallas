#!/bin/bash
# DIE-KV-61/grt variant chain (DIE-KV-58 recipe end to end) for pad variant V:
#  ot_clk kit (kv61_vV.yaml) -> bind remap (tree_kv58 -> new) -> tap GRT TT -> tap readout -> tap arrivals -> START emit (wide row search)
#  -> START-loaded combo GRT TT+FF (parallel, 48 GB docker each) -> both-edge readout -> proof -> die STA (nom61.sh, hold >= 0)
# usage: chain_v.sh V      (run under one ot-run reservation of ~100 GB)
set -u; V=$1; B=/home/ubuntu/scratch-root/claude/die-kv-61/grt; S=$B/wt/tools/die_plan; P=$B/wt/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json
D=$B/v$V; rm -rf $D; mkdir -p $D; cd $D; IMG=openroad/orfs:latest
log(){ echo "$1 $(date '+%F %T')" >> $D/CHAIN.log; }
docker run --rm --name dkv61-v$V-tree --memory=24g --memory-swap=24g --cpus=4 -u 1000:1000 -v $B:$B $IMG bash -lc "cd $B/wt && python3 tools/clk/ot_clk.py kit $B/kv61_v$V.yaml --out $D/tree > $D/tree.log 2>&1"; log "TREE $?"
K=$D/tree/kit; [ -s $K/clock/tree.json ] || { log FAIL_TREE; exit 2; }
python3 $B/bind_remap.py $B/in/die-kv-58/clk/tree_kv58/kit/clock/tree.json $K/clock/tree.json $B/in/die-kv-58/clk/bind_kv58.json $D/bind.json $D/bind_map.json > $D/remap.log 2>&1; log "REMAP $? $(cat $D/remap.log)"
grt(){ # tag corner clkdir
  local R=$D/grt_$1; local O=$R/out_$2; mkdir -p $R/clk $O
  cp $3/ctree.v $K/clock/tree.json $R/clk/; cp $3/ctree.tcl $R/clk/ctree_ck89.tcl
  CORNER=$2 ADJ=0.75 ADJ7=0 python3 $B/mk_combo_kv.py $K $R/clk $O || return 1
  python3 $B/duty_patch.py $O/combo.tcl || return 1
  docker run --rm --name dkv61-v$V-grt-$1-$2 --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$2 -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$2.log 2>&1; echo EXIT \$? >> /out/combo_$2.log; chown -R 1000:1000 /out"
}
readout(){ # tag corner outdir
  bash $B/mk_read.sh $D/grt_$1/clk/ctree.v $D/read_$1.tcl || return 1; mkdir -p $3
  docker run --rm --name dkv61-v$V-read-$1-$2 --memory=32g --memory-swap=32g --cpus 4 -e CORNER=$2 -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $D:/w -v $3:/out -v $D/grt_$1:/n:ro -v $K:/work:ro $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /w/read_$1.tcl > /out/read.log 2>&1; r=\$?; chown -R 1000:1000 /out; exit \$r"
}
grt tap TT $K/clock; log "GRT_TAP $(grep -h EXIT $D/grt_tap/out_TT/combo_TT.log)"
readout tap TT $D/edges_tap_TT; log "READ_TAP $?"
mkdir -p $D/pcomp_tap; cp $B/in/die-kv-58/clk/pcomp/{mesh.json,droop_regions.json} $D/pcomp_tap/
python3 $S/trial_tap_arrivals.py $D/grt_tap/clk/tree.json $D/edges_tap_TT/arr_TT.txt TT $D/pcomp_tap/tap_arrivals_TT.json --node-cell-names --clock-components --physical-paths > $D/comp_tap_TT.txt 2>&1; log "TTA_TAP $?"
docker run --rm --name dkv61-v$V-emit --memory=24g --cpus=2 -u 1000:1000 -v $B:$B $IMG bash -lc "cd $S && python3 $B/emit_wide.py 400 $S emit $D/bind.json $D/pcomp_tap --ctree $K/clock --plan $P --reset-wave --path-encoding base36 --out $D/em" > $D/em.log 2>&1; log "EMIT $? $(tail -n 1 $D/em.log)"
grt st TT $D/em & grt st FF $D/em & wait; log "GRT_ST $(grep -h EXIT $D/grt_st/out_*/combo_*.log | tr '\n' ' ')"
readout st TT $D/edges_TT & readout st FF $D/edges_FF & wait; log "READ_ST"
mkdir -p $D/pcomp; cp $B/in/die-kv-58/clk/pcomp/{mesh.json,droop_regions.json} $D/pcomp/
for C in TT FF; do python3 $S/trial_tap_arrivals.py $D/grt_st/clk/tree.json $D/edges_$C/arr_$C.txt $C $D/pcomp/tap_arrivals_$C.json --node-cell-names --clock-components --physical-paths > $D/comp_$C.txt 2>&1; log "TTA_$C $?"; done
python3 $S/start_stage_emit.py proof $D/pcomp --stages $D/em/start_stages.json --arr TT=$D/edges_TT/arr_TT.txt --arr FF=$D/edges_FF/arr_FF.txt --clock-netlist $D/em/ctree.v --out $D/proof_loaded > $D/proof.log 2>&1; log "PROOF $?"; cp $D/em/ctree.v $D/proof_loaded/
nice bash $B/nom61.sh $D/proof_loaded $P $D/sta_grt $D/bind.json; log "STA $(grep -h 'STA rc' $D/sta_grt.log)"
log CHAIN_DONE
