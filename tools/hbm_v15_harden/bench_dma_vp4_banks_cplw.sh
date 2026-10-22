#!/usr/bin/env bash
# SAFE-HBM-DBK 10-21: WA-LANDED _cplw (wa/wb_ready landed at the N face, +1 edge); from HBM-DBK9 OUTPUT-LANDED parent ot_hgi_dma_back_static_vp4_banks_cplw (every output from a face
# register; rtl/.../ot_hgi_dma_back_static_vp4_banks_cplw.sv).  Verilator (fleet / daemon pin: 5.050).
#   bench_dma_vp4_banks_cplw.sh OUT CFG   (mut_nopre = die re-padded one edge only, DIE_PRE 1: rq face register not padded)
#   fold      lockstep vs the die composition through the real host ingress (tb_dma_vp4_banks_cplw.sv)   -> CPL_LAND PASS
#   banklat   RR_RT 80 core on the d4g faces bank + GEN2c NE lanes, die re-padded one edge (tb_..._banklat_rl) -> BANKLAT_RL PASS
#   mut_cvraw    RL_MUT 1 controller response valid not landed                (banklat)  -> BANKLAT_RL FAIL mv_fault
#   mut_wsrelay  RL_MUT 2 write slot relayed (write frame shifted)            (banklat)  -> BANKLAT_RL FAIL landing payload
#   mut_fill     RL_MUT 3 wb_fill_* not relayed with wd                       (fold)     -> CP_FOLD control mismatch
#   mut_nopre    die not re-padded (rr on the old edge)                       (banklat)  -> BANKLAT_RL FAIL mv_fault
#   mut_wa       RL_MUT 4 wa / wb_ready not landed at the N face              (fold)     -> CP_FOLD control mismatch
#   mut_rst      RST_MUT 1 controller reset straight from the port            (fold)     -> DMA absolute cycle did not advance
set -euo pipefail
out=${1:?output};cfg=${2:?cfg};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
W="-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN"
FOLD=("$m" rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv
      rtl/lib/ot_rst_relay.sv "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv"
      "$d/ot_hgi_dma_back_cp_collar.sv" "$d/ot_hgi_dma_back_static_vp4_banks_cplw.sv" "$d/tb_dma_vp4_banks_cplw.sv")
LAT=("$m" "$d/ot_hgi_dma_back_static_vp_banks.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv"
     "$d/ot_hgi_dma_back_static_vp4_banks_cplw.sv" "$d/tb_dma_vp4_banklat_rlw.sv")
LATD="-DRR_RT=80 -DDIE_RT=80 -DFACES_D=8 -DLANES=1"
case "$cfg" in
 fold)        tb=tb_dma_vp4_banks_cplw;  S=("${FOLD[@]}"); D="";;
 mut_fill)    tb=tb_dma_vp4_banks_cplw;  S=("${FOLD[@]}"); D="-DRL_MUT=3";;
 mut_rst)     tb=tb_dma_vp4_banks_cplw;  S=("${FOLD[@]}"); D="-DRST_MUT=1";;
 mut_wa)      tb=tb_dma_vp4_banks_cplw;  S=("${FOLD[@]}"); D="-DRL_MUT=4";;
 banklat)     tb=tb_dma_vp4_banklat_rlw; S=("${LAT[@]}");  D="$LATD";;
 mut_cvraw)   tb=tb_dma_vp4_banklat_rlw; S=("${LAT[@]}");  D="$LATD -DRL_MUT=1";;
 mut_wsrelay) tb=tb_dma_vp4_banklat_rlw; S=("${LAT[@]}");  D="$LATD -DRL_MUT=2";;
 mut_nopre)   tb=tb_dma_vp4_banklat_rlw; S=("${LAT[@]}");  D="$LATD -DDIE_PRE=1";;
 *) echo "unknown cfg $cfg"; exit 2;;
esac
verilator --version
if [ "$cfg" = fold ]; then   # the synthesis view elaborates (OT_DBK_HARD: hard children without parameters)
  verilator --lint-only $W -DSYNTHESIS -DOT_DBK_HARD --top-module ot_hgi_dma_back_static_vp4_banks_cplw \
    "$d/ot_hgi_dma_back_static_vp4_banks_cplw.sv" "$d/ot_hgi_dma_back_cp_collar.sv" "$d/ot_hgi_dma_back_static_vp4_banks.sv" \
    "$d/ot_hgi_dma_back_static_vp_banks.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv \
    "$m" 2>&1 | tee "$out/lint_cpl.log"
  echo LINT_CPL_HARD_OK
fi
# shellcheck disable=SC2086
verilator --binary --timing -j 4 $W $D --top-module $tb -Mdir "$out/obj_$cfg" -o sim "${S[@]}" > "$out/build_$cfg.log" 2>&1 \
  || { tail -40 "$out/build_$cfg.log"; exit 1; }
"$out/obj_$cfg/sim" > "$out/$cfg.log" 2>&1 || true
cat "$out/$cfg.log"
grep -qE 'CPL_LAND PASS|BANKLAT_RL PASS' "$out/$cfg.log"
