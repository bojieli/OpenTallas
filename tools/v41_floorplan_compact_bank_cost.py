#!/usr/bin/env python3
"""Charge the actual independent 80bit ME-bank proposal, not ideal shared scales."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def derive():
 p=ROOT/'results/floorplan/v41_spill_resolved_dense.json';x=json.loads(p.read_text());rows=[]
 for s in x['stages']:
  for r in s['ranks']:
   free=r['free_bytes']+len(s['dense_layers'])*(16777216-10485760)
   rows.append(dict(stage=s['stage'],rank=r['rank'],dense_layer_count=len(s['dense_layers']),free_bytes=free))
 return dict(schema='opentallas.v41.compact_woa_finitebank_capacity.v1',status='nonadopted_finite_bank_sensitivity',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bank_contract=dict(banks=8,word_bits=80,words_per_bank=131072,logical_bytes=10485760,savings_per_dense_layer_rank_bytes=6291456),ranks=rows,total_positive_bytes=sum(max(0,r['free_bytes']) for r in rows),total_deficit_bytes=sum(max(0,-r['free_bytes']) for r in rows),net_free_bytes=sum(r['free_bytes'] for r in rows),claim_boundary='Geometry-derived finite 80bit bank payload, preserves conservative dense reservations. No route, complete capacity or rate claim.')
if __name__=='__main__':(ROOT/'results/floorplan/v41_compact_woa_finitebank_capacity.json').write_text(json.dumps(derive(),indent=2)+'\n')
