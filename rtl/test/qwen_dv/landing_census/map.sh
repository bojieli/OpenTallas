#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
# Exact container liberty source, common RVT TT NLDM families, no behavior proof.
python3 - "$out" <<'PY'
from pathlib import Path
import gzip,re,sys,hashlib,json
p=Path(sys.argv[1]);lib=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
parts=[];hashes={}
for kind in ('AO','INVBUF','OA','SIMPLE','SEQ'):
 f=lib/f'asap7sc7p5t_{kind}_RVT_TT_nldm_211120.lib.gz'
 s=gzip.open(f,'rt').read();parts.append(s[s.index('{')+1:s.rindex('}')]);hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
(p/'merged.lib').write_text('library(landing_count) {\n'+'\n'.join(parts)+'\n}\n')
(p/'liberty_manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
PY
yosys --version > "$out/yosys_version.txt"
for mode in generic4 physical4 generic8 physical8; do
 case $mode in generic*) phys=0;; *) phys=1;; esac
 d=${mode: -1};k=$((d/2))
 yosys -Q -p "read_liberty -lib $out/merged.lib; read_verilog -sv -D SYNTHESIS rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv rtl/test/qwen_dv/landing_census/vehicle.sv; chparam -set W 1095 -set D $d -set K $k -set PHYSICAL $phys landing_vehicle; synth -top landing_vehicle -flatten -noabc; dfflibmap -liberty $out/merged.lib; abc -liberty $out/merged.lib; clean; write_json $out/$mode.json; stat -liberty $out/merged.lib" > "$out/$mode.log" 2>&1
 python3 rtl/test/qwen_dv/landing_census/census.py "$out/$mode.json" landing_vehicle > "$out/${mode}_census.json"
done
