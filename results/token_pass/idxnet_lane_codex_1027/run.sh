#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/wt/codex-idxnet-tx-0954
O=/srv/opentallas-scratch2/claude/codex-idxnet-tx-0954/route3
p=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for mutant in 0 6; do
 d=$O/lane_m$mutant
 mkdir -p "$d"
 verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DTX_LANE_MUTANT=$mutant --top-module tb_idxnet_tx_lane --Mdir "$d/obj" --build-jobs 4 rtl/lib/ot_rst_relay.sv "$p" rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv tools/s81_dv/layer_prog/tb_idxnet_tx_lane.sv > "$d/build.log" 2>&1
 if [ "$mutant" = 0 ];then
  for dst in 0 1 2; do for lane in 0 1 2 3; do "$d/obj/Vtb_idxnet_tx_lane" +DST=$dst +LANE=$lane > "$d/dst${dst}_lane$lane.log" 2>&1; done; done
 else
  set +e
  "$d/obj/Vtb_idxnet_tx_lane" +LANE=0 > "$d/mutant.log" 2>&1
  rc=$?
  set -e
  test "$rc" != 0
  grep TX_PHYSICAL_LANE "$d/mutant.log"
 fi
 done
 echo IDXTX_LANE_GATE_PASS
