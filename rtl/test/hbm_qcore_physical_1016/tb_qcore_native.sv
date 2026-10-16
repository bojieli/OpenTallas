`timescale 1ns/1ps
`default_nettype none
module tb_qcore_native;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [53:0] rf_rd_cmd=0;
 reg [73:0] red_cmd=0;
 reg [1:0] rf_drain_cmd=0;
 reg [127:0] slice_x=0;
 reg [3:0] rf_wv=0;
 reg [31:0] rf_wa=0;
 reg [127:0] rf_wd=0;
 reg rr_wv=0; reg[4:0]rr_wa=0; reg[255:0]rr_wd=0;reg[31:0]sfu_x=0;
 wire[127:0]rf_bword;wire[35:0]rf_bcmd;wire[255:0]rf_dsec;
 wire red_sv,red_rf_v,fault;wire[31:0]red_tag,red_x;
 ot_hbm_su_static_qcore #(.MUT(MUT),.COLLPORT(1)) dut(
 .clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),.rst_n(rst_n),
 .rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),.rf_drain_cmd(rf_drain_cmd),.slice_x(slice_x),
 .rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),.rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),
 .red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.red_rf_v(red_rf_v),.rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),.sfu_x(sfu_x),.fault(fault));
 reg[31:0]model[0:255];reg exp_v[0:19999];reg[31:0]exp_x[0:19999],exp_tag[0:19999];
 integer cyc=0,checks=0,errors=0,rf_checks=0,scalar_checks=0,guard_checks=0;
 reg monitor=0;
 task automatic ck(input bit ok,input string msg);
 begin checks=checks+1;if(!ok)begin errors=errors+1;if(errors<20)$display("ERROR cycle=%0d %s",cyc,msg);end end endtask
 task automatic tick;
 begin @(posedge clk);#1;cyc=cyc+1;
 if(monitor)begin
  ck(red_sv===exp_v[cyc],$sformatf("scalar edge expected=%b got=%b",exp_v[cyc],red_sv));
  if(exp_v[cyc])begin
   ck(red_x===exp_x[cyc],$sformatf("scalar expected=%h got=%h",exp_x[cyc],red_x));
   ck(red_tag===exp_tag[cyc],"scalar tag identity");scalar_checks=scalar_checks+1;
  end
  ck(red_rf_v===(red_sv&&red_tag[8]),"registered native reducer RF head valid/tag[8]");
 end
 end endtask
 task automatic idle(input integer n);begin repeat(n)tick();end endtask
 task automatic reset_core;
 begin rst_n=0;monitor=0;rf_rd_cmd=0;red_cmd=0;rf_drain_cmd=0;rf_wv=0;rr_wv=0;idle(5);rst_n=1;idle(5);monitor=1;end endtask
 task automatic read4(input integer addr);
 integer p;begin
 for(p=0;p<4;p=p+1)rf_rd_cmd[p*9+:9]={1'b1,8'((addr+p)%256)};
 tick();ck(rf_bcmd===rf_rd_cmd[35:0],"RF command pin rung fixed edge");rf_rd_cmd=0;idle(3);
 for(p=0;p<4;p=p+1)begin ck(rf_bword[p*32+:32]===model[(addr+p)%256],$sformatf("RF addr=%0d expected=%h got=%h",(addr+p)%256,model[(addr+p)%256],rf_bword[p*32+:32]));rf_checks=rf_checks+1;end
 end endtask
 task automatic readsector(input integer row,input integer sec);
 integer w;begin
 rf_rd_cmd[45+:9]={1'b1,2'(row),3'(sec),3'd0};tick();rf_rd_cmd=0;idle(3);
 for(w=0;w<8;w=w+1)begin ck(rf_dsec[w*32+:32]===model[row*64+sec*8+w],"sector drain bank order and word identity");rf_checks=rf_checks+1;end
 end endtask
 task automatic red(input integer op,input integer a,input integer b,input integer dst,input integer src,input[31:0]value,input[31:0]tag,input bit emits,input[31:0]answer);
 begin
 // src0..3 slice; src4 RF(class4 address0); src5 new SFU join.
 slice_x={4{value}};sfu_x=value;
 red_cmd={1'b1,3'(op),10'(a),10'(b),10'(dst),tag,1'(src>=4),7'((src==5)?64:((src<4)?src*16:0))};
 tick();if(emits)begin exp_v[cyc+11]=1;exp_x[cyc+11]=answer;exp_tag[cyc+11]=tag;end
 red_cmd=0;idle(14);
 end endtask
 integer i,row,block,p,sec,w;reg[31:0]v;
 initial begin
 for(i=0;i<20000;i=i+1)begin exp_v[i]=0;exp_x[i]=0;exp_tag[i]=0;end
 reset_core();
 // Four real relay writers cover every bank and row, without conflicts.
 for(row=0;row<4;row=row+1)for(block=0;block<16;block=block+1)begin
  rf_wv=4'hf;for(p=0;p<4;p=p+1)begin
   rf_wa[p*8+:8]=8'(row*64+block*4+p);v=32'h3f800000|32'((row*64+block*4+p)*32+p);rf_wd[p*32+:32]=v;model[row*64+block*4+p]=v;
  end tick();
 end
 rf_wv=0;idle(3);for(i=0;i<256;i=i+4)read4(i);
 for(row=0;row<4;row=row+1)for(sec=0;sec<8;sec=sec+1)readsector(row,sec);
 ck(!fault,"legacy relay/RF reads have no fault");
 // Actual COLL RR input replaces all rows/sectors, then all replicas/drains are observed.
 for(row=0;row<4;row=row+1)for(sec=0;sec<8;sec=sec+1)begin
  rr_wv=1;rr_wa={2'(row),3'(sec)};
  for(w=0;w<8;w=w+1)begin v=32'h40000000|32'((row*64+sec*8+w)*64+w);rr_wd[w*32+:32]=v;model[row*64+sec*8+w]=v;end tick();
 end
 rr_wv=0;idle(3);for(i=0;i<256;i=i+4)read4(i);
 for(row=0;row<4;row=row+1)for(sec=0;sec<8;sec=sec+1)readsector(row,sec);
 ck(!fault,"RR writes and all reads have no fault");
 // Reducer all six op kinds, fixed11-edge scalar return and native tag[8] output.
 red(0,0,0,0,0,32'h3f800000,0,0,0); // scratch0 = 1
 red(0,0,0,1,1,32'h40000000,0,0,0); // scratch1 = 2
 red(0,0,0,2,5,32'h40800000,0,0,0); // new SFU operand, scratch2 = 4
 red(4,2,0,0,0,0,32'h00000102,1,32'h40800000);
 red(4,0,0,0,0,0,32'h00000003,1,32'h3f800000);
 red(1,0,0,3,2,32'h40000000,0,0,0); // ADD_EXT 1+2=3
 red(4,3,0,0,0,0,32'h00000104,1,32'h40400000);
 red(2,0,1,4,0,0,0,0,0); // ADD_TREE 1+2=3
 red(4,4,0,0,0,0,32'h00000005,1,32'h40400000);
 red(3,0,0,5,3,32'h41000000,0,0,0); // MAX_EXT 1,8 =>8
 red(4,5,0,0,0,0,32'h00000106,1,32'h41000000);
 red(5,1,2,6,0,0,0,0,0); // MAX_TREE 2,4=>4
 red(4,6,0,0,0,0,32'h00000007,1,32'h40800000);
 // RF class4 external operand uses the real read path and a fixed prefetch slot.
 rf_rd_cmd[36+:9]={1'b1,8'd0};tick();rf_rd_cmd=0;idle(2);
 red(0,0,0,7,4,0,0,0,0);red(4,7,0,0,0,0,32'h00000108,1,model[0]);
 ck(!fault,"all supported reducers/operands have no fault");
 // Drain guard: src0 does not require an RF read (MUT16 must fault).
 rf_drain_cmd=2'b10;tick();rf_drain_cmd=0;idle(2);ck(!fault,"non-RF drain skips class5 requirement");guard_checks=guard_checks+1;
 reset_core();rf_drain_cmd=2'b11;tick();rf_drain_cmd=0;idle(2);ck(fault,"RF drain without prefetch faults");guard_checks=guard_checks+1;
 reset_core();rf_rd_cmd[45+:9]={1'b1,8'd8};tick();rf_rd_cmd=0;rf_drain_cmd=2'b11;tick();rf_drain_cmd=0;idle(2);ck(!fault,"RF drain with exact prior prefetch is legal");guard_checks=guard_checks+1;
 reset_core();rf_wv=4'b0011;rf_wa=0;tick();rf_wv=0;idle(2);ck(fault,"two relay writers in one bank fault");guard_checks=guard_checks+1;
 reset_core();rf_wv=1;rf_wa=0;rr_wv=1;rr_wa=0;tick();rf_wv=0;rr_wv=0;idle(2);ck(fault,"relay and RR same bank conflict faults");guard_checks=guard_checks+1;
 $display("QCORE_NATIVE checks=%0d rf_words=%0d scalars=%0d guards=%0d cycles=%0d errors=%0d",checks,rf_checks,scalar_checks,guard_checks,cyc,errors);
 if(errors||rf_checks!=1024||scalar_checks!=7||guard_checks!=5)$fatal(1,"QCORE_NATIVE FAIL");
 $display("QCORE_NATIVE PASS");$finish;
 end
 initial begin #199000;$fatal(1,"QCORE_NATIVE timeout FAIL");end
endmodule
`default_nettype wire
