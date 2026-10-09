#!/usr/bin/env bash
# Control-sequencing campaign of the full-shape Qwen ROM control plane (stream qwen-system).
# usage: run_ctl.sh <repo> <ctl_golden.py out dir> <work dir>
set -uo pipefail
repo=$1; gold=$2; wd=$3
mkdir -p "$wd"
src=("$repo/rtl/test/qwen_system/tb_qfd_ctl_sys.sv" "$repo/rtl/qwen_sys/system_20261008/ot_qfd_sysctl.sv"
     "$repo/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$repo/rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv"
     "$repo/rtl/host/ot_host_if.sv" "$repo/rtl/qwen_sys/ot_qwen_sys_csr.sv" "$repo/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv"
     "$repo/rtl/lib/ot_reset_sync.sv")
build() {  # name CL WDOG
  verilator --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY \
    -Wno-INITIALDLY -Wno-BLKSEQ -I"$gold" -DCL=$2 -DWDOG=$3 --top-module tb_qfd_ctl_sys -Mdir "$wd/obj_$1" \
    "${src[@]}" > "$wd/build_$1.log" 2>&1 || { echo "BUILD FAIL $1"; tail -20 "$wd/build_$1.log"; }
}
build f40 40 5000 & build m1 1 1048576 & build m40 40 1048576 & build m170 170 1048576 & wait
run() {  # tag binary args...
  local tag=$1 b=$2; shift 2
  "$wd/obj_$b/Vtb_qfd_ctl_sys" "$@" > "$wd/run_$tag.log" 2>&1
  echo "$tag: $(grep -h 'CTL_RESULT' "$wd/run_$tag.log" | tail -1)"
}
S=$gold
run eos      f40 +SCEN=$S/scen_eos.hex &
run length   f40 +SCEN=$S/scen_length.hex &
run badlen   f40 +SCEN=$S/scen_badlen.hex &
run fullctx  f40 +SCEN=$S/scen_fullctx.hex &
run f_seq    f40 +SCEN=$S/scen_eos.hex +FAULT_DIE=2 +FAULT_STEP=1 +FAULT_STAGE=17 +FAULT_KIND=1 &
run f_core   f40 +SCEN=$S/scen_eos.hex +FAULT_DIE=0 +FAULT_STEP=4 +FAULT_STAGE=37 +FAULT_KIND=2 &
run f_coll   f40 +SCEN=$S/scen_eos.hex +FAULT_DIE=3 +FAULT_STEP=2 +FAULT_STAGE=1 +FAULT_KIND=3 &
run f_hang   f40 +SCEN=$S/scen_eos.hex +FAULT_DIE=1 +FAULT_STEP=3 +FAULT_STAGE=5 +FAULT_KIND=4 &
run f_dis    f40 +SCEN=$S/scen_eos.hex +DISAGREE_STEP=2 &
run meas_cl1   m1   +SCEN=$S/scen_length.hex +MEAS &
run meas_cl40  m40  +SCEN=$S/scen_length.hex +MEAS &
run meas_cl170 m170 +SCEN=$S/scen_length.hex +MEAS &
wait
n=$(grep -h 'CTL_RESULT pass=1' "$wd"/run_*.log | wc -l); t=$(ls "$wd"/run_*.log | wc -l)
echo "CTL_CAMPAIGN $n/$t pass"
