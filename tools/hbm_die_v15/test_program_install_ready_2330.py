#!/usr/bin/env python3
"""Actual two full programme SRAM paths; source-bound old failures and structural mutants."""
import pathlib,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[2]
source='rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv'
bench=R/'rtl/hbm_accel/host_static_20261015/tb_hbm_program_install_ready.sv'
deps=[R/'rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv',
      R/'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
with tempfile.TemporaryDirectory(prefix='hbm-install-ready-') as td:
    d=pathlib.Path(td)
    def build(name,text):
        p=d/(name+'.sv');p.write_text(text)
        subprocess.run(['iverilog','-g2012','-s','tb_hbm_program_install_ready','-o',str(d/name),str(bench),str(p)]+list(map(str,deps)),check=True)
    def run(name,case=None,ok=False):
        cmd=['vvp',str(d/name)]+([] if case is None else [f'+CASE={case}'])
        r=subprocess.run(cmd,capture_output=True,text=True)
        print(f'{name} case{case} rc={r.returncode}: {r.stdout.splitlines()[0] if r.stdout else r.stderr.strip()}')
        assert (r.returncode==0 and 'PROGRAM_INSTALL_READY PASS' in r.stdout) if ok else (r.returncode!=0 and 'FATAL:' in r.stdout)
    text=(R/source).read_text();build('actual',text);run('actual',ok=True)
    old=subprocess.check_output(['git','-C',str(R),'show','005075acd:'+source],text=True)
    build('before',old)
    for case in (1,2,3,4,5,11,12,14):run('before',case)
    variants=[
     ('missing_bypass',1,text.replace('if(missing || !installed[scan_row])fault<=1;',"if(1'b0)fault<=1;")),
     ('stale_generation',4,text.replace('if(!install_open)installed<=',"if(1'b0)installed<=")),
     ('early_launch',5,text.replace('if(!launch_ready || cv || dv)fault<=1;','if(cv || dv)fault<=1;')),
     ('bad_magic',11,text.replace("data_q[255:240]!=16'hc7a1 || ",'')),
     ('wrong_pc',12,text.replace(" || data_q[239:224]!={4'b0,address}",'')),
     ('wrong_write_owner',14,text.replace('if(program_cfg_we)begin','if(cfg_v)begin').replace('<<program_cfg_addr','<<cfg_addr[PCW-1:0]').replace('installed[program_cfg_addr]','installed[cfg_addr[PCW-1:0]]'))]
    for name,case,mut in variants:
        assert mut!=text,name
        build(name,mut);run(name,case)
print('PROGRAM_INSTALL_READY_GATE PASS actual15cases,8oldsource failures,6structuralmutants rejected')
