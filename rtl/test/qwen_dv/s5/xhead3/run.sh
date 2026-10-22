#!/bin/bash
# Lockstep bench of qfd_dv_s5_xhead3 against the current leaf qfd_dv_s5_xhead (new(t+1) == old(t), every output).
#   bash rtl/test/qwen_dv/s5/xhead3/run.sh OUT pass            8 runs (4 column ids x 2 seeds), all must PASS
#   bash rtl/test/qwen_dv/s5/xhead3/run.sh OUT retag|rot|poolw|fwd   one mutant build, must FAIL (exec: exit status)
set -euo pipefail
O=$1; MODE=${2:-pass}; CYC=${CYC:-150000}; mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$O/verilator.version"
SRC=(rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv
     rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv rtl/test/qwen_dv/s5/xhead3/tb_xhead3.sv)
D=()
case "$MODE" in
  pass) ;;
  retag) D+=(-DOT_S5_XH3_MUT_RETAG) ;;
  rot) D+=(-DOT_S5_XH3_MUT_ROT) ;;
  poolw) D+=(-DOT_S5_XH3_MUT_POOLW) ;;
  fwd) D+=(-DOT_S5_XH3_MUT_FWD) ;;
  *) echo "unknown mode $MODE"; exit 2 ;;
esac
"$V" --binary -O2 -j 8 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN "${D[@]}" \
  --top-module tb_xhead3 "${SRC[@]}" -Mdir "$O/obj_$MODE" > "$O/build_$MODE.log" 2>&1 || { tail -40 "$O/build_$MODE.log"; exit 3; }
if [ "$MODE" != pass ]; then
  exec "$O/obj_$MODE/Vtb_xhead3" +seed=7 +cid=22 +cycles=$CYC
fi
rc=0
for cid in 0 5 22 63; do
  for seed in 1 2; do
    set +e
    "$O/obj_pass/Vtb_xhead3" +seed=$seed +cid=$cid +cycles=$CYC > "$O/run_${cid}_${seed}.log" 2>&1
    r=$?
    set -e
    tail -2 "$O/run_${cid}_${seed}.log"
    grep -q 'S5_XH3_EQ PASS' "$O/run_${cid}_${seed}.log" || rc=1
    [ $r -eq 0 ] || rc=1
  done
done
if [ $rc -eq 0 ]; then echo "S5_XH3_EQ ALL PASS"; else echo "S5_XH3_EQ FAIL (see $O/run_*.log)"; fi
exit $rc
