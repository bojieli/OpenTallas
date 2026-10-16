#!/bin/bash
# Q-B2 10-16: build the REF-vs-DUT lane-route equivalence bench once; then run it per route/strap configuration.
# usage: run_lane_route_bench.sh build OUT TB_SV [CAL_DIR...]
#        run_lane_route_bench.sh run   OUT NAME IMAGES [+TC=n +AM=n +LC=n +F=n +R=n +SEL=n +TY=n +HL=n]
set -eu
mode=$1;out=$2
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
if [ "$mode" = build ];then
 tb=$3;shift 3
 mkdir -p "$out"
 grep -v 'tools/qwen_b2_join/tb_b2_rom_e3.sv' tools/qwen_b2_join/rom_e3_sources.f > "$out/sources.f"
 for f in rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/physical/ot_qwen_spine_lane.sv rtl/physical/ot_qwen_halfband_lanes_slots.sv \
   rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv rtl/physical/ot_qwen_halfband_lanes_slots_b2_l2.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv;do
  grep -qx "$f" "$out/sources.f" || echo "$f" >> "$out/sources.f"
 done
 for c in "$@";do ls "$c"/*.sv >> "$out/sources.f";done
 echo "$tb" >> "$out/sources.f"
 sha256sum $(cat "$out/sources.f") > "$out/source.sha256"
 "$VL" --binary --timing -j 16 -O1 -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFD_VM_PARTITIONED_CLOCKS -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 \
   -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-LATCH -Irtl/hdc --top-module tb_b2_lane_route --Mdir "$out/obj" -f "$out/sources.f" > "$out/build.log" 2>&1
 echo BUILT
else
 name=$3;images=$4;shift 4
 "$out/obj/Vtb_b2_lane_route" +OT_ROM_DIR="$images/rank0/masks" "$@" > "$out/$name.log" 2>&1 && echo "$name PASS" || echo "$name FAIL rc=$?"
 grep -E "^PASS|^FAIL|MISMATCH|FAULT" "$out/$name.log" | head -5
fi
