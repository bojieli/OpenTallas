from pathlib import Path
import json,re,copy,collections,subprocess,os,hashlib,sys
r=Path(sys.argv[1])
a=json.load(open(r/'native_cut_flat.json'));profile=json.load(open(r/'native_cut_profile.json'));inv=json.load(open(r/'inverse_inventory.json'))
top=profile['top'];m=a['modules'][top];original=copy.deepcopy(m);cells=m['cells'];nativecells=copy.deepcopy(cells)
# Clock sharing is allowed only where the ACTUAL current bound outer wires are identical.
clocks={};aliases={}
for name,i,expr,key in inv['clock_aliases_from_actual_bound']:
 b=m['ports'][name]['bits'][i]
 if key in clocks:aliases[b]=clocks[key]
 else:clocks[key]=b
canon=lambda b: aliases.get(b,b) if isinstance(b,int) else b
for c in cells.values():
 for p,bs in c['connections'].items():c['connections'][p]=[canon(b) for b in bs]
source=copy.deepcopy(cells)
allmembers={p for v in profile['members'].values() for p in v['paths']};assert allmembers<=set(cells),allmembers-set(cells)
outside=collections.defaultdict(set)
for nm,c in cells.items():
 for bs in c['connections'].values():
  for b in bs:
   if isinstance(b,int):outside[b].add(nm)
topnets={canon(b) for p in m['ports'].values() for b in p['bits'] if isinstance(b,int)}
expected={};records=[];models={}
for ci in inv['cores']:
 members=set(ci['members']);assert members==set(profile['members'][ci['inst']]['paths'])
 ports={};directions={};offsets={};covered=set()
 for pin,anchors in ci['ports'].items():
  pm=re.fullmatch(r'(.*)\[(\d+)\]',pin);assert pm,pin
  base,k=pm[1],int(pm[2]);vals=[];ds=[]
  for ar in anchors:
   c=cells[ar['member']];vals.append(c['connections'][ar['port']][ar['bit']]);ds.append(c['port_directions'][ar['port']])
  assert len(set(map(str,vals)))==1,(ci['inst'],pin,vals)
  assert len(set(ds))==1,(ci['inst'],pin,ds)
  directions[base]=ds[0];ports.setdefault(base,{})[k]=vals[0]
  if isinstance(vals[0],int):covered.add(vals[0])
 for base,bs in list(ports.items()):
  ix=sorted(bs);assert ix==list(range(ix[0],ix[-1]+1)),(ci['inst'],base,'pin hole',ix)
  offsets[base]=ix[0];ports[base]=[bs[k] for k in ix]
 boundary={b for name in members for bs in cells[name]['connections'].values() for b in bs if isinstance(b,int) and (outside[b]-members or b in topnets)}
 assert boundary<=covered,(ci['inst'],'uncovered native boundary',boundary-covered)
 # Preserve actual parameter values in the cut receipt; no specialization is inferred.
 actual=[{'path':name,'type':cells[name]['type'],'parameters':a['modules'][cells[name]['type']].get('parameter_default_values',{})} for name in sorted(members)]
 new={'type':ci['module'],'parameters':{},'attributes':{},'port_directions':directions,'connections':ports}
 cells[ci['inst']]=new;expected[ci['inst']]=copy.deepcopy(new)
 for name in members:del cells[name]
 if ci['module'] not in models:
  n=2; ps={};ns={}
  for p,bs in ports.items():
   ids=list(range(n,n+len(bs)));n+=len(bs)
   ps[p]={'direction':directions[p],'bits':ids,'offset':offsets[p]};ns[p]={'hide_name':0,'bits':ids,'offset':offsets[p],'attributes':{}}
  models[ci['module']]={'attributes':{'blackbox':'1'},'ports':ps,'cells':{},'netnames':ns}
 else:
  assert {p:(x['direction'],len(x['bits']),x.get('offset',0)) for p,x in models[ci['module']]['ports'].items()}=={p:(directions[p],len(bs),offsets[p]) for p,bs in ports.items()}
 records.append({'inst':ci['inst'],'module':ci['module'],'members':sorted(members),'pins':sum(map(len,ports.values())),'native_parameters':actual,'uncovered_boundary':0})
# Independent emitted-graph check from retained source/template mapping, plus a wrong connection control.
def verify(candidate):
 for name,c in source.items():
  if name not in allmembers:assert candidate['cells'][name]==c,('changed sibling',name)
 for name,c in expected.items():assert candidate['cells'][name]==c,('changed child pin map',name)
 assert set(candidate['cells'])==(set(source)-allmembers)|set(expected)
 assert candidate['ports']==original['ports'],'outer native ABI changed'
verify(m)
mutant=copy.deepcopy(m)
name=next(iter(expected));port=next(p for p,d in expected[name]['port_directions'].items() if d=='input' and p not in ('ck','ck_phy'))
v=mutant['cells'][name]['connections'][port][0];mutant['cells'][name]['connections'][port][0]='1' if v!='1' else '0'
try:verify(mutant)
except AssertionError:pass
else:raise AssertionError('wiring mutant survived')
# Keep original primitive declarations and init attributes. Drop unused native hierarchy via stock Yosys.
a['modules'].update(models);a['modules'][top]=m
(r/'native_parent.json').write_text(json.dumps(a))
(r/'native_parent_receipt.json').write_text(json.dumps({'schema':'opentallas.kv.native_parent.v1','top':top,'native_abi_preserved':True,'source_siblings_unchanged':True,'clock_aliases':inv['clock_aliases_from_actual_bound'],'cores':records,'wiring_mutant':'caught','qualified_child_phase_join':'required independently; no timing or cycle waiver'},indent=1))
ys=r/'native_parent.ys';ys.write_text(f'read_json {r}/native_parent.json\nhierarchy -check -top {top}\nopt_clean\ncheck -assert\nwrite_verilog -noattr {r}/qkd_hr_host_parent.sv\n')
env=dict(os.environ,PATH=str(Path.home()/'.local/opentallas-tools/bin')+':'+os.environ.get('PATH',''))
with (r/'native_parent_emit.log').open('w') as f:subprocess.run(['yosys','-Q','-s',str(ys)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('NATIVE_PARENT_EMIT_PASS',len(records),'children',len(cells),'parentcells; source siblings exact; wiring mutant caught',flush=True)
