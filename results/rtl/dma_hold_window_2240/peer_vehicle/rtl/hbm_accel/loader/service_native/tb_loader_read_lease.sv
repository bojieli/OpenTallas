`timescale 1ns/1ps
module tb_loader_read_lease;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg normal_v=0,normal_rsp_rdy=0,native_v=0,native_rsp_rdy=0,k_rdy=0,kr_v=0;
 reg[29:0]normal_addr=33,native_addr=99;reg[3:0]normal_len=5;reg[16:0]normal_tag=17'h01234;
 reg[15:0]native_tag=16'hbeef;reg[16:0]kr_tag=0;reg[3:0]kr_beat=0;reg[255:0]kr_data=0;
 wire normal_rdy,normal_rsp_v,native_rdy,native_rsp_v,k_v,kr_rdy,fault;
 wire[16:0]normal_rsp_tag,k_tag;wire[3:0]normal_rsp_beat,native_rsp_beat,k_len;
 wire[255:0]normal_rsp_data,native_rsp_data;wire[15:0]native_rsp_tag;wire[29:0]k_addr;
 ot_hbm_loader_read_lease #(.ENABLE(1))dut(.*);
 task tick;begin @(posedge clk);#1;end endtask
 integer i;
 initial begin
 tick;@(negedge clk);rst_n=1;tick;
 @(negedge clk);normal_v=1;native_v=1;k_rdy=0;
 for(i=0;i<4;i=i+1)begin tick;if(native_rdy||!k_v||k_addr!=33||k_tag!=normal_tag)$fatal(1,"normal stalled priority");end
 @(negedge clk);k_rdy=1;tick;@(negedge clk);normal_v=0;k_rdy=0;
 tick;if(native_rdy||k_v)$fatal(1,"native stole live lease");
 // Out-of-order normal beats with held responses, no release until all five.
 for(i=4;i>=0;i=i-1)begin
 @(negedge clk);kr_v=1;kr_tag=normal_tag;kr_beat=i;kr_data=i;
 tick;if(!normal_rsp_v||native_rsp_v||kr_rdy||normal_rsp_data!=i)$fatal(1,"normal held reply");
 @(negedge clk);normal_rsp_rdy=1;tick;@(negedge clk);kr_v=0;normal_rsp_rdy=0;
 end
 tick; // Native captured now that normal lease has drained.
 @(negedge clk);native_v=0;
 for(i=0;i<3;i=i+1)begin tick;if(!k_v||k_addr!=99||k_len!=1||k_tag!={1'b1,native_tag})$fatal(1,"native descriptor hold");end
 @(negedge clk);k_rdy=1;tick;@(negedge clk);k_rdy=0;normal_v=1;
 tick;if(normal_rdy||k_v)$fatal(1,"normal stole native lease");
 @(negedge clk);kr_v=1;kr_tag={1'b1,native_tag};kr_beat=0;kr_data=256'hfed;
 for(i=0;i<3;i=i+1)begin tick;if(!native_rsp_v||normal_rsp_v||kr_rdy||native_rsp_tag!=native_tag||native_rsp_data!=256'hfed)$fatal(1,"native response hold");end
 @(negedge clk);native_rsp_rdy=1;tick;@(negedge clk);kr_v=0;native_rsp_rdy=0;k_rdy=1;
 tick;@(negedge clk);normal_v=0;k_rdy=0;kr_v=1;kr_tag=normal_tag^1;
 tick;if(!fault||normal_rsp_v||native_rsp_v||kr_rdy)$fatal(1,"identity fault not fenced");
 $display("PASS normal priority five reorder beats native lease stalls held replies identity");$finish;
 end
endmodule
