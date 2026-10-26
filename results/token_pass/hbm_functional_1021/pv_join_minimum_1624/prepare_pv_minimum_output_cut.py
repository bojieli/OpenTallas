from pathlib import Path
import re,json,hashlib,sys
sys.path.insert(0,'/home/ubuntu/wt/codex-hbm-token-resume-1021/tools')
from hbm_layer_vehicle.cut_slice import parse_die,ID
r=Path('/home/ubuntu/scratch/tok-func2-hbm/conn_idx')
_,_,_,ii=parse_die((r/'die.v').read_text());idx={i['name']:i for i in ii}
contract=json.loads((r/'contract_func.json').read_text())
seeds=set()
for n in idx:
 if (re.fullmatch(r'(sucore|stl)_(SW|SE|NW|NE)',n) or re.fullmatch(r'(stu|std)_(SW|SE|NW|NE)_[0-9]{2}[ab]?',n) or n=='str_C'
     or n in ['pgp_SW','subr_SW','hb_ckgen','cp_svg_SW0','sm_SW0','svg_SW0','vmks_SW0','xc_SW0','fs_SW','phy_SW','refcfg_SW','sfault_SW']
     or re.fullmatch(r'su_SW[0-3]',n) or re.fullmatch(r'ctl_SW_p[0-9]{2}',n)
     or re.fullmatch(r'(calendar|hleaf|hb_vms|hb_coll|hcollgi|hcollgl|hcollrs|hcollks|hcollb)_(SW|SE|NW|NE)',n)
     or re.fullmatch(r'vmb_(SW|SE|NW|NE)[0-7]',n)
     or n.startswith(('xl_SW_','xq_SW_'))):seeds.add(n)
pads={n for n,i in idx.items() if n.startswith('l12p_') or i['master'].startswith('hbfd_')}
drivers={};readers={}
for i in ii:
 ports=contract['instances'][i['name']]['ports']
 for p,e in i['conns']:
  for net in ID.findall(e):
   if ports[p]['direction']=='output':drivers[net]=i['name']
   elif ports[p]['direction']=='input' and (i['name'] not in pads or p in ('i','d','data_in')):readers.setdefault(net,[]).append(i['name'])
# Include only real pad chains whose two non-pad endpoints are selected.
adj={n:set() for n in idx}
for net,s in drivers.items():adj[s].update(readers.get(net,[]))
selected=set(seeds)
def path(n,trail):
 if n in trail:return
 if n not in pads:
  if n in seeds:selected.update(trail)
  return
 for nxt in adj[n]:path(nxt,trail+[n])
for n in seeds:
 for nxt in adj[n]:
  if nxt in pads:path(nxt,[])
out=Path('/home/ubuntu/scratch/tok-func2-hbm/pv_join_minimum_output_1600');out.mkdir(exist_ok=True)
x=dict(status='CUT_PLAN_ONLY_NOT_BUILT',source_die_sha256=hashlib.sha256((r/'die.v').read_bytes()).hexdigest(),contract_sha256=hashlib.sha256((r/'contract_func.json').read_bytes()).hexdigest(),core_instances=sorted(seeds),instances=sorted(selected),count=len(selected),regex='^(?:'+'|'.join(re.escape(n) for n in sorted(selected))+')$',programme_boundary='su_prog__r_* inputs; host-to-SU sparse install explicitly unqualified',scope='authentic score->max->exp_sum->BF16->fourquarter GQ copies->new XQL->selected SM0 pstore/KV/PV component; unnormalized oneSM chunk node only',obligations=['actual source overlays/defines/params','all required feedback/control paths checked from generated boundary','finite actual bank calendar, CP anchors, immutable programme/NEV','current SM3 PV latency is candidate until actual selected-source proof','no P/intermediate preload; only genuine score/K inputs'])
(out/'cut_plan.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(dict(count=len(selected),cores=len(seeds),pads=len(selected-seeds),out=str(out))))
