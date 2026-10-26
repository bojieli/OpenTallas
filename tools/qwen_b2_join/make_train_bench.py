#!/usr/bin/env python3
"""Actual halftrain native SRAM bench, full shapes at the real producer boundary."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'tools/qwen_b2_join/tb_b2_vm.sv').read_text();con=s[s.index('qfd_sp_vector_memory_b2 #('):s.index('function automatic')]
head='''`timescale 1ns/1ps
module tb_b2_train;
reg clk=0,rst_n=0; always #1 clk=~clk;
integer mut=0;initial void'($value$plusargs("MUT=%d",mut));
reg[2212:0]rq[0:5];wire[550:0]rb[0:5];wire[5:0]sf;
reg start=0,payload=0;reg[3:0]count=0,nh=0;reg[31:0]stride=0;
reg[20:0]svr=0;wire[511:0]svq;wire svq_v;wire[15:0]ld;wire vf;
for(genvar h=0;h<6;h=h+1)begin:g_ser
 qfd_res_train_half_b2 #(.BAND(h),.MUT(0))u(.ck(clk),.ck_bank({24{clk}}),.rst_n(rst_n),
 .train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),
 .rq(rq[h]),.rb(rb[h]),.fault(sf[h]));
end
'''
# Exercise parameter-free physical masters rather than relying on per-instance sidecars.
begin=head.index('for(genvar h=0;')
head=head[:begin]
for hb in range(6):
 head+=f"qfd_res_train_half_b2_{hb} u_ser{hb}(.ck(clk),.ck_bank({{24{{clk}}}}),.rst_n(rst_n),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[{hb}]),.rb(rb[{hb}]),.fault(sf[{hb}]));\n"
body='''
function automatic [511:0]image(input integer row,input integer op);
 for(integer l=0;l<16;l=l+1)image[32*l+:32]=32'h3f800000+32'(row*16+l+op*65536);
endfunction
reg[511:0]gold[0:65535];reg touched[0:65535];integer issued[0:65535];
integer cycle=0,op_start=0,op_ends=0,rows_emitted=0,rows_checked=0,read_issued=0;
integer op_tiles=0,op_ns=0,op_stride=0,op_payload=0,op_split=0,op_id=0;
integer expected_end=0,op_base=0,op_ots=0,op_ojs=0;
reg op_started=0;reg[550:0]expected_rb;integer grow,gid;reg row_active,slot_end;
always @(negedge clk)if(rst_n)begin
 cycle=cycle+1;
 for(integer h=0;h<6;h=h+1)begin
  expected_rb=0;
  if(op_started)for(integer k=0;k<8*op_tiles;k=k+1)for(integer j=0;j<op_ns;j=j+1)begin
   if(cycle==op_start+2+h*op_ns+(k/8)*((8*op_ns>op_stride)?8*op_ns:op_stride)+(k%8)*op_ns+j+(op_payload?2:1))begin
    row_active=op_payload&&(op_split<=9||h==0);
    slot_end=h==5&&j==op_ns-1;
    gid=(op_split<=9)?h*(1<<(9-op_split))+j:j;
    grow=op_base+(k/8)*op_ots*(3072>>op_split)+(k%8)*op_ojs+gid*op_ots;
    if(row_active||slot_end)expected_rb={1'b1,slot_end,slot_end&&!row_active,
      (row_active?20'(grow):20'd0),(row_active?16'hffff:16'd0),(row_active?image(grow,op_id):512'd0)};
   end
  end
  if(op_started&&rb[h]!==expected_rb)$fatal(1,"exact RB calendar/data mismatch op%0d h%0d cycle%0d got%h want%h",op_id,h,cycle,rb[h],expected_rb);
 end
 for(integer h=0;h<6;h=h+1)if(rb[h][550])begin
  if(!rb[h][548])rows_emitted=rows_emitted+1;
  if(rb[h][549])begin
   expected_end=op_start+2+5*op_ns+(op_ends/8)*((8*op_ns>op_stride)?8*op_ns:op_stride)+(op_ends%8)*op_ns+op_ns-1+(op_payload?2:1);
   if(cycle!=expected_end)$fatal(1,"end cycle got%0d expected%0d op%0d burst%0d",cycle,expected_end,op_id,op_ends);
   op_ends=op_ends+1;
  end
 end
 if(svq_v)begin
  if(svq!==gold[issued[rows_checked]])$fatal(1,"native SRAM readback row%0d got%h want%h",issued[rows_checked],svq,gold[issued[rows_checked]]);
  rows_checked=rows_checked+1;
 end
end
// Port results are ideal stimuli only at the declared serializer producer boundary.
// Every internal write, SRAM access and fixed read/return path is actual native RTL.
task automatic run_op(input integer id,sp,tiles,ts,base,ots,ojs,pay);
 integer ns,span,k,g,row,cap;
 begin
 ns=(sp<=7)?4:(sp==8)?2:(sp==9)?1:(sp==10)?3:1;
 op_started=1;op_base=base;op_ots=ots;op_ojs=ojs;
 op_id=id;op_tiles=tiles;op_ns=ns;op_stride=ts;op_payload=pay;op_split=sp;op_ends=0;
 start=1;count=4'(tiles);nh=4'(ns);stride=32'(ts);payload=pay;op_start=cycle;
 span=(tiles-1)*ts+8;
 for(integer age=0;age<span;age=age+1)begin
  for(integer h=0;h<6;h=h+1)rq[h]=0;
  cap=(age%ts<8);k=(age/ts)*8+age%ts;
  if(cap)for(integer h=0;h<6;h=h+1)begin
   rq[h][2212]=1;
   if(pay)for(integer j=0;j<4;j=j+1)begin
    if(sp<=9)g=h*(1<<(9-sp))+j;else g=j;
    if(j<ns&&(sp<=9||h==0))begin
     row=base+(k/8)*ots*(3072>>sp)+(k%8)*ojs+g*ots;
     rq[h][2212-4+j]=1;
     rq[h][552*j+:552]={24'(row),16'hffff,image(row,id)};
     // Deliberately wrong source payload is caught through actual SRAM readback.
     if(mut==1&&h==4)rq[h][552*j]=~rq[h][552*j];
     gold[row]=image(row,id);touched[row]=1;
    end
   end
  end
  // Deliberately off-calendar capture fault must be observable.
  if(mut==2&&age==1)rq[3][2212]=0;
  @(negedge clk);#0.01;start=0;
 end
 for(integer h=0;h<6;h=h+1)rq[h]=0;
 repeat(900)@(negedge clk);#0.01;
 if(op_ends!=8*tiles||sf!=0||vf)$fatal(1,"train fault op%0d ends%0d sf%b vf%b",id,op_ends,sf,vf);
 $display("OP id%0d split%0d tiles%0d ns%0d last_end_delta%0d",id,sp,tiles,ns,expected_end-op_start);
 end
endtask
initial begin
 for(integer h=0;h<6;h=h+1)rq[h]=0;
 for(integer r=0;r<65536;r=r+1)touched[r]=0;
 repeat(5)@(negedge clk);rst_n=1;repeat(30)@(negedge clk);#0.01;
 run_op(1,9,1,64,768,8,1,1);
 run_op(12,8,3,16,0,8,1,1);
 run_op(16,7,1,256,2975,8,1,1);
 run_op(20,8,3,48,0,8,1,1);
 run_op(110,10,1,8,8192,8,1,1);
 run_op(111,11,1,8,9216,8,1,1);
 run_op(64,7,8,8,16384,8,1,0);
 if(ld!=144)$fatal(1,"native landed count%0d expected144",ld);
 for(integer row=0;row<65536;row=row+1)if(touched[row])begin
  issued[read_issued]=row;read_issued=read_issued+1;svr={1'b1,20'(row)};@(negedge clk);
 end
 svr=0;repeat(60)@(negedge clk);
 if(rows_checked!=read_issued)$fatal(1,"missing native responses %0d/%0d",rows_checked,read_issued);
 $display("PASS b2 native halftrain SRAM checked%0d emitted%0d bursts144 with64headmarkers",rows_checked,rows_emitted);
 $finish;
end
endmodule
'''
(R/'tools/qwen_b2_join/tb_b2_train.sv').write_text(head+con+body)
