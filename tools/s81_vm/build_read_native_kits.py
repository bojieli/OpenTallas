#!/usr/bin/env python3
"""Source-bound native hardening candidates; no inherited physical views.
Input outlines/face order are explicit geometry candidate choices. Actual layers
and track offsets are fixed here; adoption requires die geometry approval.
"""
import pathlib,json,hashlib,re,subprocess,math
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'physical/s81_vm_read_native_1015';OUT.mkdir(parents=True,exist_ok=True)
SPECS=ROOT/'tools/ref_tile/specs_s81vm_read_native_1015';SPECS.mkdir(parents=True,exist_ok=True)
# The source-exact per-bit face candidates already include every functional pin.
subprocess.run(['python3',str(ROOT/'tools/s81_vm/read_router_pin_options.py'),str(OUT/'read_pin_candidates.json')],check=True)
read=json.loads((OUT/'read_pin_candidates.json').read_text())['types']
fsr_artifact=json.loads((OUT/'fsr_pin_candidates.json').read_text())
assert hashlib.sha256((ROOT/fsr_artifact['source']).read_bytes()).hexdigest()==fsr_artifact['source_sha256'], 'FSR pin candidate source drift'
fsr=fsr_artifact['types']
model={'schema':'s81.native-read-leaves.v1','scope':'Source-bound representatives, no physical/throughput qualification','period_ps':833.333,'route_period_ps':770,'whole_vm512':{'read_data_roots':64,'read_valid_roots':8,'read_data_valid_age':13,'FSR_roots':16,'FSR_pin_to_bank_age':1,'global_fault_age':None},'types':{}}
for kind,g in [('q',0),('q',1),('v',0),('b',0)]:
 top=f'dsfd_vm_static_read_{kind}{g}'if kind!='b'else f'dsfd_vm_static_fsr_b{g}'
 choice=(read if kind!='b'else fsr)[top];w,h=choice['outline_um']
 faces={x:[]for x in 'NSEW'};bitpins=[]
 # Resnap centers to actualM4 horizontal /M5 vertical tracks, offset.012pitch.048.
 for face in ['W','N','E','S']:
  bits=[p['port']for p in choice['pins']if p['face']==face]
  length=h if face in 'WE'else w
  start=.012+math.floor(((length-(len(bits)-1)*.432)/2-.012)/.048)*.048 if bits else 0
  if bits:assert start>=4.32 and start+(len(bits)-1)*.432<=length-4.32,(top,face)
  for i,name in enumerate(bits):
   d=round(start+i*.432,6);layer='M4'if face in 'WE'else'M5'
   x=.042 if face=='W'else round(w-.042,6)if face=='E'else d
   y=d if face in 'WE'else round(h-.042,6)if face=='N'else .042
   bitpins.append({'port':name,'face':face,'layer':layer,'x_um':x,'y_um':y})
   base=name.split('[')[0]
   if base not in faces[face]:faces[face].append(base)
 pins=OUT/f'{top}.tcl';pins.write_text('# Source-exact native candidate: M4W/E, M5N/S .012mod.048 tracks. Geometry adoption pending.\n'+''.join(f"place_pin -pin_name {{{p['port']}}} -layer {p['layer']} -location {{{p['x_um']:.6f} {p['y_um']:.6f}}} -force_to_die_boundary\n"for p in bitpins))
 (OUT/f'{top}.pins.json').write_text(json.dumps({'top':top,'outline_um':[w,h],'pins':bitpins},indent=2)+'\n')
 sources=['rtl/dsrom_sys/s81_ph/vm/'+n for n in (['dsfd_vm_static_fsr_bank8.sv','dsfd_vm_static_fsr_quartets.sv']if kind=='b'else['dsfd_vm_static_read_valid.sv','dsfd_vm_static_read_valid_quartets.sv']if kind=='v'else['dsfd_vm_static_read_leaf.sv','dsfd_vm_static_read_quartets.sv'])]
 script='native_fsr_leaf_gate.py'if kind=='b'else'native_read_leaf_gate.py'
 cmd=f'python3 tools/s81_vm/{script} '+(str(g)if kind=='b'else f'{kind} {g}')
 marker='NATIVE_FSR'if kind=='b'else'NATIVE_LEAF';label='mode0'if kind=='b'else f'{kind}{g}'
 benches=[]
 for mode in ['positive','mutant']:
  b={'name':f'{kind}{g}_{mode}','cmd':cmd+f' {mode} {{RUN}}/bench/{kind}{g}_{mode}','expect':'pass'if mode=='positive'else'fail','threads':1,'peak_ram_gb':1,'needs':['iverilog','python3']}
  b['pass_regex'if mode=='positive'else'fail_regex']=f'{marker} '+('PASS'if mode=='positive'else'FAIL')+f' {label} '
  if mode=='positive':b['min_count_regex']=r'banks(\d+)'if kind=='b'else r'checks (\d+)'
  benches.append(b)
 spec={'name':f'{top}_native_1015_r1','top':top,'kind':'tile','sources':sources,'clock_port':'ck','reset_ports':['rst_n'],'outline':{'w':w,'h':h,'exact':True},'pins':faces,'io_tcl':str(pins.relative_to(ROOT)),'macros':[],'route':{'pd':.4,'threads':8,'peak_ram_gb':16,'period_ps':770,'hold_margin_ns':.03},'recipe':2,'structural_change':'Actual independentlyclocked bounded leaf replaces scalar parent flop/mux ownership; exactstaticpipeline and fullfunctionalpins, no ready or inheritedview. Pinbound generous native shape avoids highface density; originalclock833.333 androute770 unchanged.','slot_change_request':{'contract':'S81 VM native read/FSR geometry candidate','version':'aa939e30d/2ca1a96e6/b18f5a9b0','why':'Actualindependentregistered roots andsource-exact signal pins; diegeometryreservation required beforeparentadoption'},'job':{'owner':'Codex:S_VM read native','branch':'codex/s81-read-router-1015','tag':'native1','extra_paths':['tools/s81_vm','rtl/dsrom_sys/s81_ph/vm','rtl/dsrom_sys/s81_ph/test','physical/s81_vm_read_native_1015'],'purpose':'Actualhardmaster ownpayload/control positiveoracle+observedmutant, nativeCTS/pin/reset beforeonevalidatedroute; wholeparentremainsunqualified.','benches':benches,'cycles_added':1 if kind!='b'else 0}}
 path=SPECS/f'{top}.json';path.write_text(json.dumps(spec,indent=2)+'\n')
 model['types'][top]={'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in sources},'signal_pins':len(bitpins),'outline_um':[w,h],'pin_face_counts':{f:sum(p['face']==f for p in bitpins)for f in faces},'RTL_FF_before_constant_optimization':choice.get('rtl_ff_before_constant_optimization',choice.get('rtl_ff_before_optimization')),'cycles_added':1 if kind!='b'else 0,'qualification':'UNQUALIFIED_PENDING_NATIVE_CTS_ROUTE_PG_PIN_IO_CLOCK'}
 subprocess.run(['python3',str(ROOT/'tools/ref_tile/ref_tile.py'),'gen',str(path)],cwd=ROOT,check=True)
(OUT/'model.json').write_text(json.dumps(model,indent=2)+'\n')
