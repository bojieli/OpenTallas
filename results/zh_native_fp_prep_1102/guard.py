#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);d=json.loads((r/'EXPECTED.json').read_text());k=r/'kit'
for rel,expected in d['expected'].items():
 p=k/rel
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,rel
b=k/'run/results/asap7/hc_ot_nhb_zh__151_2x151_2/base'
assert not any(p.name.startswith(('2_','3_','4_','5_','6_')) for p in b.iterdir())
assert set(d['changed_files'])=={'io.tcl','pins.json','.kw_inputs.json'}
assert d['status']=='PREP_ONLY_NOT_DISPATCHED'
print('PASS exact89inputs/genuineSYNTH/noCADoutputs; no execution authorization')
