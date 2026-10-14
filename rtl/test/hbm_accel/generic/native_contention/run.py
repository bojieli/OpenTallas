#!/usr/bin/env python3
"""Freeze actual producer/common/parent blobs, compile and run the combined fixture.
Use through ot-run --mem 32 --threads 4; immutable prices are never rewritten.
"""
import argparse,hashlib,json,os,pathlib,subprocess,sys,re
ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--phase',type=int,default=61);ap.add_argument('--mut',type=int,default=0);ap.add_argument('--parent',default='ba12d099a');ap.add_argument('--front12',action='store_true');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--lint-only',action='store_true');ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[5];out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
parent=a.parent;common='64fced1f9';quant='88b62f789';dma='552786d9c' if a.front12 else '4a49c18bc';vectors='7027d3ab1'
graph={}
def add(commit,prefix,names):
 for name in names.split():graph[f'{prefix}/{name}.sv']=commit
p='rtl/hbm_accel/generic/peers';q='rtl/hbm_accel/generic/adapters/native_b2/su_quadrant';qw='rtl/hbm_accel/generic/qw'
if a.front12:add(dma,p,'ot_hgi_dma_front ot_hgi_dma_front_core12 ot_hgi_dma_front_ctrl11 ot_hgi_dma_front_main11 ot_hgi_dma_front_lane12 ot_hgi_dma_front_xs_vm3 ot_hgi_dma_front_xsw12 ot_hgi_dma_ixpipe ot_hgi_dma_vm_queue ot_hgi_dma_vm_router9 ot_hgi_dma_vm_bank9 ot_hgi_dma_vm_transport9')
else:add(dma,p,'ot_hgi_dma_front ot_hgi_dma_front_core6b ot_hgi_dma_front_ctrl6b ot_hgi_dma_front_lane2 ot_hgi_dma_front_xs_vm2 ot_hgi_dma_front_xsw6b ot_hgi_dma_ixpipe ot_hgi_dma_vm_queue ot_hgi_dma_vm_router ot_hgi_dma_vm_transport')
add(parent,q,'ot_hgi_su_ctlw_native_q ot_hgi_su_ctlw_native_lane2 ot_hgi_su_ctlw_native_h ot_hbm_b2_lane_cdc_owned ot_hbm_b2_peer_lease_owned ot_hbm_b2_peer_mux_q ot_hbm_b2_native_owned4')
add(common,q,'ot_hbm_b2_lane_cdc ot_hbm_b2_su_vm4')
if parent!='0ec722402':add(parent,q,'ot_hbm_b2_mirror_commit ot_hbm_b2_su_vm4_mirror')
if parent not in ['0ec722402','a76c2fede']:add(parent,q,'ot_hbm_b2_peer_mux_lane')
add(common,'rtl/hbm_accel/generic/vm/b2','ot_vms_bank ot_vms_hub ot_vms_rstop ot_vms_rcl ot_vms_star ot_vms_relay ot_vms_slice')
add(common,'rtl/hbm_accel/service','ot_hbm_accel_cdc_fifo_p2')
add(parent,qw,'ot_hgi_qdq_native_peer4_owned')
add(quant,qw,'ot_hgi_qw_dec ot_hgi_qw_dec3 ot_hgi_qdq_lq ot_hgi_qdq_fr ot_hgi_qdq_fr_one_s2 ot_hgi_qdq_fr_retire ot_hgi_qdq_fr_mix ot_hgi_qdq_core ot_hgi_qdq_asm ot_hgi_qdq_wr ot_hgi_qdq_q ot_hgi_qdq_q_pin4')
add(quant,'rtl/hdc','ot_hdc_delay ot_hdc_fpu ot_hdc_fp32_mul_pipe ot_hdc_sfu ot_hdc_fastfp ot_hdc_fastfp_lat_f12 ot_hdc_fp32_f12 ot_hdc_prefix')
add(quant,'rtl/hbm_accel/generic','ot_hgi_fp4qdq ot_hgi_quant_decode ot_hgi_quant_record')
add(quant,'rtl/lib','ot_rst_relay');add(quant,'rtl/link','ot_fifo_sram_fwft')
add(quant,'physical/hbm_accel_die_views/common','ot_hfd_oreg1');add(quant,'physical/hbm_accel_die_views/quant/rtl','ot_hfd_actquant_m')
for macro in ['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_64x16_m1','ot_sram_1r1w_64x512_m1_r2c2','ot_sram_1r1w_1024x256_m2_r2c2']:
 graph[f'physical/asap7_memory_macros/{macro}/{macro}.v']=parent
# Resolve the actual source39 q10's module dependencies from that immutable tree.
# Existing shared front/memory modules remain explicitly pinned above; no obsolete
# monolithic or native-two-ticket prototype is substituted for the production core.
core='39f276214'
module_files={};core_text={}
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',core,'rtl/hbm_accel/generic/peers','rtl/hbm_accel/generic/adapters','rtl/lib'],cwd=root,text=True).splitlines()
for path in paths:
 if not path.endswith('.sv'):continue
 data=subprocess.check_output(['git','show',f'{core}:{path}'],cwd=root).decode()
 core_text[path]=data
 for symbol in re.findall(r'\bmodule\s+(ot_\w+)',data):module_files[symbol]=path
walk=[f'{p}/ot_hgi_b2_dma_q.sv'];visited=set()
while walk:
 path=walk.pop()
 if path in visited:continue
 visited.add(path)
 if path not in graph:graph[path]=core
 text=re.sub(r'/\*.*?\*/|//[^\n]*','',core_text[path],flags=re.S)
 for symbol in re.findall(r'\bot_\w+\b',text):
  dependency=module_files.get(symbol)
  if dependency and dependency not in visited:walk.append(dependency)
for macro in ['ot_sram_1r1w_256x256_m2_r2c2']:
 graph[f'physical/asap7_memory_macros/{macro}/{macro}.v']=core
receipt=[];sources=[]
def freeze(path,commit,data):
 target=out/'src'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 receipt.append({'path':path,'source_commit':commit,'sha256':hashlib.sha256(data).hexdigest()});return str(target)
for path,commit in graph.items():
 data=subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=root);sources.append(freeze(path,commit,data))
bench=pathlib.Path(__file__).resolve().parent
sources.append(freeze(f'{p}/ot_hgi_dma_native_read_owned.sv','fixture-worktree',(root/p/'ot_hgi_dma_native_read_owned.sv').read_bytes()))
for name in ['ot_native_quant_stimulus.sv','ot_native_dma_core_stimulus.sv','tb_hbm_native_threeproducer.sv']:
 path=str((bench/name).relative_to(root));sources.append(freeze(path,'fixture-worktree', (bench/name).read_bytes()))
vecdir=out/'vectors';vecdir.mkdir(exist_ok=True)
for name in ['recs.txt','meta.json']+[f'{kind}_{k}.hex' for kind in ['in','out'] for k in range(8)]:
 path=f'results/rtl/ref_tile/qdq_native_peer4/vectors/{name}';data=subprocess.check_output(['git','show',f'{vectors}:{path}'],cwd=root)
 (vecdir/name).write_bytes(data);receipt.append({'path':'vectors/'+name,'source_commit':vectors,'sha256':hashlib.sha256(data).hexdigest()})
(out/'sourcegraph.json').write_text(json.dumps({'parent':parent,'common':common,'quant':quant,'dma_front':dma,'front12':a.front12,'DMA_read_core':core,'vectors':vectors,'phase':a.phase,'mut':a.mut,'clocks_ps':{'engine':833.33325,'VM':1111.111},'physical_clock_delivery_and_reset_phase_qualification':'OPEN: explicit nominal clock/global reset bindings only', 'hard_clock_ports':{'station':32,'VM_NC':4,'VM_children':52,'relay':24,'CDC_source':96,'CDC_VM':96,'commit':32,'DMA_bridge':64,'DMA_producer':10},'immutable_prices':{'quant_per_quarter':168,'DMA147':15674.320143998484},'scope':'actual SU native_h stage/drain; actual quant qpin4; actual DMAfront DQ; actual source39 q10 STORE/FENCE on32-reservation native read bridge, all4 held R owners; fullSUarithmetic/productionDMAcore workload/physical bridge qualification not proven','files':receipt},indent=2)+'\n')
frozen_runner = r'''#!/usr/bin/env python3
import json,pathlib,os,subprocess,sys,hashlib
out=pathlib.Path(__file__).resolve().parent
meta=json.loads((out/'sourcegraph.json').read_text())
for entry in meta['files']:
 path=out/entry['path'] if entry['path'].startswith('vectors/') else out/'src'/entry['path']
 if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise SystemExit(f"frozen source mismatch {entry['path']}")
v=os.environ.get('VERILATOR',str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
src=[str(out/'src'/f['path']) for f in meta['files'] if not f['path'].startswith('vectors/')]
cmd=[v,'--lint-only' if '--lint-only' in sys.argv else '--binary','--timing','-O2','-CFLAGS','-O0','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_hbm_native_threeproducer',f"-GMUT={meta['mut']}",f"-GPHASE={meta['phase']}",'--Mdir',str(out/'obj'),'-o','sim']+(['+define+FRONT12'] if meta.get('front12',False) else [])+src
(out/'build-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'build.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
if rc:print((out/'build.log').read_text()[-7000:]);sys.exit(rc)
if '--lint-only' in sys.argv:sys.exit(0)
runtime=[str(out/'obj'/'sim'),'+FULL',f'+QDIR={out/"vectors"}']+(['+SMOKE'] if '--smoke' in sys.argv else [])
(out/'runtime-command.json').write_text(json.dumps(runtime,indent=2)+'\n')
with (out/'run.log').open('w') as f:rc=subprocess.call(runtime,stdout=f,stderr=subprocess.STDOUT)
print((out/'run.log').read_text()[-7000:]);sys.exit(rc)
'''
(out/'run_frozen.py').write_text(frozen_runner)
if a.prepare_only:sys.exit(0)
v=os.environ.get('VERILATOR',str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
cmd=[v,'--lint-only' if a.lint_only else '--binary','--timing','-O2','-CFLAGS','-O0','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_hbm_native_threeproducer',f'-GMUT={a.mut}',f'-GPHASE={a.phase}','--Mdir',str(out/'obj'),'-o','sim']+(['+define+FRONT12'] if a.front12 else [])+sources
(out/'build-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'build.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
if rc:print((out/'build.log').read_text()[-7000:]);sys.exit(rc)
if a.lint_only:sys.exit(0)
runtime=[str(out/'obj'/'sim'),'+FULL',f'+QDIR={vecdir}']+(['+SMOKE'] if a.smoke else [])
(out/'runtime-command.json').write_text(json.dumps(runtime,indent=2)+'\n')
with (out/'run.log').open('w') as f:rc=subprocess.call(runtime,stdout=f,stderr=subprocess.STDOUT)
print((out/'run.log').read_text()[-7000:]);sys.exit(rc)
