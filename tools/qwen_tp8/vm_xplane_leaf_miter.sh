#!/bin/bash
# remote leaf miter: rleaf.sh name [-G...]
cd ~/claude-vm-1013/wt || exit 9
n=$1; shift; B=~/claude-vm-1013/b
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -j 8 --top-module tb_qfd_vm_xplane -GNRB=16 -GELEMS=16384 "$@" --Mdir $B/$n rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_xplane.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv > $B/$n.build.log 2>&1 || { echo "$n BUILD-FAIL"; grep -m5 Error $B/$n.build.log; exit 2; }
/usr/bin/time -f "maxrss_kb=%M wall=%e" $B/$n/Vtb_qfd_vm_xplane > $B/$n.log 2>&1; echo "$n rc=$? $(grep -E 'PASS|FAIL' $B/$n.log | head -1) $(grep maxrss $B/$n.log)"
