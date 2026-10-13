#!/bin/bash
# q13-kvleaves 2026-10-13: thin-cluster KV end vs the flat KV end (rtl/test/qwen_kv_die/tb_qkvd_ke_eq.sv), iverilog.
#   ke_eq_bench.sh OUT [MUT]      MUT = TI | RQ | TM | TF | RO | CTL | WF (hard-tile mutants) | PQ2 (shadow mutant) | "" (positive)
# env QD / UCX / FCR_RES / NCYC override the parameters (default 48 / 48 / 32 / 40000 = the kit parameters).
# exit 0 iff the bench prints "KE_EQ PASS" (so a mutant job expects FAIL).
set -u
OUT=$1; MUT=${2:-}
K=rtl/qwen_sys/kv_die_20261009
mkdir -p "$OUT"
DEF=""
case "$MUT" in "") ;; PQ2) DEF="-DKVD_PQ2MUT" ;; *) DEF="-DKVD_KE_MUT_$MUT" ;; esac
iverilog -g2012 $DEF -s tb_qkvd_ke_eq -P tb_qkvd_ke_eq.QD=${QD:-48} -P tb_qkvd_ke_eq.UCX=${UCX:-48} \
  -P tb_qkvd_ke_eq.FCR_RES=${FCR_RES:-32} -P tb_qkvd_ke_eq.NCYC=${NCYC:-40000} -o "$OUT/ke_eq${MUT:+_$MUT}" \
  rtl/test/qwen_kv_die/tb_qkvd_ke_eq.sv $K/ot_qkvd_kv_end.sv $K/ot_qkvd_ke_cluster.sv $K/ot_qkvd_ke_tiles.sv $K/ot_qkvd_d2d.sv \
  $K/ot_qkvd_fifo.sv $K/ot_qkvd_fifo_sb.sv $K/ot_qkvd_buf_tiles.sv $K/ot_qkvd_fifo_sl.sv rtl/lib/ot_rst_relay.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -5 "$OUT/build${MUT:+_$MUT}.log"; echo BUILD_FAIL; exit 3; }
vvp -n "$OUT/ke_eq${MUT:+_$MUT}" | tee "$OUT/ke_eq${MUT:+_$MUT}.log" | tail -12
grep -q "^KE_EQ PASS" "$OUT/ke_eq${MUT:+_$MUT}.log"
