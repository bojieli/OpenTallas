"""Join canonical DieROM ownership to existing S82 physical instance homes.
Metadata only. No Checkpoint object, payload read, mapping/repacking or inference.
"""
import argparse,ast,gzip,hashlib,json,subprocess
from collections import defaultdict
from pathlib import Path
import dsrom_c_s82_combined as G
API_COMMIT='e6dffa754a1bfa6b8b4fc1868f67ee632348574b'
SELECTED='results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1'
def die_class(path):
 # Compile the authoritative class alone, avoiding imports of historical
 # compiler tools and any generated Python caches; no class rewrite.
 source=path.read_text();tree=ast.parse(source)
 classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DieROM']
 if len(classes)!=1:raise ValueError('canonical DieROM class absent/ambiguous')
 ns={};exec(compile(ast.Module(body=classes,type_ignores=[]),str(path),'exec'),ns)
 return ns['DieROM']
def join(root):
 root=Path(root);base=root/SELECTED;api=root/'tools/dsrom_s82_payload_interface.py'
 # Check the five physical inputs against the immutable construction before
 # associating API owner IDs with these homes.
 for name in ('inventory','stage_map','physical_contract','area_ledger','return_baseline'):
  if (base/(name+'.json')).read_bytes()!=(G.P.I/(name+'.json')).read_bytes():
   raise ValueError('canonical physical input changed: '+name)
 expected=subprocess.check_output(['git','-C',str(root),'show',API_COMMIT+':tools/dsrom_s82_payload_interface.py'])
 if api.read_bytes()!=expected:raise ValueError('API differs from frozen corrective source')
 DieROM=die_class(api)
 bystage=defaultdict(list)
 with gzip.open(base/'matrix_map.jsonl.gz','rt') as stream:
  for line in stream:
   m=json.loads(line);bystage[m['stage']].append(m)
 providers=json.loads((root/'results/uarch/dsrom_s82_source_interface_20261003/provider_interfaces.json').read_text())
 aux=json.loads((base/'auxiliary_map.json').read_text())['tensors']
 physical=G.build();homes={a['site']:a for a in physical['rectangles'] if a['kind'] in ('q','BF')}
 matrix_count=sum(map(len,bystage.values()));records=[];unknown_pair_count=0
 bounds=G.P.read('stage_map')['region_bounds'];region={p:r for r in range(128) for p in range(bounds[r],bounds[r+1])}
 for stage in range(82):
  for rank in range(4):
   owner=DieROM(stage,rank,bystage[stage],providers,aux)
   pairs=[]
   for pair in range(2388):
    classes=[name for name,d in [('matrix',owner.intervals),('raw_provider',owner.providers),('auxiliary',owner.aux)] if pair in d]
    if len(classes)>1:raise ValueError('payload class overlap')
    kind=classes[0] if classes else 'unowned_charged_frame'
    unknown_pair_count+=not classes
    pairs.append(dict(pair=pair,weight_macro_IDs=list(range(4*pair,4*pair+4)),bbox_um=homes[pair]['bbox_um'],element=homes[pair]['kind'],source_owner_class=kind,ragged_region=region[pair],retained_return_pair=32*region[pair]+pair-bounds[region[pair]],physical_frame_retained=True,unowned_word_fallback_allowed=False,word_owner_intervals=[r[:2] for r in owner.intervals.get(pair,[])]))
   records.append(dict(**owner.inventory(),physical_pairs=pairs))
 sources=[api,base/'inventory.json',base/'stage_map.json',base/'physical_contract.json',base/'area_ledger.json',base/'return_baseline.json',base/'matrix_map.jsonl.gz',base/'auxiliary_map.json',root/'results/uarch/dsrom_s82_source_interface_20261003/provider_interfaces.json']
 return dict(stage_identity=dict(selected_stage_bits=7,legacy_capture_stage_bits=6,legacy_stage64_alias=True,legacy_global_context_bits=169,required_global_context_bits=170,legacy_PAR2_route_bit_not_required_on_PAIR1=True,required_request_bits=187,required_response_bits=240,source_header_stage_bit_delta=1,codec_control_cost_not_qualified=True,actual_identity_adapter_implemented=False),candidate=physical['candidate'],canonical_main_commit='feba0739366dfe9adb98991e59bd0cee687f5d55',owner_API_commit=API_COMMIT,API_class_sha256=hashlib.sha256(ast.get_source_segment(api.read_text(),next(n for n in ast.parse(api.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='DieROM')).encode()).hexdigest(),rank_dies=328,total_target_dies=372,source_matrices=matrix_count,physical_weight_instances=328*9552,physical_pairs=328*2388,unowned_charged_pairs=unknown_pair_count,unowned_is_not_zero_weight=True,word_payload_reads=0,new_mapping=False,head_table_die_homes_in_this_layer_case=False,physical_fit=False,contextual_route=False,stage_maps=records,source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--owner-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(gzip.compress((json.dumps(join(a.owner_root),sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
