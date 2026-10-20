import json,subprocess
from pathlib import Path
args=['python3','/src/tools/ref_tile/native_census.py','--netlist','/work/results/asap7/opentallas_qkd_pv_fin_s32_asap7_ref_gate/base/1_2_yosys.v','--top','qkd_pv_fin_s32','--out','/work/native_census.json']
for p in json.loads(Path('/work/census_args.json').read_text()):args+=['--liberty',p]
raise SystemExit(subprocess.call(args))
