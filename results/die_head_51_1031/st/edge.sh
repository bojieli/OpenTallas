#!/bin/bash
# DIE-HEAD-51 helper st: re-run the l48c combo GRT (same script, deterministic) + FLOW-ONEMODEL-2 both-edge readout (T/F/N/M, polarity-resolved)
C=$1; R=/srv/opentallas-scratch2/claude/die-head-48; K=$R/clk/kit_l48c/kit; O=$R/st51/edge_$C
docker run --rm --name dh51st-edge-$C --memory=64g --memory-swap=64g --cpus=8 -e CORNER=$C \
  -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R 1000:1000 /out"
tail -n 2 $O/combo_$C.log
