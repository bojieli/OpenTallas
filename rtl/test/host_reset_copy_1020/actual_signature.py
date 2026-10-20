#!/usr/bin/env python3
"""Proposal evidence only. Equal after reset, never unconditional arbitrary-initial Q aliasing."""
import sys,json,re,copy
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import gray_fifo_cdc_constraints as G

def qualified_signature(f):
 if not re.fullmatch(r'\$_DFF_[PN][PN][01]_',f.get('t','')):
  raise ValueError('requires literal async reset value and edge type')
 if not isinstance(f.get('r'),int):raise ValueError('requires real common reset, never missing/tied reset')
 return f['t'],f['d'],f['c'],f['r']

def same_after_reset(a,b):
 if qualified_signature(a)!=qualified_signature(b):raise ValueError('D/clock/reset/type/value mismatch')
 return True

def verify(root):
 s=json.loads((root/'rtl/test/host_cdc_safe_1020/host_sram1.json').read_text())
 hashes,_=G._elaborate_sources(s,root)
 doc=G.elaborate(str(root),s['top'],hashes,tuple(sorted(s.get('params',{}).items())),G._yosys(),True,preserve_kept=True)
 net=G._netlist(doc,s,G._macro_clock_pins(s,root),True)
 out=[]
 for canonical,copies in [('req','req_copy'),('ack_host','ack_copy')]:
  base='u_rank__u_fence.g_on.'
  cb=net.resolve(base+canonical,'canonical')[1][0];bs=net.resolve(base+copies,'copies')[1]
  f=net.flops[cb]
  row=dict(canonical=net.key(cb),signature=qualified_signature(f),copies=[])
  for b in bs:
   same_after_reset(f,net.flops[b]);row['copies'].append(net.key(b))
  for key,value in [('d',-7),('c',-8),('r',None),('r','0'),('t','$_DFF_PN1_')]:
   mutant=copy.deepcopy(f);mutant[key]=value
   try:same_after_reset(f,mutant)
   except ValueError:pass
   else:raise AssertionError('bad signature admitted '+key)
  out.append(row)
 return dict(qualification='PROPOSAL_ONLY_AFTER_COMMON_RESET_ASSERTION; no pre-reset alias or signoff/adoption',groups=out,negative_checks_per_group=5)

if __name__=='__main__':
 report=verify(ROOT)
 out=ROOT/'reset_copy_proof/actual_signature.json';out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+'\n');print(out)
