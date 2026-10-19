#!/usr/bin/env python3
"""Fleet-only bit/edge equivalence against unchanged VM, including priorities."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as P


def prepare(work):
    work.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'rtl/qwen_dv/qfd_dv_vm.sv').read_text()
    assert source.count('module qfd_dv_vm #(')==1
    (work/'vm_reference.sv').write_text(source.replace('module qfd_dv_vm #(','module qfd_dv_vm_reference #('))
    m=next(m for m in P.parse_modules(P.strip_comments(source),'VM baseline') if m.name=='qfd_dv_vm')
    ins=[p for p in m.ports if m.ports[p][0]=='input'];outs=[p for p in m.ports if m.ports[p][0]=='output']
    lines=['`timescale 1ns/1ps','module tb #(parameter integer MUT=0);']
    for p in ins:
        w=m.width(p,m.env());lines.append(f'reg [{w-1}:0] {p}=0;')
    for p in outs:
        w=m.width(p,m.env());lines.append(f'wire [{w-1}:0] {p}_ref,{p}_safe;')
    for mod,inst,post,mut in [('qfd_dv_vm_reference','u_ref','ref',0),('qfd_dv_vm','u_safe','safe','MUT')]:
        con=[f'.{p}({p})' for p in ins]+[f'.{p}({p}_{post})' for p in outs]
        lines.append(f'{mod} #(.MUT({mut})) {inst}('+','.join(con)+');')
    lines+=['reg check=0;integer checks=0; task tick; begin #0.5;ck=1;#0.01;if(check) begin']
    for p in outs:lines.append(f'if({p}_ref!=={p}_safe) $fatal(1,"VM_SAFE_MISMATCH port {p} check%0d",checks);')
    lines+=['checks=checks+1;end #0.49;ck=0;end endtask']
    lines.append(r'''
    reg [31:0] seed=32'h372916af;
    function [31:0] rnd;
        begin seed=seed*32'd1664525+32'd1013904223;rnd=seed;end
    endfunction
    integer n,l,j;reg[23:0] rowa,rowb,rowc,rowcr,write_row;
    task table_data;
        begin for(j=0;j<32;j=j+1) tw_data[32*j+:32]=rnd();end
    endtask
    initial begin
        tick();rst_n=1;
        // Initialize every native row used by any client. No active reads.
        w16_we=1;
        for(n=0;n<1024;n=n+1) begin
            w16_addr=n*16;
            for(j=0;j<16;j=j+1) w16_data[32*j+:32]=rnd();
            tick();
        end
        w16_we=0;tw_we=1;tw_kind=1;
        for(n=0;n<1024;n=n+1) begin tw_addr=n;table_data();tick();end
        tw_kind=2;
        for(n=0;n<128;n=n+1) begin tw_addr=n*4;table_data();tick();end
        tw_kind=3;
        for(n=0;n<256;n=n+1) begin tw_addr=n;table_data();tick();end
        tw_we=0;
        for(n=0;n<6008;n=n+1) begin
            a_re=255;b_re=255;c_re=255;cr_re=255;bs_re=1;bt_re=1;p_re=1;
            rowa=rnd()&24'h3ff8;rowb=rnd()&24'h3ff8;
            rowc=rnd()&24'h3ff8;rowcr=rnd()&24'h3ff8;
            for(l=0;l<8;l=l+1) begin
                a_addr[24*l+:24]=rowa+(rnd()&7);
                b_addr[24*l+:24]=rowb+(rnd()&7);
                c_addr[24*l+:24]=rowc+(rnd()&7);
                cr_addr[24*l+:24]=rowcr+(rnd()&7);
            end
            bs_addr=rnd()&511;bt_word=rnd()&511;p_idx=rnd()&511;
            w1_we=(rnd()&7)==0;w1_addr=rnd()&24'h3fff;w1_data=rnd();
            if((n%91)==0) w1_addr=w1_addr|24'h008000;
            w16_we=(rnd()&15)==0;w16_addr=rnd()&24'h3ff0;
            for(j=0;j<16;j=j+1) w16_data[32*j+:32]=rnd();
            su_we=((rnd()&3)==0) ? rnd() : 0;write_row=rnd()&24'h3ff8;
            for(l=0;l<8;l=l+1) begin
                // Random duplicate slots exercise exact highest-lane priority.
                su_waddr[24*l+:24]=write_row+(rnd()&7);
                su_wdata[32*l+:32]=rnd();
            end
            if((n%37)==0) su_waddr[24*2+4]=~su_waddr[24*2+4];
            if((n%43)==0) begin
                su_we=255;w1_we=1;w1_addr=write_row;w16_we=1;
            end
            tw_we=(rnd()&31)==0;
            if(tw_we) begin
                tw_kind=1+(rnd()%3);tw_addr=rnd()&255;
                if(tw_kind==1) tw_addr=rnd()&1023;
                if(tw_kind==2) tw_addr=tw_addr&24'h0001fc;
                table_data();
                // Table load/read exclusion is the native schedule contract.
                cr_re=0;bs_re=0;bt_re=0;p_re=0;
            end
            // Fault reset does not clear SRAM/data or alter fixed read stages.
            rst_n=(n%1000)!=0;
            check=(n>=8);tick();
        end
        if(checks!=6000) $fatal(1,"wrong comparison count");
        $display("VM_SAFE_EQUIVALENCE PASS6000 exact-edge allports randomslots/priority/fault/reset");
        $finish;
    end
    endmodule
''')
    (work/'tb.sv').write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',required=True)
    ap.add_argument('--mut',type=int,default=0);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    work=Path(a.work).resolve();prepare(work)
    if a.prepare_only:return
    models=['rtl/test/full_sm_service/sram_models.sv','rtl/test/hbm_rf_visibility/scale_sram_model.sv']
    # These existing models cover legacy VM masters. This test proves RTL
    # control equivalence; native macro timing/pin-access remain separate.
    src=[str(work/'tb.sv'),str(work/'vm_reference.sv'),str(ROOT/'rtl/qwen_dv/qfd_dv_vm_safe.sv')]+[str(ROOT/p) for p in models]
    obj=work/f'obj_m{a.mut}';cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb',f'-GMUT={a.mut}','--Mdir',str(obj),'-o','sim','-j','4']+src
    with (work/f'build_m{a.mut}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    sim=subprocess.run([str(obj/'sim')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (work/f'run_m{a.mut}.log').write_text(sim.stdout);print(sim.stdout,end='')
    if a.mut:
        assert sim.returncode!=0 and 'VM_SAFE_MISMATCH' in sim.stdout,'mutant not witnessed'
        print(f'VM_SAFE_MUT{a.mut} WITNESS PASS')
    else:sim.check_returncode()


if __name__=='__main__':main()
