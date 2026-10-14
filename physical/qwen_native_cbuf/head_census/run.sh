#!/usr/bin/env bash
set -eu
OUT=$1;QLA=$2;QLM=$3;mkdir -p "$OUT"
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
[ -x "$Y" ]||Y=yosys
"$Y" -V > "$OUT/tool.txt"
while IFS= read -r file;do sha256sum "$file";done < physical/qwen_native_cbuf/head_census/sources.txt > "$OUT/source.sha256"
python3 - "$OUT/design.ys" "$OUT/design.json" "$QLA" "$QLM" <<'PY'
from pathlib import Path
import sys
files=Path('physical/qwen_native_cbuf/head_census/sources.txt').read_text().splitlines()
s='read_verilog -sv -defer -D SYNTHESIS '+' '.join(files)+'\n'
s+='hierarchy -check -top ot_hdc_vstream_lane_h -chparam WR 16 -chparam AW 24 -chparam NW 18 -chparam KV_FP8 1 -chparam ML 15 -chparam RD 2 -chparam QLA '+sys.argv[3]+' -chparam QLM '+sys.argv[4]+'\n'
s+='synth -top ot_hdc_vstream_lane_h -noabc -noshare\nstat\nwrite_json '+sys.argv[2]+'\n'
Path(sys.argv[1]).write_text(s)
PY
"$Y" -s "$OUT/design.ys" > "$OUT/synth.log" 2>&1
python3 physical/qwen_native_cbuf/head_census/count.py "$OUT/design.json" "$OUT/census.json" "$QLA" "$QLM"
