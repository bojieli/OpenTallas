#!/usr/bin/env python3
"""Enumerate every rank/SM installation obligation without claiming completion."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 source=ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json';r=json.loads(source.read_text());slots=[]
 for rank in range(96):
  for sm in range(32):
   active=sum((m['rank_row_intervals'][rank][1]-m['rank_row_intervals'][rank][0])>sm for m in r['matrices'])
   slots.append(dict(rank=rank,sm=sm,stack=sm//8,pcs=list(range(4*(sm%8),4*(sm%8)+4)),payload_bytes=r['rank_sm_reserved_bytes'][rank][sm],active_matrices=active,idle_matrices=len(r['matrices'])-active,actual_image_exported=False,actual_ACK_verified=False,native_programme_verified=False))
 result=dict(schema='opentallas.hbm.native-checkpoint-install-domain.v1',source_residency=str(source.relative_to(ROOT)),source_sha256={str(source.relative_to(ROOT)):hashlib.sha256(source.read_bytes()).hexdigest(),'tools/hbm_checkpoint_native_install_domain.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},selector='hbm_checkpoint_native_plan.descriptor + hbm_checkpoint_native_stream.export, explicit matrix/expert; idle assignments emit no surrogate',status='ALL_SLOTS_ENUMERATED_NOT_ALL_INSTALLED',payload_bytes_total=sum(x['payload_bytes'] for x in slots),slots=slots)
 out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(dict(slots=len(slots),payload_bytes=result['payload_bytes_total'],all_installed=False)))
if __name__=='__main__':run(ROOT/'results/arch/hbm_die_v15/full_native_streamed_images/all96rank32sm_install_domain.json')
