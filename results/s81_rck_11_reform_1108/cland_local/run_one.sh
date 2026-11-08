#!/bin/bash
set -euo pipefail
R=$1;E=$2;M=${3:-base}
D=$(mktemp -d /srv/opentallas-scratch2/claude/codex-s81-rck-0222/tmp/clon.XXXXXX)
cp "$R/rtl/common/ot_meso_fifo.sv" "$D/meso.sv"
cp "$R/rtl/common/ot_dp_clk_landing.sv" "$D/land.sv"
ren(){ local f=$1 sfx=$2;for m in $(grep -oP '^\s*module\s+\K\w+' "$f"|sort -u);do sed -i -E "s/\b$m\b/${m}${sfx}/g" "$f";done; }
verilator -E -P -DOT_S81_CLAND_WCHK "$D/meso.sv" "$D/land.sv" > "$D/ref.sv"
ren "$D/ref.sv" _r;sed -i 's/\bot_dp_clk_landing_r\b/cl_ref/' "$D/ref.sv"
python3 -I - "$D" "$M" <<'PY'
from pathlib import Path
import sys
D=Path(sys.argv[1]);m=sys.argv[2]
if m=='old_on':
 p=D/'land.sv';s=p.read_text();a="on_c <= {NC{rst_i && (on || (count == CW'(SETTLE)))}};";assert a in s;s=s.replace(a,"on_c <= {NC{on}};");p.write_text(s)
elif m=='old_align':
 p=D/'land.sv';s=p.read_text();a="align_c <= {NC{rst_n && rst_i && !on && (count == CW'(SETTLE - 1))}};";assert a in s;s=s.replace(a,"align_c <= {NC{align}};");p.write_text(s)
elif m=='slot':
 p=D/'meso.sv';s=p.read_text();start=s.index('module ot_meso_wcc #(');a='always_ff @(posedge clk) tcc <= nxt;';assert a in s[start:];s=s[:start]+s[start:].replace(a,"always_ff @(posedge clk) tcc <= nxt - 1'b1;",1);p.write_text(s)
PY
verilator -E -P -DOT_S81_CLAND_WCHK -DOT_S81_CLAND_LOCAL_ON "$D/meso.sv" "$D/land.sv" > "$D/new.sv"
ren "$D/new.sv" _n;sed -i 's/\bot_dp_clk_landing_n\b/cl_new/' "$D/new.sv"
verilator --binary --timing -j 4 -O1 -Wno-fatal -Wno-MULTIDRIVEN --top-module tb --Mdir "$D/obj" -o tb "$E/tb_local.sv" "$D/ref.sv" "$D/new.sv" > "$E/build_$M.log" 2>&1
if [ "$M" = base ];then phases=(0.03 0.17 0.29 0.41 0.59 0.79);else phases=(0.29);fi
for p in "${phases[@]}";do
 set +e
 "$D/obj/tb" "+PH=$p" > "$E/${M}_$p.log" 2>&1
 rc=$?
 set -e
 grep CLON "$E/${M}_$p.log"
 if [ "$M" = base ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'CLON lockstep FAIL' "$E/${M}_$p.log";fi
 printf '%s phase=%s rc=%s\n' "$M" "$p" "$rc" >> "$E/summary.log"
done
