#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=${1:?output directory};mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
S=("$R/rtl/test/meso/raw_export/tb_raw_export.sv" "$R/rtl/common/ot_dp_clk_landing_ca.sv" "$R/rtl/common/ot_dp_clk_landing.sv" "$R/rtl/common/ot_meso_fifo.sv")
verilator --binary --timing --build -j 4 -Wno-fatal --top-module tb_raw_export --Mdir "$OUT/base" "${S[@]}" > "$OUT/build.log" 2>&1
"$OUT/base/Vtb_raw_export" > "$OUT/lockstep.log" 2>&1
verilator --binary --timing --build -j 4 -Wno-fatal -DOT_HEAD_RAW_EXPORT_MUTANT_LATE --top-module tb_raw_export --Mdir "$OUT/mut" "${S[@]}" > "$OUT/build_mut.log" 2>&1
if "$OUT/mut/Vtb_raw_export" > "$OUT/mutant.log" 2>&1;then echo RAW_EXPORT_MUTANT_SURVIVED;exit 1;fi
grep -q RAW_EXPORT_PAIR_MISMATCH "$OUT/mutant.log"
echo RAW_EXPORT_MUTANT_CAUGHT
cat "$OUT/lockstep.log"
yosys -Q -T -p "read_slang --top raw_export_synth $R/rtl/test/meso/raw_export/synth_top.sv $R/rtl/common/ot_dp_clk_landing_ca.sv $R/rtl/common/ot_dp_clk_landing.sv $R/rtl/common/ot_meso_fifo.sv; tcl $R/physical/common_flow/ot_keep_regs.tcl; synth -top raw_export_synth -flatten; write_json $OUT/netlist.json" > "$OUT/synth.log" 2>&1
python3 - "$OUT/netlist.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))['modules']['raw_export_synth'];q=m['ports']['q']['bits'];ex=m['ports']['export_q']['bits'];assert q!=ex,(q,ex)
ff=[v for v in m['cells'].values() if 'DFF' in v['type'].upper()];assert len(ff)==2,ff
print('RAW_EXPORT_PAIR_RETAINED actual_FF=2 added_FF=1 distinct_outputs=2 added_cycles=0')
PY
