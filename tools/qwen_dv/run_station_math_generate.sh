#!/bin/bash
set -euo pipefail
# Fleet-only invocation from repository root; all generated outputs go to $1.
work=$1
mkdir -p "$work"
python3 tools/qwen_dv/gen_station_math_input.py "$work"
yosys --version > "$work/tool_version.txt"
for mode in add add_base mul; do
 if [ "$mode" = add ]; then top=qfd_dv_station_add_lat;lat=7;src=rtl/qwen_dv/qfd_dv_redstn2_csafe.sv;elif [ "$mode" = add_base ]; then top=ot_hdc_fp32_add_lat;lat=7;src=;else top=qfd_dv_station_mul_lat;lat=6;src=$work/station_mul_exact.sv;fi
 yosys -Q -p "read_verilog -sv -D SYNTHESIS rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv $src; chparam -set LAT $lat -set DRST 0 $top; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; synth -top $top -flatten -noabc -nofsm -noshare; write_json $work/$mode.json" > "$work/$mode.log" 2>&1
 python3 tools/qwen_dv/bound_math_netlist.py "$work/$mode.json" --top "$top" --name "qfd_dv_station_${mode}_g" --out "$work/${mode}_bounded.sv" --helpers "$work/${mode}_helpers.sv" --record "$work/${mode}_receipt.json"
 python3 tools/qwen_dv/bound_math_netlist.py "$work/$mode.json" --top "$top" --name "qfd_dv_station_${mode}_nov_g" --drop-output valid_out --out "$work/${mode}_nov_bounded.sv" --helpers "$work/${mode}_nov_helpers.sv" --record "$work/${mode}_nov_receipt.json"
done
python3 - "$work" <<'PY'
from pathlib import Path
import re,sys,hashlib,json
p=Path(sys.argv[1]);helpers={}
for kind in ['add','add_nov','add_base','add_base_nov','mul','mul_nov']:
 for m in re.finditer(r'(\(\* keep_hierarchy="yes" \*\) module (\w+).*?endmodule)',(p/(kind+'_helpers.sv')).read_text(),re.S):
  if m[2] in helpers:assert helpers[m[2]]==m[1],m[2]
  helpers[m[2]]=m[1]
source=''.join((p/(kind+'_bounded.sv')).read_text() for kind in ['add','add_nov','add_base','add_base_nov','mul','mul_nov'])+'\n'.join(helpers.values())+'\n'
(p/'qfd_dv_station_math_g.sv').write_text(source)
m=json.loads((p/'manifest.json').read_text());m['emitted_source_sha256']=hashlib.sha256(source.encode()).hexdigest();(p/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
PY
