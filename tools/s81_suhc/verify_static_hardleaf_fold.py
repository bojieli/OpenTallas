#!/usr/bin/env python3
"""Fail-closed structural identity proof for a static SU reparenting.
All native/state/comb data connections are compared, not sampled. Clocks normalize
to their declared common source epoch solely for functional identity. This does
not prove physical skew, phase, per-pin timing, macro closure or full-token work.
"""
import argparse,copy,hashlib,json,collections
from pathlib import Path

def normalize(c,roots):
 c=copy.deepcopy(c)
 for r in roots:
  if r['cell'] in ('native','state'):c['connections'][r['native_port']][r['bit']]=r['source_bit']
 return c

def sig(c):return dict(type=c['type'],parameters=c.get('parameters',{}),connections=c['connections'])
def verify(original,design,manifest):
 old=original['modules']['dsfd_sp_su_static'];new=design['modules']['dsfd_sp_su_static_hardleaf_candidate'];seq=set();native=set();delays=collections.defaultdict(list);comb_matches=0
 assert {k:v for k,v in new['ports'].items() if k!='ck_owner'}=={k:v for k,v in old['ports'].items() if k!='sk'}
 assert len(new['cells'])==len(manifest['owners']) and manifest['parent_own_cells']==0
 for index,o in enumerate(manifest['owners']):
  m=design['modules'][o['module']];body=m['cells'];top=new['cells']['owner'+str(index)]
  for port,row in m['ports'].items():
   if port in ('i','o'):assert top['connections'][port]==row['bits']
  for name,c in body.items():
   if name not in ('native','state'):
    assert name in old['cells'] and sig(c)==sig(old['cells'][name]);comb_matches+=1
  kind=o['kind'];orig_name=o.get('source_cell')
  if kind=='native_core' or kind=='zero_delay_native':
   c=normalize(body['native'],o['roots']);orig=old['cells'][orig_name]
   if c['type']=='ot_s81_su_rxh_clocked_candidate':
    assert len(c['connections']['ck_leaf'])==38 and len(set(c['connections']['ck_leaf']))==1
    assert len(c['connections']['rs_leaf'])==38 and len(set(c['connections']['rs_leaf']))==1
    c['connections']['clk']=[c['connections'].pop('ck_leaf')[0]];c['connections']['rst_in']=[c['connections'].pop('rs_leaf')[0]];c['type']='ot_s81_su_rxh'
   assert orig_name not in native and sig(c)==sig(orig),(orig_name,kind);native.add(orig_name)
  elif kind=='glue_state':
   c=normalize(body['state'],o['roots']);assert orig_name not in seq and sig(c)==sig(old['cells'][orig_name]);seq.add(orig_name)
  elif kind=='delay_stage':delays[orig_name].append(normalize(body['native'],o['roots']))
  else:assert kind=='boundary_comb'
 for name,stages in delays.items():
  orig=old['cells'][name];depth=int(orig['parameters'].get('D','1'),2);assert len(stages)==depth
  assert stages[0]['connections']['d']==orig['connections']['d'] and stages[-1]['connections']['q']==orig['connections']['q']
  for i,s in enumerate(stages):
   assert s['type']==orig['type'] and int(s['parameters']['D'],2)==1
   assert {k:v for k,v in s['parameters'].items() if k!='D'}=={k:v for k,v in orig['parameters'].items() if k!='D'}
   for p in ['clk','rst_n']:assert s['connections'][p]==orig['connections'][p]
   if i:assert s['connections']['d']==stages[i-1]['connections']['q']
 assert seq=={n for n,c in old['cells'].items() if c['type'] in ('$dff','$adff')}
 assert native|set(delays)=={n for n,c in old['cells'].items() if not c['type'].startswith('$')}
 assert manifest['added_logical_state_bits']==0 and manifest['added_normal_edges']==0
 return dict(status='PASS',proof='all native/state/comb data connections + exact fixed delay stage chain identity; functional common epoch only',native_owners=len(native),delay_chains=len(delays),delay_stage_owners=sum(map(len,delays.values())),state_owners=len(seq),state_bits=sum(len(old['cells'][n]['connections']['Q']) for n in seq),comb_copies_checked=comb_matches,clock_entries=manifest['clock_entries'],scope='structural composition identity, not numerical fullshape/native physical/fulltoken qualification')

def main():
 p=argparse.ArgumentParser();p.add_argument('--census',required=True);p.add_argument('--design',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);p.add_argument('--negative-controls',action='store_true');a=p.parse_args();paths={k:Path(getattr(a,k)) for k in ['census','design','manifest']};data={k:p.read_bytes() for k,p in paths.items()};original=json.loads(data['census']);design=json.loads(data['design']);manifest=json.loads(data['manifest']);r=verify(original,design,manifest);r['negative_controls']=[]
 if a.negative_controls:
  for kind,port in [('glue_state','D'),('native_core',None),('delay_stage','d')]:
   owner=next(o for o in manifest['owners'] if o['kind']==kind);cell=design['modules'][owner['module']]['cells']['state' if kind=='glue_state' else 'native']
   if port is None:port=next(p for p,v in cell['connections'].items() if cell['port_directions'][p]=='input' and p not in ('clk','ck','rst_in','rst_n','ck_leaf','rs_leaf'))
   saved=cell['connections'][port][0];cell['connections'][port][0]='1' if saved!='1' else '0';caught=False
   try:verify(original,design,manifest)
   except AssertionError:caught=True
   finally:cell['connections'][port][0]=saved
   assert caught,('unobserved graph mutant',kind,port);r['negative_controls'].append(dict(kind=kind,port=port,status='REJECTED'))
 r['input_sha256']={k:hashlib.sha256(v).hexdigest() for k,v in data.items()};Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
