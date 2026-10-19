#!/usr/bin/env bash
# HBM-BANKLAT-DMA 10-19: DMA write-back controller RR_RT (VM read round trip at the controller pins) against the d4g
# faces bank contract + GEN2c hb_dbk_NE lanes (rtl/.../tb_dma_vp4_banklat.sv).  Verilator (fleet: 5.050).
#   bench_dma_banklat.sh OUT CFG
#   base         closed default (no RR_RT override = 7), bare ot_vms_bank_static (7), no lanes          -> PASS
#   pass         RR_RT 80 (d4g budget), faces bank (8), GEN2c NE lanes, die pads rq lanes to 80         -> PASS
#   mut_oldlat   RR_RT 7 (the old latency) on the same die                                               -> FAIL
#   mut_padshort RR_RT 80, die pad of bank 4 one stage short (round trip 79)                              -> FAIL
#   mut_lag      RR_RT 80, compiler drain lag one below the rule (RR_RT+2)                                -> FAIL
# Every config also lint-elaborates the folded parent ot_hgi_dma_back_static_vp4_banks_cp #(RR_RT) once (cfg pass).
set -euo pipefail
out=${1:?output};cfg=${2:?cfg};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
case "$cfg" in
 base)         D="";;
 pass)         D="-DRR_RT=80 -DDIE_RT=80 -DFACES_D=8 -DLANES=1";;
 mut_oldlat)   D="-DRR_RT=7 -DDIE_RT=80 -DFACES_D=8 -DLANES=1";;
 mut_padshort) D="-DRR_RT=80 -DDIE_RT=80 -DFACES_D=8 -DLANES=1 -DPAD_SHORT=4";;
 mut_lag)      D="-DRR_RT=80 -DDIE_RT=80 -DFACES_D=8 -DLANES=1 -DLAG_ADJ=-1";;
 *) echo "unknown cfg $cfg"; exit 2;;
esac
verilator --version
W="-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN"
if [ "$cfg" = pass ]; then
  printf '%s\n' 'module ot_lint_cp; ot_hgi_dma_back_static_vp4_banks_cp #(.RR_RT(80)) u (); endmodule' > "$out/lint_cp.sv"
  verilator --lint-only $W -DSYNTHESIS --top-module ot_lint_cp "$out/lint_cp.sv" "$d/ot_hgi_dma_back_static_vp4_banks_cp.sv" \
    "$d/ot_hgi_dma_back_cp_collar.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$d/ot_hgi_dma_back_static_vp_banks.sv" \
    rtl/lib/ot_rst_relay.sv rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv "$m" 2>&1 | tee "$out/lint_cp.log"
  echo LINT_CP_RR_RT80_OK
fi
# shellcheck disable=SC2086
verilator --binary --timing -j 4 $W $D --top-module tb_dma_vp4_banklat -Mdir "$out/obj_$cfg" -o sim \
  "$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$d/tb_dma_vp4_banklat.sv" > "$out/build_$cfg.log" 2>&1 \
  || { tail -40 "$out/build_$cfg.log"; exit 1; }
"$out/obj_$cfg/sim" > "$out/$cfg.log" 2>&1 || true
cat "$out/$cfg.log"
grep -q 'BANKLAT PASS' "$out/$cfg.log"
