`timescale 1ns/1ps
module tb_qfd_xpf_pw_loader;
 parameter integer MUT_WORD_ORDER=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,pv=0,start=0,stop=0;reg [9:0] pa=0;reg [63:0] pd=0;
 wire clear,cv,seal;wire [2:0] ix;wire [187:0] data;
 wire [3:0] count;wire [5:0] stage;wire [31:0] stop_cycle,cycle;
 wire lf,mf,active;wire [71:0] pf;reg si=0;
 ot_qfd_xpf_pw_loader l (.clk(clk),.rst_n(rst_n),.stage_active(active),.pw_v(pv),.pw_addr(pa),.pw_data(pd),
 .cfg_clear(clear),.cfg_v(cv),.cfg_seal(seal),.cfg_index(ix),.cfg_data(data),.cfg_count(count),
 .stage(stage),.stop_cycle(stop_cycle),.fault(lf));
 ot_qfd_xpf_static_schedule #(.ARM_TRANSPORT_EDGES(13)) m
 (.clk(clk),.rst_n(rst_n),.cfg_clear(clear),.cfg_v(cv),.cfg_seal(seal),.cfg_index(ix),.cfg_data(data),
 .cfg_count(count),.start(start),.stop(stop),.stage(stage),.me_issue(1'b0),.me_pc(12'd0),
 .su_issue(si),.su_pc(12'd0),.xpf(pf),.fault(mf),.active(active),.cycle(cycle));
 reg [187:0] record_r;integer c,seen=0;
 task tick;begin @(posedge clk);#0.1;if(lf||mf)$fatal(1,"real pw loader/static monitor fault");end endtask
 task write_pw(input [9:0] address,input [63:0] word_r);begin pv=1;pa=address;pd=word_r;tick();pv=0;end endtask
 initial begin
  repeat(3)tick();rst_n=1;
  // Program words travel untouched: the metadata decoder ignores them.
  write_pw(10'd0,64'h0123456789abcdef);
  write_pw(10'd1023,64'h5850463100000005);
  record_r={32'd30,32'd2,32'd14,6'd0,2'd2,12'd0,72'h800112002010002001};
  write_pw(MUT_WORD_ORDER!=0?10'd1005:10'd1004,record_r[63:0]);
  write_pw(10'd1005,record_r[127:64]);write_pw(10'd1006,{4'd0,record_r[187:128]});
  write_pw(10'd1022,64'h5850465400000023);
  write_pw(10'd1023,64'h5850463100000006);
  repeat(3)tick();start=1;tick();start=0;
  for(c=0;c<35;c=c+1)begin
   si=c==2;tick();
   if(pf[0])begin if(c!=14||pf!==72'h800112002010002001)$fatal(1,"compiled launch drift");seen=seen+1;end
  end
  si=0;stop=1;tick();stop=0;
  if(seen!=1||stop_cycle!=35)$fatal(1,"table/stop image mismatch");
  $display("PASS real pw10x64 typed image load, seal, fixed-cycle arm, no producer gating");$finish;
 end
endmodule
