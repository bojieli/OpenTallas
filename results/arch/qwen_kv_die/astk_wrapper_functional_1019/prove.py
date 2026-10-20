#!/usr/bin/env python3
"""Exact unary-graph isomorphism proof; refuses any unrecognized primitive/edge.
No state values assumed. Native IQN is complement of logical RTL state.
"""
import json,re,gzip,hashlib,pathlib,collections,subprocess
P=pathlib.Path('inputs'); OUT=pathlib.Path('out');OUT.mkdir(exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def block(s,start):
 a=s.index('{',start);depth=1;i=a+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a+1:i-1]
def groups(s,kind):
 return {m.group(1).strip():block(s,m.start()) for m in re.finditer(r'\b'+kind+r'\s*\(([^()]*)\)\s*\{',s)}
libs={}
libnames=['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz']
for p in [P/n for n in libnames]:
 s=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
 libs.update(groups(s,'cell'))
raw=(P/'6_final.v').read_text(); assert 'assign' not in raw, 'Unexpected assigns: extend audited parser first'
inst=[]
for m in re.finditer(r'^\s*(\w+_ASAP7_75t_R)\s+(\\\S+|\w+)\s*\((.*?)\);',raw,re.M|re.S):
 typ,name,ports=m.groups();con=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)',ports));inst.append((typ,name,con))
assert len(inst)==sum(1 for x in raw.splitlines() if '_ASAP7_75t_R ' in x)
assert len(inst)==len(re.findall(r'^\s*(?!module\b)(\w+)\s+(\\\S+|\w+)\s*\(',raw,re.M)), 'unrecognized nonnative instance'
# Symbols are (atom, inversion parity). Logical state is complement of native IQN.
def inv(x):return (x[0],x[1]^1)
def atom(x):return(str(x),0)
def graph_check(label,drivers,ffs,inputs,outputs):
 visiting=set()
 def get(net):
  if net in inputs:return inputs[net]
  assert net in drivers,(label,'undriven',net)
  val=drivers[net]
  if val[0]=='atom':return val[1]
  assert net not in visiting,(label,'combinational cycle',net)
  visiting.add(net);x=get(val[1]);visiting.remove(net)
  return inv(x) if val[0]=='inv' else x
 data=[]
 for i,n in enumerate(outputs):
  a=get(n);assert a[1]==0 and a[0].startswith('q:'),(label,'output polarity',i,a)
  key=a[0][2:];assert key in ffs;data.append(key)
 assert len(set(data))==296
 reset=None
 for i,k in enumerate(data):
  ff=ffs[k];assert get(ff['D'])==atom('a'+str(i)),(label,'data',i,get(ff['D']))
  r=get(ff['R']);reset=r if reset is None else reset;assert reset==r
 assert reset[1]==0 and reset[0].startswith('q:')
 rkey=reset[0][2:];s1=get(ffs[rkey]['D']);assert s1[1]==0 and s1[0].startswith('q:')
 s1key=s1[0][2:];s0=get(ffs[s1key]['D']);assert s0[1]==0 and s0[0].startswith('q:')
 s0key=s0[0][2:];assert get(ffs[s0key]['D'])==atom('1')
 assert set(ffs)==set(data+[rkey,s1key,s0key]),(label,'unmatched states')
 for k,f in ffs.items():
  assert get(f['C'])==atom('ck'),(label,'clock',k,get(f['C']))
  assert get(f['R'])==(atom('rst_n') if k in [rkey,s1key,s0key] else reset)
  if 'S' in f:assert get(f['S'])==atom('1'),(label,'async set not tied inactive')
 # Resolve every graph driver, even unobserved nodes. Every cell accounted.
 for n in drivers:get(n)
 return {'label':label,'outputs':296,'data_states':296,'reset_states':3,'total_states':299,'arbitrary_state_bijection':dict(zip(['data'+str(i) for i in range(296)]+['relay','sync1','sync0'],data+[rkey,s1key,s0key])),'all_drivers_resolved':len(drivers),'clock':'positive ck through pure combinational identity','reset':'async clear logical state to zero; reset states rst_n; data states relay','verdict':'PROVEN_TRANSITION_GRAPH_ISOMORPHISM'}
def add(d,n,v):assert n not in d,('multiple drivers',n);d[n]=v
native_drivers={};native_ffs={};used={};models=[]; dangling=[]
for typ,name,con in inst:
 assert typ in libs,('missing Liberty',typ)
 cell=libs[typ];pins=groups(cell,'pin');ffs=groups(cell,'ff')
 if typ=='DFFASRHQNx1_ASAP7_75t_R':
  assert set(con)=={'CLK','D','QN','RESETN','SETN'}
  assert len(ffs)==1 and 'IQN,IQNN' in ffs
  f=ffs['IQN,IQNN']
  for key,val in [('clear','!SETN'),('preset','!RESETN'),('clocked_on','CLK'),('next_state','!D')]:
   assert re.search(r'\b'+key+r'\s*:\s*"'+re.escape(val)+r'"',f),(key,val)
  assert re.search(r'function\s*:\s*"IQN"',pins['QN'])
  add(native_drivers,con['QN'],('atom',inv(atom('q:'+name))))
  native_ffs[name]={'D':con['D'],'R':con['RESETN'],'C':con['CLK'],'S':con['SETN']}
 else:
  outputs=[p for p,b in pins.items() if re.search(r'direction\s*:\s*output',b)]
  assert len(outputs)==1;output=outputs[0];f=re.search(r'function\s*:\s*"([^"]+)"',pins[output]).group(1)
  assert set(con)==set(pins) or (name.startswith('clkload') and set(con)=={'A'}),(typ,con.keys(),pins.keys())
  if output not in con:
   dangling.append({'cell':name,'type':typ,'input':con['A']}); con[output]='__unused_'+name
  if f=='1':add(native_drivers,con[output],('atom',atom('1')))
  elif f in ['A','!A']:add(native_drivers,con[output],('inv' if f=='!A' else 'buf',con['A']))
  else:raise AssertionError(('unrecognized primitive function',typ,f))
  if typ not in used:
   models.append('module '+typ+'('+','.join(con)+');\n'+''.join(('output' if p==output else 'input')+' '+p+';\n' for p in con)+'assign '+output+' = '+("1\'b1" if f=='1' else f)+';\nendmodule\n')
 used[typ]=used.get(typ,0)+1
inp={'ck':atom('ck'),'rst_n':atom('rst_n')};inp.update({'a['+str(i)+']':atom('a'+str(i)) for i in range(296)})
results=[graph_check('native_routed',native_drivers,native_ffs,inp,['b['+str(i)+']' for i in range(296)])]
# Actual RTL is elaborated independently for default and explicit MUT=0.
mutant_controls=[]
for mode in ['default','mut0','mut1']:
 cmd='read_verilog -sv inputs/ot_rst_relay.sv inputs/qkd_astk_phys.sv inputs/qkd_astk_rly_296_fl.sv; '
 if mode!='default':cmd+='chparam -set MUT '+('0' if mode=='mut0' else '1')+' qkd_astk_rly_296_fl; '
 cmd+='hierarchy -check -top qkd_astk_rly_296_fl; proc; flatten; opt_clean; write_json out/'+mode+'.json'
 with open(OUT/(mode+'.log'),'w') as log:subprocess.run(['yosys','-Q','-p',cmd],stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((OUT/(mode+'.json')).read_text())['modules']['qkd_astk_rly_296_fl'];drivers={};ffs={}
 inputs={'0':atom('0'),'1':atom('1')}
 for n,p in m['ports'].items():
  if p['direction']=='input':
   for i,b in enumerate(p['bits']):inputs[b]=atom(n+str(i) if n=='a' else n)
 for n,c in m['cells'].items():
  if c['type']=='$scopeinfo':
   assert not c['connections']; continue # elaboration source-location metadata, no logic
  assert c['type']=='$adff',(mode,'unaccounted cell',n,c['type'])
  assert int(c['parameters']['CLK_POLARITY'],2)==1 and int(c['parameters']['ARST_POLARITY'],2)==0
  assert int(c['parameters']['ARST_VALUE'],2)==0
  p=c['connections'];assert set(p)=={'CLK','ARST','D','Q'}
  for i,(d,q) in enumerate(zip(p['D'],p['Q'])):
   key=n+':'+str(i);add(drivers,q,('atom',atom('q:'+key)));ffs[key]={'D':d,'C':p['CLK'][0],'R':p['ARST'][0]}
 if mode=='mut1':
  try: graph_check('rtl_mut1',drivers,ffs,inputs,m['ports']['b']['bits'])
  except AssertionError as e: mutant_controls.append({'actual_source_MUT':1,'verdict':'REJECTED','detail':str(e),'states':len(ffs)})
  else: raise AssertionError('actual MUT1 incorrectly accepted')
 else: results.append(graph_check('rtl_'+mode,drivers,ffs,inputs,m['ports']['b']['bits']))
# Exact native-library-derived zero-delay models only for causal simulation.
models.append('module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);\nalways @(posedge CLK or negedge RESETN or negedge SETN) if (!SETN) QN<=0; else if (!RESETN) QN<=1; else QN<=!D;\nendmodule\n')
(OUT/'native_models.v').write_text(''.join(models))
# The simultaneous clear/preset undefined priority is unreachable: all299 SETN proven1.
summary={'scope':'FUNCTIONAL ONLY: ideal event / zero-delay Boolean semantics, fault-free tied power; no electrical/metastability or timing qualification','method':'Complete output/state-transition graph isomorphism, bijection over all299 arbitrary states; no initial-value assumption, no reset preamble assumption, no async2sync','native_cells':used,'actual_source_mutant_controls':mutant_controls,'disconnected_clock_load_outputs':dangling,'proofs':results,'input_sha256':{p.name:digest(p) for p in P.iterdir() if p.is_file()},'blackboxes':0,'unaccounted_cells':0,'state_or_output_waivers':0,'physical_status':'HOLD: fanout296, PG, contact, current native reset safety not discharged'}
(OUT/'proof.json').write_text(json.dumps(summary,indent=2)+'\n');print('PASS exact graph identity: native vs default vs explicit MUT0; all296 outputs +3 reset states; no initial state assumed')
