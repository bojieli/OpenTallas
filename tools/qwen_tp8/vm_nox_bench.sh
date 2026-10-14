#!/bin/bash
# TRIMMED central VM (no x read, OT_QFD_VM_NOX, 2026-10-14) bench runner, ONE case, ON a fleet host inside a synced tree:
#   vm_nox_bench.sh <root> <name> <kind: region|system> <expect: pass|fail> [-G / +define args ...]
# region = tb_qfd_vm_region_nx (ot_qfd_vm_region_nx vs the flat ot_qfd_vm_region_quarter, ro / so every clock)
# system = tb_qfd_vm_bv_ports +define+OT_QFD_VM_NOX (ot_qfd_sp_vector_memory_bv without the x read, region tile
#          ot_qfd_vm_region_nx): SU reads / writes, row reads, skid writes, ME result links, final image
# Writes <root>/<name>/{build.log,run.log}; exit 0 iff the expectation holds (a build failure is exit 2, never a kill).
root=$1; n=$2; kind=$3; expect=$4; shift 4
cd "$root/src" || exit 9
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012; N=rtl/qwen_sys/vm_nox_20261014
COMMON_SRC="$N/ot_qfd_vm_region_nx.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv
 $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv $P/ot_qfd_vm_xtree.sv
 rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
 rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv
 rtl/physical/ot_qwen_tree_delay_tiles.sv"
W="-Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT"
out=$root/$n; rm -rf "$out"; mkdir -p "$out"
if [ "$kind" = region ]; then
  top=tb_qfd_vm_region_nx; files="$N/tb_qfd_vm_region_nx.sv $COMMON_SRC"; pre=""
else
  top=tb_qfd_vm_bv_ports; files="rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv $COMMON_SRC"
  pre="-GCYCLES=40000 -GTSR=1 -GXQT=1 -GMEE=1 -GVMT=1 +define+OT_QFD_VM_NOX"
fi
# shellcheck disable=SC2086
$V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 $W -j 8 --top-module $top $pre "$@" \
   --Mdir "$out/obj" $files > "$out/build.log" 2>&1 || { echo "$n BUILD-FAIL"; grep -m5 -iE "%Error|Killed" "$out/build.log"; exit 2; }
/usr/bin/time -f "maxrss_kb=%M wall=%e" "$out/obj/V$top" > "$out/run.log" 2>&1
rc=$?
rm -rf "$out/obj"
echo "$n rc=$rc $(grep -E '^(PASS|FAIL)' "$out/run.log" | head -1 | cut -c1-260) $(grep maxrss "$out/run.log")"
if [ "$expect" = pass ]; then grep -q '^PASS' "$out/run.log" && ! grep -q '^FAIL' "$out/run.log"
else grep -q '^FAIL' "$out/run.log" && ! grep -q '^PASS' "$out/run.log"; fi
