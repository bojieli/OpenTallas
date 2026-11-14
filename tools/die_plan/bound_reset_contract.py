"""Carry the reset tree emitted with bound RTL; never solve a replacement tree."""
import copy,hashlib,json,re,subprocess
from pathlib import Path

SCHEMA='opentallas.bound_reset_source.v1'
KIT_SCHEMA='opentallas.bound_reset_kit.v1'

def digest(value):
 # Receipts are JSON: integer tap-map keys become strings on disk.
 # Canonicalize that representation before ordering keys, including before emission.
 value=json.loads(json.dumps(value))
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def emitted(path,tn,tree,provenance=None):
 path=Path(path);tree=copy.deepcopy(tree)
 rec=dict(schema=SCHEMA,plan_type=tn,bound_module=path.stem,tree=tree,tree_sha256=digest(tree),
          bound_rtl_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),authority='tree used by this bound RTL emission',provenance=provenance)
 path.with_suffix('.reset_tree.json').write_text(json.dumps(rec,indent=1)+'\n')
 import reset_tree as RT
 path.with_suffix('.reset_tree.tcl').write_text(RT.tcl_text(tree))
 return rec

def validate(record,tn):
 if record.get('schema') not in (SCHEMA,KIT_SCHEMA) or record.get('plan_type')!=tn:
  raise ValueError('bound reset source type/schema differs')
 if record.get('tree_sha256')!=digest(record.get('tree')):
  raise ValueError('bound reset tree content differs from receipt')
 return record

def source(bound,tn,bind_out,repo):
 """Read an emission receipt, or exact clean bind-provenance plan's serialized tree.

 Historical recovery reads only git's captured bytes. It never invokes a reset
 solver and never substitutes the caller's current geometry plan.
 """
 bound,bind_out=Path(bound),Path(bind_out)
 meta=bound.with_suffix('.reset_tree.json')
 if meta.exists():
  rec=validate(json.loads(meta.read_text()),tn)
  if rec.get('bound_module')!=bound.stem or rec.get('bound_rtl_sha256')!=hashlib.sha256(bound.read_bytes()).hexdigest():
   raise ValueError('bound reset emission source RTL identity differs')
  return rec
 text=bound.read_text()
 if not re.search(r'\bot_dp_r(?:relay|sync_s[23])\s+u_rst_(?:in|root)\s*\(',text):return None
 prov=json.loads((bind_out/'provenance_bind.json').read_text()).get('provenance',{})
 commit,plan=prov.get('commit',''),prov.get('plan','')
 if prov.get('dirty') is not False or prov.get('source')!='git' or not re.fullmatch('[0-9a-f]{40}',commit) or not plan or Path(plan).is_absolute() or '..' in Path(plan).parts:
  raise ValueError('native bound reset lacks clean captured plan authority; preserve the original emitted tree')
 raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+plan])
 doc=json.loads(raw);typ=doc.get('partition_types',{}).get(tn,{})
 tree=typ.get('clock',{}).get('landing_contract',{}).get('collector_tree')
 if isinstance(tree,dict):
  tree=copy.deepcopy(tree)
  mode=doc.get('reset',{}).get('relay_lockup',{})
  if mode.get('form') in ('negedge','latch') and tn in mode.get('types',[]):tree['relay_lockup']=mode['form']
 if not isinstance(tree,dict):
  raise ValueError('captured bind plan has no serialized reset tree; an emitted native receipt is required (no re-solve)')
 return dict(schema=SCHEMA,plan_type=tn,bound_module=bound.stem,tree=copy.deepcopy(tree),tree_sha256=digest(tree),
             bound_rtl_sha256=hashlib.sha256(bound.read_bytes()).hexdigest(),authority='exact serialized collector_tree from clean bind provenance',
             provenance=prov,source_plan_sha256=hashlib.sha256(raw).hexdigest())

def kit(files,tn):
 if not files:return None
 path=Path(files[0]).parent/'bound_reset.json'
 if not path.is_file():return None
 record=validate(json.loads(path.read_text()),tn)
 placement=path.with_name('reset_tree.tcl')
 if record.get('placement_tcl_sha256') and (not placement.is_file() or hashlib.sha256(placement.read_bytes()).hexdigest()!=record['placement_tcl_sha256']):
  raise ValueError('bound reset placement sidecar differs from captured receipt')
 return record

def stage(kd,source_record,contract):
 kd=Path(kd);record=copy.deepcopy(source_record)
 record.update(schema=KIT_SCHEMA,native_paths=contract['native_paths'],physical_nodes=contract['physical_nodes'],
               verified_cell_classes=contract['verified_cell_classes'],placement_sites=contract.get('placement_sites',{}),placement_review=contract.get('placement_review'),core_reset_policy='preserve exact bound connections; no native core-port rewiring')
 import reset_tree as RT
 text=RT.tcl_text(record['tree'],native_paths=record['native_paths'],native_nodes=record['physical_nodes'],native_sites=contract.get('placement_sites'))
 record['placement_tcl_sha256']=hashlib.sha256(text.encode()).hexdigest()
 (kd/'bound_reset.json').write_text(json.dumps(record,indent=1)+'\n')
 (kd/'reset_tree.tcl').write_text(text)
 return record


def placement(P,tn,tree,nodes,paths,source_record=None):
 """A reviewed sites-only overlay cannot change a native graph or relay ID."""
 import math
 nodes=copy.deepcopy(nodes)
 overlay=P.types[tn].get('clock',{}).get('landing_contract',{}).get('bound_reset_placement')
 if overlay is None and source_record and source_record.get('placement_sites'):
  overlay=dict(schema='opentallas.bound_reset_placement.v1',source_tree_sha256=source_record['tree_sha256'],
               sites=source_record['placement_sites'],review=source_record.get('placement_review'))
 sites={};review=None
 if overlay is not None:
  if not isinstance(overlay,dict) or set(overlay)-{'schema','source_tree_sha256','sites','review'} or overlay.get('schema')!='opentallas.bound_reset_placement.v1' or overlay.get('source_tree_sha256')!=digest(tree):
   raise ValueError('bound reset placement must name the exact captured tree and sites-only schema')
  sites=copy.deepcopy(overlay.get('sites'));review=copy.deepcopy(overlay.get('review'))
  if not isinstance(sites,dict) or not sites or not isinstance(review,dict) or review.get('verdict')!='PASS' or not review.get('findings') or not review.get('image'):
   raise ValueError('bound reset resites require explicit PASS image review and findings')
  image=Path(review['image'])
  if not image.is_absolute():
   if not getattr(P,'path',None):raise ValueError('relative reset review image needs the actual plan path')
   image=Path(P.path).parent/image
  if not image.is_file():raise ValueError('bound reset resite review image is missing')
  review['image']=str(image.resolve())
  if set(sites)-set(paths):raise ValueError('bound reset placement names an unknown native instance ID')
  w,h=P.types[tn]['outline_um']
  for name,xy in sites.items():
   if not isinstance(xy,(list,tuple)) or len(xy)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xy) or not 0<=xy[0]<=w or not 0<=xy[1]<=h:
    raise ValueError('bound reset resite outside outline: '+name)
  for r in nodes:
   if r['name'] in sites:r['xy']=list(sites[r['name']])
   elif r.get('optional') and r['name'].endswith('_t') and r['name'][:-2] in sites:r['xy']=list(sites[r['name'][:-2]])
 root='u_rst_root' if tree['entry']=='sync' else 'u_rst_in'
 xy={'rst_root_n':sites.get(root,tree['root'])}
 import reset_tree as RT
 for c in RT.pin_root_copies(tree)+RT.pin_start_copies(tree):
  xy[c['q']]=sites.get(c['name'],c['xy'])
 if tree.get('start'):xy['run_root']=sites.get('u_run_root' if tree['entry']=='sync' else 'u_run_in',tree['start_in'])
 xy.update({r['q']:r['xy'] for r in nodes})
 maximum=0
 for r in nodes:
  for parent in [r['d']]+([r['run']] if r.get('run') else []):
   if parent not in xy:raise ValueError('native physical reset edge has no verified driver: '+parent)
   hop=sum(abs(a-b) for a,b in zip(r['xy'],xy[parent]));maximum=max(maximum,hop)
   if hop>float(tree['reach_um'])+1e-6:raise ValueError(f"native reset edge {r['name']} <- {parent} is {hop:.3f}um, beyond captured reach {tree['reach_um']}")
 return nodes,sites,review,maximum
