#!/usr/bin/env python3
"""Create a whole native pair observer; one fixed optional START, no data/control forcing."""
import argparse,json,re,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'tools/qwen_tokfunc/xdie_bound'));import bound_carve as B

def make(qc_top,pair,out):
    if not json.loads((pair/'pair.json').read_text())['whole_qc']:raise ValueError('complete observer requires whole QC')
    _,_,insts=B.parse_top(qc_top);obs=[];ids=set()
    for i in insts:
        if not re.fullmatch(r'c_[EW][0-5]_[bt][fn]_00',i['name']):continue
        m=re.search(r"\.S_u_t_0_0_tile_id\(16'b([01]{16})\)",'\n'.join(i['text']))
        if not m:raise ValueError('missing exact root tile strap')
        cid=int(m[1],2)>>4
        if cid in ids:raise ValueError('duplicate cluster')
        ids.add(cid);sig=f'u_d.u_qc.{i["name"]}.u_u_t_0_0.n_y'
        obs.append(f'            if ({sig}[512] || {sig}[513]) $fdisplay(lg,"%0d CLUSTER {cid} %0d %h",cycle,{sig}[513],{sig}[511:0]);')
    if ids!=set(range(48)):raise ValueError('incomplete native projection observation')
    text='''`timescale 1ns/1ps
module tb_qwen_native_pair;
    reg ck=0; always #0.4165 ck=~ck;
    reg rst_n=0,start=0;
    integer cycle,ncyc,start_cycle,die_id,lg,qc_beats,kv_beats;
    reg [1023:0] log_path;
    wire qv,kv;wire [582:0] qf,kf;
    qwen_native_pair u_d(.ck(ck),.rst_n(rst_n),.start(start),
        .kv__pad_die_id(die_id[2:0]),.kv__pad_por_n(rst_n),.kv__pad_refclk(ck),
        .qc__ucie_kv_link_v(qv),.qc__ucie_kv_link_flit(qf),
        .kv__sys_c_link_v(kv),.kv__sys_c_link_flit(kf));
`define OT_ROM_BIND_TOP tb_qwen_native_pair.u_d
`include "rom_bind_pair.vh"
`undef OT_ROM_BIND_TOP
    initial begin
        ncyc=10000;start_cycle=-1;qc_beats=0;kv_beats=0;log_path="pair.log";
        if (!$value$plusargs("KV_DIE_ID=%d",die_id)) $fatal(1,"explicit KV_DIE_ID required");
        if ($value$plusargs("NCYC=%d",ncyc)) begin end
        if ($value$plusargs("START_CYCLE=%d",start_cycle)) begin end
        if ($value$plusargs("LOG=%s",log_path)) begin end
        lg=$fopen(log_path,"w");if(!lg)$fatal(1,"log open failed");
        repeat(4) @(negedge ck);rst_n=1;
        for(cycle=0;cycle<ncyc;cycle=cycle+1)begin
            if(cycle==start_cycle)begin start=1;$fdisplay(lg,"%0d GLOBAL_START",cycle);end
            @(posedge ck);#0.001;
            if(qv)begin qc_beats=qc_beats+1;$fdisplay(lg,"%0d C2K %h",cycle,qf);end
            if(kv)begin kv_beats=kv_beats+1;$fdisplay(lg,"%0d K2C %h",cycle,kf);end
'''+ '\n'.join(obs)+'''
            @(negedge ck);
        end
        $fdisplay(lg,"OBSERVE_END cycles=%0d start=%0d c2k=%0d k2c=%0d",ncyc,start_cycle,qc_beats,kv_beats);
        $fclose(lg);$display("NATIVE_PAIR_OBSERVE_END cycles=%0d c2k=%0d k2c=%0d",ncyc,qc_beats,kv_beats);$finish;
    end
endmodule
'''
    out.write_text(text)
    print('NATIVE_PAIR_OBSERVER_STAGED',len(obs),'clusters; no PASS verdict emitted')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--qc-top',type=Path,required=True);p.add_argument('--pair',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.qc_top,a.pair,a.out)
