#!/bin/bash
# DIE-S81-51/RF-C RE-FORM 11-03 (S81-056): lockstep bench of dsdv_idx_tx_n32 FACE 1 / LKL 1 vs the old form, delayed +1.
#   bench_idx_tx_face.sh <work dir> <base|base_nolkl|mut3|dly0> [seed ...]      (run from the repo root)
# base / base_nolkl must PASS (bit-exact, +1 edge); mut3 (new instance MUT 3, grid one pitch late) and dly0 (claims 0
# cycles) are negative controls and must FAIL.  Prints IDXTX_FACE PASS|FAIL <variant>.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F=(rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_tx_face.sv)
case $V in base) G=();; base_nolkl) G=(-GNEW_LKL=0);; mut3) G=(-GNEW_MUT=3);; dly0) G=(-GDLY_EXP=0);;
  *) echo "IDXTX_FACE FAIL bad variant $V"; exit 2;; esac
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -Wno-LATCH -Wno-COMBDLY -CFLAGS -O1 --top-module tb_dsdv_idx_tx_face "${G[@]}" "${F[@]}" \
    --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "IDXTX_FACE FAIL build $V"; exit 1; }
ok=1
for s in ${@:-1 2 3}; do
  $W/obj/sim +SEED=$s > $W/run_$s.log 2>&1
  grep -h 'TB_IDXTX_FACE' $W/run_$s.log | tail -3
  grep -q 'TB_IDXTX_FACE PASS' $W/run_$s.log || ok=0
done
[ $ok = 1 ] && { echo "IDXTX_FACE PASS $V"; exit 0; }
echo "IDXTX_FACE FAIL $V"; exit 1
