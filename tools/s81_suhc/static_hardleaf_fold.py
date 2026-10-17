#!/usr/bin/env python3
"""Partition elaborated static SU graph into actual native-core and glue leaves.

Input is a Yosys source-derived interface census; blackboxes are used ONLY to
identify native leaf boundaries. Emitted hardware instantiates the real original
RTL modules. No blackbox is a functional qualification model. Combinational
cones are cloned into their receiving owner; original state and edges survive.
"""
import argparse,copy,collections,hashlib,json
from pathlib import Path

def integer(p,k,default=0):return int(p.get(k,format(default,'b')),2)
def build(d,scalar_owner_internals=False):
 old=d['modules']['dsfd_sp_su_static'];cells=old['cells'];source_clk=old['ports']['sk']['bits'][0]
 seq={n:c for n,c in cells.items() if c['type'] in ('$dff','$adff')}
 native={n:c for n,c in cells.items() if not c['type'].startswith('$')}
 comb={n:c for n,c in cells.items() if n not in seq and n not in native}
 drivers={}
 for n,c in comb.items():
  for p,bits in c['connections'].items():
   if c['port_directions'][p]=='output':
    for b in bits:
     if isinstance(b,int):
      if b in drivers and drivers[b]!=n:raise ValueError(('multiple combinational drivers',b))
      drivers[b]=n
 maxbit=max([b for c in cells.values() for v in c['connections'].values() for b in v if isinstance(b,int)]+[0])+1
 top=dict(attributes={'top':'1'},ports=copy.deepcopy(old['ports']),cells={},netnames={});top['ports'].pop('sk');modules={};owners=[];clocks=[];core_connections={};comb_uses=collections.Counter()
 def cone(inputs):
  todo=list(inputs);seen=set()
  while todo:
   bit=todo.pop();n=drivers.get(bit)
   if n is None or n in seen:continue
   seen.add(n)
   for p,v in comb[n]['connections'].items():
    if comb[n]['port_directions'][p]=='input':todo.extend(v)
  return seen
 def add_owner(name,owned,outputs,kind,old_name=None):
  nonlocal maxbit
  cn=cone([b for c in owned.values() for p,v in c['connections'].items() if c['port_directions'][p]=='input' for b in v]+list(outputs))
  body={n:copy.deepcopy(comb[n]) for n in sorted(cn)};body.update(copy.deepcopy(owned));comb_uses.update(cn)
  used=set();driven=set()
  for c in body.values():
   for p,v in c['connections'].items():
    used.update(b for b in v if isinstance(b,int))
    if c['port_directions'][p]=='output':driven.update(b for b in v if isinstance(b,int))
  inputs=sorted(used-driven);outputbits=sorted(set(b for b in outputs if isinstance(b,int)))
  assert not(set(inputs)&set(outputbits))
  ports={};conn={};root_entries=[]
  # Separate each actual sequential/core clock port. Top clock aliases are
  # removed, retaining explicit source root identity in the manifest.
  clock_conns=[]
  for n,c in body.items():
   pnames=['CLK'] if c['type'] in ('$dff','$adff') else [p for p in c['connections'] if p in ('clk','ck','ck_half','ck_reduce','ck_leaf')]
   for p in pnames:
    for j,b in enumerate(c['connections'][p]):
     if b!=source_clk:continue
     new=maxbit;maxbit+=1;c['connections'][p][j]=new
     key='clock'+str(len(root_entries));ports[key]={'direction':'input','bits':[new]};external=maxbit;maxbit+=1;conn[key]=[external];clocks.append(external);root_entries.append(dict(port=key,cell=n,native_port=p,bit=j,source_bit=b))
  # Source clock may also feed zero-delay combinational paths; keep a declared
  # source port when it survives outside actual clock sinks.
  inputs=sorted({b for c in body.values() for p,v in c['connections'].items() if c['port_directions'][p]=='input' for b in v if isinstance(b,int)}-{b for c in body.values() for p,v in c['connections'].items() if c['port_directions'][p]=='output' for b in v if isinstance(b,int)}-{b for q in ports.values() for b in q['bits']})
  for p,bits,direction in [('i',inputs,'input'),('o',outputbits,'output')]:
   if bits:ports[p]={'direction':direction,'bits':bits};conn[p]=bits
  mod='ot_s81_su_hard_owner_'+str(len(owners));modules[mod]={'attributes':{'keep_hierarchy':'1'},'ports':ports,'cells':body,'netnames':{}}
  top['cells']['owner'+str(len(owners))]={'hide_name':0,'type':mod,'parameters':{},'attributes':{'keep_hierarchy':'1'},'port_directions':{p:q['direction'] for p,q in ports.items()},'connections':conn}
  owners.append(dict(name=name,module=mod,kind=kind,source_cell=old_name,roots=root_entries,comb_cells=len(cn),native_cells=[dict(name=n,type=c['type'],params=c.get('parameters',{})) for n,c in owned.items()],state_bits=sum(len(c['connections'].get('Q',[])) for c in owned.values() if c['type'] in ('$dff','$adff')),inputs=len(inputs),outputs=len(outputbits)))
 for n,c in sorted(native.items()):
  c=copy.deepcopy(c)
  if c['type']=='ot_s81_su_rxh':
   c['type']='ot_s81_su_rxh_clocked_candidate'
   clock=c['connections'].pop('clk');reset=c['connections'].pop('rst_in')
   c['port_directions'].pop('clk');c['port_directions'].pop('rst_in')
   c['connections']['ck_leaf']=clock*38;c['connections']['rs_leaf']=reset*38
   c['port_directions']['ck_leaf']='input';c['port_directions']['rs_leaf']='input'
  if c['type']=='ot_hdc_delay':
   w=integer(c['parameters'],'W',32);depth=integer(c['parameters'],'D',1);reset=integer(c['parameters'],'RESET',0)
   if depth==0:
    # Zero-delay native wires are already aliases after hierarchy; preserve
    # any remaining explicit wire cell as actual RTL without a root.
    add_owner(n,{n:c},c['connections']['q'],'zero_delay_native',n);continue
   inputs=c['connections']['d']
   for s in range(depth):
    outputs=c['connections']['q'] if s==depth-1 else list(range(maxbit,maxbit+w));maxbit+=w if s<depth-1 else 0
    stage=copy.deepcopy(c);stage['parameters']['D']=format(1,'032b');stage['connections']['d']=inputs;stage['connections']['q']=outputs
    add_owner(n+'/stage'+str(s),{'native':stage},outputs,'delay_stage',n);inputs=outputs
  else:
   outputbits=[b for p,v in c['connections'].items() if c['port_directions'][p]=='output' for b in v]
   add_owner(n,{'native':c},outputbits,'native_core',n)
 for n,c in sorted(seq.items()):add_owner(n,{'state':c},c['connections']['Q'],'glue_state',n)
 # Output-only combinational functions have explicit owners, never hidden in
 # a nominally wires-only parent. Their boundary timing is an OPEN gate.
 aliased_outputs=set(b for o in top['cells'].values() for p,v in o['connections'].items() if o['port_directions'][p]=='output' for b in v)
 need=[b for p in old['ports'].values() if p['direction']=='output' for b in p['bits'] if isinstance(b,int) and b not in aliased_outputs]
 # Group every output cone into one explicit combinational owner.
 if need:add_owner('boundary_combinational',{},need,'boundary_comb')
 top['ports']['ck_owner']={'direction':'input','bits':clocks}
 # All native and state sink connections are preserved except clocks and
 # decomposition of an identical fixed delay into its original stages.
 assert sum(o['state_bits'] for o in owners)==sum(len(c['connections']['Q']) for c in seq.values())
 assert all(o['state_bits']<=15000 for o in owners)
 modules['dsfd_sp_su_static_hardleaf_candidate']=top
 # Give the backend actual packed buses, avoiding millions of temporary scalar
 # declarations without changing a single cell/port/connection.
 for module_name,module in modules.items():
  portbits={b for p in module['ports'].values() for b in p['bits'] if isinstance(b,int)}
  module['netnames']={n:dict(hide_name=0,bits=p['bits'],attributes={}) for n,p in module['ports'].items()}
  bits=sorted({b for c in module['cells'].values() for v in c['connections'].values() for b in v if isinstance(b,int)}-portbits)
  if scalar_owner_internals and module_name!='dsfd_sp_su_static_hardleaf_candidate':
   for bit in bits:module['netnames']['internal_'+str(bit)]=dict(hide_name=0,bits=[bit],attributes={})
  elif bits:module['netnames']['internal_bus']=dict(hide_name=0,bits=bits,attributes={})
 report=dict(schema='opentallas.s81.static-hardleaf-fold.v1',qualified=False,owners=owners,clock_entries=len(clocks),owner_count=len(owners),original_native_cells=len(native),original_parent_state_bits=sum(o['state_bits'] for o in owners),parent_own_cells=0,parent_wires_only=True,comb_original_cells=len(comb),comb_owned_copies=sum(comb_uses.values()),comb_unconsumed_cells=len(set(comb)-set(comb_uses)),max_glue_owner_state_bits=max(o['state_bits'] for o in owners),added_logical_state_bits=0,added_normal_edges=0,scope='Source-derived elaboration graph and actual RTL reparenting. Arithmetic/native source modules remain real RTL at functional build. Exact proof/realviews/cuts/clock insertion/calendar/native integration required.',open=['RX exposes38actual roots; IK three and MOE six existing roots retained. Composite internal physical leaf/memory ownership remains source-bound integration work.','Native historical view reuse requires exact current port/parameter/body match; new norm_v/norm_y outputs differ from historical KVE wrappers.','Combinational cones copied into receiving owners change physical area/pins; measure native area and gate actual views.','Every actual owner boundary needs native per-pin audit; no extra boundary combinational owner is present when all outputs already come from native/state leaves.','Every clock root has source provenance; no timing insertion or physical clock delivery is inferred.'])
 return {'creator':'source-bound static SU native hardleaf fold','modules':modules},report

def main():
 p=argparse.ArgumentParser();p.add_argument('--census',required=True);p.add_argument('--out',required=True);p.add_argument('--scalar-owner-internals',action='store_true');a=p.parse_args();raw=Path(a.census).read_bytes();d=json.loads(raw);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);design,report=build(d,a.scalar_owner_internals);report['census_sha256']=hashlib.sha256(raw).hexdigest();(out/'hardleaf.json').write_text(json.dumps(design,separators=(',',':'))+'\n');(out/'manifest.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='owners'}))
if __name__=='__main__':main()
