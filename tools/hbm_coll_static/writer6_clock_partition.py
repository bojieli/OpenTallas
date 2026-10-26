#!/usr/bin/env python3
"""Classify actual writer-v5 final ODB FF rows into additive v6 source clock owners.
Input is source-pinned classify.json from the retained routed ODB, not an area estimate.
The v6 mapped count and per-root physical phi-R remain separate pending gates.
"""
import argparse,collections,csv,gzip,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('classification',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
d=json.loads(a.classification.read_text());groups=collections.defaultdict(list)
def owner(r):
 n=r['instance'];m=re.match(r'(d0|a0|v0|m0|kq)\[(\d+)\]',n)
 if m:
  family,bit=m[1],int(m[2])
  if family=='d0':return f'clk_rgx_data{bit//512}' if bit<2048 else 'clk_tkw'
  if family=='a0':return 'clk_rgx_ctrl' if bit<160 else 'clk_tkw'
  if family=='v0':return 'clk_rgx_ctrl' if bit<4 else 'clk_tkw'
  if family=='m0':return 'clk_tkw' if bit>=64 else 'clk_rgx_ctrl'
  if family=='kq':return f'clk_bank{bit//281}'
 if 'in:meta' in r['groups']:return 'clk_meta'
 return 'clk_body'
for r in d['registers']:groups[owner(r)].append(r)
assert len(groups)==16 and sum(map(len,groups.values()))==9247
rows={k:dict(old_mapped_flops=len(v),tt_arrival_min_ps=min(x['arrival_ps'] for x in v),tt_arrival_max_ps=max(x['arrival_ps'] for x in v),tt_arrival_mean_ps=sum(x['arrival_ps'] for x in v)/len(v),bbox_um=[min(x['x'] for x in v),min(x['y'] for x in v),max(x['x'] for x in v),max(x['y'] for x in v)]) for k,v in groups.items()}
with gzip.open(a.out/'old_ff_to_v6_root.csv.gz','wt',newline='') as f:
 w=csv.writer(f);w.writerow(['instance','x_um','y_um','tt_clock_arrival_ps','proposed_v6_root'])
 for r in d['registers']:w.writerow([r['instance'],r['x'],r['y'],r['arrival_ps'],owner(r)])
(a.out/'partition.json').write_text(json.dumps(dict(scope='Actual v5 routed FF classification and proposed source ownership only; new v6 physical mapping and phase closure OPEN',original_source='8e0909ea18fe7fcb22027f03b77b28fe6e6dc053',original_odb_sha256='88d3bf85a5d806eb3a1059395b9249ad0de56ec043d924ce238bdff72dc5e6d8',classification_sha256=hashlib.sha256(a.classification.read_bytes()).hexdigest(),old_mapped_flops=9247,roots=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
