#!/usr/bin/env python3
"""Follow actual selected PC group fault bits to D2D KV flush (source edge ledger)."""
import argparse,collections,hashlib,json,re
from pathlib import Path
SHA='18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6'
def bits(s):
 s=s.strip()
 if s.startswith('{'):
  # Selected relay ports use flat concatenations; reject unsupported expression syntax.
  inside=s[1:-1];m=re.fullmatch(r'(\d+)\{(.*)\}',inside)
  if m:return bits(m[2])*int(m[1])
  return sum((bits(x) for x in inside.split(',')),[])
 m=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',s)
 if m:
  hi=int(m[2]);lo=int(m[3] or m[2]);return [(m[1],i) for i in range(hi,lo-1,-1)]
 m=re.fullmatch(r"(\d+)'[bdh]([0-9a-fA-FxXzZ]+)",s)
 if m:return [(s,None)]*int(m[1])
 if re.fullmatch(r'\w+',s):return [(s,0)]
 raise ValueError('unsupported bound expression '+s)
def main():
 p=argparse.ArgumentParser();p.add_argument('die',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raw=a.die.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 instances={}
 for line in raw.decode().splitlines():
  m=re.fullmatch(r'\s*(\w+)(?:\s*#\(.*?\))?\s+(\w+)\s*\((.*)\);\s*',line)
  if m:instances[m[2]]=dict(master=m[1],ports=dict(re.findall(r'\.(\w+)\((.*?)\)(?=,\s*\.|$)',m[3])))
 arcs=collections.defaultdict(list);endpoints=collections.defaultdict(list)
 def wire(src,dst,edges,label,clock):
  assert len(src)==len(dst),(label,len(src),len(dst))
  for x,y in zip(src,dst):arcs[x].append((y,edges,label,clock))
 for name,i in instances.items():
  master=i['master'];ps=i['ports'];ck=ps.get('ck')
  if re.fullmatch(r'qkd_rlys_\d+',master):wire(bits(ps['a']),bits(ps['b']),1,name+':'+master,ck)
  elif re.fullmatch(r'qkd_landsh0?_\d+|qkd_rlysh0?_\d+',master):
   wire(bits(ps['a']),bits(ps['b']),None,name+':'+master+':production_calendar_required',dict(source=ps.get('ck_s',ps.get('ckf',ps.get('ck'))),destination=ps.get('ck'),k=[ps.get('k0'),ps.get('k1'),ps.get('k2')],reset=ps.get('rs'),epoch=ps.get('en',ps.get('ea'))))
  elif master=='qkd_kvs_grp':wire(bits(ps['i_up'])[18:],bits(ps['o_ctl'])[:-18],0,name+':group_forward',ck)
  elif master=='qkd_kvs_hroot':
   ins=bits(ps['i_g']);outs=bits(ps['o_ctl']);il=list(reversed(ins));
   # Easier direct MSB-first assignment copied from the exact source equation.
   rhs=sum(([il[b] for b in range(hi,lo-1,-1)] for hi,lo in [(17,0),(35,18),(125,108),(143,126),(53,36),(71,54),(89,72),(107,90)]),[])
   wire(rhs,outs,1,name+':stack_g_register_and_permute',ck)
  elif master=='qkd_kvs_ctl':
   for pn,exp in ps.items():
    if pn.startswith('i_hroot_'):
     b=list(reversed(bits(exp)))
     for bit in range(17,144,18):wire([b[bit]],bits(ps['oobs__kv_flush_local']),2,name+':oobs_gf_q_then_flush',ck)
  elif master=='qkd_d2d_static':
   for x in bits(ps['kv_flush_local']):endpoints[x].append(dict(instance=name,port='kv_flush_local',clock=ck,internal_STATUS_latency=None,host_retirement_veto=False))
 groups=[(n,i) for n,i in instances.items() if i['master'] in ('qkd_kvs_grp','qkd_kvs_grp_h')];assert len(groups)==32
 records=[]
 for name,g in groups:
  source=list(reversed(bits(g['ports']['o_ctl'])))[17]
  queue=collections.deque([(source,0,[],[])]) ;found=[];seen=set()
  while queue:
   x,age,path,clks=queue.popleft()
   if x in seen:continue
   seen.add(x)
   for ep in endpoints[x]:found.append(dict(**ep,group_Q_to_D2D_ordinary_register_stage_sum=age,nominal_registered_stage_sum_with_E0_E6_prefix=(6+age if age is not None else None),absolute_edge_age=None,native_phase_qualified=False,path=path,clocks=clks))
   for y,e,label,clock in arcs[x]:queue.append((y,age+e if age is not None and e is not None else None,path+[dict(instance=label,edges=e,from_net=x,to_net=y)],clks+[clock]))
  records.append(dict(group=name,master=g['master'],starting_bit=17,paths=found,complete_to_D2D_input=bool(found),deadends=[x for x in seen if not arcs[x] and not endpoints[x]]))
 assert all(r['complete_to_D2D_input'] for r in records),[r['group'] for r in records if not r['paths']]
 bounds=[p['nominal_registered_stage_sum_with_E0_E6_prefix'] for r in records for p in r['paths'] if p['nominal_registered_stage_sum_with_E0_E6_prefix'] is not None]
 out=dict(status='SOURCE_SUFFIX_TO_D2D_KV_FLUSH_ONLY',selected_die_sha256=SHA,groups=32,pc_producer_objects=128,records=records,nominal_ordinary_stage_sum_min=min(bounds),nominal_ordinary_stage_sum_max=max(bounds),whole_plane_E0_to_D2D_max=None,unknown_landing_phase_groups=[r['group'] for r in records if any(p['nominal_registered_stage_sum_with_E0_E6_prefix'] is None for p in r['paths'])],STATUS_cutoff_and_retirement_bound=None,reason='All reported numeric values are nominal registered stage sums, not absolute cross-region edge ages. D2D compiled STATUS phase and actual host veto/cause union remain separately open; source edge sums do not prove regional clock/landing phase or first-use resets')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='records'}))
if __name__=='__main__':main()
