"""Reprice exact shared column spans and check current source owner admission."""
import argparse,gzip,hashlib,importlib.util,json
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[3];I=B.parent/'c0_program_shared64_r1'
spec=importlib.util.spec_from_file_location('calendar',R/'tools/h3_complete_native_calendar_successor_r1.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ap=argparse.ArgumentParser();ap.add_argument('--program-root',type=Path,required=True);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
qpath='results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz'
dpath='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
qraw=(args.program_root/qpath).read_bytes();draw=(args.program_root/dpath).read_bytes()
pins=json.loads((I/'source_pins.json').read_bytes());sources={n:gzip.decompress((I/(Path(n).name+'.gz')).read_bytes()) for n in pins if '/' in n}
admission=c.analyze_c0_program_owner_admission(draw,qraw,{n:v for n,v in sources.items() if n!='tools/hbm_provider_microvm_r21.py'})
progress=c.derive_source_sector_provider_progress(sources['tools/hbm_provider_microvm_r21.py'])
spans=c.compile_qwen_shared64_spans(qraw,sources['tools/h3_qwen_bounded_native.py'])
control=c.compile_qwen_shared64_spans(qraw,sources['tools/h3_qwen_bounded_native.py'],position=17)
summary={k:v for k,v in spans.items() if k not in ['layouts','PCs']}
summary['admission']={k:v for k,v in admission.items() if k!='programs'}
summary['program_DAG_PCs']={k:v['PCs'] for k,v in admission['programs'].items()}
terminal=c.join_qwen_actual_terminal_demands(qraw,sources['tools/h3_qwen_bounded_native.py'],(I/'Qwen_actual_native_terminal.json').read_bytes(),(I/'Qwen_actual_supervisor_terminal.json').read_bytes())
# Regenerate the union schema from exact retained AST functions. ZERO requests.
import ast,sys,tempfile,types
r46pins=json.loads((I/'R46_source_pins.json').read_bytes())
r46sources={n:gzip.decompress((I/(Path(n).name+'.gz')).read_bytes()) for n in r46pins if '/' in n}
engine=gzip.decompress((I/'ds_hbm_pc10_engine_r44.py.gz').read_bytes())
if hashlib.sha256(engine).hexdigest()!=r46pins['resource_model_source']:raise ValueError('resource source pin differs')
node=next(n for n in ast.parse(engine).body if isinstance(n,ast.FunctionDef) and n.name=='resource_model')
ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'retained_resource_model','exec'),ns)
node=next(n for n in ast.parse(r46sources['tools/ds_hbm_pc10_journal_model_r44.py']).body if isinstance(n,ast.FunctionDef) and n.name=='model')
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'sector.py';path.write_bytes(r46sources['tools/hbm_provider_microvm_r21.py'])
 module=types.ModuleType('hbm_provider_microvm_r21');module.__file__=str(path)
 previous=sys.modules.get(module.__name__);sys.modules[module.__name__]=module
 try:
  exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
  ns.update(hashlib=hashlib,json=json,Path=Path,inputs=lambda:{'sector.py':path.read_bytes()})
  exec(compile(ast.Module(body=[node],type_ignores=[]),'retained_union_model','exec'),ns)
  union=ns['model']()
  provider=module.SectorProvider({('DeepSeek',95):[dict(base=0,bytes=64)]},tags=1)
  provider.seed('DeepSeek',95,0,b'actual\x00payload')
  transaction=provider.submit(module.Identity('DeepSeek',95,1,9,0,1),write=True,payload=bytes(range(32)))
  provider.wait(transaction);provider.finish(transaction)
  owners=dict(scope='complete codec control ONLY; no PC9 production bytes',leases=['actual.control.next_reader'],published_versions=['actual.control.PC9'])
  image=Path(tmp)/'checkpoint.bin';size=c._actual_provider_checkpoint_plan([('RF95',provider)],owners)[2]
  checkpoint=c.write_actual_provider_checkpoint(image,[('RF95',provider)],owners,size);checkpoint.pop('path')
  fresh=module.SectorProvider(provider.extents,tags=1)
  restored=c.restore_actual_provider_checkpoint(image,[('RF95',fresh)])
  if fresh.backing!=provider.backing or fresh.generations!=provider.generations:raise ValueError('actual checkpoint control bytes differ')
  checkpoint['restore']=restored
  checkpoint['scope']='all actual sectors of one complete codec control; no actual production resume'
 finally:
  if previous is None:sys.modules.pop(module.__name__,None)
  else:sys.modules[module.__name__]=previous
if union!=json.loads((I/'R46_shared_source_union.json').read_bytes()):raise ValueError('retained source union replay differs')
projection=json.loads(gzip.decompress((I/'R46_conservative_projection.json.gz').read_bytes()))
compact=c.project_r46_compact_shared_journal(projection,union,r46sources)
continuation=c.project_ds_collective_continuation_obligations(draw,gzip.decompress((I/'Sagan_h4_c0_ds_runtime_bindings.py.gz').read_bytes()),gzip.decompress((I/'Sagan_summary.json.gz').read_bytes()))
selected=c.compose_selected_owner_wait_calendar((I/'Popper_selected_r4_commands.json.gz').read_bytes(),(I/'Popper_selected_r4_model.json').read_bytes(),(I/'Popper_owner_wait_requirements_r4.json').read_bytes(),admission)
storage=c.compose_actual_checkpoint_storage_admission(compact,None,available_bytes=830*(1<<30),additional_new_bytes=0)
outputs={'selected_r4_owner_wait_calendar.json.gz':selected,'actual_checkpoint_storage_admission_UNKNOWN.json':storage,'actual_payload_checkpoint_codec_control.json':checkpoint,'R46_compact_shared_complete_projection.json':compact,'DS_fullgraph_continuation_obligations.json.gz':continuation,'Qwen_actual_runtime_demand_join.json':terminal,'sector_provider_software_progress.json':progress,'program_owner_admission.json.gz':admission,'Qwen_shared64_full_context.json.gz':spans,
         'Qwen_shared64_position17_control.json.gz':control,'summary.json':summary}
native=json.loads(gzip.decompress(qraw));examples={}
for family in ['MATRIX','SCORES','PV']:
 pc=next(o['pc'] for o in native['operations'] if o['opcode']==family)
 packets=[]
 for packet in c.iter_qwen_shared64_packets(spans,pc,1,native=native):
  packets.append(packet)
  if packet['eligible_for_tile_owner_release']:break
 examples[family]={'PC':pc,'scope':'complete FIRST source tile only, descriptor expansion control; no provider execution or whole-program journal','packets':packets}
outputs['first_tile_packet_controls.json.gz']=examples
for name,value in outputs.items():
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode() if not name.endswith('.gz') else gzip.compress(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),mtime=0)
 p=B/name
 if args.verify:
  if p.read_bytes()!=raw:raise ValueError('source-bound DAG/shared64 replay differs '+name)
 elif p.exists():raise ValueError('fresh evidence output required')
 else:p.write_bytes(raw)
print(json.dumps(dict(PCs=summary['program_DAG_PCs'],Qwen_dot_PCs=spans['shared_dot_PC_count'],
 fill64_transactions=spans['fill64_transactions'],column64_transactions=spans['column64_transactions'],
 old_packed128_reads=spans['retained_packed128_column_transactions'],finite_external_consumer_reverse_bound=None,
 hardware_qualified=False),sort_keys=True))
