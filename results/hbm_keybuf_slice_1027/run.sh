#!/bin/bash
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
OUT=${1:?Usage: run.sh SCRATCH_OUTPUT_DIRECTORY}
mkdir -p "$OUT"
cp "$HERE"/{ot_hnx_idxn_keybuf.sv,ref_sram_256x256.v,tb_keybuf_slice.sv} "$OUT/"
cp "$ROOT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_slice.sv" "$OUT/"
cd "$OUT"
iverilog -g2012 -s tb -o positive.vvp ref_sram_256x256.v ot_hnx_idxn_keybuf.sv ot_hnx_idxn_keybuf_slice.sv tb_keybuf_slice.sv
vvp positive.vvp >positive.log
python3 - <<'PY'
from pathlib import Path
p=Path('ot_hnx_idxn_keybuf_slice.sv');s=p.read_text()
old="7'b0}+{2'b0,replay_index}";assert old in s
Path('mutant.sv').write_text(s.replace(old,old+"+10'd1"))
PY
iverilog -g2012 -s tb -o mutant.vvp ref_sram_256x256.v ot_hnx_idxn_keybuf.sv mutant.sv tb_keybuf_slice.sv
if vvp mutant.vvp >mutant.log;then echo MUTANT_ESCAPED;exit 1;else echo MUTANT_CAUGHT;fi
cat positive.log
