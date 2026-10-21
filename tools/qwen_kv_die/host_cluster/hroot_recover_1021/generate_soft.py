#!/usr/bin/env python3
"""Invoke the unchanged primitive copy algorithm on a scalarized soft region.

This cut has no engine-level done_v boundary; request no special output copies.
Every non-clock input remains bounded, and all output bits are ordinary roots.
"""
import argparse,hashlib,json
from pathlib import Path
import engine_native32 as E
p=argparse.ArgumentParser();p.add_argument('--netlist',type=Path,required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--top',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
E.OUT_COPIES={}
r=E.generate(a.netlist,a.parser,a.sha256,a.top,a.out)
r['entrypoint_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['output_policy']='no special engine done_v boundary exists in this cut';a.out.with_suffix('.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='copied_cells'},indent=1))
