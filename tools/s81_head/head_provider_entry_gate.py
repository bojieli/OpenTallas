#!/usr/bin/env python3
"""Real HOST/HBC/HOST276/CTL AR entry with80 actual K_XB beats.

All source events come from the emitted static calendar. The compiled job
loads5120 BF16 values through the actual four SRAMs and checks all81920 input
bits in the native replay stream. No head array/result/MTP pass is claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from head_entry_schedule import compile_entry
from head_control_plan_delta import CTL_SOURCES
from head_host_plan_delta import SOURCES

ROOT=Path(__file__).resolve().parents[2]
TB=r'''`timescale 1ns/100fs
module tb_head_provider_entry;
reg ck=0,rn=0,start=0;always #0.4165 ck=~ck;
wire[511:0]ht0,ht1,pt0,pt1;reg[1:0]pv=0;reg[552:0]pd0=0,pd1=0;
wire[1:0]prv;wire[552:0]prd0,prd1;wire[3:0]pf0,pf1;
wire[276:0]hosttx;wire[275:0]hostrx;
ot_s81hd_mesh_lane p0(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,ht0}),.tx(pt0),.tx_v(pv[0]),.tx_d(pd0),.rx_v(prv[0]),.rx_d(prd0),.flt(pf0));
ot_s81hd_mesh_lane p1(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,ht1}),.tx(pt1),.tx_v(pv[1]),.tx_d(pd1),.rx_v(prv[1]),.rx_d(prd1),.flt(pf1));
ot_s81hd_host_ep_core #(.LOCAL_STAGE(@STAGE@),.LOCAL_RANK(@RANK@),.PHASE_BOUND(1),
 .CLOCK_RESET_ID(64'd@ID@),.BOOT_HEADER_EDGE(48'd@HEADER@),.BOOT_COMMIT_EDGE(48'd@COMMIT@))host(
 .ck(ck),.rst_n(rn),.start_i(start),.coll_i0({2'b10,pt0}),.coll_i1({2'b10,pt1}),
 .coll_o0(ht0),.coll_o1(ht1),.h_tx_i(hosttx),.h_rx_o(hostrx));
reg[1103:0]ri=0;reg[31:0]tag=0;
wire[1103:0]ro;wire fault;wire[44:0]unitbus;wire[564:0]stream;wire[63:0]ma,mb,mn;
ot_s81hd_ctl_core ctl(.ck(ck),.rst_n(rn),.start_i(start),.lep_fault_i(1'b0),.lw_i(11'd0),
 .lepk_i0(ri),.lepk_o0(ro),.lepf_o0(fault),.unit_o0(unitbus),.ctrl_i0(tag),.x_o(stream),.b_i(565'd0),
 .h_tx_o(hosttx),.h_rx_i(hostrx),.a_tx_o(ma),.b7_tx_o(mb),.n_tx_o(mn),.a_rx_i(64'd0),.b7_rx_i(64'd0),.n_rx_i(64'd0));
reg[607:0]setup[0:10];reg[1023:0]data[0:79];
integer c=0,i,index,m=0,sent=0,issues=0,mut=0;
reg[552:0]fr;reg[255:0]ea,eb;string dir;
initial begin
 if(!$value$plusargs("DATA=%s",dir))$fatal(1,"DATA required");
 if($value$plusargs("MUT=%d",mut))begin end
 $readmemh({dir,"/setup.memh"},setup);$readmemh({dir,"/xb.memh"},data);
end
always@(negedge ck)begin
 c++;rn=(c>=8);start=(c>=@START@);pv=0;pd0=0;pd1=0;ri=0;tag=0;
 for(i=0;i<11;i++)if(c==int'(setup[i]>>554))begin
  fr=setup[i][552:0];
  if(mut==1&&fr[3:0]==6&&fr[23:16]==2)fr[24]=~fr[24];
  if(setup[i][553])begin pv[1]=1;pd1=fr;end else begin pv[0]=1;pd0=fr;end
 end
 if(c>=@XB_FIRST@&&c<@XB_FIRST@+80)begin
  index=c-@XB_FIRST@;
  if(!(mut==2&&index==79))begin
   ri=(1104'(data[index])<<21)|(1104'(index)<<13)|1104'd5;
   if(mut==3||mut==4)ri[20]=1'b1; // actual rstop_xo HEAD egress flag
   if(mut==4&&index==0)ri[19:13]=7'd80; // invalid low index stays invalid
   tag=32'd@TAG@;sent++;
  end
 end
 if(c==@START@-1)begin
  if(!host.ctxv||host.hbc_fault||host.host_fault||fault)$fatal(1,"actual HBC/CTL setup not admitted");
  if(ctl.u_logic.c_rank!=@RANK@)$fatal(1,"wrong rank CSR2");
  if(ctl.u_logic.c_plen!=1||ctl.u_logic.c_glen!=0||ctl.u_logic.c_rbase!=97024||!ctl.u_logic.c_run)
   $fatal(1,"actual CTL CSR setup incomplete");
  if(ctl.u_logic.nbeat!=80||sent!=80)$fatal(1,"actual XB residency missing");
 end
 if(ctl.u_logic.start)begin
  issues++;
  if(c!=@ISSUE@)$fatal(1,"issue moved from compiled edge got%0d expected@ISSUE@",c);
 end
 if(c>100&&((|pf0)||(|pf1)||(|host.host_fault)||fault))$fatal(1,"current provider fault c%0d peer%h/%h host%h ctl%b",c,pf0,pf1,host.host_fault,fault);
 if(stream[513])begin
  ea=data[m/4][(m%4)*256+:256];eb=data[64+(m%64)/4][(m%4)*256+:256];
  if(stream[255:0]!==ea||stream[511:256]!==eb)$fatal(1,"actual xstore replay mismatch m%0d",m);
  m++;
  if(m==256)begin
   if(issues!=1||!ctl.u_logic.job_active_o)$fatal(1,"missing static job admission");
   $display("HEAD_PROVIDER_ENTRY PASS HBC3 CSR8 XB80 HALF512160 BF165120 stored_bits81920 replay256 rank3 static_START@START@ issue@ISSUE@ AR_ONLY no_full_HEAD_token");$finish;
  end
 end
 if(c>@ISSUE@+400)$fatal(1,"entry stream did not complete");
end
endmodule
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    beats=[sum((0x3000+b*64+k)<<(16*k) for k in range(64)) for b in range(80)]
    job=dict(mode='ar',rank=3,tid=37,user=513,position=17,token=7,epoch=1,programme=9,
             host_word_count=417,activation_beats=beats,plen=1,glen=0,group=4,rbase=97024,
             issue_offset=20,issue_period=10357,merge_deadline=10000)
    timing=dict(scope='PROVIDER_PIN_ENTRY_COMPONENT',reset_deassert_edge=8,host_counter_zero_edge=10,
                link_ready_edge=256,peer_to_hbc_input=29,peer_frame_period=4,
                peer_launch_modulus=2,peer_launch_residue=0,peer_to_ctl_settled=37,
                commit_to_context_valid=1,ctl_start_offset=0,xb_first_edge=400,xb_period=1,xb_pin_to_resident_edges=3)
    schedule=compile_entry(dict(stages=81,TP=4,head_dies=4),job,timing)
    params=schedule['host_params'];assert 'HBC_VARIABLE_WORDS' not in params and 'HBC_COMMAND_SCOPE' not in params
    values=dict(STAGE=params['LOCAL_STAGE'],RANK=params['LOCAL_RANK'],ID=params['CLOCK_RESET_ID'],
                HEADER=params['BOOT_HEADER_EDGE'],COMMIT=params['BOOT_COMMIT_EDGE'],START=schedule['authority']['start_global_edge'],
                ISSUE=schedule['first_issue_global_edge'],XB_FIRST=400,TAG=(1<<31)|(513<<21)|17)
    tb=TB
    for key,value in values.items():tb=tb.replace('@'+key+'@',str(value))
    (out/'tb.sv').write_text(tb)
    (out/'schedule.json').write_text(json.dumps(schedule,indent=1)+'\n')
    (out/'setup.memh').write_text(''.join(f"{(f['edge']<<554)|(f['lane']<<553)|f['frame']:0152x}\n" for f in schedule['frames']))
    (out/'xb.memh').write_text(''.join(f'{b:0256x}\n' for b in beats))
    files=list(dict.fromkeys(CTL_SOURCES+SOURCES))
    missing=[f for f in files if not (ROOT/f).is_file()]
    if missing:raise SystemExit('missing source closure: '+str(missing))
    (out/'source_hashes.json').write_text(json.dumps({f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},indent=1)+'\n')
    cmd=['verilator','--binary','--timing','-O1','--build-jobs','4','-Wno-fatal','-Wno-TIMESCALEMOD',
         '--top-module','tb_head_provider_entry','+define+OT_COLL_NATIVE32','+define+OT_COLL_NATIVE32_OFF',
         '--Mdir',str(out/'obj'),'-o','tb',*(str(ROOT/f) for f in files),str(out/'tb.sv')]
    with (out/'build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    results={}
    for mode in (0,1,2,3,4):
        with (out/f'run{mode}.log').open('w') as log:
            r=subprocess.run([str(out/'obj/tb'),'+DATA='+str(out),f'+MUT={mode}'],stdout=log,stderr=subprocess.STDOUT)
        text=(out/f'run{mode}.log').read_text()
        ok=(r.returncode==0 and 'HEAD_PROVIDER_ENTRY PASS' in text) if mode in (0,3) else (
            r.returncode!=0 and ({1:'wrong rank CSR2',2:'actual XB residency missing',4:'current provider fault'}[mode]) in text)
        results[mode]=dict(passed=ok,returncode=r.returncode,kind=('positive','wrong_rank','missing_last_XB','flagged_XB_positive','invalid_low_index')[mode])
        if not ok:raise SystemExit('entry gate failed mode'+str(mode)+'; inspect '+str(out))
    (out/'verdict.json').write_text(json.dumps(dict(verdict='PASS_AR_PROVIDER_ENTRY_COMPONENT',results=results,
        source_counts=schedule['source_counts'],full_head_token=False,production_transport=False,MTP=False),indent=1)+'\n')
    print((out/'run0.log').read_text().strip());print('flagged_XB positive PASS; wrong_rank, missing_last_XB, invalid_low_index controls CAUGHT')


if __name__=='__main__':main()
