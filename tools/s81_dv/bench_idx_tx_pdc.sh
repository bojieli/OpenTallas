#!/bin/bash
# S81-IDX-B5/B6 11-06: lockstep bench of dsdv_idx_tx_n32 PDC 1 vs the FACE 2 form (dsdv_idx_tx_n32_old), bit-exact, 0 cycles.
#   bench_idx_tx_pdc.sh <work dir> <base|pdc0|mut_pdc|mut3|dly1> [seed ...]      (run from the repo root)
# base / pdc0 must PASS; negative controls mut_pdc (PDC 2) / mut3 (MUT 3) / dly1 (claims +1) must FAIL.
set -u
W=$(realpath -m ${1:?work}); V=${2:?variant}; shift 2; mkdir -p $W
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
T=rtl/dsrom_sys/s81_dv/idx
F=(rtl/lib/ot_rst_relay.sv $T/dsdv_idx_tree.sv $T/dsdv_idx_l20s.sv $T/test/dsdv_idx_tx_n32_old.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $T/test/tb_dsdv_idx_tx_pdc.sv)
case $V in base) P=();; pdc0) P=(-GNEW_PDC=0);; mut_pdc) P=(-GNEW_PDC=2);; mut3) P=(-GNEW_MUT=3);; dly1) P=(-GDLY_EXP=1);;
  *) echo "IDXTX_PDC FAIL bad variant"; exit 2;; esac
$VL --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING \
    -Wno-IMPLICIT -Wno-SELRANGE -Wno-LATCH -Wno-COMBDLY -CFLAGS -O1 --top-module tb_dsdv_idx_tx_pdc "${P[@]}" "${F[@]}" \
    --Mdir $W/obj -o sim > $W/build.log 2>&1 || { tail -20 $W/build.log; echo "IDXTX_PDC FAIL build $V"; exit 1; }
ok=1
for s in ${@:-1 2 3}; do $W/obj/sim +SEED=$s > $W/run_$s.log 2>&1; grep -h TB_IDXTX_PDC $W/run_$s.log | tail -2; grep -q "TB_IDXTX_PDC PASS" $W/run_$s.log || ok=0; done
[ $ok = 1 ] && { echo "IDXTX_PDC PASS $V"; exit 0; }; echo "IDXTX_PDC FAIL $V"; exit 1
