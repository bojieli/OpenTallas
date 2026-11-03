from pathlib import Path
import json,hashlib,sys
r=Path(sys.argv[1]);mode=sys.argv[2];d=json.loads((r/'CTS_SOURCE_INPUTS.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,want in {**d['original_inputs'],**d['actual_saved_PLACE_inputs']}.items():assert sha(r/'kit'/rel)==want,rel
m=json.loads((r/'CTS_INSTRUMENT_INPUTS.json').read_text())
for rel,want in m['files'].items():assert sha(r/rel)==want,rel
base=r/'kit/run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';assert not any(p.name.startswith(('5_','6_')) for p in base.iterdir())
if mode!='run':assert not any(p.name.startswith('4_') for p in base.iterdir())
else:assert all((base/n).is_file() for n in ['4_1_cts.odb','4_cts.odb','4_cts.sdc'])
print('PASS_CTS_CURRENT_INPUT_GUARD',mode,'94 source inputs plus exact current PLACE and pinned instruments; no stage5+')
