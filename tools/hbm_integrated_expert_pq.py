#!/usr/bin/env python3
"""Exact 32-PC interleave -> gearbox -> full NC8 PQ/XMAP production SM.

Retained released GU inputs and their golden rows are mandatory. PACK_W2=1
is compiled, but this GU-only numerical boundary does not exercise W2 pairing,
SU or attention. The existing service checks all released W2 transport bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import dshbm_expert_interleave_native as I
import dshbm_w2_pair_seq as P
import hbm_accel_activation_layout as X
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
TOP='tb_hbm_integrated_expert_pq'
SRC=list(dict.fromkeys([s for s in P.SRC if not s.startswith('rtl/test/')]+I.NEW+[
 'rtl/test/hbm_accel/integrated_20261006/'+TOP+'.sv']))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare_arithmetic(out, weights, inputs, layer, die=2, stack=0):
 """Golden only the 72 released GU rows consumed by this minimum component."""
 ids=tuple(map(int,np.fromfile(inputs/f'L{layer}/expert_ids.u32',dtype='<u4')))
 x=I.G.from_bits(np.fromfile(inputs/f'L{layer}/ffn_norm.u32',dtype='<u4'))
 reader=I.exported_weight_reader(weights/f'L{layer}',layer,ids)
 out.mkdir(parents=True,exist_ok=False);gu=[];expected=[];gold=[];xw=None
 for e in ids:
  p,sc=I.paired_rows(reader,e,die,stack);raw=I.compact_stream(p,sc);g=I.sm_vectors(p,sc,x)
  if I.expand_stream(raw)!=tuple(g['lines']):raise ValueError('service/numerical byte order')
  gu.extend(int.from_bytes(raw[i:i+128],'little') for i in range(0,len(raw),128))
  expected.extend(g['lines']);gold.extend(int(I.G.bits(v)) for v in g['gold'][0]);xw=g['xw']
 for name,data,width in [('gu.hex',gu,256),('sm_expected.hex',expected,272),('gold.hex',gold,8),('x.hex',xw,6816)]:
  (out/name).write_text(''.join(f'{v:0{width}x}\n' for v in data))
 (out/'input_origin.json').write_text(json.dumps(dict(layer=layer,die=die,stack=stack,ids=ids,
  source_weights=sha(weights/f'L{layer}/source.json'),source_activation=sha(inputs/f'L{layer}/ffn_norm.u32'),
  scope='72-row reference arithmetic; no model inference'),indent=2)+'\n')
 return ids
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--service',type=Path,required=True)
 p.add_argument('--arithmetic',type=Path,required=True);p.add_argument('--ids',required=True)
 p.add_argument('--jobs',type=int,default=16)
 p.add_argument('--step',choices=['all','frontend','build-run'],default='all');a=p.parse_args()
 if a.step!='build-run':
  a.out.mkdir(parents=True,exist_ok=False);case=a.out/'case';case.mkdir()
  for name in ('gu.hex','sm_expected.hex'):
   if sha(a.service/name)!=sha(a.arithmetic/name):raise ValueError('numerical and service source bytes differ: '+name)
  for name in ('gu.hex','sm_expected.hex','w2.hex','cfg_lut.hex'):
   shutil.copyfile(a.service/name,case/name)
  shutil.copyfile(a.arithmetic/'gold.hex',case/'gold.hex')
  words=[int(x,16) for x in (a.arithmetic/'x.hex').read_text().split()]
  if len(words)!=24:raise ValueError('full GU activation extent')
  (case/'xmap.hex').write_text(''.join(f'{X.pack_fragment(x,2,1):06816x}\n' for x in words))
  sources={s:sha(ROOT/s) for s in SRC}
  command=['verilator','--cc','--exe','--main','--timing','-O2','-Wno-fatal','--top-module',TOP,
   '--Mdir',str(a.out/'obj'),'-j',str(a.jobs),*[str(ROOT/s) for s in SRC]]
  (a.out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
  with (a.out/'build.log').open('w') as log:
   rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
  if rc:return rc
  (a.out/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
 else:
  case=a.out/'case';sources=json.loads((a.out/'sources.json').read_text())
  if any(sha(ROOT/s)!=h for s,h in sources.items()):raise ValueError('frontend source changed')
 if a.step=='frontend':return 0
 with (a.out/'make.log').open('x') as log:
  rc=subprocess.run(['make','-C',str(a.out/'obj'),'-f','V'+TOP+'.mk','-j',str(a.jobs)],stdout=log,stderr=subprocess.STDOUT).returncode
 if rc:return rc
 exe=a.out/'obj'/('V'+TOP);ids=[int(x) for x in a.ids.split(',')]
 if len(ids)!=6:raise ValueError('six router IDs required')
 base=[str(exe),f'+DIR={case}','+notice_lead_ps=300000']+[f'+id{k}={i}' for k,i in enumerate(ids)]
 rows=[]
 for slot in range(6):
  log=a.out/f'slot{slot}.log'
  with log.open('w') as f:rc=subprocess.run(base+[f'+sm_slot={slot}'],stdout=f,stderr=subprocess.STDOUT).returncode
  body=log.read_text();ok=rc==0 and 'INTEGRATED_PQ_XMAP_PASS' in body and 'FIRST verdict=PASS' in body
  rows.append(dict(slot=slot,exit=rc,exact=ok,measurements=[s for s in body.splitlines() if s.startswith(('INTEGRATED_','BW ','SLOT '))]))
  if not ok:break
 negative=a.out/'corrupt_sector.log'
 with negative.open('w') as f:nrc=subprocess.run(base+['+sm_slot=0','+mut=1'],stdout=f,stderr=subprocess.STDOUT).returncode
 neg=nrc!=0 and 'GU sector mismatch' in negative.read_text()
 stable=all(sha(ROOT/s)==h for s,h in sources.items())
 passed=len(rows)==6 and all(x['exact'] for x in rows) and neg and stable
 record=dict(pass_exact=passed,source_sha256=sources,binary_sha256=sha(exe),rows=rows,
  corrupt_sector_rejected=neg,source_stable=stable,inputs={n:sha(case/n) for n in ('gu.hex','sm_expected.hex','w2.hex','cfg_lut.hex','gold.hex','xmap.hex')},
  flags=dict(ENABLE=1,PQ_ENABLE=1,XMAP=1,PACK_W2=1,WG=1),
  scope='L20 actual GU service to NC8 arithmetic; W2 byte transport only; not all-lever layer/token or physical qualification')
 (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(dict(pass_exact=passed,slots=len(rows),negative=neg)))
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
