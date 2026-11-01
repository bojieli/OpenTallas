#!/usr/bin/env python3
"""Prepare genuine STACK0 body-DMA transport probes; run generated script via ot-run.

No source rebasing, production target allocation, numeric layer or G5 claim.
The two-pilot vehicle and grouped volume preserve every selected native227.
"""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
SPLIT='rtl/hbm_accel/loader/service_native/split/'
FILES=[SPLIT+n+'.sv' for n in ['ot_hbm_static_load_stack0_service','ot_hbm_static_load_addr_counter','ot_hbm_static_load_addr_map','ot_hbm_static_load_quad_vehicle','ot_hbm_static_load_provider_quad','ot_hbm_static_load_vm_dq_demux','ot_hbm_svc_vmdel_lane_load_static']]
FILES += ['physical/asap7_memory_macros/'+n+'/'+n+'.v' for n in ['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_1024x256_m2_r2c2']]
FILES += ['rtl/hbm_accel/generic/vm/static/faces_q0/'+n+'.sv' for n in ['hfd_vms_bank_native_q0_faces','ot_vms_bank_q0_faces_core','ot_vms_bank_q0_faces_body']]
FILES += ['rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv']
FILES += ['rtl/hbm_accel/loader/service_native/'+n+'.sv' for n in ['ot_hbm_svc_vm_kshare_splitstrap','ot_hbm_svc_pc_ctrl_leaf_cfg_h9b','ot_hbm_pc_refresh_cfg','ot_hbm_svc_async_fifo','ot_hbm_svc_ring_h9b','ot_hbm_svc_ring_h9b_ff','ot_hbm_svc_pc_ctrl_leaf','ot_hbm_svc_pin_skid2_h9']]
FILES += ['rtl/lib/ot_reset_sync.sv','rtl/lib/ot_rst_relay.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv']
ROLE=['physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/vm/static/'+n+'.sv' for n in ['hfd_hgi_vm_calendar_f20_role','ot_static_program_target','ot_vms_calendar_static_xcap']]

def git(repo,rev,path):return subprocess.check_output(['git','-C',str(repo),'show',rev+':'+path])
def prepare(repo,body,out,mode):
 if out.exists():raise ValueError('New output directory required; preserve old verdicts')
 out.mkdir(parents=True);src=out/'sources';src.mkdir();manifest={};selected=[]
 for rev,paths in [('24de429cd',FILES),('8c5f35a6f',ROLE),('8f448a371',['rtl/test/hbm_layer/ot_hbm3e_phy_rc_e8p5_dram_model.sv'])]:
  for path in paths:
   raw=git(repo,rev,path);dest=src/Path(path).name;dest.write_bytes(raw);selected.append(dest);manifest[path]={'revision':rev,'sha256':hashlib.sha256(raw).hexdigest()}
 tb=Path(__file__).with_name('tb_stack0_body_provider.sv');(src/tb.name).write_bytes(tb.read_bytes());selected.append(src/tb.name)
 (out/'profile.py').write_bytes(git(repo,'24de429cd','tools/hbm_timing_833_profile.py'))
 for half in (0,1):subprocess.run(['python3',str(out/'profile.py'),'--first-pc',str(half*16),'--npc','16','--boot-row-out',str(out/f'timing_boot_{"lo" if half==0 else "hi"}.mem')],check=True,stdout=subprocess.DEVNULL)
 data=json.loads(body.read_text());runs=data['runs']
 if mode=='pilot':runs=runs[:2]
 else:
  groups=collections.OrderedDict()
  for r in runs:groups.setdefault((r['row'],r['col'],r['half']),[]).append(r)
  runs=[g[0]for g in groups.values()]if mode=='canary' else[r for g in groups.values()for r in g]
 desc=[];steps=[];ends=[];windows=[];expected=[];words=0
 for r in runs:
  assert r['stack']==0 and r['row']==16384 and r['format']in('FP32','U32'),r
  raw=int(r['effective227'],16);assert (raw>>186)&((1<<20)-1)==1
  desc.append(raw);windows.append((r['row']<<5)|(r['col']<<1)|r['half']);remaining=r['n'];sa=r['source_byte'];da=r['destination_word'];count=0
  while remaining:
   n=min(8-((sa&31)//4),8-(da&7),remaining);payload=0;mask=0
   for w in range(n):
    value=0x3f800000+((sa-0x400000000)//4)+w;lane=(da&7)+w;payload|=value<<(lane*32);mask|=1<<lane
   expected.append((1<<280)|((da>>3)<<264)|(payload<<8)|mask);count+=1;words+=n;remaining-=n;sa+=4*n;da+=n
  steps.append(count);ends.append(len(expected))
 def mem(name,values,digits):(out/name).write_text(''.join(f'{v:0{digits}x}\n'for v in values))
 mem('body_desc.mem',desc,57);mem('windows.mem',windows,5);mem('steps.mem',steps,8);mem('packet_ends.mem',ends,8);mem('expected.mem',expected,71)
 image=out/'images';image.mkdir()
 with(image/'stack0.hex').open('w')as f:
  for sector in range(0x20000000,0x20008000):
   value=sum((0x3f800000+(sector-0x20000000)*8+w)<<(w*32)for w in range(8));f.write(f'{sector:08x} {value:064x}\n')
 # All command source addresses remain the original stack0 addresses.
 (out/'source_runs.json').write_text(json.dumps(runs,indent=1)+'\n');(out/'sources.json').write_text(json.dumps(manifest,indent=1)+'\n')
 (out/'files.f').write_text('\n'.join('sources/'+p.name for p in selected)+'\n')
 run=f'''#!/bin/bash
set -euo pipefail
ulimit -c 0
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -j 2 --output-split 10000 -Wno-fatal --top-module tb_stack0_body_provider -GND={len(runs)} -GNP={len(expected)} -GNW={words} -Mdir obj -f files.f > build.log 2>&1
./obj/Vtb_stack0_body_provider +HBM_IMG_DIR="$PWD/images" > positive.log 2>&1
grep 'S0_BODY_PROVIDER PASS' positive.log
if ./obj/Vtb_stack0_body_provider +HBM_IMG_DIR="$PWD/images" +MUT_EPOCH=1 > mutant_epoch.log 2>&1;then echo 'MUTANT ESCAPED';exit 2;fi
grep 'S0_PROBE_FAULT' mutant_epoch.log
'''
 (out/'run.sh').write_text(run);(out/'run.sh').chmod(0o755)
 meta={'scope':'Real SOURCE0 body DMA transport only; not arithmetic/full G5 or production schedule adoption','mode':mode,'descriptors':len(runs),'packets':len(expected),'words':words,'windows':len(set(windows)),'source_stack':0,'source_aliases':False,'clock_ps':833,'external_read_edges':29,'fixture_refresh_straps':[127,126],'production_target_allocation':False,'grouped_window_order':mode!='pilot','source_sha256':hashlib.sha256(body.read_bytes()).hexdigest()}
 (out/'spec.json').write_text(json.dumps(meta,indent=1)+'\n');print(json.dumps(meta))
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--body-plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=['pilot','canary','volume'],default='pilot');a=ap.parse_args();prepare(a.repo,a.body_plan,a.out,a.mode)
