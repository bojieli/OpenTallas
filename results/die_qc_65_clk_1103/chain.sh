#!/bin/bash
# DIE-QC-65/CLK: v2 config (early-merge su_l0/l1 + all su_c merge) on POST-RED plan_qc52 (main 79420b14aaa):
# ot_clk kit (main tools) -> combo GRT50 TT+FF -> tap arrivals -> die STA (main plan + need dump)
set -u
V=$1; N=/home/ubuntu/scratch-root/claude/die-qc-65-clk; O=/home/ubuntu/scratch-root/claude/die-qc-64-clk; R=$N/$V; W=$N/mainwt
log(){ echo "$1 $(date "+%F %T")" >> $R/CHAIN.log; }
cd $W; export PYTHONPATH=/home/ubuntu/scratch-root/claude/die-qc-63-clk/fh
python3 tools/clk/ot_clk.py check $R/config.yaml > $R/check.log 2>&1 || { log "CHECK FAIL"; exit 1; }
log "KIT start"
timeout 6h python3 tools/clk/ot_clk.py kit $R/config.yaml --out $R/emitted > $R/kit.log 2>&1; log "KIT rc=$?"
K=$R/emitted/kit; [ -s $K/clock/tree.json ] || { log FAIL_TREE; exit 2; }
G=$N/grt_tools_ref
run(){ local C=$1; local Q=$R/grt/out_$C; mkdir -p $Q
  CORNER=$C python3 $G/mk_combo_qc.py $K $K/clock $Q > $Q/mk.log 2>&1 && python3 $G/drop_pst.py $Q/combo.v >> $Q/mk.log 2>&1 || { log "MK_$C FAIL"; return 1; }
  docker run --rm --name dqc65clk-$V-grt-$C --memory=80g --memory-swap=80g --cpus=8 -e CORNER=$C \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $Q:/out openroad/orfs:latest \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
  log "GRT_$C $(grep -h -E "^EXIT|^Total " $Q/combo_$C.log | tr "\n" " ")"
}
run TT & run FF & wait
S=$W/tools/die_plan; P=$W/physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json; PR=$R/proof; mkdir -p $PR
for C in TT FF; do python3 $S/trial_tap_arrivals.py $K/clock/tree.json $R/grt/out_$C/arr_$C.txt $C $PR/tap_arrivals_$C.json --node-cell-names > $PR/tta_$C.log 2>&1; log "TTA_$C $?"; done
mkdir -p $R/need; OT_NEED_DUMP=$R/need/need python3 $N/needtool/die_sta_related.py $PR --plan $P --out $R/sta --corner TT --corner FF --margin-policy nominal --cppr-lca --clock-cell inv2 > $R/sta.log 2>&1; log "STA rc=$?"
log DONE
