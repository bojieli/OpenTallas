#!/usr/bin/env python3
"""Exact direct-wrapper and generated-native output ownership proof (not core LEC)."""
import collections,hashlib,json,pathlib,re
from pin_plan import M,PACK,ROOT,ports
HERE=pathlib.Path(__file__).parent

def topology(top):
 s=(PACK/(top+'.sv')).read_text();P=ports(top);banks=1 if top=='ot_hnx_su_exp__rst3' else 4
 aliases=dict(re.findall(r'assign\s+(\w+\[\d+\])\s*=\s*(n\d+)\s*;',s))
 members={int(k):dict((p,list(reversed([q.strip()for q in v.split(',')if q.strip()])))for p,v in re.findall(r'\.(\w+)\(\{(.*?)\}\)',body))for k,body in re.findall(r'\bm(\d+)\s*\((.*?)\);',s,re.S)}
 checked=[]
 for d,n,w in P:
  if d!='output':continue
  per=w//banks;assert per*banks==w
  for bit in range(w):
   b=bit//per;local=bit%per;member=2*b if n=='bank_read_data' else 2*b+1;port='read_data'if n=='bank_read_data'else n.removeprefix('lane_')
   expected=members[member][port][local];actual=aliases[n+'['+str(bit)+']'];assert actual==expected,(top,n,bit,member,port,expected,actual)
   checked.append(dict(output=n,bit=bit,member='m'+str(member),port=port,member_bit=local,wire=actual))
 return dict(native=top,outputs=len(checked),banks=banks,sha256=hashlib.sha256(s.encode()).hexdigest(),bits=checked)

def adapter(module,top,mutant=False):
 s=(ROOT/'physical/die_plan/hbm_arch_cores/wrappers'/(module+'.sv')).read_text();P=ports(top)
 if mutant:s=s.replace('.lane_lane_id(strap_lane_lane_id)', '.lane_lane_id(~strap_lane_lane_id)')
 head=s.split(');',1)[0];decl={n:(d,int(w)+1 if w else 1)for d,w,n in re.findall(r'(input|output) wire (?:\[(\d+):0\] )?(\w+)',head)}
 assert decl=={('strap_lane_lane_id'if n=='lane_lane_id'else n):(d,w)for d,n,w in P}
 body=s.split('u_native(',1)[1].split(');',1)[0];bindings=dict(re.findall(r'\.(\w+)\(([^()]*)\)',body))
 assert len(bindings)==len(P)
 for d,n,w in P:assert bindings[n]==('strap_lane_lane_id'if n=='lane_lane_id'else n),(module,n,bindings[n])
 assert re.search(r'\b'+re.escape(top)+r'\s+u_native\(',s)
 assert not re.search(r'\b(always|assign|initial|generate)\b',s)
 return dict(module=module,native=top,boundary_bits=sum(w for d,n,w in P),ports=len(P),proof='Every native port maps directly and completely; no state/logic, all possible input histories and native initial states retained')

def main():
 T={top:topology(top)for top in set(M.values())};A=[adapter(m,t)for m,t in M.items()]
 mutants=0
 for m,t in M.items():
  try:adapter(m,t,True)
  except AssertionError:mutants+=1
  else:raise AssertionError('wrong-ID mutant escaped')
 facts=json.load(open(HERE/'native_cut_abi.json'));covered=[r for r in facts if r['module']in T]
 for r in covered:
  P=ports(r['module']);assert r['ports']=={n:w for d,n,w in P};assert r['port_directions']=={n:d for d,n,w in P}
  assert len(r['ids'])==1;id=r['ids']['lane_lane_id'];assert id['width']in(9,11)and 0<=id['value']<2**id['width']
 report=dict(status='PASS_BOUNDARY_AND_OUTPUT_OWNERSHIP_ONLY',adapters=A,wrong_ID_mutants_rejected=mutants,native_cut_instances_covered=len(covered),native_lane_ID_bindings_covered=sum(T[r['module']]['banks']for r in covered),topologies=T,holds=['R7 native identity capture bypass not yet proved','Not a full native arithmetic/sequential LEC','Special 4 plain cuts require their own current adapter; not these canonical families'])
 (HERE/'boundary_graph_receipt.json').write_text(json.dumps(report,indent=1)+'\n');print(report['status'],len(covered),'cuts',report['native_lane_ID_bindings_covered'],'lane IDs',mutants,'mutants')
if __name__=='__main__':main()
