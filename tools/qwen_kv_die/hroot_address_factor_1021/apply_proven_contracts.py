#!/usr/bin/env python3
"""Compositional proof only: apply source-bound, universally proved helper lemmas.

This lowered vehicle is never shipping RTL and is never a native/cold proof.
"""
from pathlib import Path
import re,hashlib,json,sys
src=Path(sys.argv[1]);math=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
binding=json.loads((math/'binding.json').read_text());receipt=json.loads((math/'receipt.json').read_text())
assert all(receipt[k]['pass'] and receipt[k]['rc']==0 for k in ['add','mul3','mul5'])
for k in ['add','mul3','mul5']:
 assert hashlib.sha256((math/(k+'.sv')).read_bytes()).hexdigest()==receipt['sha256'][k+'.sv']
s=src.read_text();helpers='\n'.join(re.findall(r'    function automatic \[31:0\] af_.*?    endfunction',s,re.S))
assert hashlib.sha256(helpers.encode()).hexdigest()==binding['extracted_helper_sha256']
s=re.sub(r'    function automatic \[31:0\] af_.*?    endfunction\n?', '',s,flags=re.S)
applications=[]
while True:
 matches=list(re.finditer(r'\b(af_add32|af_mul3|af_mul5)\(',s))
 if not matches:break
 m=matches[-1];start=m.end();depth=1;i=start;comma=None;braces=0;brackets=0
 while depth:
  c=s[i]
  if c=='(':depth+=1
  elif c==')':depth-=1
  elif c=='{':braces+=1
  elif c=='}':braces-=1
  elif c=='[':brackets+=1
  elif c==']':brackets-=1
  elif c==',' and depth==1 and braces==0 and brackets==0:
   assert comma is None;comma=i
  i+=1
 assert comma is not None
 a=s[start:comma];b=s[comma+1:i-1];operator='+' if m.group(1)=='af_add32' else '*'
 replacement=f'(({a}) {operator} ({b}))'
 applications.append(dict(helper=m.group(1),original_call=s[m.start():i],contract='unsigned32 modular '+operator,lemma_fixture_sha256=receipt['sha256'][{'af_add32':'add.sv','af_mul3':'mul3.sv','af_mul5':'mul5.sv'}[m.group(1)]]))
 s=s[:m.start()]+replacement+s[i:]
s=s.replace('module candidate(', 'module candidate_lowered(')
assert 'af_' not in s
(out/'candidate_lowered.sv').write_text(s)
(out/'contract_application.json').write_text(json.dumps(dict(scope='compositional binary source address equivalence using universally proved helper lemmas; not direct monolithic SAT, not mapped/cold proof',projection_candidate_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),helper_sha256=binding['extracted_helper_sha256'],math_receipt_sha256=hashlib.sha256((math/'receipt.json').read_bytes()).hexdigest(),applications=applications,lowered_sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2)+'\n')
print('SOURCE_BOUND_LEMMA_APPLICATIONS',len(applications))
