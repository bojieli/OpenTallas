#!/usr/bin/env bash
set -euo pipefail
out=${1:?out}; mut=${2:-0};mkdir -p "$out"
python3 - "$out" <<'PY'
import shlex,sys
from pathlib import Path
src=next(x for x in Path('physical/qwen_die_masters/cfg/qfd_tile_lsl6.env').read_text().splitlines() if x.startswith('SRCS='))
Path(sys.argv[1]+'/sources.list').write_text('\n'.join(shlex.split(src[5:])[0].split())+'\n')
PY
mapfile -t sources < "$out/sources.list"
iverilog -g2012 -s tb_tx198 -Ptb_tx198.MUT="$mut" -o "$out/sim.vvp" physical/qwen_tile_glue_banks_1015/tb_tx198.sv rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl_fp1.sv "${sources[@]}" > "$out/compile.log" 2>&1
rc=0;vvp "$out/sim.vvp" > "$out/result.log" 2>&1||rc=$?
cat "$out/result.log";exit "$rc"
