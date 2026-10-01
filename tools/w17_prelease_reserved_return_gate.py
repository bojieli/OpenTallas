#!/usr/bin/env python3
"""Bounded unchanged index-ring RTL witness: posted returns land despite stalled key output."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
PATHS=['rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv']
BENCH=r'''
`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,cmd_v=0;reg [31:0] rv=0;reg [511:0] rt=0;reg [127:0] rb=0;reg [8191:0] rd=0;
wire [31:0] qv,rr;wire [959:0] qa;wire [127:0] ql;wire [511:0] qt;
wire ov,busy;wire[15:0]kv;wire[8703:0]key;wire[47:0]nk,nb;
ot_hdc_v41x_idx_kstream_ring #(.NPC(32),.WB(32),.GA(24),.AW(30),.HW(20)) dut(
.clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base(20'd0),.cmd_skip(10'd0),.cmd_nkeys(30'd64),.cmd_base2(20'd0),.cmd_nkeys2(30'd0),.busy(busy),
.req_v(qv),.req_rdy(32'hffffffff),.req_addr(qa),.req_len(ql),.req_tag(qt),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd),
.o_valid(ov),.o_ready(1'b0),.o_kv(kv),.o_key(key),.cnt_keys_streamed(nk),.cnt_hbm_beats(nb));
reg[15:0] tags[0:31][0:15];integer left[0:31][0:15],beat[0:31][0:15],head[0:31],tail[0:31],cnt[0:31];
integer cyc=0,p,l,received=0,requested=0;
initial for(p=0;p<32;p=p+1)begin head[p]=0;tail[p]=0;cnt[p]=0;for(l=0;l<16;l=l+1)begin tags[p][l]=0;left[p][l]=0;beat[p][l]=0;end end
integer mode=0; integer accepted=0; integer j;
initial begin if($value$plusargs("MODE=%d",mode))begin end end
always @(posedge clk) begin
 if(rst_n===1'b1)begin
  for(j=0;j<32;j=j+1)begin
   if(qv[j]===1'b1)begin
    if(cnt[j]>=16)$fatal(1,"bench queue overflow");
    tags[j][tail[j]]=qt[j*16+:16];left[j][tail[j]]=ql[j*4+:4];beat[j][tail[j]]=0;
    requested=requested+ql[j*4+:4];tail[j]=(tail[j]+1)%16;cnt[j]=cnt[j]+1;
   end else if(qv[j]!==1'b0)$fatal(1,"unknown request");
   if(rv[j]===1'b1)begin
    if(rr[j]!==1'b1)$fatal(1,"reservation not ready at sampling edge");
    received=received+1;left[j][head[j]]=left[j][head[j]]-1;beat[j][head[j]]=beat[j][head[j]]+1;
    if(left[j][head[j]]==0)begin head[j]=(head[j]+1)%16;cnt[j]=cnt[j]-1;end
   end else if(rv[j]!==1'b0)$fatal(1,"unknown response valid");
  end
 end
end
// Check actual landing after nonblocking RTL writes, with input fields still stable.
always @(posedge clk)begin
 #1;
 if(rst_n===1'b1)for(integer v=0;v<32;v=v+1)begin
  if(rv[v]===1'b1 && rr[v]===1'b1)
   if(dut.u_d.rob[v][rt[v*16+:16]%32][256*dut.rsp_beat_adj[v*4+:2]+:256] !== rd[v*256+:256])$fatal(1,"actual reserved ROB data mismatch");
 end
end
always @(negedge clk)begin
 cyc=cyc+1;
 // Exercise inputs while reset asserted, then settle before releasing reset.
 rv=0;rt=0;rb=0;rd=0;
 if(cyc==1)rv=32'hffffffff;
 if(cyc==4)rst_n=1;
 cmd_v=(cyc==6);
 if(rst_n===1'b1 && cyc>6)begin
  for(p=0;p<32;p=p+1)begin
   if(cnt[p]>0 && mode!=1 && !(mode==3 && p==0) && (mode!=2 || cyc>=40))begin
    rv[p]=1;rt[p*16+:16]=tags[p][head[p]];rb[p*4+:4]=beat[p][head[p]];rd[p*256+:256]={8{32'h01010101}};
   end
  end
 end
 if(cyc==300)begin
  if(requested!==136 || received!==136 || nb!==48'd136 || nk!==48'd0 || ov!==1'b1)$fatal(1,"finite drain failed requested=%0d recv=%0d beats=%0d out=%0d ov=%0d",requested,received,nb,nk,ov);
  $display("PASS_RESERVED_RETURN req=136 recv=136 stalled_output=1 hbm_beats=%0d delivered_keys=%0d mode=%0d",nb,nk,mode);$finish;
 end
end
endmodule
'''
def main(out):
 pins={};logs={}
 with tempfile.TemporaryDirectory(prefix='w17-prelease-rtl-',dir='/home/ubuntu') as tmp:
  t=pathlib.Path(tmp);sources=[]
  for i,p in enumerate(PATHS):
   raw=subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT);pins[p]=dict(commit=PIN,sha256=hashlib.sha256(raw).hexdigest());f=t/f's{i}.sv';f.write_bytes(raw);sources.append(str(f))
  bench=t/'tb.sv';bench.write_text(BENCH)
  c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(t/'gate'),str(bench),*sources],capture_output=True,text=True,timeout=30);logs['compile']=c.stdout+c.stderr
  if c.returncode:raise RuntimeError(logs)
  cases={}
  for name,mode,expected in [('positive',0,True),('stalled_returns_rejected',1,False),('delayed_returns',2,True),('one_channel_stalled_rejected',3,False)]:
   run=subprocess.run(['vvp',str(t/'gate'),f'+MODE={mode}'],capture_output=True,text=True,timeout=30)
   passed=run.returncode==0 and 'PASS_RESERVED_RETURN' in run.stdout
   cases[name]=dict(returncode=run.returncode,log=run.stdout+run.stderr,expected_pass=expected,matched_expectation=passed==expected)
  logs['cases']=cases
  good=all(v['matched_expectation'] for v in cases.values())
  r=dict(verdict='PASS_UNCHANGED_RESERVED_RETURN_RTL' if good else 'FAIL_UNCHANGED_RESERVED_RETURN_RTL',source_pins=pins,bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),logs=logs,scope='NPC32/WB32/GA24 ring posted136 synthetic sectors accepted with o_ready0; no DRAMtime/exactarithmetic/newhardware/fulltoken/physical qualification',source_unchanged=True,adopt=False,reset_protocol='Inputs exercised under four reset edges; all queue/tag/beat/data fields initialized; command after release',acceptance='Requests and returns counted only at posedge; actual ROB checked after NBA; strict four-state counters and ready; finite bound 300 cycles',cases=cases)
  assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(cases,indent=2))
  if not r['verdict'].startswith('PASS'):raise SystemExit(1)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();main(a.out)
