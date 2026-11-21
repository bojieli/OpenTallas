#!/bin/bash
# colrom_loop_bench.sh SRC_ROOT OUT (FABLE-FIX-S81-COLROM-R2/R3 2026-11-21): functional gate of the S81 col ROM-input stage + cfg7 go guard.
# Closed loop of one col pair as the bound RTL of col_h10_r1 wires it (rtl/v41die/test/tb_colrom_loop.sv); SRC = a tree with rtl/ + physical/
# macro models (die tree or main).  Expect: every pass run PASS (serial, preload spacing K 1..12/14/20/30/150), mutants MUT_CFGONLY,
# MUT_EFSTUCK and OT_S81_CFG7_MUT_NOGUARD (at K=9) FAIL; NOGUARD passes at K=10 (the stale-ef window the guard closes).  SEQ=<file> overrides the seq RTL.
set -u
S=$(cd "$1" && pwd); W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd); HERE=$(cd "$(dirname "$0")" && pwd); TB=$HERE/../../rtl/v41die/test/tb_colrom_loop.sv
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
RTL="rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv
 rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv
 rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv
 rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv
 rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv
 rtl/v41rom/ot_v41_segtree6.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv
 physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v"
F="${SEQ:-$S/rtl/v41die/ot_s81_cfg7_seq.sv}"; for f in $RTL; do F="$F $S/$f"; done
sha256sum ${SEQ:-$S/rtl/v41die/ot_s81_cfg7_seq.sv} | cut -c1-16,65-
sha256sum $TB $S/rtl/v41die/ot_s81_cfg7_seq.sv $S/rtl/v41rom/ot_v41_elem_pq_tags.sv | cut -c1-16,65-
build() { local n=$1; shift
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_colrom_loop --Mdir "$W/$n" -j 16 -CFLAGS -O1 +define+OT_S81_CFG7_RDX \
    "$@" $F "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; grep -m8 "%Error" "$W/$n.build.log"; tail -5 "$W/$n.build.log"; return 1; }
}
run() { # name expect args...
  local n=$1 e=$2; shift 2; local t=$(echo "$*" | tr -d '+ ' | tr '=' '_')
  "$W/$n/Vtb_colrom_loop" "$@" > "$W/${n}_$t.log" 2>&1
  local v=$(grep -o "^COLROM_LOOP \(PASS\|FAIL\)" "$W/${n}_$t.log" | tail -1)
  echo "RUN $n $* expect $e -> ${v:-NO_VERDICT}"; grep -h "^COLROM_LOOP K\|A_ILLEGAL\|^[AB]_FAULT\|REC_MISMATCH\|TIMEOUT" "$W/${n}_$t.log" | head -6
}
build pass || exit 2
run pass pass +K=0 +nops=30 +seed=1
for k in 1 2 3 4 5 6 7 8 9 10 11 12 14 20 30; do run pass pass +K=$k +nops=12 +seed=1; done
run pass pass +K=9 +nops=30 +seed=2 +GQ=0
run pass pass +K=150 +nops=12 +seed=1
build mut_cfgonly +define+MUT_CFGONLY && run mut_cfgonly fail +K=0 +nops=12 +seed=1
build mut_efstuck +define+MUT_EFSTUCK && run mut_efstuck fail +K=30 +nops=12 +seed=1
build mut_noguard +define+OT_S81_CFG7_MUT_NOGUARD && { run mut_noguard fail +K=9 +nops=12 +seed=1; run mut_noguard pass +K=10 +nops=12 +seed=1; }
echo BENCH_DONE
