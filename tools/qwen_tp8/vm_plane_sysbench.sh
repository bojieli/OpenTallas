#!/bin/bash
# Bit-plane VM system bench (tb_qfd_vm_bv_ports), ONE run.  Runs ON the remote host inside a synced tree
# (default ~/claude-vm-rtl-1013/A/wt; override with VM_SYSB_WT / VM_SYSB_B).  Never run it on localhost.
#   vm_plane_sysbench.sh <name> "<-G args>" [extra verilator args / files ...]
# prints   <name> rc=<rc> <PASS/FAIL line> maxrss_kb=<sim peak> wall=<sim s> build_s=<s>
# The full set with expectations and the record writer: tools/qwen_tp8/vm_plane_sysbench_set.py
WT=${VM_SYSB_WT:-$HOME/claude-vm-rtl-1013/A/wt}; B=${VM_SYSB_B:-$HOME/claude-vm-rtl-1013/A/b}
cd "$WT" || exit 9; mkdir -p "$B"
n=$1; shift; g=$1; shift
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
rm -rf "$B/$n" "$B/$n.log" "$B/$n.build.log"
t0=$(date +%s)
# shellcheck disable=SC2086
$V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING \
   -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_vm_bv_ports \
   -GCYCLES=40000 -GTSR=1 -GXQT=1 -GMEE=1 -GVMT=1 $g "$@" --Mdir "$B/$n" \
   rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv \
   rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xtree.sv \
   rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv \
   rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv \
   rtl/hdc/ot_hdc_delay.sv > "$B/$n.build.log" 2>&1 \
   || { echo "$n BUILD-FAIL $(grep -m1 -E 'Error|terminated|Killed' "$B/$n.build.log" | cut -c1-160)"; exit 2; }
t1=$(date +%s)
/usr/bin/time -f "maxrss_kb=%M wall=%e" "$B/$n/Vtb_qfd_vm_bv_ports" > "$B/$n.log" 2>&1; rc=$?
echo "$n rc=$rc $(grep -E '^(PASS|FAIL)' "$B/$n.log" | head -1 | cut -c1-200) $(grep -E '^maxrss_kb=' "$B/$n.log" | tail -1) build_s=$((t1 - t0))"
