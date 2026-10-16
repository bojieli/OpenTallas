#!/bin/bash
# usage: run_qfd_rst_tiles.sh <outdir> [mut_rstsync|mut_rstseq]   -> prints RST_TILES ... PASS|FAIL
set -eu
OUT=$1; MODE=${2:-}
W=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
DEF=""
[ "$MODE" = mut_rstsync ] && DEF="-DOT_QFD_RSTSYNC_MUT"
[ "$MODE" = mut_rstseq ] && DEF="-DOT_QFD_RSTSEQ_MUT"
# only the two reset modules of the slot file (the rest instantiates link RTL not needed here)
python3 - "$W/qwen_split/qfd_link_slots.sv" "$OUT/rst_mods.sv" <<'PY'
import re, sys
t = open(sys.argv[1]).read(); out = ['`timescale 1ns/1ps']
for m in ('qfd_rstsync', 'qfd_rstseq'):
    a = t.index('module %s' % m); b = t.index('endmodule', a) + len('endmodule'); out.append(t[a:b])
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
PY
iverilog -g2012 $DEF -o "$OUT/sim" "$OUT/rst_mods.sv" "$W/test/qwen_split/tb_qfd_rst_tiles.sv"
vvp -n "$OUT/sim" | tee "$OUT/sim.log" | grep -E "RST_TILES|MISMATCH" | head -8
