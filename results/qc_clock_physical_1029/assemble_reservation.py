#!/usr/bin/env python3
"""Keep exact clock-cell PG prefix and append native M8 bridge geometry."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--clock-access',required=True);p.add_argument('--bridge-plan',required=True);p.add_argument('--out',required=True);a=p.parse_args()
raw=Path(a.clock_access).read_bytes().strip();assert raw.startswith(b'[') and raw.endswith(b']')
b=json.load(open(a.bridge_plan));assert not b['failed'];tail=[[q['net'],'M8',*[v/b['dbu'] for v in q['m8_dbu']]] for q in b['paths']]
assert all(r[0] in ('VDD','VSS') for r in tail)
result=raw if not tail else raw[:-1]+b','+json.dumps(tail,separators=(',',':')).encode()[1:]
Path(a.out).write_bytes(result+b'\n');print('ASSEMBLED_NATIVE_BRIDGES',len(tail),flush=True)
