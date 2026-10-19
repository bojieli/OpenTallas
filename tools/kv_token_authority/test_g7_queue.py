#!/usr/bin/env python3
"""Emit a bounded bench containing the actual repaired G7 responder block."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('driver',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
s=a.driver.read_text();start=s.index('    always @(negedge ck) begin : grp_model');end=s.index('    // ---- the d2d face',start);block=s[start:end]
head=r'''`timescale 1ns/1ps
module tb_queue;
localparam KVA_NG=1,KMAX=1,KV_ROWS=16;
reg ck=0;always #5 ck=~ck;
integer cyc=0;always @(posedge ck) cyc<=cyc+1;
reg [17:0] kva_authority_known=0;
reg [37:0] kva_kreq[0:0],kva_pk[0:0][0:63];
reg [14:0] kva_vreq[0:0],kva_pv[0:0][0:63];
integer kva_pvk[0:0][0:63];
reg [1061:0] kva_krsp[0:0]; reg[1055:0] kva_rsp[0:0];
reg [1023:0] kva_kv[0:15];integer kva_u[0:0],kva_l[0:0];reg [15:0] kva_ep[0:0];
integer kva_T=2,kva_lg=8,kva_mut=0,kva_coll=0,kva_rowerr=0,errors=0,rsps=0;
integer kva_nk[0:0],kva_nv[0:0],kva_k0[0:0],kva_v0[0:0],kva_klast[0:0],kva_vlast[0:0];
integer kva_sk0[0:0][0:0],kva_skl[0:0][0:0],kva_sv0[0:0][0:0],kva_svl[0:0][0:0];
reg idle_window=0; reg reset_episode=0;
function automatic integer kva_cur(input integer c,input integer lead);kva_cur=idle_window?-1:0;endfunction
function automatic integer kva_row(input integer u,input integer l);kva_row=64+l+256*u;endfunction
function automatic integer kva_map_user(input integer u);kva_map_user=u;endfunction
function automatic integer kva_step_of_row(input integer r);kva_step_of_row=(r==64)?0:-1;endfunction
task smoke_err(input string msg);errors++;$display("QUEUE_ERROR %s",msg);endtask
initial begin
 kva_u[0]=0;kva_l[0]=0;kva_ep[0]=16'h24;
 kva_kreq[0]=0;kva_vreq[0]=0;kva_nk[0]=0;kva_nv[0]=0;kva_k0[0]=-1;kva_v0[0]=-1;
 kva_sk0[0][0]=-1;kva_sv0[0][0]=-1;
 for(int i=0;i<64;i++)begin kva_pk[0][i]=0;kva_pv[0][i]=0;kva_pvk[0][i]=0;end
 for(int i=0;i<16;i++)kva_kv[i]=i;
end
'''
tail=r'''
always @(posedge ck) if(kva_krsp[0][0]) rsps++;
initial begin
 // Actual arbitrary startup request is raw, with no queue/state mutation.
 #1;kva_kreq[0]={6'd0,16'h24,1'b0,14'd1,1'b1};
 repeat(3)@(posedge ck);#1;
 if(kva_nk[0]!=0) $fatal(1,"preknown enqueue");
 for(int i=0;i<64;i++)if(kva_pk[0][i]!=0)$fatal(1,"preknown pending queue");
 kva_kreq[0]=0;kva_authority_known='1;
 // First known idle malformed request must be checked, before a programme.
 idle_window=1;kva_kreq[0]={6'd0,16'h24,1'b0,14'd1,1'b1};
 @(posedge ck);#1;kva_kreq[0]=0;
 @(posedge ck);#1;if(kva_rowerr!=1)$fatal(1,"idle request masked");
 repeat(10)@(posedge ck);#1;
 if(rsps!=1)$fatal(1,"owned idle request response not exactly once");
 // Genuine accepted request remains owned during repeated reset episode.
 // This is the original responder behavior: no invented queue cancellation.
 idle_window=0;kva_kreq[0]={6'd0,16'h24,1'b0,14'd1,1'b1};
 @(posedge ck);#1;kva_kreq[0]=0;reset_episode=1;
 repeat(3)@(posedge ck);#1;reset_episode=0;
 repeat(10)@(posedge ck);#1;
 if(rsps!=2 || kva_nk[0]!=1 || errors!=0 || kva_rowerr!=1)$fatal(1,"queue history/drain violation");
 $display("QUEUE_CONTROL_PASS exact block; historical response drains once, no reset clear");$finish;
end
endmodule
'''
a.out.write_text(head+block+tail)
