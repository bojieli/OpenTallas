#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);OUT=${1:?scratch out}
mkdir -p "$OUT"
python3 tools/hbm_next/hnx_idxn_calendar.py "$OUT/calendar" --score-chain 14 > "$OUT/compile.log"
python3 - "$OUT" <<'PY'
from pathlib import Path
import json,sys
p=Path(sys.argv[1]);d=json.loads((p/'calendar/frame/calendar.json').read_text());w=[int(x,16) for x in (p/'calendar/frame/calendar_instructions.hex').read_text().split()]
assert len(w)<=2048
(p/'program.mem').write_text(''.join(f'{sum((w[i+j] if i+j<len(w) else 0)<<(32*j) for j in range(8)):064x}\n' for i in range(0,len(w),8)))
(p/'args.txt').write_text(f'+DIR={p} +LENGTH={len(w)} +PITCH={d["pitch"]} +WORDS={(len(w)+7)//8}\n')
PY
iverilog -g2012 -s tb_calendar_quad -o "$OUT/native.vvp" \
 results/hbm_keybuf_slice_1027/ref_sram_256x256.v \
 results/hbm_keybuf_binding_1027/gold_native_keybuf.sv \
 rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv \
 rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_slice.sv \
 rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_quarter.sv \
 rtl/hbm_next/idxn/ot_hnx_idxn_quad_key_replay.sv \
 results/hbm_keybuf_binding_1027/tb_calendar_quad.sv > "$OUT/build.log" 2>&1
vvp "$OUT/native.vvp" $(cat "$OUT/args.txt") > "$OUT/positive.log"
tail -3 "$OUT/positive.log"
if vvp "$OUT/native.vvp" $(cat "$OUT/args.txt") +MUT_TAG > "$OUT/mutant.log";then echo MUTANT_ESCAPED;exit 1;else echo MUTANT_CAUGHT;fi
