#!/usr/bin/env python3
"""Run the genuine provider mechanism fixture in an owned scratch output.

Run through ot-run. Provider sources must be the binder's reviewed candidate,
not a behavioral replacement. No production address map or calendar is changed.
"""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--provider-dir',type=Path);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
canonical=REPO/'rtl/hbm_accel/loader/service_native/split'
if a.provider_dir is None:a.provider_dir=canonical if(canonical/'ot_hbm_static_load_provider_quad.sv').is_file()else REPO/'results/hbm_bind_1030/static_load'
subprocess.run([sys.executable,str(HERE/'gen_fixture.py'),'--out',str(out)],check=True)
names=['ot_hbm_static_load_vm_commit_guard.sv','ot_hbm_static_load_vm_dq_demux.sv','ot_hbm_static_load_cp_provider_quad.sv','ot_hbm_static_load_provider_quad.sv','ot_hbm_static_load_addr_counter.sv','ot_hbm_static_load_addr_map.sv','ot_hbm_static_load_quad_vehicle.sv']
from dependency_guard import require_sources
manifest_name='phy_source_dependencies.json'
if(a.provider_dir.resolve()/'ot_hbm_static_load_cmd_provider_quad.sv').is_file():
 names.append('ot_hbm_static_load_cmd_provider_quad.sv');manifest_name='phy_shared_source_dependencies.json'
require_sources(REPO,a.provider_dir.resolve(),names,manifest_name)
sources=[a.provider_dir.resolve()/x for x in names]+[HERE/'tb_phy_provider.sv',REPO/'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_cp_collar.sv',REPO/'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv',REPO/'rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_load_static.sv',REPO/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
sources += [REPO/'rtl/hbm_accel/generic/vm/static/faces_q0/hfd_vms_bank_native_q0_faces.sv',REPO/'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_core.sv',REPO/'rtl/hbm_accel/generic/vm/static/faces_q0/ot_vms_bank_q0_faces_body.sv',REPO/'rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv',REPO/'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
sources += [REPO/x for x in ['rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare_splitstrap.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_pc_refresh_cfg.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_h9b.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_h9b_ff.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv', 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_pin_skid2_h9.sv', 'rtl/lib/ot_reset_sync.sv', 'rtl/lib/ot_rst_relay.sv', 'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv']]
if any(not p.is_file()for p in sources):raise FileNotFoundError('provider/source dependency missing: '+','.join(str(p)for p in sources if not p.is_file()))
with(out/'build.log').open('w')as f:subprocess.run(['verilator','--binary','--timing','-j','8','--output-split','10000','-Wno-fatal','--top-module','tb_phy_provider',*map(str,sources),'--Mdir',str(out/'obj')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
result=[]
for name,arg in [('baseline',None),('wrong_bank','MUT_BANK')]:
 cp=subprocess.run([str(out/'obj/Vtb_phy_provider')]+(['+'+arg+'=1']if arg else[]),cwd=out,capture_output=True,text=True);log=cp.stdout+cp.stderr;(out/(name+'.log')).write_text(log)
 if arg:assert cp.returncode!=0 and'VM_PROVIDER_FAULT'in log,log
 else:assert cp.returncode==0 and'PASS NATIVE_PHY_VM_CP_PROVIDER'in log,log
 result.append(dict(name=name,returncode=cp.returncode,last_lines=log.splitlines()[-3:]))
(out/'phy_run.json').write_text(json.dumps(dict(status='PASS_SOURCE_MECHANISM_ONLY',runs=result),indent=1)+'\n');print(json.dumps(result))
