from pathlib import Path
import json,subprocess,hashlib,sys,time,copy,shutil
B=Path('/srv/opentallas-scratch2/claude/codex-qc-stm-count-1131');R=B/'private_gen_172';S=R/'source';sys.path.insert(0,str(S/'tools/die_plan'));import schema as C
F=Path('/srv/opentallas-scratch2/claude/wt/codex-qc-event-1131');FP=F/'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json';raw=json.load(open(R/'plan_private.json'));full=copy.deepcopy(raw);T=json.load(open(R/'overlay/type_overlay.json'));T['clock']['sink_bins_file']=str(R/'overlay/native_sink_estimate.json');P=C.Plan(raw);raw['partition_types']={'slw_stm_v3':T};raw['partitions']=[x for x in raw['partitions'] if x['name']=='sl_W5_stm'];raw['ports']=[];raw['lanes']=[]
# Explicit isolated boundary. SAME native ABI/window: no peer/channel commitment or latency replacement.
for bus in T['buses']:
 n=bus['name'];inside={'part':'sl_W5_stm','bus':n};outside={'part':C.DIE_PART,'bus':'isolated_'+n};src,dst=(outside,inside) if bus['dir']=='in' else (inside,outside)
 raw['ports'].append({'id':'isolated_'+n,'src':src,'dst':dst,'width':bus['width'],'epoch':True})
for slot in T.get('ft_slots',[]):
 for suffix,d in [('_i','in'),('_o','out')]:
  n=slot['name']+suffix;inside={'part':'sl_W5_stm','bus':n};outside={'part':C.DIE_PART,'bus':'isolated_'+n};src,dst=(outside,inside) if d=='in' else(inside,outside)
  raw['ports'].append({'id':'isolated_'+n,'src':src,'dst':dst,'width':slot['width'],'epoch':True})
raw['die']['channels']=[]
raw.pop('latency',None);raw.pop('latency_groups',None)
for key in ('clock','reset'):
 if raw.get(key,{}).get('source'):raw[key]['source']={'part':C.DIE_PART,'bus':'isolated_'+key+'_input'}
for bus in T['buses']:raw['lanes'].append({'id':'isolated_'+bus['name'],'ports':['isolated_'+bus['name']]})
for slot in T.get('ft_slots',[]):raw['lanes'].append({'id':'isolated_'+slot['name'],'ports':['isolated_'+slot['name']+'_i','isolated_'+slot['name']+'_o']})
for p in FP.parent.iterdir():
 if p.name not in ['plan_qc52.json'] and not(R/p.name).exists():(R/p.name).symlink_to(p,target_is_directory=p.is_dir())
err=C.validate(raw);(R/'isolated_validation.json').write_text(json.dumps({'errors':err,'scope':'isolated child-only physical prototype. No parent path/latency/adoption claim.','boundary_ports':len(raw['ports']),'sidecar':'Original full frozen plan/sidecar used ONLY for target native identity slots in separate supported API.'},indent=2)+'\n')
if err:print('\n'.join(err[:30]));sys.exit(1)
(R/'plan_isolated.json').write_text(json.dumps(raw,separators=(',',':'))+'\n')
cmd=['python3',str(S/'tools/die_plan/gen.py'),'phys',str(R/'plan_isolated.json'),'--out',str(R/'isolated_phys'),'--types','slw_stm_v3','--rtl-root',str(F),'--kit-rtl','slw_stm_v3='+str(B/'rtl-kit/kit_rtl.f'),'--hold-ff-margin','10']
with open(R/'isolated_gen.log','w') as f:rc=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT).returncode
j={'command':cmd,'exit':rc,'scope':'standard validated isolated GEN only; no CAD','time':time.time(),'source':'d90b109213c6949da87b330ef143d96bbe937934','tool':'fbd2f0625eb7969caea7647b6c46d8d1ec58ca02'};(R/'isolated_gen_receipt.json').write_text(json.dumps(j,indent=2)+'\n')
print('GEN',rc,flush=True)
if rc:sys.exit(rc)
# Unmodified full-sidecar native identity API: returns ONLY target's D/form/ring/origin, no geometry.
import clock_landings as CL,gen_phys as G
files=[Path(x.strip()) for x in (B/'rtl-kit/kit_rtl.f').read_text().splitlines() if x.strip()]
lands=CL.Landings(json.load(open(FP)),json.load(open(R/'frozen_sidecar.json')))
ls=G.kit_rtl_land_slots(lands,'slw_stm_v3',files);old=json.load(open(B/'guard_native/land_slots.json'));assert ls==old,(ls,old)
keys=sorted({k for v in ls['buses'].values() for k in v});assert set(keys)<={'D','form','origin','ring','copies'}
k=R/'isolated_phys/slw_stm_v3';(k/'land_slots.json').write_text(json.dumps(ls,indent=1)+'\n');(R/'native_metadata_join.json').write_text(json.dumps({'target':'slw_stm_v3','records':len(ls['buses']),'record_keys':keys,'matches_previously_guarded_native_slots':True,'has_geometry':False,'source_API':'fbd kit_rtl_land_slots(CL.Landings(original full frozen plan, original sidecar), target, original13RTLfiles)','physical_geometry_source':'canonical private isolated type ONLY','no_slot_edits':True},indent=2)+'\n');print('JOIN25 PASS',flush=True)
