`timescale 1ns/1ps
module tb_link_reset_profile;
 reg[3:0] clk=0,en=0;reg rst_n=0;integer edges[0:3];integer phase,j;
 wire[3:0]ov,ot,fault;wire[1139:0]packet;
 ot_hbm_svc_four_owner_links dut(.clk(clk),.rst_n(rst_n),.in_v(4'd0),.in_packet(1140'd0),
 .in_target(4'd0),.target_reserved(8'hff),.out_v(ov),.out_target(ot),.fault(fault),.out_packet(packet));
 for(genvar q=0;q<4;q=q+1)begin:g_clock
  always #0.512 if(en[q])clk[q]=~clk[q];
  always @(posedge clk[q] or negedge rst_n)if(!rst_n)edges[q]=0;else edges[q]=edges[q]+1;
  for(genvar k=0;k<48;k=k+1)begin:g_prove
   always @(posedge clk[q] or negedge rst_n)begin
    #0.02;
    if(!rst_n&&dut.g_link[q].u_link.g_slice[k].u_slice.reset_q!==0)$fatal(1,"FAIL reset async assertion");
    if(rst_n&&edges[q]==1&&dut.g_link[q].u_link.g_slice[k].u_slice.reset_q!==0)$fatal(1,"FAIL reset early release");
    if(rst_n&&edges[q]>=2&&dut.g_link[q].u_link.g_slice[k].u_slice.reset_q!==1)$fatal(1,"FAIL reset late release");
   end
  end
 end
 initial begin
  for(phase=0;phase<8;phase=phase+1)begin
   en=0;clk=0;rst_n=0;#0.03;
   for(j=0;j<4;j=j+1)edges[j]=0;
   #0.1;rst_n=1;#2.0; // raw release while all local clocks stopped
   for(j=0;j<4;j=j+1)begin
    en[j]=1;repeat(3)@(posedge clk[j]);@(negedge clk[j]);en[j]=0;
   end
   #(0.02*phase+0.05);rst_n=0;#0.03;if(ov||fault)$fatal(1,"FAIL reset occupied flags");
  end
  $display("PASS link_reset_profile raw8 first8 final196 independent_faces4 phases8 assert_without_clock release_exact2");$finish;
 end
endmodule
