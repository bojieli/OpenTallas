#!/usr/bin/env bash
# Slot cell qfd_seq_su: the body's own exact lockstep bench (tb_qfd_seq_su_bi_psram: u0 = reference body PSRAM 0 / HQ2 0)
# with u1 = the slot cell driven through its bundles (qfd_seq_su_bodyview unpacks with the packing table).
#   bench_seq_su.sh OUT_DIR [mut]     mut: OT_QFD_SEQ_SU_SLOT_MUT (vwr bits 0 / 1 swapped inside the cell) must FAIL
# Prints "PASS kv_slots seq_su ..." (rc 0) or "FAIL kv_slots seq_su ..." (rc 1).  Verilator (see run_seq_su_bi_lockstep.sh).
set -u
OUT=$1; MUT=${2:-}
R=$(cd "$(dirname "$0")/../.." && pwd); cd "$R" || exit 1
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
mkdir -p "$OUT"
python3 physical/qwen_kv_slots/gen_seq_su_slot.py --check > "$OUT/table.log" 2>&1 || { cat "$OUT/table.log"; echo "FAIL kv_slots seq_su table"; exit 1; }
sed -e 's/^    ot_qfd_seq_su_bi #(.PSRAM(U1_PSRAM)/    qfd_seq_su_bodyview #(.PSRAM(U1_PSRAM)/' -e 's/u1\./u1.u_slot.u_body./g' \
    rtl/test/tb_qfd_seq_su_bi_psram.sv > "$OUT/tb_slot.sv"
grep -q 'qfd_seq_su_bodyview' "$OUT/tb_slot.sv" || { echo "FAIL kv_slots seq_su tb rewrite"; exit 1; }
L=$(grep -o 'L="[^"]*"' rtl/test/run_seq_su_bi_lockstep.sh | sed -e 's/^L="//' -e 's/"$//' -e 's#rtl/test/tb_qfd_seq_su_bi_psram.sv##')
D=""; [ -n "$MUT" ] && D="-DOT_QFD_SEQ_SU_SLOT_MUT"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
    --top-module tb_qfd_seq_su_bi_psram -GU1_HQ2=1 -GARCOV=1 -GPCOV=1 -GMINVW=20 $D --Mdir "$OUT/obj" "$OUT/tb_slot.sv" rtl/test/qfd_seq_su_slot_shim.sv \
    rtl/physical/ot_qfd_seq_su_slot.sv $L > "$OUT/build.log" 2>&1 || { tail -5 "$OUT/build.log"; echo "FAIL kv_slots seq_su build"; exit 1; }
"$OUT/obj/Vtb_qfd_seq_su_bi_psram" > "$OUT/run.log" 2>&1
L1=$(grep -E '^(PASS|FAIL) seq_su_bi_psram' "$OUT/run.log" | tail -1)
case "$L1" in
  PASS*) echo "PASS kv_slots seq_su ${L1#PASS seq_su_bi_psram }"; exit 0 ;;
  FAIL*) M=""; [ -n "$MUT" ] && echo "$L1" | grep -q "mismatches=[1-9]" && M=" mutant detected"; echo "FAIL kv_slots seq_su$M ${L1#FAIL seq_su_bi_psram }"; exit 1 ;;
  *) tail -5 "$OUT/run.log"; echo "FAIL kv_slots seq_su no verdict"; exit 1 ;;
esac
