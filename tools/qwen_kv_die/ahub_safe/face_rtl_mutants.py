#!/usr/bin/env python3
import gzip,hashlib,json,re
from pathlib import Path
s=Path('distributed/qkd_ahub_static_dw_safe_native.v').read_text();p=json.load(open('distributed/distribution.json'));v=json.load(open('evidence/verification.json'));old=json.load(gzip.open('results/arch/kv_ahub_structural_source_1019/distribution.json.gz'))
face=next(x['ff']for x in v['output_boundary_ledger']if x['port']=='am1'and x['bit']==9)
origin=next(x['origin']for x in old['emitted']if x['emitted']=='safe_c7351');reset=next(x['emitted']for x in p['emitted']if x['origin']==origin and x['copy']==0)
manifest={}
for tag,inst,pin,value in [('face_D',face,'D','~('+next(x['ports']['D'][0]for x in p['emitted']if x['emitted']==face)+')'),('sticky_RESETN',reset,'RESETN',"1'b1")]:
 lines=s.splitlines();changes=0
 for i,line in enumerate(lines):
  if f' {inst} 'in line:
   lines[i],count=re.subn(r'\.\\'+pin+r' \([^)]*\)',lambda m:'.\\'+pin+' ('+value+')',line);changes+=count
 assert changes==1,(tag,inst,changes)
 text='\n'.join(lines)+'\n';path=Path('evidence/negatives')/(tag+'.v');path.write_text(text);manifest[tag]={'instance':inst,'pin':pin,'value':value,'sha256':hashlib.sha256(text.encode()).hexdigest()}
Path('evidence/negatives/rtl_mutants.json').write_text(json.dumps(manifest,indent=2)+'\n')
