#!/usr/bin/env python3
"""Actual HOST leaf composition: fixed ingress slots, source-exact IKEY and boot.

External HBM storage/ACKs and expected numerical images are test models. Every
on-chip packet/FIFO/arithmetic/decoder result comes from actual source RTL.
Scope is initialization/off-chip ingress; normal-token compiler reservations,
physical pin/clock timing and die/full-token throughput remain OPEN.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import rtl_rom_host_ingest_bench as B
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
SRC=['rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv','rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv','physical/rom_host_ingest/rtl/dsfd_host.sv','rtl/hdc/ingest/ot_rom_host_ingest.sv','rtl/link/ot_link_afifo.sv','rtl/hdc/ingest/ot_hdc_kv_ingest.sv','rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd_sliced.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv']
DEFS=['-DDSFD_HOST_C_STATIC','-DDSFD_HOST_PQ_BOOT','-DOT_S81_HOST_PHASESAFE','-DOT_S81_HOST_BOOT300']
c=B.C.case_ikey(np.random.default_rng(20261016),1024);c['nb']=B.stream_nb(c['descs']);B.write_case(a.out,c,65536)
words=[(0,0)];pi=0
for desc,nb in zip(c['descs'],c['nb']):
    words.append((1,int(desc)))
    for _ in range(nb):words.append((2,int(c['beats'][pi])));pi+=1
(a.out/'packets.mem').write_text(''.join(f'{(cls<<513)|(word<<1)|1:0129x}\n' for cls,word in words))
records=[]
def build(top,tb,mut,name):
    exe=a.out/(name+'.vvp')
    cmd=['iverilog','-g2012','-s',top,f'-P{top}.MUT={mut}',*DEFS,'-o',str(exe),str(tb),*[str(ROOT/x) for x in SRC]]
    cp=subprocess.run(cmd,capture_output=True,text=True)
    (a.out/(name+'.build.log')).write_text(cp.stdout+cp.stderr)
    if cp.returncode:raise SystemExit('HOST_C_SLICED BUILD_FAIL '+name+' '+cp.stderr[-1000:])
    return exe
def run(exe,name,args,expect,marker):
    cp=subprocess.run(['vvp','-n',str(exe),*args],cwd=a.out,capture_output=True,text=True,timeout=300)
    output=cp.stdout+cp.stderr;(a.out/(name+'.log')).write_text(output)
    if (cp.returncode==0)!=expect or marker not in output:raise SystemExit('HOST_C_SLICED UNEXPECTED '+name+' '+output[-1500:])
    records.append(dict(case=name,returncode=cp.returncode,marker=marker))
    print(name,output.strip().splitlines()[-1],flush=True)
for mut in [0,6]:
    name=f'native_m{mut}';exe=build('tb_host_c_sliced_native',ROOT/'tests/s81/tb_host_c_sliced_native.sv',mut,name)
    run(exe,name,[f'+NP={len(words)}'],mut==0,'HOST_SLICED_NATIVE PASS' if mut==0 else 'HOST_SLICED_NATIVE FAIL exact producer/calendar')
# Reuse the exact legacy boundary transport vectors, with actual new clock
# entry pins bound to their ideal source-family phase. This is not timing proof.
boot=(ROOT/'tests/s81/tb_host_boot300.sv').read_text().replace('module tb_host_boot300;', 'module tb_host_boot300_sliced;').replace('dsfd_host_c #','dsfd_host_c_sliced #').replace('.ck(ck),.ckv(ckv)', '.ck(ck),.ck_data({4{ck}}),.ck_native(ck),.ck_launch(ck),.ck_return(ck),.ckv(ckv)')
tb=a.out/'boot_sliced.sv';tb.write_text(boot)
exe=build('tb_host_boot300_sliced',tb,0,'boot0')
for phase in range(8):run(exe,f'boot_phase{phase}',[f'+serial_phase={phase}'],True,'BOOT300 PASS')
for name,arg in [('stop','+stop_boot=1'),('capacity','+overload=1')]:run(exe,'boot_'+name,[arg],True,'BOOT300 FAIL_EXPECTED')
exe=build('tb_host_boot300_sliced',tb,5,'boot_kind_mutant')
run(exe,'boot_kind_mutant',[],False,'BOOT300 FAIL payload/kind')
rec=dict(scope=__doc__,generator_source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in ['tools/rtl_rom_host_ingest_bench.py','tools/rtl_hdc_kv_ingest_campaign.py','tools/kv_ingest_ref.py','tools/s81_static_control/host_c_sliced_gate.py']},input_image_sha256={x:hashlib.sha256((a.out/x).read_bytes()).hexdigest() for x in ['packets.mem','init.mem','exp.mem']},source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in SRC+['tests/s81/tb_host_c_sliced_native.sv','tests/s81/tb_host_boot300.sv']},input_slots=dict(first=128,stride=32,packets=len(words),final_verification_edge=60000),normal_token_reservation='OPEN: queue-nonempty service is not a compiled execution calendar',diagnostic_delta=dict(native_fault_host_edges=1,payload_ack_service_edges=0),cases=records)
(a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
print('HOST_C_SLICED_GATE PASS actual IKEY544sectors/full256 exact59989edges + badpayload mutant + boot8phases/kind/missingclock/capacity')
