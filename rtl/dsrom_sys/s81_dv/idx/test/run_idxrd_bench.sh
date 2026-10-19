#!/usr/bin/env bash
# S81-IDXRD (10-18): build + run tb_dsdv_idx_rg (16 x dsdv_idx_rg + 16 x dsfd_ctrl_rg2 + per-PC HBM model, reference
# engine, selector V-ingress decode).  Run from the repo root on a fleet host (Verilator 5.050, the closure daemon's).
#   run_idxrd_bench.sh OUT NAME "-GN=.. -GGATHER=.. -GT0=.. -GP=.. -GMUT=.. -GSRAM_MACRO=.." [threads]
# Exit 0 = TB_IDXRD PASS.  OUT/NAME/{build.log,run.log}.
set -u
O=$1/$2; G=$3; T=${4:-4}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
SRC=(rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv rtl/dsrom_sys/s81_ph/ot_s81ph_ctrl_pc.sv rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_rg2.sv
     rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv
     rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg.sv)
"$VL" --version > "$O/build.log"
# shellcheck disable=SC2086
"$VL" --binary --timing -j "$T" --top-module tb_dsdv_idx_rg -O2 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -Wno-TIMESCALEMOD -Wno-BLKSEQ -Wno-INITIALDLY $G --Mdir "$O/obj" "${SRC[@]}" >> "$O/build.log" 2>&1 \
  || { echo "$2 BUILD_FAILED"; grep -m5 -E '%Error' "$O/build.log"; exit 2; }
/usr/bin/time -v "$O/obj/Vtb_dsdv_idx_rg" > "$O/run.log" 2>&1
rc=$?
echo "$2: $(grep -h -E 'TB_IDXRD (PASS|FAIL)$' "$O/run.log" | tail -1) $(grep -h TB_IDXRD_STATS "$O/run.log" | tail -1) maxrss_kb=$(grep -h 'Maximum resident' "$O/run.log" | awk '{print $NF}') rc=$rc"
grep -q '^TB_IDXRD PASS$' "$O/run.log" && [ $rc -eq 0 ] && exit 0
exit 1
