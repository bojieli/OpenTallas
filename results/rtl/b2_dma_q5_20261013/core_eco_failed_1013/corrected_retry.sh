#!/bin/bash
set -euo pipefail
DMA_OLD=/srv/opentallas-scratch/dma-core-repair-1013-v1
DMA_NEW=/srv/opentallas-scratch/dma-core-evidence-repair-2240
cd "$DMA_OLD/src"
export ORFS_IMAGE=openroad/orfs:latest ECO_SESSION=mm ECO_RB_DB=6_final.odb
export SETUP_LIB=TT HM=30 ALLOW=12 SM=40 FILT=40 PASSES=2 RESAWARE=1 HOLDCELLS=1
export ACC_SS=0 ACC_FF=0 THREADS=8 BUF=30 KEEPWIRES=0 ALLOW_FRESH_GRT=1
export MACROS=physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2
export ROUTE_CFG=$DMA_OLD/route_config.mk
BASE=$DMA_OLD/orfs/results/asap7/tile/base
bash "$DMA_NEW/helpers/hold_eco.sh" "$BASE" "$BASE" "$DMA_NEW/eco-corrected" ot_hgi_dma_kvw_core physical/hbm_accel_die_views/common/signoff_unc60.sdc physical/hbm_accel_die_views/common/vclk_corner_true.sdc physical/common_flow/link_budget_consistent.sdc physical/common_flow/io_ref_routed.sdc physical/common_flow/core_original_appended_ioref.sdc
