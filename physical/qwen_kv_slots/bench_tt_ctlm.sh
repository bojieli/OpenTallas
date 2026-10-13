#!/usr/bin/env bash
# Slot cell qfd_tt_ctlm: the body's own bench (tb_qfd_tt_ctlm_i_psram, u0 = reference ot_qfd_tt_ctlm_i PSRAM 0 / HQ2 0 at
# G 3,072) with u1 = the slot cell driven and observed through its contract bundles (qfd_tt_ctlm_bodyview unpacks with the
# packing table).  The route top is MEREG 3 (engine wake +1), so the compare is the tb's transaction-level one (TXN 1:
# per-interface event streams per reset window), as the body's own tp8_txn bench.
#   bench_tt_ctlm.sh OUT_DIR [mut]     mut: OT_QFD_TT_CTLM_SLOT_MUT (mx bits 0 / 1 swapped inside the cell) must FAIL
# Prints "PASS kv_slots tt_ctlm ..." (rc 0) or "FAIL kv_slots tt_ctlm ..." (rc 1).  Verilator.
set -u
OUT=$1; MUT=${2:-}
R=$(cd "$(dirname "$0")/../.." && pwd); cd "$R" || exit 1
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
mkdir -p "$OUT"
python3 physical/qwen_kv_slots/gen_slot.py qfd_tt_ctlm --check > "$OUT/table.log" 2>&1 || { cat "$OUT/table.log"; echo "FAIL kv_slots tt_ctlm table"; exit 1; }
sed -e 's/^    ot_qfd_tt_ctlm_i #(.PSRAM(U1_PSRAM)/    qfd_tt_ctlm_bodyview #(.PSRAM(U1_PSRAM)/' -e 's/u1\./u1.u_slot.u_body.u_fpm.u_c./g' \
    rtl/test/tb_qfd_tt_ctlm_i_psram.sv > "$OUT/tb_slot.sv"
grep -q 'qfd_tt_ctlm_bodyview' "$OUT/tb_slot.sv" || { echo "FAIL kv_slots tt_ctlm tb rewrite"; exit 1; }
L=$(grep -o 'L="[^"]*"' rtl/test/run_tt_ctlm_i_lockstep.sh | sed -e 's/^L="//' -e 's/"$//' -e 's#rtl/test/tb_qfd_tt_ctlm_i_psram.sv##')
D=""; [ "$MUT" = mut ] && D="-DOT_QFD_TT_CTLM_SLOT_MUT"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
    +define+OT_ICUT_NONFATAL --top-module tb_qfd_tt_ctlm_i_psram -GNCYC=20000 -GMINRD=200 -GSEED=1 -GU1_HQ2=1 -GU1_RRG=1 -GU1_PCUT=1 \
    -GMOK=1 -GPFMASK=1 -GU1_AUD=33975 -GU1_MEREG=3 -GTXN=1 -GTBG=3072 $D --Mdir "$OUT/obj" "$OUT/tb_slot.sv" \
    rtl/test/qfd_tt_ctlm_slot_shim.sv rtl/physical/ot_qfd_tt_ctlm_slot.sv rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm_i_fpm.sv \
    rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm_i_fpm_tp8.sv $L > "$OUT/build.log" 2>&1 || { grep -m5 '%Error' "$OUT/build.log"; echo "FAIL kv_slots tt_ctlm build"; exit 1; }
"$OUT/obj/Vtb_qfd_tt_ctlm_i_psram" > "$OUT/run.log" 2>&1
L1=$(grep -E '^(PASS|FAIL) tt_ctlm_i_psram' "$OUT/run.log" | tail -1)
case "$L1" in
  PASS*) echo "PASS kv_slots tt_ctlm ${L1#PASS tt_ctlm_i_psram }"; exit 0 ;;
  FAIL*) M=""; [ -n "$MUT" ] && echo "$L1" | grep -q "mismatches=[1-9]" && M=" mutant detected"; echo "FAIL kv_slots tt_ctlm$M ${L1#FAIL tt_ctlm_i_psram }"; exit 1 ;;
  *) tail -5 "$OUT/run.log"; echo "FAIL kv_slots tt_ctlm no verdict"; exit 1 ;;
esac
