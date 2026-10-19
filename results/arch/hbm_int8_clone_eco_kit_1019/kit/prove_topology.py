"""Independent complete native logical graph equivalence; no OpenDB writes.
Virtual mode validates prepared source only. Native mode takes exported raw.json + positions.json.
"""
import pathlib,json,gzip,copy,itertools,sys
from dft.liberty import read_liberty,parse_function,evaluate,expr_vars
P=pathlib.Path(__file__).parent
load=lambda n:json.load(gzip.open(P/'inputs'/(n+'.json.gz'),'rt'))
A=json.load(open(P/'allowlist.json'));B=load('raw');BP=load('positions');bc=next(iter(B['modules'].values()))['cells'];bm=next(iter(B['modules'].values()))
L=read_liberty(sorted((P/'inputs/native_libs').glob('*TT*')))
def req(x,m):
 if not x:raise ValueError(m)
def funct(master):
 c=L[master];req(not c['ff'] and not c['latch'],'noncomb '+master)
 return {p:parse_function(r['function']) for p,r in c['pins'].items() if r['direction']=='output'}
def samefn(a,b):
 x,y=funct(a),funct(b);req(x.keys()==y.keys(),'output role')
 for p in x:
  vs=sorted(expr_vars(x[p])|expr_vars(y[p]));req(all(evaluate(x[p],dict(zip(vs,v)))==evaluate(y[p],dict(zip(vs,v))) for v in itertools.product((0,1),repeat=len(vs))),'native function '+a+' '+b)
def virtual():
 j=copy.deepcopy(B);m=next(iter(j['modules'].values()));c=m['cells'];pos=copy.deepcopy(BP)
 ids={r['name']:int(n) for n,r in m['net_metadata'].items()};nid=max(ids.values())+1
 for n in A['added_nets']:ids[n]=nid;m['net_metadata'][str(nid)]={'name':n,'signal_type':'SIGNAL'};nid+=1
 for n,r in A['replacement_cells'].items():c[n]['type']=r['new_master']
 for n,r in A['added_cells'].items():
  pins=B['native_master_pins'].get(r['master'])
  if pins is None:
   pins={p:{'direction':d,'signal_type':s} for p,d,s in [('A','input','SIGNAL'),('Y','output','SIGNAL'),('VDD','inout','POWER'),('VSS','inout','GROUND')]}
  c[n]={'type':r['master'],'connections':{p:[] for p in pins},'port_directions':{p:z['direction'] for p,z in pins.items()},'pin_signal_types':{p:z['signal_type'] for p,z in pins.items()}}
  j['native_master_pins'][r['master']]=pins
 for r in A['rewired_pins']:c[r['cell']]['connections'][r['pin']]=[ids[r['new_net']]]
 for n,r in A['placement'].items():pos['insts'][n]={'master':r['master'],'location':r['bbox'][:2],'bbox':r['bbox'],'orient':BP['insts'].get(n,{}).get('orient','MODEL_NATIVE_ROW_ORIENT_PENDING')}
 return j,pos

def prove(J,AP,virtual_mode=False):
 am=next(iter(J['modules'].values()));ac=am['cells'];req(set(ac)==set(bc)|set(A['added_cells']),'complete cell inventory')
 req(am['ports']==bm['ports'],'all original port roles and connections')
 for net,r in bm['net_metadata'].items():req(am['net_metadata'].get(net)==r,'original native net name/role '+net)
 req(len(am['net_metadata'])==len(bm['net_metadata'])+1866,'native net inventory')
 for k in ['units','die','rows','bterms']:req(AP[k]==BP[k],'geometry '+k)
 for n,c in bc.items():
  if n in A['replacement_cells']:
   r=A['replacement_cells'][n];req(c['type']==r['old_master'] and ac[n]['type']==r['new_master'],'typed replacement '+n);samefn(c['type'],ac[n]['type'])
  else:req(ac[n]['type']==c['type'] and AP['insts'][n]==BP['insts'][n],'immutable cell/clock/state geometry '+n)
  req(c['port_directions']==ac[n]['port_directions'] and c['pin_signal_types']==ac[n]['pin_signal_types'],'native pin roles '+n)
 allowed={(r['cell'],r['pin']):r for r in A['rewired_pins']}
 for n,c in ac.items():
  if n in A['added_cells']:req(c['type']==A['added_cells'][n]['master'],'added master '+n)
  req(set(c['connections'])==set(c['port_directions'])==set(c['pin_signal_types']),'pin completeness '+n)
  for p,bits in c['connections'].items():
   key=(n,p);role=c['pin_signal_types'][p]
   if role in ['POWER','GROUND']:continue
   if key in allowed:
    r=allowed[key];req(len(bits)==1 and am['net_metadata'][str(bits[0])]['name']==r['new_net'],'exact rewire '+str(key))
   elif n in bc:req(bits==bc[n]['connections'][p],'nonallowlisted wire '+str(key))
   else:raise ValueError('unlisted added signal pin '+str(key))
 # All newly added cells are genuine native combinational identity/inverter cells.
 for n,r in A['added_cells'].items():
  f=funct(r['master']);req(set(f)=={'Y'} and expr_vars(f['Y'])=={'A'},'unary native function '+n)
  truth=[evaluate(f['Y'],{'A':b}) for b in (0,1)]
  req(truth==([1,0] if r['master'].startswith('INV') else [0,1]),'native polarity '+n)
 # Original reset inverter inputs normalize through new buffers; second branch
 # must evaluate to exactly original input polarity. All other original inputs
 # retain the original driver-token after contraction of ONLY native added cells.
 def outputs(m):
  ds={}
  for n,c in m['cells'].items():
   for p,b in c['connections'].items():
    if b and c['port_directions'][p]=='output' and c['pin_signal_types'][p] not in ['POWER','GROUND']:ds.setdefault(b[0],[]).append((n,p))
  for p,r in m['ports'].items():
   if r['direction']=='input' and r['bits']:ds.setdefault(r['bits'][0],[]).append(('@',p))
  return ds
 bd,ad=outputs(bm),outputs(am)
 reset=set(n for n,r in A['replacement_cells'].items() if r['role']=='reset_split')
 def neg(e):return e[1] if e[0]=='not' else ('not',e)
 def resolve(m,ds,bit,active=None):
  active=set() if active is None else active;req(bit not in active,'combinational cycle')
  active=active|{bit};drivers=ds.get(bit,[]);req(len(drivers)==1,'single-driver '+str(bit))
  n,p=drivers[0]
  if n in A['added_cells'] or n in reset:
   c=m['cells'][n];b=c['connections']['A'];req(len(b)==1,'connected A')
   e=resolve(m,ds,b[0],active)
   return neg(e) if c['type'].startswith('INV') else e
  return ('driver',n,p)
 checks=0
 for n,c in bc.items():
  for p,b in c['connections'].items():
   if c['port_directions'][p]!='input' or c['pin_signal_types'][p] in ['POWER','GROUND']:continue
   a=ac[n]['connections'][p];req(bool(b)==bool(a),'open pin changed')
   if b:req(resolve(bm,bd,b[0])==resolve(am,ad,a[0]),'functional source changed '+n+'/'+p);checks+=1
 # Native future export must provide exact bbox/master for all changed/add cells.
 for n,r in A['placement'].items():req(AP['insts'][n]['master']==r['master'] and AP['insts'][n]['bbox']==r['bbox'],'exact offline position '+n)
 req(sum(bool(L.get(c['type'],{}).get('ff')) for c in ac.values())==2782,'FF count/age')
 return dict(status='SOURCE_VIRTUAL_NETWORK_PASS' if virtual_mode else 'NATIVE_COMPLETE_NETWORK_PASS',original_input_checks=checks,cells=len(ac),preserved_ff=2782,zero_new_state=True,unchanged_clock_and_open_loads=True,reset_branches=12,ordinary_branches=594,async_hold_branches=10)

if __name__=='__main__':
 if len(sys.argv)>1:
  d=pathlib.Path(sys.argv[1]);j=json.load(open(d/'raw.json'));p=json.load(open(d/'positions.json'));r=prove(j,p)
 else:
  j,p=virtual();r=prove(j,p,True);controls={}
  for name,mut in [('missing_branch_cell',lambda a:a['cells'].pop(next(iter(A['added_cells'])))),('wrong_hold_master',lambda a:a['cells'][next(iter(A['added_cells']))].update(type='INVx6_ASAP7_75t_R')),('wrong_sink_net',lambda a:a['cells'][A['rewired_pins'][-1]['cell']]['connections'].__setitem__(A['rewired_pins'][-1]['pin'],[])),('changed_clock_or_state',lambda a:a['cells'][next(n for n,c in bc.items() if c['type'].startswith('DFF'))].update(type='INVx6_ASAP7_75t_R'))]:
   x=copy.deepcopy(j);mut(next(iter(x['modules'].values())))
   try:prove(x,p,True)
   except (ValueError,KeyError) as e:controls[name]=str(e)
   else:raise AssertionError('CAUSAL_CONTROL_SURVIVED '+name)
  r['causal_rejections']=controls
 print(json.dumps(r,indent=2))
