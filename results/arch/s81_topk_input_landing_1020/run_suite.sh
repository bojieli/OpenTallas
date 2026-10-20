#!/bin/bash
set -uo pipefail
O=${1:?out}; mkdir -p "$O"
R=results/arch/s81_topk_input_landing_1020
python3 - "$R" <<'PYC'
from pathlib import Path
import sys
r=Path(sys.argv[1]); t=Path('rtl/dsrom_sys/s81_ph/ot_s81ph_hq_tile.sv').read_text();(r/'dut_hq_in.sv').write_text(t[:t.index('endmodule')+len('endmodule')]+'\n')
PYC
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mode in default raw mut1 mut2; do
 mkdir -p "$O/$mode"
 flags=(); [ "$mode" != default ] && flags+=(-DOT_S81PH_HQ_INPUT_RAW)
 [ "$mode" = mut1 ] && flags+=(-DOT_S81PH_HQ_INPUT_RAW_MUT=1)
 [ "$mode" = mut2 ] && flags+=(-DOT_S81PH_HQ_INPUT_RAW_MUT=2)
 ( "$VL" --version > "$O/$mode/verilator.version"; sha256sum "$R/gold_hq_in.sv" "$R/dut_hq_in.sv" "$R/tb_input_landing.sv" > "$O/$mode/sources.sha256"; "$VL" --binary --timing -j4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style "${flags[@]}" --top-module tb_input_landing "$R/gold_hq_in.sv" "$R/dut_hq_in.sv" "$R/tb_input_landing.sv" -Mdir "$O/$mode/obj" > "$O/$mode/build.log" 2>&1 && "$O/$mode/obj/Vtb_input_landing" > "$O/$mode/run.log" 2>&1; echo $? > "$O/$mode/rc" ) &
done
wait
python3 - "$O" <<'PYC'
import sys,json
from pathlib import Path
p=Path(sys.argv[1]);r={}
for n in ['default','raw','mut1','mut2']:
 d=p/n;t=(d/'run.log').read_text() if (d/'run.log').exists() else '';rc=int((d/'rc').read_text());r[n]=dict(rc=rc,pass_seen='IN_LAND PASS checks=23992' in t,fail_seen='IN_LAND FAIL MUT=' in t)
ok=all(r[n]['rc']==0 and r[n]['pass_seen'] for n in ['default','raw']) and all(r[n]['rc']!=0 and r[n]['fail_seen'] for n in ['mut1','mut2'])
print('INPUT_LANDING_SUITE','PASS' if ok else 'FAIL',json.dumps(r));sys.exit(0 if ok else 1)
PYC
