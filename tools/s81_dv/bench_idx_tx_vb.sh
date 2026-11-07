#!/bin/bash
# S81-IDX-B 11-05: lockstep bench of dsdv_idx_tx_n32 version B (FACE 2 + MLK 1) vs the signed-view form (FACE 1), +2 edges.
#   bench_idx_tx_vb.sh <work dir> <variant> [seed ...]      (run from the repo root)
# Variants that must PASS: base (FACE 2 + MLK 1, +2), mlk (FACE 1 + MLK 1, +0 = MLK is cycle-exact), face (FACE 2, +2).
# Negative controls that must FAIL: mut3 (new MUT 3), mlkpos (MLK 2: rising-edge macro stage), dly1 (claims +1).
# Prints IDXTX_VB PASS|FAIL <variant>.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F=(rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
   rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_tx_vb.sv)
case $V in
  base) G=();;
  mlk) G=(-GNEW_FACE=1 -GDLY_EXP=0);;
  face) G=(-GNEW_MLK=0);;
  mut3) G=(-GNEW_MUT=3);;
  mlkpos) G=(-GNEW_MLK=2);;
  dly1) G=(-GDLY_EXP=1);;
  *) echo "IDXTX_VB FAIL bad variant $V"; exit 2;; esac
$VL --binary --timing -j ${J:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -Wno-LATCH -Wno-COMBDLY -CFLAGS -O1 --top-module tb_dsdv_idx_tx_vb "${G[@]}" "${F[@]}" \
    --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "IDXTX_VB FAIL build $V"; exit 1; }
ok=1
for s in ${@:-1 2 3}; do
  $W/obj/sim +SEED=$s > $W/run_$s.log 2>&1
  grep -h 'TB_IDXTX_VB' $W/run_$s.log | tail -3
  grep -q 'TB_IDXTX_VB PASS' $W/run_$s.log || ok=0
done
[ $ok = 1 ] && { echo "IDXTX_VB PASS $V"; exit 0; }
echo "IDXTX_VB FAIL $V"; exit 1
