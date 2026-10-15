#!/usr/bin/env python3
"""Export real-port aliases from the exact configured canonical source tree."""
import argparse,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import dsrom_s81_fulldie as G
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args();q=argparse.ArgumentParser();q.add_argument('mode');q.add_argument('--k',type=int,default=16);G.die_options(q);G.apply_options(q.parse_args(a.args));assert G.CANONICAL_LAYOUT is not None
aliases=G.real_ports();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(aliases,indent=1)+'\n')
src=['tools/dsrom_s81_fulldie.py','tools/s81/canonical_layout.py','tools/s81/canonical_aliases.py',G.Q_LEF,G.CFG_LEF,G.PHY_LEF,G.SERDES_LEF,G.UCIE_LEF]
receipt={'scope':'Real aliases exported from the configured generator, no guessed names or inferred hardware','alias_sha256':hashlib.sha256(a.out.read_bytes()).hexdigest(),'masters':len(aliases),'source_sha256':{x:hashlib.sha256((R/x).read_bytes()).hexdigest() for x in src},'capacity_sha256':G.CANONICAL_LAYOUT['sha256'],'pair_count':G.PAIRS,'bf_pairs':G.BF_PAIRS};a.out.with_suffix('.sources.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt,indent=1))
