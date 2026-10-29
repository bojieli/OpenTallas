#!/bin/bash
# KDIE4-LP 10-22: lockstep random equivalence, native-safe rope core vs the 015489b01 core (git show of that commit).
# usage: run_dcal_ovl_rope_eq.sh OUT [SEEDS="1 2 3"] [NCYC=400000] [MUT=0] [HMUT=0]
set -eu
OUT=$(realpath -m "$1"); SEEDS=${2:-"1 2 3"}; NCYC=${3:-400000}; MUT=${4:-0}; HMUT=${5:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015
OLD=015489b01
mkdir -p "$OUT"
git show "$OLD:$D/qkd_d2d_cal_seq_ovl_rope.sv" | sed -n '/^module qkd_d2d_cal_seq_ovl_rope_bc_core/,/^endmodule/p' \
  | sed 's/^module qkd_d2d_cal_seq_ovl_rope_bc_core /module qkd_d2d_cal_seq_ovl_rope_bc_core_old /' > "$OUT/old_core.sv"
# TOK-KV-DCAL-1 10-29: the reference takes the same intended change as the rope core (a reload keeps the boot base-word
# record btx/brx_seen; only reset clears it).  OLD_RELOAD_CLEAR=1 keeps the 015489b01 clear: the lockstep must then FAIL
# (f_early differs after a reload between the base words and a cal_start), which shows the bench sees the change.
if [ "${OLD_RELOAD_CLEAR:-0}" != 1 ]; then
python3 - "$OUT/old_core.sv" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1]); s = p.read_text()
old = ("            if (reload_q) begin btx_seen <= 1'b0; brx_seen <= 1'b0; end\n            else begin\n"
       "                if (b_base && b_tx_q) btx_seen <= 1'b1;\n                if (b_base && b_rx_q) brx_seen <= 1'b1;\n"
       "            end\n")
assert s.count(old) == 1, 'old core: reload clear of btx/brx_seen not found exactly once'
p.write_text(s.replace(old, "            if (b_base && b_tx_q) btx_seen <= 1'b1;\n            if (b_base && b_rx_q) brx_seen <= 1'b1;\n"))
PY
fi
git show "$OLD:$D/ot_qwen_d2d_ovl_seq.sv" > "$OUT/old_ovl_seq.sv"
git show "$OLD:$D/ot_qwen_d2d_cal_seq.sv" > "$OUT/old_cal_seq.sv"
OBJ="$OUT/obj_m${MUT}_h${HMUT}"
"$V" --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  --x-assign unique --x-initial unique -I"$D" --top-module tb_kv_dcal_ovl_rope_eq -GMUT="$MUT" -GHMUT="$HMUT" --Mdir "$OBJ" \
  physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v "$OUT/old_cal_seq.sv" "$OUT/old_ovl_seq.sv" \
  "$OUT/old_core.sv" "$D/qkd_d2d_cal_seq_ovl_rope.sv" rtl/test/qwen_split/tb_kv_dcal_ovl_rope_eq.sv > "$OUT/build_m${MUT}_h${HMUT}.log" 2>&1
rc=0
for s in $SEEDS; do
  "$OBJ/Vtb_kv_dcal_ovl_rope_eq" +SEED=$s +NCYC=$NCYC +verilator+seed+$s +verilator+rand+reset+2 > "$OUT/eq_m${MUT}_h${HMUT}_s$s.log" 2>&1 || rc=1
  grep -h "KDCALEQ_" "$OUT/eq_m${MUT}_h${HMUT}_s$s.log"
done
exit $rc
