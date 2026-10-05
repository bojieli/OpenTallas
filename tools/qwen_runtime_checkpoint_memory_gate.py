#!/usr/bin/env python3
"""Qualify full-size layer0 hex loading and host memory edge semantics only."""
import argparse,pathlib,subprocess,json,hashlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--images',type=pathlib.Path,required=True);ap.add_argument('--oracle',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
oracle=json.loads(a.oracle.read_text());pins={}
for name,expected in [(f'die0/{n}',h) for n,h in oracle['input_image_sha256']['die0'].items() if n in ('matrix_int8.hex','matrix_scale_bf16.hex')]+[('vm_x_fp32.hex',oracle['x_preload_sha256'])]:
 pins[name]=hashlib.sha256((a.images/name).read_bytes()).hexdigest()
 if pins[name]!=expected:raise ValueError('oracle input hash mismatch: '+name)
source=ROOT/'tools/runtime/qwen_runtime_memory_gate.cpp';header=ROOT/'tools/runtime/qwen_runtime_memory.hpp'
subprocess.run(['g++','-std=c++17','-O2',str(source),'-o',str(a.out/'gate')],check=True)
start=time.monotonic();run=subprocess.run(['/usr/bin/time','-v',str(a.out/'gate'),str(a.images),str(a.out/'samples.txt')],capture_output=True,text=True,check=True);elapsed=time.monotonic()-start
(a.out/'run.log').write_text(run.stdout+run.stderr)
codes=(a.images/'die0/matrix_int8.hex').read_text().splitlines();scales=(a.images/'die0/matrix_scale_bf16.hex').read_text().splitlines();count=0
for line in (a.out/'samples.txt').read_text().splitlines():
 fields=line.split()
 if fields[0]=='S':_,r,l,value=fields;r,l,value=map(int,(r,l,value));expected=(int(scales[r],16)>>(32*l))&0xffffffff
 else:r,g,l,value=map(int,fields);expected=(int(codes[r],16)>>(32*(g*4+l)))&0xffffffff
 if value!=expected:raise ValueError('independent packed word mismatch')
 count+=1
result={'status':'pass','independent_word_checks':count,'image_sha256':pins,'oracle_sha256':hashlib.sha256(a.oracle.read_bytes()).hexdigest(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,header,pathlib.Path(__file__)]},'wall_seconds':elapsed,'verdict':run.stdout.strip(),'claim_boundary':'Checkpoint loader and host edge read/write semantics; not composed RTL token or memory-performance proof.'}
(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['verdict'])
