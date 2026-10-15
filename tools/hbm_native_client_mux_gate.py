#!/usr/bin/env python3
"""Actual finite K-client ownership mux + ONE native controller + strict offchip DRAM."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TB=r'''`timescale 1ps/1fs
module tb;
parameter integer MUT_READ=0,MUT_ACK=0,MUT_BURST=0;
reg clk=0;always #512 clk=~clk;reg rst_n=0;
reg[95:0]c_k_v,c_k_we,c_kr_rdy;wire[95:0]c_k_rdy,c_kr_v,c_k_wr_done;
reg[2879:0]c_k_addr;reg[383:0]c_k_len;reg[1631:0]c_k_tag;reg[24575:0]c_k_wdata;reg[3071:0]c_k_wstrb;
wire[1631:0]c_kr_tag;wire[383:0]c_kr_beat;wire[24575:0]c_kr_data;
wire[31:0]k_v,k_rdy,k_we,kr_v,kr_rdy,k_wr_done;wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;
wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;wire mux_fault,controller_fault;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire[31:0]dram_rvalid;
ot_hbm_native_client_mux #(.MUT_READ_OWNER(MUT_READ),.MUT_EARLY_ACK(MUT_ACK),.MUT_BURST_COUNT(MUT_BURST)) mux(
 .pc_clk({32{clk}}),.rst_n(rst_n),.c_k_v(c_k_v),.c_k_rdy(c_k_rdy),.c_k_we(c_k_we),.c_k_addr(c_k_addr),.c_k_len(c_k_len),.c_k_tag(c_k_tag),.c_k_wdata(c_k_wdata),.c_k_wstrb(c_k_wstrb),
 .c_kr_v(c_kr_v),.c_kr_rdy(c_kr_rdy),.c_kr_tag(c_kr_tag),.c_kr_beat(c_kr_beat),.c_kr_data(c_kr_data),.c_k_wr_done(c_k_wr_done),
 .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.k_wr_done(k_wr_done),.fault(mux_fault));
ot_hbm_svc_native_sector_owned_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1),.COLUMN_CLOSE_GUARD(1)) controller(
 .clk(clk),.pc_clk({32{clk}}),.rst_n(rst_n),.k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.k_wr_done(k_wr_done),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
 .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(controller_fault));
ot_hbm_svc_command_dram_pipeline_fixture dram(.clk(clk),.rst_n(rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
integer sent[0:2][0:31],received[0:2][0:31],acks[0:2][0:31];
integer wr_owner[0:31][0:63],wr_wp[0:31],wr_rp[0:31];
integer cycle=0,phase=0,read_start=0,total_acks=0,total_reads=0,max_owner=0,max_native_reserved=0;
function[29:0]address(input integer c,p,r,b);
 reg[29:0]s;begin s=30'h28800000+30'((c*4+r)*128+b);s[6:2]=5'(p)^s[11:7]^s[16:12];address=s;end
endfunction
function[255:0]pattern(input[29:0]s,input integer salt);
 begin for(integer n=0;n<8;n=n+1)pattern[n*32+:32]={2'b0,s}^(32'h9e3779b9*n)^(salt?32'hd1537a91:0);end
endfunction
always @*begin:CLIENT_PINS
 integer idx,r,b;reg[29:0]sa;
 c_k_v=0;c_k_we=0;c_k_addr=0;c_k_len=0;c_k_tag=0;c_k_wdata=0;c_k_wstrb=0;c_kr_rdy=0;
 for(integer c=0;c<3;c=c+1)for(integer p=0;p<32;p=p+1)begin
  idx=c*32+p;r=phase==0?sent[c][p]/4:sent[c][p];b=phase==0?sent[c][p]%4:0;sa=address(c,p,r,b);
  c_k_v[idx]=rst_n && (phase==0?(c!=0 && sent[c][p]<16):sent[c][p]<4);
  c_k_we[idx]=phase==0;c_k_addr[idx*30+:30]=sa;c_k_len[idx*4+:4]=phase==0?1:4;
  c_k_tag[idx*17+:17]=17'h10000|17'(p*16+r);c_k_wdata[idx*256+:256]=pattern(sa,1);c_k_wstrb[idx*32+:32]=32'hffffffff;
  c_kr_rdy[idx]=phase==1 && cycle>read_start+300 && ((cycle+c+p)%7!=0);
 end
end
always @(posedge clk)begin:SCORE
 integer c,idx,n,r,b,owner;reg[2:0]got_done;reg[29:0]sa;
 cycle<=cycle+1;
 if(rst_n)begin
  for(integer p=0;p<32;p=p+1)begin
   got_done=0;
   for(c=0;c<3;c=c+1)begin
    idx=c*32+p;got_done[c]=c_k_wr_done[idx];
    if(c_k_v[idx]&&c_k_rdy[idx])begin
     sent[c][p]<=sent[c][p]+1;
     if(c_k_we[idx])begin wr_owner[p][wr_wp[p]]=c;wr_wp[p]=wr_wp[p]+1;end
    end
    if(c_k_wr_done[idx])begin acks[c][p]<=acks[c][p]+1;total_acks=total_acks+1;end
    if(c_kr_v[idx]&&c_kr_rdy[idx])begin
     n=received[c][p];r=n/4;b=n%4;sa=address(c,p,r,b);
     if(n>=16 || c_kr_tag[idx*17+:17] !== (17'h10000|17'(p*16+r)) || c_kr_beat[idx*4+:4]!==4'(b) || c_kr_data[idx*256+:256]!==pattern(sa,c!=0))
       $fatal(1,"muxreadownership/tag/beat/data c%0d p%0d n%0d tag%h beat%0d",c,p,n,c_kr_tag[idx*17+:17],c_kr_beat[idx*4+:4]);
     received[c][p]<=n+1;total_reads=total_reads+1;
    end
   end
   if(k_wr_done[p])begin
    if(wr_rp[p]>=wr_wp[p])$fatal(1,"physicalACKwithoutacceptedowner");
    owner=wr_owner[p][wr_rp[p]];wr_rp[p]=wr_rp[p]+1;
    if(got_done!==(3'b1<<owner))$fatal(1,"truephysicalWRACKowner p%0d got%b owner%0d",p,got_done,owner);
   end else if(got_done!=0)$fatal(1,"enqueueACKinsteadphysicalWRcommit p%0d",p);
   if(got_done[0])$fatal(1,"readonlyclientreceivedotherclientWRdone");
  end
  if(phase==0 && total_acks==1024)begin
   phase<=1;read_start<=cycle;
   for(c=0;c<3;c=c+1)for(integer p=0;p<32;p=p+1)sent[c][p]<=0;
  end
  #2;
  if(mux_fault||controller_fault)$fatal(1,"mux/nativefault %b%b",mux_fault,controller_fault);
  if(mux.g_pc[0].read_count>max_owner)max_owner=mux.g_pc[0].read_count;
  if(controller.g_pc[0].read_reserved>max_native_reserved)max_native_reserved=controller.g_pc[0].read_reserved;
  if(controller.g_pc[0].read_reserved>32 || mux.g_pc[0].read_count>64)$fatal(1,"unboundedphysicalreadreservation");
  if(total_reads==1536)begin
   if(total_acks!=1024 || dram.writes!=1024 || dram.reads!=1536 || max_owner<=32 || max_native_reserved!=32 || dram.refreshes<32)$fatal(1,"muxcounts/capacity %0d %0d",max_owner,max_native_reserved);
   $display("PASS actual3client nativeKmux original17tags burst4beats 1024trueWRACK 1536exactRD readowners%0d nativeReserved%0d REFpb%0d",max_owner,max_native_reserved,dram.refreshes);$finish;
  end
  if(cycle>6000)$fatal(1,"muxboundedtesttimeout acks%0d reads%0d",total_acks,total_reads);
 end
end
initial begin
 for(integer c=0;c<3;c=c+1)for(integer p=0;p<32;p=p+1)begin sent[c][p]=0;received[c][p]=0;acks[c][p]=0;end
 for(integer p=0;p<32;p=p+1)begin wr_wp[p]=0;wr_rp[p]=0;end
 for(integer i=0;i<65536;i=i+1)dram.mem[i]=pattern(30'h28800000+30'(i),0);
 repeat(4)@(negedge clk);rst_n=1;
end
endmodule
'''
def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);tb=out/'tb.sv';tb.write_text(TB)
 paths=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_stream_pc_lease.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_owned_stack.sv','rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_native_client_mux.sv']
 runs=[];start=time.monotonic()
 for name,mr,ma,mb in [('baseline',0,0,0),('wrong_read_owner',1,0,0),('enqueue_ack',0,1,0),('non_atomic_burst',0,0,1)]:
  sim=(out/name).resolve();cp=subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.MUT_READ={mr}',f'-Ptb.MUT_ACK={ma}',f'-Ptb.MUT_BURST={mb}','-o',str(sim),*[str(ROOT/p)for p in paths],str(tb)],capture_output=True,text=True)
  (out/(name+'.build.log')).write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
  rp=subprocess.run(['vvp',str(sim)],capture_output=True,text=True);(out/(name+'.run.log')).write_text(rp.stdout+rp.stderr)
  print(name,rp.stdout.strip(),flush=True);assert (rp.returncode==0)==(name=='baseline'),rp.stdout+rp.stderr
  runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
 result=dict(schema='opentallas.hbm.native_K_client_mux.v1',status='pass',clients=3,physical_PCs=32,read_owner_entries_per_PC=64,write_owner_entries_per_PC=32,native_read_reservations_per_PC=32,original_tag_bits=17,burst_read_lengths=[1,2,3,4],tested_burst_length=4,controller_instances=1,controller_profile=dict(FAST_IDLE_DESC=1,AQ_ROW_LEASE=1,COLUMN_CLOSE_GUARD=1),wall_seconds=time.monotonic()-start,runs=runs,scope='Ownership protocol component with actual single native controller/real response SRAMs and strict offchip read/write timing fixture. Request stimuli are synthetic port transactions; no whole Engram/WKV/kernel/performance/physical qualification.',source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths})
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
