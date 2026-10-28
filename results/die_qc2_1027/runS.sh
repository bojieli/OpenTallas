#!/bin/bash
# DIE-QC-2 NDR what-if on the C1w5 routed topology: clock-only SPEF x {none, trunk16w, all16w} -> ctree STA -> run dirs
set -u
D=/srv/opentallas-scratch2/claude/die-qc2-1027; R=$D/C1w5
for M in none trunk all; do
  mkdir -p $D/S_$M/out_TT $D/S_$M/out_FF; ln -sfn $R/clk $D/S_$M/clk
  for C in TT FF; do
    ( python3 -I $D/spef_ck.py $R/spef_$C/combo_$C.spef $D/S_$M/out_$C/ck_${M}_$C.spef $M $R/clk/tree.json $R/clk/ctree.v > $D/S_$M/spef_$C.log 2>&1
      docker run --rm --name dieqc2-sta-$M-$C-$$ --memory=16g --memory-swap=16g --cpus=2 -e CORNER=$C -e MODE=$M -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $R/clk:/clk:ro -v $D/S_$M/out_$C:/out -v $D/sta_spef.tcl:/sta.tcl:ro openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /sta.tcl > /out/sta_$C.log 2>&1; chown -R $(id -u):$(id -g) /out"
      cp $D/S_$M/out_$C/arr_${M}_$C.txt $D/S_$M/out_$C/arr_$C.txt ) &
  done
done
wait; echo S_DONE $(date)
