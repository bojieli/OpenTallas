#!/usr/bin/env python3
"""Pinned structural m3 successor with M8 strip and current die IO contract."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import qwen_slab_structural_run as R
from uarch_model import qwen_slab_m3_closure_model
ROOT=Path(__file__).resolve().parents[1]
S='physical/qwen_slab_structural'
BENCH_SOURCES=['rtl/test/tb_qwen_slab_port_group.sv','rtl/physical/ot_qwen_slab_port_group.sv',
 'rtl/common/ot_meso_fifo.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv',
 'rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv',
 'rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/proto/ot_fp32_add_rne_pipe.sv']

def command(out,name,threads):
    a=SimpleNamespace(height=455.76,mul_lat=10,bw_m8=True,
      param=['OREG=1','MUL_KCP=4','IN_STAGE=1','AM_SPLIT=1','S5_CTL=1','SCALE_PAIR=1'],
      hold_margin_ns=.010,cores=threads,sdc='port_group_m3_m8_die_p770.sdc',io_hold_extra=80,
      diamond=True,cts_derate=.75,rom_lead=3,max_transition_ns=None,slew_margin_percent=30,
      td_only=True,orfs_var=['OT_IO_SKEW=90','OT_IO_HOLD_SKEW=50',
      'SYNTH_KEEP_MODULES=ot_qwen_slab_pg_oreg1 ot_hdc_mul_kcp48'],name=name)
    cmd=R.command(a,out)
    cmd[cmd.index('--clock-period-ns')+1]='0.770'
    mapping={'pre_cts.tcl':'pre_cts_skew_m3.tcl','post_plain.tcl':'post_plain_m3.tcl',
             'pre_ref.tcl':'pre_ref_skew_m3.tcl','pre_grt_bwm8.tcl':'pre_grt_m3_bwm8.tcl'}
    for i,v in enumerate(cmd):
        if '=' in v and v.split('=')[0].startswith(('PRE_','POST_')):
            for old,new in mapping.items():
                if v.endswith('/'+old): cmd[i]=v[:-len(old)]+new;break
    cmd+=['--step-tcl',f'PRE_RESIZE={S}/pre_resize_ioanchor.tcl']
    return cmd


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['model','bench','route'])
    p.add_argument('--out',type=Path);p.add_argument('--name');p.add_argument('--threads',type=int,default=16)
    p.add_argument('--negative',action='store_true');a=p.parse_args()
    if a.mode=='model':print(json.dumps(qwen_slab_m3_closure_model(),indent=2));return
    a.out.mkdir(parents=True,exist_ok=False)
    if a.mode=='bench':
        cmd=['iverilog','-g2012','-s','tb_qwen_slab_port_group','-o',str(a.out/'bench.vvp')]
        for kv in ['MUL_LAT=10','MUL_KCP=4','OREG=1','IN_STAGE=1','AM_SPLIT=1','S5_CTL=1','SCALE_PAIR=1',
                   'LEAD=8' if a.negative else 'LEAD=9']:
            cmd+=['-P','tb_qwen_slab_port_group.'+kv]
        cmd+=BENCH_SOURCES
        proc=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
        (a.out/'compile.log').write_text(proc.stdout+proc.stderr)
        if proc.returncode: raise SystemExit(proc.returncode)
        proc=subprocess.run(['vvp',str(a.out/'bench.vvp')],capture_output=True,text=True)
        (a.out/'run.log').write_text(proc.stdout+proc.stderr)
        pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in BENCH_SOURCES}
        (a.out/'result.json').write_text(json.dumps(dict(returncode=proc.returncode,negative=a.negative,source_pins=pins),indent=2)+'\n')
        print((proc.stdout+proc.stderr)[-1500:]);raise SystemExit(proc.returncode)
    cmd=command(a.out,a.name,a.threads)
    (a.out/'recipe.json').write_text(json.dumps(dict(argv=cmd,model=qwen_slab_m3_closure_model()),indent=2)+'\n')
    with (a.out/'flow.log').open('w') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
    (a.out/'flow.rc').write_text(str(rc)+'\n')
    if rc: raise SystemExit(rc)
    cmd=[sys.executable,'tools/w18/corner_sta.py','--orfs-dir',str(a.out/'work/orfs'),
         '--macro',R.MACRO,'--post-sdc',f'{S}/signoff833_die.sdc','--output',str(a.out/'corner_sta.json')]
    with (a.out/'corner.log').open('w') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
    (a.out/'corner.rc').write_text(str(rc)+'\n');raise SystemExit(rc)

if __name__=='__main__':main()
