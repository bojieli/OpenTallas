#!/bin/bash
set -u
R=${VM_RTL_ROOT:-$(pwd)}; B=${VM_RTL_OUT:-/tmp/qwen-xcol-select}; mkdir -p "$B"; cd "$R" || exit 9
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
one() { n=$1; shift
 "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD -j 2 --top-module tb_qfd_vm_xcol_roots "$@" --Mdir "$B/$n" rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_xcol_roots.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xcol_roots.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xtree.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv > "$B/$n.build.log" 2>&1 || { echo "$n BUILD_FAIL"; return; }
 "$B/$n/Vtb_qfd_vm_xcol_roots" > "$B/$n.log" 2>&1
 echo "$n $(grep -E '^(PASS|FAIL)' "$B/$n.log" | head -1)"
}
one ok & one seed2 -GSEED=2 & one native -GNRB=64 -GSMAX=9 & one prod -GNRB=64 -GSMAX=11 &
one live -GSNAPSHOT=0 -GNRB=64 -GSMAX=11 & one mut1 -GMUT=1 & one mut2 -GMUT=2 & one mut3 -GMUT=3 & one mut4 -GMUT=4 & one mut5 -GMUT=5 & wait
