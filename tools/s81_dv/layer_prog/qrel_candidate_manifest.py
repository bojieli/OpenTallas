#!/usr/bin/env python3
"""Prepare only an explicit candidate of the existing QREL macro definition."""
import argparse,json,re
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--lut',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():raise ValueError('fresh candidate manifest required')
if not re.fullmatch(r'[0-9a-fA-F]{32}',a.lut):raise ValueError('exact128-bit LUT hex required')
d=json.loads(a.manifest.read_text());definitions=d.get('defines',[])
if not all(isinstance(x,str)for x in definitions):raise ValueError('actual string definition list required')
d['defines']=[x for x in definitions if x.split('=',1)[0]!='OT_S81SL_QREL_DELAYS']+["OT_S81SL_QREL_DELAYS=128'h"+a.lut.lower()]
d['note']=d.get('note','')+' | ROOT-approved QDELAYS PARAMETER PREP ONLY: existing opt-in macro, no canonical adoption/source epoch/physical qualification.'
a.out.write_text(json.dumps(d,indent=1)+'\n');print('QREL_CANDIDATE_MANIFEST_ONLY',a.out)
