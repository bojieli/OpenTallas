#!/usr/bin/env python3
"""Source-qualified local collector clear regression; not epoch admission."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
from w17_ckv_collector_clear_counterexample import ROOT,PIN,SOURCES,BENCH
COMP='rtl/w17_runtime/chip/ckv_count_clear/ot_chip_v41x_ckv_die_service.sv'
def run(out):
 assert not out.exists()
 cases=[];pins={}
 with tempfile.TemporaryDirectory(prefix='w17-clear-gate-',dir='/home/ubuntu') as tmp:
  d=pathlib.Path(tmp); common=[]
  for i,p in enumerate(SOURCES):
   raw=subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT);pins[p]=hashlib.sha256(raw).hexdigest();f=d/f's{i}.sv';f.write_bytes(raw)
   if i:common.append(str(f))
  for name,enable,collision,full in [('original',None,False,False),('default_off',0,False,False),('clear_one',1,False,False),('clear_512',1,False,True),('reject_same_edge',1,True,False),('reset',1,False,False),('mutant_clear_disabled',1,False,False)]:
   b=BENCH
   if enable is not None:b=b.replace('.K(512),.NSLOT(64)',f'.K(512),.NSLOT(64),.COLLECTOR_CLEAR_PRIORITY({enable})')
   if full:
    b=b.replace('10\'d16}),.ag_rx_gid({21\'d0,21\'d0,21\'d16})',"10'(cyc-200)}),.ag_rx_gid({21'd0,21'd0,21'(cyc-200)})")
    b=b.replace('cyc==210','cyc==720').replace("rx=(cyc==200)?3'b001:0;","rx=(cyc>=200&&cyc<712)?3'b001:0;")
    start=b.index(' if(cyc==202)');end=b.index(' if(cyc==212)',start)
    b=b[:start]+" if(cyc==715 && (fault!==1'b0||dut.npresent!==11'd512||dut.present!=={512{1'b1}}))$fatal(1,\"full collector not captured\");\n"+b[end:]
    b=b.replace('cyc==212','cyc==722').replace('cyc==300','cyc==800')
   if collision:b=b.replace("rx=(cyc==200)?3'b001:0;","rx=(cyc==200||cyc==210)?3'b001:0;")
   if name=='reset':b=b.replace('sel=(cyc==7||cyc==210);','sel=(cyc==7);if(cyc==210)rst_n=0;if(cyc==211)rst_n=1;')
   if enable==1:
    expected_fault="1'b1" if collision else "1'b0"
    b=b.replace("fault!==1'b0||dut.present!==512'd0||dut.npresent!==11'd1",f"fault!=={expected_fault}||dut.present!==512'd0||dut.npresent!==11'd0||dut.st_rows_remote!==32'd0"+("||fc[2]!==1'b1" if collision else ''))
    b=b.replace('REPRODUCED_CLEAR_FAILURE old_count=1 new_present=0 new_count=1 expected_new_count=0','LOCAL_CLEAR_PASS '+name)
   src=str(d/'s0.sv') if enable is None else str(ROOT/COMP)
   if name=='mutant_clear_disabled':
    m=d/'mutant.sv';m.write_text((ROOT/COMP).read_text().replace('if (COLLECTOR_CLEAR_PRIORITY && sel_v && !rd_act)', 'if (1\'b0 && sel_v && !rd_act)'));src=str(m)
   tb=d/'tb.sv';tb.write_text(b);exe=d/'gate'
   c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(tb),src,*common],capture_output=True,text=True,timeout=30)
   v=subprocess.run(['vvp',str(exe)],capture_output=True,text=True,timeout=30) if c.returncode==0 else c
   marker='REPRODUCED_CLEAR_FAILURE' if enable in (None,0) else 'LOCAL_CLEAR_PASS '+name
   ok=c.returncode==0 and v.returncode==0 and marker in v.stdout
   if name=='mutant_clear_disabled':ok=c.returncode==0 and v.returncode==1 and 'unexpected collector reset outcome' in v.stdout
   cases.append(dict(case=name,pass_gate=ok,compile_returncode=c.returncode,run_returncode=v.returncode,log=v.stdout+v.stderr,bench_sha256=hashlib.sha256(b.encode()).hexdigest()))
 r=dict(status='PASS_LOCAL_CONTROL' if all(x['pass_gate'] for x in cases) else 'FAIL_LOCAL_CONTROL',source_commit=PIN,source_sha256=pins,companion_path=COMP,companion_sha256=hashlib.sha256((ROOT/COMP).read_bytes()).hexdigest(),cases=cases,scope='Actual K512/NSLOT64 seven-module interface regression. Full512 synthetic peer arrivals stress collector control only, not real peer generation/transport or safe epoch transition. Original/default-off failure retained. No force, no numerical or connected token claim.',hardware_admission=False,model_commit='5d8931239',original_failure_commit='ef81265e7')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));return r['status']=='PASS_LOCAL_CONTROL'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();raise SystemExit(0 if run(a.out) else 1)
