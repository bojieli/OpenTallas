#!/bin/bash
set -euo pipefail
python3 tools/hbm_hc/compact_netlist.py out_fold/retained.v out_fold/root_k4_p40_native.v --top ot_hbm_hc_root_static --header 'DIAGNOSTIC parent source: native24 qualified at explicit QCHX12 SAFE1 TAILC1 PTFS1 SDIV17 TTPIPE1 SKP2. Children use interface-only stand-ins until actual k4 views replace them.' > out_fold/compact.log
python3 - <<'PYS'
from pathlib import Path
import glob,json,re,subprocess,hashlib
libs=sorted(glob.glob('libs/*.lib'))
script='read_verilog out_fold/retained.v; stat '+' '.join('-liberty '+p for p in libs)
subprocess.run(['yosys','-Q','-T','-p',script],stdout=open('out_fold/area.log','w'),stderr=subprocess.STDOUT,check=True)
s=Path('out_fold/area.log').read_text();print(s[-2000:])
m=re.search(r'Chip area[^:]*:\s*([0-9.]+)',s)
if not m:raise SystemExit('area not reported')
n=json.load(open('out_fold/native_retained.json'))
d={k:n[k] for k in ['status','max_dynamic_loads','roots_examined','role_errors','netlist']};d['std_area_um2']=float(m.group(1));d['compacted_sha256']=hashlib.sha256(Path('out_fold/root_k4_p40_native.v').read_bytes()).hexdigest();d['source_params']=json.load(open('sources.json'))['params'];d['child_counts']={'ot_hbm_hc_tail_child_static':2,'ot_sram_1r1w_1024x256_m2_r2c2':2,'ot_sram_1r1w_128x256_m1_r2c2':3};Path('out_fold/parent_native_summary.json').write_text(json.dumps(d,indent=2)+'\n')
PYS
