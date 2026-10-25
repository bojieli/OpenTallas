#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
O=$(realpath "${1:-out_su_oneclock}")
mkdir -p "$O"
profile=${SU_ONECLOCK_PROFILE:-light}
if [ "$profile" = sfu ];then
 python3 tools/hbm_static/su_arith_sfu_compile.py "$O/vectors" 4 4 1 > "$O/compile.log" 2>&1
else
 python3 tools/hbm_static/su_arith_compile.py "$O/vectors" > "$O/compile.log" 2>&1
fi
python3 - "$O" "$profile" <<'PY'
import re,sys
from pathlib import Path
out=Path(sys.argv[1]);profile=sys.argv[2];kind=1 if profile=='sfu' else 0
p=Path(f'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_kind{kind}_lat4_leaf1_physical.sv')
s=p.read_text().replace(f'ot_hbm_su_static_kind{kind}_lat4_leaf1_physical','su_oneclock_kind0').replace('.ALAT(3)', '.ALAT(4)')
(out/'su_oneclock_kind0.sv').write_text(s)
bench=Path('rtl/hbm_accel/generic/adapters/static_su/arithmetic/tb_su_static_lane_leaf.sv').read_text()
if profile=='sfu':
 bench=bench.replace('localparam integer LATENCY=', 'integer LATENCY=').replace('localparam integer FIRST_OUTPUT=', 'integer FIRST_OUTPUT=')
 bench=bench.replace('reg [6967:0] programme', 'reg[11:0] opinfo[0:NOPS-1];\n reg [6967:0] programme')
 bench=bench.replace('176', '256')
 bench=bench.replace('$readmemh({dir,"/control.mem"},programme);', '$readmemh({dir,"/control.mem"},programme);$readmemh({dir,"/opinfo.mem"},opinfo);')
 bench=bench.replace('op=j;count=0;', 'op=j;count=0;LATENCY=opinfo[j][11:4];FIRST_OUTPUT=8+LATENCY+4*PINREG;')
(out/'tb_lane.sv').write_text(bench)
s=Path('tools/hbm_static/su_arith_run.sh').read_text()
files=re.findall(r'(?:rtl|physical)/[\w/]+\.sv|physical/[\w/]+\.v',s)
files=[x for x in files if not x.endswith(('tb_su_static_arithmetic.sv','ot_hdc_fastfp_lat.sv'))]
files += ['rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane_pinreg.sv',str(out/'tb_lane.sv'),str(out/'su_oneclock_kind0.sv'),'rtl/hdc/ot_hdc_fastfp_lat_c12.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/v41x/ot_dsrom_su_add6.sv']
(out/'sources.f').write_text('\n'.join(files)+'\n')
PY
lane=205;if [ "$profile" = sfu ];then lane=129;fi
N=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["ops"]))' "$O/vectors/programme.json")
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -j 2 -Wno-fatal --top-module tb_su_static_lane_leaf -DLEAF_TOP=su_oneclock_kind0 -GNOPS="$N" -GMLAT=4 -GALAT=4 -GLEAF=1 -GLANE="$lane" -GPINREG=1 --Mdir "$O/obj" -f "$O/sources.f" > "$O/build.log" 2>&1
for mode in base ADDR DATA PHASE;do
 args=();if [ "$mode" != base ];then args+=(+MUT_"$mode");fi
 set +e
 "$O/obj/Vtb_su_static_lane_leaf" +DIR="$O/vectors" "${args[@]}" > "$O/$mode.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$O/$mode.exit"
 if [ "$mode" = base ];then test "$rc" = 0;grep 'SU_LANE PASS' "$O/$mode.log";else test "$rc" != 0;grep -q 'SU_LANE FAIL' "$O/$mode.log";fi
done
echo 'SU_ONECLOCK_SUITE PASS ALAT4_f12 MLAT4 actual_SRAMs=6 wrong_address/data/phase mutants_CAUGHT' | tee "$O/done"
