#!/usr/bin/env python3
"""Exact input-only remap using the existing RING placer; never runs a model."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLACER=ROOT/'tools/w11_idx_ring_place.py'
PLACER_SHA='00d0e774c683c467fee88d15397d20771697e59f346144d6454b87366383b9d5'
if hashlib.sha256(PLACER.read_bytes()).hexdigest()!=PLACER_SHA:raise ValueError('qualified placer source changed')

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    a=p.parse_args()
    if a.output_root.exists():raise ValueError('output must be fresh; no overwrite/retry')
    spec=importlib.util.spec_from_file_location('ring',PLACER);ring=importlib.util.module_from_spec(spec);spec.loader.exec_module(ring)
    assert ring.geometry(64,32)==(65568,1090)
    a.output_root.mkdir(parents=True)
    rows=[]
    for rank in range(4):
        src=a.input_root/f'r{rank}/ikhbm_region.hex'
        raw=src.read_bytes();source_hash=hashlib.sha256(raw).hexdigest()
        img=ring.read_sparse(src);keys=ring.keys_of(img)
        expected=262143 if rank==3 else 262144
        if set(keys)!=set(range(expected)):raise ValueError(f'rank{rank}: prior-history key coverage differs')
        if rank==3 and 262143 in keys:raise ValueError('native current key must not be preloaded')
        # Count selects FINAL native scan/writer quarter ownership; it is not
        # an assertion that current key exists in this prior-history image.
        placed=ring.place(img,n=262144,kb=0,rsb=64,rtail=32)
        dest=a.output_root/f'r{rank}';dest.mkdir()
        outputs=[]
        for stack,sectors in placed.items():
            out=dest/f'ikring_s{stack}.hex'
            out.write_text(''.join(f'{address:x} {word:064x}\n' for address,word in sorted(sectors.items())))
            count=sum(stack*65536<=t<(stack+1)*65536 for t in keys)
            outputs.append({'stack':stack,'path':str(out.resolve()),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
              'bytes':out.stat().st_size,'prior_keys':count,'nonzero_sparse_sector_count':len(sectors),
              'sector_min':min(sectors),'sector_max':max(sectors),
              'address_units':'256-bit sector; PC/column ownership remains selected native provider responsibility'})
        rows.append({'rank':rank,'input':str(src.resolve()),'input_bytes':len(raw),'input_sha256':source_hash,
          'legacy_relative_sector_count':len(img),'prior_key_count':len(keys),'local_key_min':min(keys),'local_key_max':max(keys),
          'global_keys':[rank*262144,rank*262144+expected-1],'outputs':outputs})
        print(f'prepared rank{rank} prior_keys={len(keys)}',flush=True)
    manifest={'schema':'dsrom-L20-raw-ring-priorhistory-v1','placer':{'path':'tools/w11_idx_ring_place.py','sha256':PLACER_SHA},
      'source_provenance':'existing seeded20260930 context1048576 L20 prior state; raw codes/scales only, not checkpoint-trained-history qualification',
      'source_context':1048576,'current_global_key_excluded':1048575,'native_current_key_owner':'rank3 local262143; actual source producer/writer only',
      'placement':{'RING':1,'RSB':64,'RTAIL':32,'WB':32,'GA':24,'C':65568,'UBLK':1090,'cfg_logical_base':16777216,
        'user':0,'region':0,'physical_base_block_KB':0,'scan_count_per_rank':262144,'quarter_per_stack':65536,
        'quarter_partition_uses_final_scan_count_not_prior_history_count':True,'ring_slot':'local key t modulo65568',
        'codes_sector':'(KB+17*(slot//1024)+1+(slot%1024)//64)*128+2*(slot%64), and+1',
        'scale_sector':'(KB+17*(slot//1024))*128+(slot%1024)//8; 32-bit field slot%8'},
      'ranks':rows,'prior_keys_total':sum(r['prior_key_count'] for r in rows),
      'native_current_key_preloaded':False,'host_quantization':False,'golden_outputs_or_activation_payload':False,
      'native_execution_or_component_benchmark':False,'actual_provider_PC_mapping_adopted':False}
    (a.output_root/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(a.output_root/'manifest.json',flush=True)
if __name__=='__main__':main()
