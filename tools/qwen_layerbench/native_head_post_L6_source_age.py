#!/usr/bin/env python3
"""Read-only bit-level emitted-register path inventory; no phase qualification."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--controls-only',action='store_true');a=p.parse_args()
kept=Path('/home/ubuntu/OpenTallas/rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv')
assert hashlib.sha256(kept.read_bytes()).hexdigest()=='83e3cfce9b34ca10eac629ea2e093f4c2571c2c5a71b2e9c49ac944c0e2c1dfc'
kt=kept.read_text()
for axis in ['s','n']:
 assert 'assign rs_'+axis+'_r0 = {rs_'+axis+'[577:514], rs_'+axis+'[63:0]};' in kt
 assert 'assign rs_'+axis+'_c  = {rs_'+axis+'[1027:1026], rs_'+axis+'[513:512]};' in kt
b=a.source;top=json.loads((b/'L6_path_top_instances.json').read_text());ca=json.loads((b/'L6_path_CA_sidecar.json').read_text());texts={};edges={};snips={};widths={};directions={};refs={}
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decl(s):
 w={};di={}
 for m in re.finditer(r'\b(input|output|wire|reg)\s+(?:(?:wire|reg)\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)',s):
  w[m[4]]=abs(int(m[2])-int(m[3]))+1 if m[2]else 1
  if m[1]in ['input','output']:di[m[4]]=m[1]
 return w,di
def bits(expr,w):
 e=expr.strip()
 if e.startswith('{') and e.endswith('}'):
  # source emitted concatenations here are flat slices, in MSB-first order.
  out=[]
  for x in reversed(e[1:-1].split(',')):out+=bits(x,w)
  return out
 m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',e)
 if not m:raise ValueError(e)
 name,hi,lo=m.groups()
 if hi is None:return [(name,i)for i in range(w[name])]
 if lo is None:return [(name,int(hi))]
 assert int(hi)>=int(lo);return [(name,i)for i in range(int(lo),int(hi)+1)]
def add(part,q,d,n,record,w):
 try:qb,db=bits(q,w),bits(d,w)
 except(ValueError,KeyError):return
 assert len(qb)==len(db),(part,q,d,len(qb),len(db))
 for qo,dd in zip(qb,db):
  key=(part,*qo);val=((part,*dd),n,record)
  assert key not in edges or edges[key]==val,('MULTIDRIVE',key)
  edges[key]=val
for part,info in top.items():
 f=b/'rtl'/(info['module']+'.sv');s=f.read_text();texts[part]=s;refs[str(f)]=sh(f);w,di=decl(s);widths[part]=w;directions[part]=di
 for m in re.finditer(r'^\s*(ot_dp_st|ot_dp_dly|ot_dp_clk_landing_cas)\s*(?:#\(([^\n]*)\))?\s+(\w+)\s*\((.*?)\);',s,re.M|re.S):
  typ,params,name,ports=m.groups();pp=dict(re.findall(r'\.(\w+)\(([^()]*)\)',ports));line=s.count('\n',0,m.start())+1
  rec={'part':part,'module':info['module'],'instance':name,'primitive':typ,'line':line,'clock':pp.get('clk'),'source':m[0].strip()}
  if typ=='ot_dp_clk_landing_cas':
   hit=[x for x in ca if x['dst']==part and x['dst_bus']==pp.get('d')]
   if not hit:continue
   assert len(hit)==1,(part,name)
   rec['sidecar']=hit[0];rec['strap_binding']=info['ports'][pp['strap_k']];rec['source_clock']=info['ports'].get(pp['fclk']);rec['source_start']=info['ports'].get(pp['t_rst_n']);rec['receiver_clock']=info['ports'].get(pp['clk'],pp['clk']);rec['receiver_start']=pp['rst_n'];rec['count_rule']='reader count m consumes sender word m-K modulo64; q registered; boundary+pad counted separately; ledger addition is sidecar added_cycles only, never K or RDREG again'
   n=hit[0]['added_cycles']
  else:n=1 if typ=='ot_dp_st'else int(re.search(r'\.D\((\d+)\)',params)[1])
  add(part,pp['q'],pp['d'],n,rec,w)
 for m in re.finditer(r'\bassign\s+([^;=]+)=\s*([^;]+);',s):
  add(part,m[1],m[2],0,{'part':part,'kind':'literal_assign','line':s.count('\n',0,m.start())+1},w)
 # These selected frontend modules are exact combinational lane projections.
 for m in re.finditer(r'\bqfd_dv_s8_(frs|fn)\s+u_u_\w+\s*\((.*?)\);',s,re.S):
  axis='s'if m[1]=='frs'else'n';pp=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[2]));ib=bits(pp['rs_'+axis],w);assert len(ib)==1028
  for r in range(8):
   qb=bits(pp['rs_'+axis+'_r'+str(r)],w);db=ib[64*r:64*(r+1)]+ib[514+64*r:514+64*(r+1)];assert len(qb)==len(db)==128
   for qo,dd in zip(qb,db):edges[(part,*qo)]=((part,*dd),0,{'part':part,'kind':'native_frontend_literal_projection','region':r})
  qb=bits(pp['rs_'+axis+'_c'],w);db=ib[512:514]+ib[1026:1028]
  for qo,dd in zip(qb,db):edges[(part,*qo)]=((part,*dd),0,{'part':part,'kind':'native_frontend_literal_control'})
# Literal global wires connect wrapper output port bits to input port bits.
drivers={}
for part,info in top.items():
 for pin,net in info['ports'].items():
  if directions[part].get(pin)=='output'and re.fullmatch(r'\w+',net):
   for i in range(widths[part][pin]):drivers[(net,i)]=(part,pin,i)
for part,info in top.items():
 for pin,net in info['ports'].items():
  if directions[part].get(pin)=='input'and re.fullmatch(r'\w+',net):
   for i in range(widths[part][pin]):
    if (net,i)in drivers:edges[(part,pin,i)]=(drivers[(net,i)],0,{'kind':'literal_top_wire','wire':net})
def trace(start):
 n=start;path=[];seen=set();ordinary=0;ca_add=0
 while n in edges:
  assert n not in seen,('CYCLE',n);seen.add(n);nn,weight,rec=edges[n]
  if weight:
   if rec.get('primitive')=='ot_dp_clk_landing_cas':ca_add+=weight
   else:ordinary+=weight
   path.append(dict(from_bit=list(nn),to_bit=list(n),ledger_cycles=weight,evidence=rec))
  n=nn
 assert n[1]=='w_u_t_0_0_n_y',('NOT_NATIVE_CLUSTER_ROOT',start,n)
 return dict(root_bit=list(n),ordinary_register_edges=ordinary,sidecar_CA_added_cycles=ca_add,conditional_nominal_edges_to_physical_station_pin=ordinary+ca_add,path=list(reversed(path)))
refs[str(kept)]=sh(kept)
rows=[]
if a.controls_only:
 for sl in ['E2','E3','E4','E5']:
  for half in ['a','b']:
   part='sl_'+sl+'_st_'+half;s=texts[part]
   stations=list(re.finditer(r'\bqfd_dv_s8_station_tail1(?:_nb0)?\s*(?:#\([^\n]*\))?\s+u_u_r([0-7])\s*\((.*?)\);',s,re.S));assert len(stations)==4,(part,len(stations))
   for mm in stations:
    ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',mm[2]))
    for pin in ['rs_s_c_p','rs_n_c_p']:
     controlbits=bits(ports[pin],widths[part]);assert len(controlbits)==4
     for i,bit in enumerate(controlbits):
      rec=trace((part,*bit));assert rec['root_bit'][2]==512+i%2,(part,pin,i,rec['root_bit'])
      rec.update(slice=sl,station_region=int(mm[1]),station_port=pin,control_bit=i,semantic='valid'if i%2==0 else'fault',station_pin_clock=top[part]['ports']['clk'],native_PIN_IN=1)
      rows.append(rec)
for sl in ([]if a.controls_only else ['W5','W4','E2','E3']):
 part='sl_'+sl+'_st_a';s=texts[part];m=re.search(r'\bqfd_dv_s8_station_tail1(?:_nb0)?\s*(?:#\([^\n]*\))?\s+u_u_r0\s*\((.*?)\);',s,re.S);assert m,part
 ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[1]))
 for pin in ['rs_s_lo_p','rs_s_hi_p','rs_n_lo_p','rs_n_hi_p']:
  wordbits=bits(ports[pin],widths[part]);assert len(wordbits)==64
  bit=wordbits[0];rec=trace((part,*bit))
  for i,wb in enumerate(wordbits):
   check=trace((part,*wb));assert check['ordinary_register_edges']==rec['ordinary_register_edges']and check['sidecar_CA_added_cycles']==rec['sidecar_CA_added_cycles']
   assert check['root_bit']==[rec['root_bit'][0],rec['root_bit'][1],rec['root_bit'][2]+i],('PAYLOAD_ORDER',part,pin,i)
  rec['payload_bits_checked']=64
  rec.update(slice=sl,station_port=pin,station_pin_clock=top[part]['ports']['clk'],native_PIN_IN=1,conditional_nominal_edges_to_internal_pin_word=rec['conditional_nominal_edges_to_physical_station_pin']+1);rows.append(rec)
requirements=[]
for sl in ([]if a.controls_only else ['W5','W4','E2','E3']):
 for axis in ['s','n']:
  pair=[next(x for x in rows if x['slice']==sl and x['station_port']=='rs_'+axis+'_'+role+'_p')for role in ['lo','hi']]
  near,far=[x['conditional_nominal_edges_to_physical_station_pin']for x in pair]
  requirements.append(dict(slice=sl,axis=axis,near_age=near,far_age=far,far_minus_near_producer_publication_required=14-(far-near),equation='far_root_publication+far_route_age = near_root_publication+near_route_age+14; nativeSKEW14; no actualproducerdateasserted'))
for file in ['L6_path_top_instances.json','L6_path_CA_sidecar.json','bind_clock_landings.json','bus_groups.json','bind_latency.json']:refs[str(b/file)]=sh(b/file)
result=dict(required_root_publication_relations=requirements,status='SOURCE_AGE_LEDGER_CONDITIONAL_ON_FROZEN_COUNT_ORIGIN_PROVIDER_CONTRACT',rows=rows,scope='exact payloadbit0 namedregister paths to region0 physical station pins plus nativePIN1; not a physicalphase/CTS/STARTdate proof',count_semantics='CA K modulo64 is frame translation not elapsedcycles. Sidecar added_cycles counted once separately from explicit ordinary registers. No universal+3, no extra RDREG.',readset=refs)
a.out.write_text(json.dumps(result,indent=2)+'\n')
print('SOURCE_CONTROL_PATHS',len(rows))if a.controls_only else None
for x in ([]if a.controls_only else rows):print(x['slice'],x['station_port'],x['ordinary_register_edges'],x['sidecar_CA_added_cycles'],x['conditional_nominal_edges_to_physical_station_pin'])
