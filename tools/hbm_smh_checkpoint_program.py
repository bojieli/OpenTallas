#!/usr/bin/env python3
"""Bind selected actualcheckpoint SM lines to actual83/34 programme words.

Does not allocate physicalPC/row locations. The downstream image installer must
receive the current explicit reservation and must prove loader/WB delivery.
"""
import hashlib,json
from pathlib import Path
from compile_hbm_smh_issue_static import compile_manifest

def build(payload_manifest,out):
 p=Path(payload_manifest);m=json.loads(p.read_text());out=Path(out);out.mkdir(parents=True,exist_ok=False)
 if m['schema']!='opentallas.actual-checkpoint-sm-payload.v1' or m['SMs']!=32:raise ValueError('actual32SMpayloadselectionrequired')
 plans=[]
 for o in m['ops']:
  if not o['active']:plans.append(dict(sm=o['sm'],active=False,requires_native_idle=True));continue
  source=p.parent/o['file'];raw=source.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=o['sha256']:raise ValueError('actualcheckpointlineSHAchanged')
  r=compile_manifest(dict(ops=[dict(rows=o['rows'],c=8,groups=o['groups'],fmt=o['fmt'],gs=True,x_base=0,base_tag=1000,launch_cycle=1)],packet_lines=raw.decode().split()))
  commands=r['commands'];reads=[];expected=[];idx=0
  for command in commands:
   if command>>29&1:
    tag=command>>30&1023;reads.append(1<<33 | 0x4567<<16 | idx<<10 | tag);idx+=1
   else:reads.append(0)
  if idx!=o['lines']:raise AssertionError('compiledrealissuecountmustmatchactualpayload')
  d=out/f"sm{o['sm']:02d}";d.mkdir()
  for name,values in [('command256.hex',commands),('read256.hex',reads)]:
   (d/name).write_text(''.join(f'{((0xc7a1<<240)|(i<<224)|v):064x}\n' for i,v in enumerate(values)))
  plans.append(dict(sm=o['sm'],active=True,programme_slots=len(commands),real_packets=idx,
     command_file=str((d/'command256.hex').resolve()),read_file=str((d/'read256.hex').resolve()),
     line_file=str(source.resolve()),source_sha256=o['sha256'],tag_base=1000,cache_epoch=0x4567,
     launch_relation='readprogramme1edgebeforecommandprogramme',first_original_S1_hop_after_command_start=6,
     prefetch=dict(useful_bytes=idx*136,sectors=((idx*136+127)//128)*4,pulses=[4,4,4,4,1]),
     compiler_ops=r['ops'],physical_PC_image_bound=False,VM_xwrite_bound=False))
 result=dict(schema='opentallas.checkpoint-sm-static-programme.v1',payload_manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),SMs=32,plans=plans,qualified=False,
 remaining=['explicitphysicalPC/rowreservation','actualloader/WB/34bandreadiness','actualVMxwrite','actualnativeSMresult/immutableprice','physicalclosure'])
 (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--payload',required=True);a.add_argument('--out',required=True);v=a.parse_args();build(v.payload,v.out)
