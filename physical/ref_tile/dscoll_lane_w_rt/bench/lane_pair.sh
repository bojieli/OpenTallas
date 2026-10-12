#!/bin/bash
# Two-lane protocol bench (rtl/dsrom_sys/s81_ph/test/tb_s81ph_gbx_pipeline_pair.sv) on this kit's lane RTL snapshot,
# tile params (GBX FMT1, EP PIPE2).  usage: lane_pair.sh <repo root> <out dir> <CH> [lane .sv override]
# prints the tb's "PAIR PASS ... records=... cycles=..." line; exit 0 only on PAIR PASS.
set -euo pipefail
R=$1; O=$2; CH=$3; LANE=${4:-$R/physical/ref_tile/dscoll_lane_w_rt/src/rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv}
S=$R/physical/ref_tile/dscoll_lane_w_rt/src/rtl
mkdir -p "$O"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -DOT_S81PH_GBX_FMT1 -DOT_S81PH_EP_PIPE2 \
  --top-module tb_s81ph_gbx_pipeline_pair -GCH=$CH -GBOARD=$((CH==400)) -GN=400 --Mdir "$O/b$CH" \
  $R/rtl/dsrom_sys/s81_ph/test/tb_s81ph_gbx_pipeline_pair.sv "$LANE" \
  $S/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv $S/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv \
  $S/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv $S/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv \
  $S/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv $S/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv $S/link/ot_link_crc32.sv \
  $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v > "$O/build$CH.log" 2>&1
timeout 3600 "$O/b$CH/Vtb_s81ph_gbx_pipeline_pair" > "$O/run$CH.log" 2>&1 || true
grep "PAIR PASS" "$O/run$CH.log"
