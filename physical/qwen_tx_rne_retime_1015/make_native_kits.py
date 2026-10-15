#!/usr/bin/env python3
"""NEW RTL-changed masters, never overwrite existing packet masters."""
from pathlib import Path
import ast,json,hashlib,math,subprocess
R=Path(__file__).resolve().parents[2]
u=R/'tools/uarch_model.py';tree=ast.parse(u.read_text())
fun=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='qwen_native_head_packet_stage_model')
# Exact unified sizing function, isolated from unrelated optional imports.
ns={};exec(compile(ast.Module(body=[fun],type_ignores=[]),str(u),'exec'),ns)
model=ns['qwen_native_head_packet_stage_model']
template=json.loads(subprocess.check_output(['git','show','85b373696:physical/ref_tile/qkh_packet_v256/spec.json'],cwd=R,text=True))
def points(n):
 pool=[round(.012+.048*k,6)for k in range(math.ceil((5.4-.012)/.048),math.floor((59.4-.012)/.048)+1)]
 chosen=[]
 for i in range(n):
  allowed=[z for z in pool if not chosen or z>=chosen[-1]+.096-1e-9]
  chosen.append(min(allowed,key=lambda z:abs(z-(5.4+54*i/(n-1)))))
 assert chosen[-1]<=59.4
 return chosen
models=[]
for stage,widths,nout in [('r0',[('x',128),('wupper',128),('ctrl',6),('gm',4),('round',1)],207),('r1',[('d',207)],198)]:
 name='qwen_tx_rne_'+stage;kit=R/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
 ni=sum(n for _,n in widths);pin={};tcl=[];yy=iter(points(ni))
 for port,n in widths:
  pos=[[.096,next(yy)]for _ in range(n)];pin[port]={'layer':'M4','xy_um':pos}
  for i,(x,y)in enumerate(pos):
   bit=port if n==1 else f'{port}[{i}]'
   tcl.append(f'place_pin -pin_name {{{bit}}} -layer M4 -location {{{x:.6f} {y:.6f}}}')
 pin['q']={'layer':'M4','xy_um':[[15.024,y]for y in points(nout)]}
 for i,(x,y)in enumerate(pin['q']['xy_um']):tcl.append(f'place_pin -pin_name {{q[{i}]}} -layer M4 -location {{{x:.6f} {y:.6f}}}')
 for port,layer,xy in [('clk','M4',[.096,1.308]),('rst_n','M5',[9.708,.096])]:
  pin[port]={'layer':layer,'xy_um':[xy]};tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{xy[0]:.6f} {xy[1]:.6f}}}')
 # PG3 M5 stripe centers after2.16core shift. M4 edge pins are below PG.
 centers=[2.46+2.7*j+d for j in range(5)for d in [0,.192]]
 assert min(abs(9.708-z)for z in centers)>.12
 for v in pin.values():
  for x,y in v['xy_um']:
   z=y if v['layer']=='M4'else x
   assert abs((z-.012)/.048-round((z-.012)/.048))<1e-6
 (kit/'assigned_pins.tcl').write_text('\n'.join(tcl)+'\n')
 (kit/'assigned_pins.json').write_text(json.dumps(dict(schema='opentallas.tx-rne-native-pins.v1',name=name,outline_um=[15.12,64.8],input_bits=ni,output_bits=nout,positions=pin,pg_rule='PG3M5 pitch2.7,width.12,pairspacing.072,offset.300,coremargin2.16; W/E M4pins belowM5; SresetM5 avoids PG; routing-axiscenters .012+.048k; data pitch>=.096'),indent=2)+'\n')
 s=json.loads(json.dumps(template));s.update(name=name,top=name,params={},sources=['rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rne.sv','rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv','rtl/lib/ot_rst_relay.sv'],io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',pins={'W':[p for p,_ in widths]+['clk'],'E':['q'],'S':['rst_n']},pin_ranges={p:[v['xy_um'][0][1],v['xy_um'][-1][1]]for p,v in pin.items()if p not in ['clk','rst_n']})
 s['io_flop_at_pins']={'cols':4}
 s['structural_change']='NEW RTL-changed standalone existing-two-edge TX master: '+('R0 exact low16RNEcarry then207real kept data bits'if stage=='r0'else'R1 exact modulo16increment/mask then198real kept data bits')+'. Not a CLOSEDmaster reroute; parent unintegrated. Packetpipe reset3 retained. Actual native timing and recipe2 posthook area unmeasured; no waiver.'
 s['job'].update(owner='Codex:q_compute_elements',branch='codex/q-parent-prune-1015',tag='rne1',purpose='Standalone proven TX RNE native candidate; parent unqualified',extra_paths=['physical/qwen_tx_rne_retime_1015','results/rtl/qwen_compute_native_glue_1014/tx_rne207_1015'],views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}',cycles_added=0,hold_merge='Standalone leaf only; parent integration and wholeparent proof pending',benches=[])
 for mut in range(7):
  b=dict(name=f'rne207to198_m{mut}',cmd=f'bash physical/qwen_tx_rne_retime_1015/bench_one.sh {{RUN}}/bench/rne_m{mut} {mut}',expect='pass'if mut==0 else'fail',threads=1,peak_ram_gb=1,needs=['iverilog'])
  b['pass_regex'if mut==0 else'fail_regex']='PASS RNE207to198'if mut==0 else'FAIL RNE';s['job']['benches'].append(b)
 s['job']['benches'].append(dict(name='source_exact_formal_receipt',cmd='python3 physical/qwen_tx_rne_retime_1015/verify_receipt.py',expect='pass',threads=1,peak_ram_gb=1,needs=['python3'],pass_regex='PASS standalone RNE207to198 receipt'))
 spec=R/'tools/ref_tile/specs_q_compute_native'/(name+'.json');spec.write_text(json.dumps(s,indent=2)+'\n')
 m=model(nout,1,'V');m.update(schema='opentallas.qwen_tx_rne_native_stage.v1',core_area_um2=(15.12-4.32)*(64.8-4.32),max_mapped_area_for_65pct_util_um2=.65*(15.12-4.32)*(64.8-4.32),mux_demux_cost=('four low16 carry predicates; no packet mux' if stage=='r0' else 'four modulo16 conditional increments and64 mask gates; no packet mux'),latency_price='one existing TX capture edge per master; two edges total, zero added compiler edges',face_payload_um=max(ni,nout)*.096,estimated_worst_cut_tracks=ni+nout,estimated_cut_ratio=(ni+nout)/m['estimated_available_cut_tracks']);m.update(name=name,input_bits_per_cycle=ni,output_bits_per_cycle=nout,arithmetic='4 exact low16carry predicates'if stage=='r0'else'4 modulo16 conditionalincrements and4masks',role='existing TX'+stage[-1]+' capture',extra_compiler_edges=0,native_mapped_area_um2=None,physical_qualification='OPEN; no route submitted',model_source_sha256=hashlib.sha256(u.read_bytes()).hexdigest());models.append(m)
 subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(spec.relative_to(R))],cwd=R,check=True)
measured_path=R/'results/rtl/qwen_compute_native_glue_1014/tx_rne207_1015/native_smoke/receipt.json'
if measured_path.exists():
 measured=json.loads(measured_path.read_text())
 if measured['rtl_sha256']==hashlib.sha256((R/'rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rne.sv').read_bytes()).hexdigest():
  for m,item in zip(models,measured['masters']):
   assert m['name']==item['name']
   m.update(native_mapped_area_um2=item['mapped_synth_area_um2'],native_mapped_area_scope='synth only before full recipe2 boundary hooks',mapped_ff_count=item['data_and_reset_ff'],full_boundary_hook_area_um2=None)
(R/'physical/qwen_tx_rne_retime_1015/native_model.json').write_text(json.dumps(dict(schema='opentallas.tx-rne-two-existing-edge.v1',masters=models,data_capture_edges=2,extra_compiler_edges=0,packets_per_cycle=1,total_register_bits=sum(m['register_bits']for m in models),memory_macros=0,macs_per_cycle=0,adoption='standalone only; wholeparent proof and actual perbit native composition pending',**({'measured_receipt':str(measured_path.relative_to(R))}if measured_path.exists()else{})),indent=2)+'\n')
