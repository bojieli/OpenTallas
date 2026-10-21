#!/bin/bash
# XHEAD successor benches on the FLEET (Verilator 5.050), from the repository root:
#   bash rtl/test/qwen_dv/s5/xhead7/bench.sh OUT eq|mut     leaf lockstep original vs bounded (eq: XH7_EQ PASS) / real mutant (FAIL)
#   bash rtl/test/qwen_dv/s5/xhead7/bench.sh OUT sys        slice lockstep: qfd_dv_slice2 vs qfd_dv_s5_flat0 with all 4 xheads = xhead2
#   bash rtl/test/qwen_dv/s5/xhead7/bench.sh OUT sysmut     same with all 4 xheads = the bounded mutant (S5_EQ FAIL)
set -euo pipefail
O=$1; K=$2; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
B="rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_helpers.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_mut.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead2.sv"
VF="--binary --timing -O2 -j ${VJOBS:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0"
case $K in
  eq|mut)
    "$V" $VF --top-module tb_xhead7 rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv \
      rtl/lib/ot_rst_pipe.sv $B rtl/test/qwen_dv/s5/xhead7/tb_xhead7.sv -Mdir "$O/obj" > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
    pa=""; [ $K = mut ] && pa=+mutate
    "$O/obj/Vtb_xhead7" $pa > "$O/$K.log" 2>&1; cat "$O/$K.log";;
  sys|sysmut)
    mkdir -p "$O/gen"; t=qfd_dv_s5_xhead2; [ $K = sysmut ] && t=qfd_dv_s5_xhead_bounded_mut
    sed "s/^    qfd_dv_s5_xhead u_xh/    $t u_xh/" rtl/qwen_dv/s5/qfd_dv_s5_flat0.sv > "$O/gen/qfd_dv_s5_flat0.sv"
    [ "$(grep -c "^    $t u_xh" "$O/gen/qfd_dv_s5_flat0.sv")" = 4 ] || { echo "SUBST FAIL"; exit 1; }
    # run_s5.sh eq 0 with the substituted flat0 and the bounded sources appended
    sed -e "s#rtl/qwen_dv/s5/qfd_dv_s5_flat0.sv#$O/gen/qfd_dv_s5_flat0.sv#" -e "s#rtl/qwen_dv/s5/qfd_dv_s5_vm.sv\"#rtl/qwen_dv/s5/qfd_dv_s5_vm.sv $B\"#" \
      rtl/test/qwen_dv/s5/run_s5.sh > "$O/gen/run_s5.sh"
    grep -q "$O/gen/qfd_dv_s5_flat0.sv" "$O/gen/run_s5.sh" && grep -q xhead_bounded "$O/gen/run_s5.sh" || { echo "RUN SUBST FAIL"; exit 1; }
    bash "$O/gen/run_s5.sh" "$O/w" eq 0;;
esac
