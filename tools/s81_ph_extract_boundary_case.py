#!/usr/bin/env python3
"""Read-only extraction of selected S81 boundary nets from an existing die case."""
import argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--generator',type=Path,required=True);a=ap.parse_args()
prefixes=tuple(f'n_co{st}_{k}0' for st in ['SW','SE','NW','NE'] for k in ['d','f'])
slabs=[f'{b}_{st}' for st in ['SW','SE','NW','NE'] for b in ['svc','ctrl','phy']]
p=a.case/'die.v';b=p.read_bytes();s=b.decode();selected={};nets={}
# Anchor at line start: unanchored matching is expensive on very large net names.
for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);',s,re.S|re.M):
 master,inst,body=m.groups()
 pairs=dict(re.findall(r'\.(\w+)\s*\(([^)]*)\)',body))
 relevant={k:v for k,v in pairs.items() if v.startswith(prefixes)}
 if relevant or inst in slabs:
  if inst.startswith('phy_'):pairs={k:v for k,v in pairs.items() if k in ['clk','rst_n','k_v','k_rdy','k_addr','k_tag','kr_v']}
  selected[inst]=dict(master=master,ports=pairs)
  for port,net in relevant.items():nets.setdefault(net,[]).append([inst,port])
widths={}
for m in re.finditer(r'\bwire\s*\[(\d+):(\d+)\]\s+(\w+)\s*;',s):
 if m[3] in ['n_clk_stream','n_clk_hbm'] or m[3].startswith(prefixes+('n_rd_','n_dfi_')):widths[m[3]]=abs(int(m[1])-int(m[2]))+1
print(json.dumps(dict(schema='opentallas.s81.boundary_case_excerpt.v1',case=str(a.case),source_commit=a.source_commit,
 die_v_sha256=hashlib.sha256(b).hexdigest(),generator_sha256=hashlib.sha256(a.generator.read_bytes()).hexdigest(),instances=selected,nets=nets,widths=widths,
 qualification='Connectivity only, not routed timing. Does not flatten the S81-PH composition.'),indent=2,sort_keys=True))
