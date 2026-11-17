"""Prepare instance-scoped BF kernel composition from actual source-traced input deltas."""
import copy,json,sys,hashlib
from pathlib import Path
r=Path('/tmp/token_ds_followthrough1116');sys.path.insert(0,str(r))
import bf_component_composition as C
base_rel='results/rtl/s81_bf_asbuilt_1101/newkit_1111/asbuilt_bf_measure_1111.json'
base_path=r/'source'/base_rel;base=json.loads(base_path.read_text())
inputs=json.loads((r/'bf_input_transport_composition.json').read_text())
schedules=r/'tapfix_profiles';composition=json.loads((schedules/'composition.json').read_text())
source=r/'tapfix_source'
output={};summary=[]
for row in composition['frames']:
 frame,top=row['frame'],row['master'];sp=schedules/'frames'/frame/(top+'_schedule.json');sch=json.loads(sp.read_text())
 choices=[x for x in inputs if x['top']==top and x['current_seam_extra']==sch['bound_plan']['seam_extra_stages']]
 assert len(choices)==1,(frame,len(choices))
 traced=choices[0];key=top.replace('_l4_lp','')+'|E2|bseg1024';b=base[key]
 rec,shifts=C.translate(b,traced['inputs'])
 sources=dict(sch['source_sha256'])
 # Native BF components are unchanged; current selected source must expose the exact closure.
 for name in C.KERNELS:
  p=source/name
  if not p.exists():
   assert C.digest(r/'source'/name)==b['asbuilt_source_qualification']['source_sha256'][name],name
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/'source'/name).read_bytes())
  sources[name]=C.digest(p)
 for name,h in sources.items():assert C.digest(source/name)==h,('source mismatch',name)
 q=dict(clock_ps=833,validated_ops=b['asbuilt_source_qualification'].get('validated_ops',['attn.wo_a','ffn.router']),bound_plan=sch['bound_plan']);q.update(status='COMPONENT_COMPOSITION',scope='unchanged BF kernel replay plus source-traced uniform input translation and current FSA return topology; Q quiescent; no new frame runtime/physical qualification',source_sha256=sources,schedule_sha256=C.digest(sp))
 q['component_composition']=dict(frame=frame,replay_file=base_rel,replay_file_sha256=C.digest(base_path),input_shifts=shifts,inputs=traced['inputs'],source_trace_class=traced['class_'],input_trace_file='results/token_pass/s81_bf_component_composition_1116/input_trace.json',input_trace_file_sha256=C.digest(r/'bf_input_transport_composition.json'))
 rec['asbuilt_source_qualification']=q;rec['die_frame']=frame;output[frame+'::'+key]=rec
 assert C.qualify(rec,source,r/'source',sp,frame)=='component_composition_bf_idle_q'
 summary.append(dict(frame=frame,key=key,input_shifts=shifts,scope='COMPONENT_COMPOSITION'))
out=r/'bf_component_records_2228.json';out.write_text(json.dumps(output,indent=1)+'\n')
(r/'bf_component_summary_2228.json').write_text(json.dumps(dict(status='COMPONENT_COMPOSITION',records=len(output),source_plan_sha256=composition['source_plan_sha256'],frames=summary),indent=1)+'\n')
print('BF_COMPONENT_COMPOSITION',len(output),'frames','keyed_by_actual_instance')
