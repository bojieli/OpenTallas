import sys,json,copy,hashlib,collections,gzip
from pathlib import Path
from types import SimpleNamespace
here=Path(__file__).resolve().parent
root=next(p for p in here.parents if (p/'tools/die_plan').is_dir());sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab
from clock_landing_verify import Verification
base=json.load(gzip.open(here/'source_graph.json.gz','rt'));modelpath=here.parent/'paired_batch/regional_model_DISABLED.json'
def build(mutant=None):
 graph=copy.deepcopy(base);top=graph['modules']['qfd_qc_tt_ctlm_part_bound'];hc=top['cells']['u_cland_origin'];graph['modules'][hc['type']]['attributes']['blackbox']='1';graph['modules']['ot_dp_rrelay']['attributes']['blackbox']='1'
 if mutant=='region':top['cells']['u_cland_fstart_tl']['connections']['d']=[hc['connections']['start_d_r'][0]]
 if mutant=='raw':top['cells']['g_tt_raw_regions.g_region[0].u_raw_copy']['connections']['d']=top['cells']['u_rrl_84']['connections']['q']
 F=bind_elab.flatten(graph,'qfd_qc_tt_ctlm_part_bound')
 for c in F.cells:c.path='tt_ctlm.'+c.path
 drv=collections.defaultdict(list);loads=collections.defaultdict(list);top_in={}
 for ci,c in enumerate(F.cells):
  for p,bits in c.ports.items():
   for bi,b in enumerate(bits):
    if isinstance(b,str):continue
    if c.dirs.get(p)=='output':drv[b].append((ci,p,bi))
    elif c.dirs.get(p)=='input':loads[b].append((ci,p,bi))
 for p,(direction,bits) in F.top_ports.items():
  if direction!='input':continue
  for bi,b in enumerate(bits):top_in[b]=('clk_region_rTT' if p=='clk' else p,bi)
 v=object.__new__(Verification);v.F=F;v.G=SimpleNamespace(drv=drv,loads=loads,top_in=top_in);v.parts={'tt_ctlm':{'type':'tt_ctlm'}};v.region={'tt_ctlm':'rTT'};v.raw={'partition_types':{'tt_ctlm':{'clock':{'landing_regional_origin':dict(enabled=True,model_file=str(modelpath),model_sha256=hashlib.sha256(modelpath.read_bytes()).hexdigest())}}}};v.table={'count_aligned':{'strap_form':True}};v._strap={'instances':{'tt_ctlm':{'values':{'strap_ca_root':0}}},'types':{'tt_ctlm':{'origin':{'tree_buses':['cland_tstart_in']}}}};v.byname={c.path:c for c in F.cells};v.expected=set();v.memo={};v.checks=0;v.errors=[];v._fstart_checked=set()
 v._check_regional_origin('tt_ctlm')
 return v
v=build();assert not v.errors,v.errors
assert v.start_net('tt_ctlm','u_cland_ctx_x')==('pin','tt_ctlm.u_cland_origin','start_r',0)
assert v.fstart_net('tt_ctlm','tl')==('pin','tt_ctlm.u_cland_fstart_tl','q',0)
assert len(v.expected)==42,len(v.expected)
print('ACTUAL_NATIVE_F_BRIDGE_PASS',v.checks,'checks',len(v.expected),'expected components')
for mutant in ['region','raw']:
 v=build(mutant);assert v.errors,mutant;print('ACTUAL_NATIVE_F_BRIDGE_REJECT',mutant,v.errors[:2])
