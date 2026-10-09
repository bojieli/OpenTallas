#!/usr/bin/env python3
"""Small reviewable native SU registry from the actual graph and ROM contract."""
import argparse,hashlib,json
from pathlib import Path
from qwen_r25_native_bridge import resolve
p=argparse.ArgumentParser();p.add_argument('--program',required=True,type=Path);p.add_argument('--install',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
x=resolve(json.loads(a.program.read_text()),json.loads(a.install.read_text()))
entries=[dict(id=o['id'],batch=b['name'],kernel=o['kernel'],unit=o['unit'],production_entry=o['production_entry']) for b in x['batches'] for o in b['operations']]
a.out.write_text(json.dumps(dict(schema='opentallas.qwen.native_su_registry.v1',program_sha256=hashlib.sha256(a.program.read_bytes()).hexdigest(),entries=entries,resolved_native_SU_entries=x['resolved_native_SU_entries'],missing_production_entries=x['missing_production_entries'],full_decode_executable=False),indent=2)+'\n')
print('native SU',sum(o['production_entry'] is not None for o in entries),'of',len(entries),'graph operations; unresolved kernel families',len(x['missing_production_entries']))
