#!/usr/bin/env bash
# HBM-COLLQ6-LINK 10-20: link-level lockstep miter ot_hgi_coll_link_e1 (body ot_hgi_coll_link_e2) == ot_hgi_coll_link_e.
# FLEET ONLY (Verilator 5.050):  bash rtl/hbm_accel/generic/collective/p2p/run_coll_link_e2_eq.sh OUT [eq|mut]
#   eq : LINK_EQ PASS required (every output every cycle; >1000 TX and RX frames, >10 aborted epochs); exit 0 on PASS
#   mut: OT_COLL_LINK2_MUT_DATA (bank 1 stores bit 140 of its slice inverted) MUST FAIL; exit 1 when REJECTED
set -u
OUT=$(realpath -m "${1:?OUT}"); WHICH=${2:-eq}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
"$V" --version | tee "$OUT/verilator.version"
p=rtl/hbm_accel/generic/collective/p2p
SRC="$p/ot_hfd_coll_q_hard_v5.sv $p/ot_hgi_coll_safe_leaves.sv $p/ot_hgi_coll_static_capture_ctl.sv $p/ot_hgi_coll_static_pinreg_ctl.sv
 $p/ot_hgi_coll_static_pinreg_store.sv $p/ot_hgi_coll_static_seq_ctl.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
 rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 $p/tb_hgi_coll_link_e2_eq.sv"
sha256sum $SRC $0 > "$OUT/sources.sha256"
run() { local n=$1; shift
  "$V" --binary -j ${VL_JOBS:-8} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN "$@" \
    --top-module tb_hgi_coll_link_e2_eq $SRC -Mdir "$OUT/obj_$n" > "$OUT/$n.build.log" 2>&1 && "$OUT/obj_$n/Vtb_hgi_coll_link_e2_eq" > "$OUT/$n.log" 2>&1
  rm -rf "$OUT/obj_$n"; grep -E '^(LINK_EQ|LINK_ACTIVITY|LINK_EQ_MISMATCH)' "$OUT/$n.log" 2>/dev/null | head -6 | sed "s/^/$n /"; }
if [ "$WHICH" = eq ]; then
  run eq
  if grep -q '^LINK_EQ PASS' "$OUT/eq.log" 2>/dev/null; then echo "LINK_E2_EQ PASS"; echo "LINK_E2_EXIT 0"; exit 0; fi
  tail -n 20 "$OUT/eq.build.log"; echo "LINK_E2_EQ FAIL"; echo "LINK_E2_EXIT 1"; exit 1
fi
run m_data +define+OT_COLL_LINK2_MUT_DATA
if grep -q '^LINK_EQ FAIL mismatches=[1-9]' "$OUT/m_data.log" 2>/dev/null; then echo "LINK_E2_MUTANT m_data REJECTED"; exit 1; fi
echo "LINK_E2_MUTANT m_data SURVIVED"; exit 0
