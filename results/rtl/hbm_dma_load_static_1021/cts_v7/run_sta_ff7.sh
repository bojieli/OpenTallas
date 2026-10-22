#!/bin/bash
set -euo pipefail
DMA_FF_HOME=/srv/opentallas-scratch/claude/ref_gate/hbm_dma_load_static_m7-20261021-223238
for tag in m7 b7; do
 if [ "$tag" = m7 ];then DMA_FF_CASE=$DMA_FF_HOME;else DMA_FF_CASE=/srv/opentallas-scratch/claude/ref_gate/hbm_dma_load_static_b7-20261021-223239;fi
 DMA_FF_BASE=$DMA_FF_CASE/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_svc_vmdel_lane_load_static_asap7_ref_gate/base
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/hbm_dma_load_static_$tag/signoff.sdc -v "$DMA_FF_CASE/src:/src:ro" -v "$DMA_FF_BASE:/base:ro" -v "$DMA_FF_HOME/sta_ff7.tcl:/sta_ff7.tcl:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /sta_ff7.tcl > "$DMA_FF_HOME/ff_$tag.log" 2>&1
 echo "DMA_FF_CASE $tag"
 grep '^DMA_FF ' "$DMA_FF_HOME/ff_$tag.log"
done
