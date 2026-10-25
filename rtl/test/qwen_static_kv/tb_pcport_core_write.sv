`timescale 1ps/1fs
module tb_pcport_core_write #(parameter integer MUT=0);
 reg ck=0,rst_n=0,w_v=0,col_v=0;
 always #416.5 ck=~ck;
 reg[255:0]w_d=0;
 wire[287:0]wd0,wd1;wire f0,f1;
 qkd_ctrl_pc_port_child_nc #(.CORE_CLOCK(0)) reference_port(.hclk(ck),.hrst(rst_n),
 .col_v_e(col_v),.col_we_e(col_v),.col_sr_e(col_v),.w_v(w_v),.w_d(w_d),.pi(289'b0),
 .wd(wd0),.kv_v(),.kv_d(),.em_v(),.em_d(),.fault(f0));
 qkd_ctrl_pc_port_child_nc #(.CORE_CLOCK(1)) core_port(.hclk(ck),.hrst(rst_n),
 .col_v_e(col_v),.col_we_e(col_v),.col_sr_e(col_v),.w_v(w_v),.w_d(w_d),.pi(289'b0),
 .wd(wd1),.kv_v(),.kv_d(),.em_v(),.em_d(),.fault(f1));
 reg[287:0]expected1,expected2,last_wd;
 integer active_cycles=0,changes=0;
 always @(posedge ck)begin expected1<=wd0;expected2<=expected1;end
 always @(negedge ck)if(rst_n)begin
  active_cycles=active_cycles+1;
  if(active_cycles>16)begin
   if(wd1!==expected2)$fatal(1,"WRITE_LATENCY_MITER expected exactly2added data edges");
   if(f0||f1)$fatal(1,"invalid test traffic faults port");
   if(wd1!=last_wd)changes=changes+1;
  end
  last_wd=wd1;
 end
 initial begin
  if(MUT)force core_port.g_wdata2.wd_q2=core_port.g_wdata2.wd_q1;
  repeat(10)@(negedge ck);rst_n=1;
  // hrst crosses hr_q before the input face can accept w_v.
  repeat(4)@(negedge ck);
  for(integer i=0;i<1024;i=i+1)begin
   w_v=(i%32)<4;col_v=(i%32)>=4&&(i%32)<8;w_d={8{32'(100+i)}};
   @(negedge ck);
  end
  w_v=0;col_v=0;repeat(10)@(negedge ck);
  if(changes<120)$fatal(1,"write miter insufficient changing payloads %0d",changes);
  $display("PASS core write latency lockstep128words changes%0d delay+2 MUT%0d",changes,MUT);$finish;
 end
endmodule
