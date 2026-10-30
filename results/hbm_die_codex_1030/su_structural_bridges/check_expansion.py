import copy,json,sys,subprocess
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030');S=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tools/die_plan'))
import bind_elab as E,bind as B,structural_bridge as H
get=lambda p:subprocess.check_output(['git','-C',str(R),'show','1f9fe3c3a:'+p],text=True)
abi=json.loads(get('results/hbm_su_native_1030/native_cut_abi.json'));mapping=json.loads(get('results/hbm_su_native_1030/native112_plan_map.json'))
rows=[];fragments={}
for master in ['ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526','ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44']:
 physical=master+'__nocoll';bridge=physical+'__native_bridge';p=S/master
 for mode in ['nominal','wrong_tie1','undriven_removed_output']:
  frag=E.flatten(json.load(open(p/(mode+'.json'))),bridge)
  child=frag.cells[0];phys=dict(module=physical,relative_path='u_phys',params={},abi={n:dict(dir=child.dirs[n],width=len(bs))for n,bs in child.ports.items()})
  if mode=='nominal':fragments[physical]=(frag,phys)
  a=next(x for x in abi if x['module']==('ot_hnx_su_plain4__7dd6a1bbbf47_rst3'if'id44'in master else'ot_hnx_su_plain4__lid9_rst3'))
  def make():
   F=E.Flat();ports={}
   for n,w in a['ports'].items():
    ports[n]=list(range(F.new(w),len(F.parent)))
   # Preserve the actual native ID strap, not merely an arbitrary public net.
   ports['lane_lane_id']=[str((a['ids']['lane_lane_id']['value']>>i)&1)for i in range(a['ports']['lane_lane_id'])]
   old=E.Cell(a['path'],a['module'],{},ports,dict(a['port_directions']),'leaf')
   loaded=E.Cell('loaded_consumer','consumer',{},dict(D=ports['lane_coll'],other=[ports['lane_fault'][0]]),dict(D='input',other='input'),'leaf')
   F.cells=[old,loaded];F.top_ports={n:(old.dirs[n],bs)for n,bs in ports.items()};return F
  F=make();expected={n:dict(dir=a['port_directions'][n],width=w)for n,w in a['ports'].items()}
  before=(len(F.parent),[c.path for c in F.cells],dict(F.const_drivers));rejected=False
  try:receipt=H.expand(F,a['path'],frag,expected_module=a['module'],expected_abi=expected,physical=phys,Cell=E.Cell)
  except H.StructuralBridgeError:rejected=True
  if mode=='undriven_removed_output':assert rejected and before==(len(F.parent),[c.path for c in F.cells],dict(F.const_drivers));rows.append(dict(master=master,mode=mode,structural_reject=True));continue
  assert not rejected
  G=B.Graph(F,B.Rules({}),[]);loaded=next(c for c in F.cells if c.path=='loaded_consumer');values=[G.source(b)for b in loaded.ports['D']];qualified=all(v[:2]==('const','0')for v in values);assert qualified==(mode=='nominal')
  assert G.source(loaded.ports['other'][0])[:3]==('pin',0,'lane_fault')
  assert next(c for c in F.cells if c.path.endswith('.u_phys')).ports['strap_lane_lane_id']==[str((a['ids']['lane_lane_id']['value']>>i)&1)for i in range(a['ports']['lane_lane_id'])]
  rows.append(dict(master=master,mode=mode,structural_accept=True,functional_constant_contract_pass=qualified,loaded_sources=values,receipt=receipt))
  if mode=='nominal':
   for negative in ['wrong_ABI','wrong_child','duplicate_path','existing_driver']:
    FF=make();ex=copy.deepcopy(expected);ph=copy.deepcopy(phys)
    if negative=='wrong_ABI':ex['lane_coll']['width']=3
    if negative=='wrong_child':ph['abi']['strap_lane_lane_id']['width']+=1
    if negative=='duplicate_path':FF.cells.append(E.Cell(a['path']+'.u_phys','old',{}, {},{},'leaf'))
    if negative=='existing_driver':FF.const_drivers[FF.cells[0].ports['lane_coll'][0]]=('0','preexisting')
    prior=(len(FF.parent),[c.path for c in FF.cells],copy.deepcopy(FF.const_drivers))
    try:H.expand(FF,a['path'],frag,expected_module=a['module'],expected_abi=ex,physical=ph,Cell=E.Cell)
    except H.StructuralBridgeError:pass
    else:raise AssertionError(negative)
    assert prior==(len(FF.parent),[c.path for c in FF.cells],FF.const_drivers)
    rows.append(dict(master=master,mode=negative,structural_reject=True,atomic=True))
(S/'expansion_receipt.json').write_text(json.dumps(dict(scope='Actual source fragments, exact native ABI/IDs/loaded consumers; structural and functional qualification are distinct',cases=rows,all_expected_results=True),indent=2)+'\n')
# Build exact descriptors for all48 native cuts, with direct bridge body path.
desc=[]
for r in mapping['rows']:
 if 'physical_source_PREP'not in r:continue
 p=r['physical_source_PREP'];frag,phys=fragments[p['module']];a=next(x for x in abi if x['path']==r['native_path']);desc.append(dict(inst=r['native_path'],expected_module=r['native_module'],expected_abi={n:dict(dir=a['port_directions'][n],width=w)for n,w in a['ports'].items()},physical=phys,fragment_top=p['parent_bridge'],physical_mapping=dict(path=r['native_path']+'.u_phys',part=r['part'],local=r['local'],pins_source=p['pins_source']),functional_qualification='1f9fe3c3a native bridge/constant proofs; current whole-parent source event still PREP'))
assert len(desc)==48
(S/'postcompose_descriptors_PREP.json').write_text(json.dumps(dict(scope='FLOW owns caller/immutable file identity validation and actual fullbind event; no plan changed',descriptors=desc),indent=2)+'\n')
F=E.Flat();old_ports={};F.top_ports={}
for a in abi:
 pp={}
 for n,w in a['ports'].items():
  k=F.new(w);pp[n]=list(range(k,k+w))
 pp['lane_lane_id']=[str((a['ids']['lane_lane_id']['value']>>i)&1)for i in range(a['ports']['lane_lane_id'])]
 old_ports[a['path']]=copy.deepcopy(pp)
 F.cells.append(E.Cell(a['path'],a['module'],{},pp,dict(a['port_directions']),'leaf'))
 for n,bs in pp.items():F.top_ports[a['path']+'.'+n]=(a['port_directions'][n],list(bs))
loaded=[b for r in desc for b in old_ports[r['inst']]['lane_coll']]
F.cells.append(E.Cell('all192_loaded','consumer',{},dict(D=loaded),dict(D='input'),'leaf'))
original_top=copy.deepcopy(F.top_ports)
receipts=[]
for r in desc:
 frag,phys=fragments[r['physical']['module']]
 receipts.append(H.expand(F,r['inst'],frag,expected_module=r['expected_module'],expected_abi=r['expected_abi'],physical=phys,Cell=E.Cell))
assert F.top_ports==original_top and len(F.cells)==113
G=B.Graph(F,B.Rules({}),[])
assert len(loaded)==192 and all(G.source(n)[:2]==('const','0')for n in loaded)
for r in desc:
 child=next(c for c in F.cells if c.path==r['inst']+'.u_phys')
 assert child.ports['strap_lane_lane_id']==old_ports[r['inst']]['lane_lane_id']
(S/'all48_context_receipt.json').write_text(json.dumps(dict(scope='Actual112 native ABIs in constructed loaded context, not current full-source bind',cuts=112,expanded=48,loaded_const0_bits=192,exact_ID_straps=48,unchanged_all_top_port_nets=True,unchanged_cell_count=113,events=receipts),indent=2)+'\n')
print('PASS actual3fragments;21cases;48descriptors;112ABI loaded context;192 source0bits;0cycles')
