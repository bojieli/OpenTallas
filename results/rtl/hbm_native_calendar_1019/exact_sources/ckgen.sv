`timescale 1ns/1ps
`default_nettype none
module hfd_ckgen (
    input  wire refclk,           
    input  wire por_n,            
    output wire pll_stream, output wire pll_serial, output wire pll_hbm, output wire pll_link,
    output wire por_stream, output wire por_serial, output wire por_hbm, output wire por_link
);
    wire locked;
    ot_hbm_pll_bb_m16 u_pll (.refclk(refclk), .reset_n(por_n), .clk_stream(pll_stream), .clk_serial(pll_serial),
                         .clk_hbm(pll_hbm), .clk_link(pll_link), .locked(locked));
    hfd_ckgen_rel4_m16 u_rel (.ck_stream(pll_stream), .ck_serial(pll_serial), .ck_hbm(pll_hbm), .ck_link(pll_link),
                          .por_n(por_n), .locked(locked),
                          .rst_stream(por_stream), .rst_serial(por_serial), .rst_hbm(por_hbm), .rst_link(por_link));
endmodule
module hfd_ckgen_rel4_m16 (input wire ck_stream, ck_serial, ck_hbm, ck_link, input wire por_n, locked,
                       output wire rst_stream, rst_serial, rst_hbm, rst_link);
    hfd_ckgen_rel_m16 u_rs (.ck(ck_stream), .por_n(por_n), .locked(locked), .rst_n(rst_stream));
    hfd_ckgen_rel_m16 u_rr (.ck(ck_serial), .por_n(por_n), .locked(locked), .rst_n(rst_serial));
    hfd_ckgen_rel_m16 u_rh (.ck(ck_hbm),    .por_n(por_n), .locked(locked), .rst_n(rst_hbm));
    hfd_ckgen_rel_m16 u_rl (.ck(ck_link),   .por_n(por_n), .locked(locked), .rst_n(rst_link));
endmodule
module hfd_ckgen_rel_m16 (input wire ck, input wire por_n, input wire locked, output wire rst_n);
    wire arm_n = por_n & locked;
    reg [1:0] s;
    always @(posedge ck or negedge arm_n)
        if (!arm_n) s <= 2'b00;
        else        s <= {s[0], 1'b1};
    assign rst_n = s[1];
endmodule
`default_nettype wire
`timescale 1ns/1ps
module ot_hbm_pll_bb_m16(input wire refclk, reset_n, output reg clk_stream,clk_serial,clk_hbm,clk_link,locked);
 initial begin clk_stream=0;clk_serial=0;clk_hbm=0;clk_link=0;locked=0;end
 integer acquisition=0;
 always #0.416667 clk_stream=~clk_stream;
 always #0.555556 clk_serial=~clk_serial;
 always #0.512 clk_hbm=~clk_hbm;
 always #0.416667 clk_link=~clk_link;
 always @(posedge refclk or negedge reset_n)
  if(!reset_n) begin acquisition<=0;locked<=0;end
  else if(acquisition==3) locked<=1;
  else acquisition<=acquisition+1;
endmodule
module tb_hfd_ckgen_m16;
 reg refclk=0,por_n=0;always #5 refclk=~refclk;
 wire pll_stream,pll_serial,pll_hbm,pll_link,por_stream,por_serial,por_hbm,por_link;
 hfd_ckgen dut(.*);
 wire [3:0] ck={pll_link,pll_hbm,pll_serial,pll_stream}, po={por_link,por_hbm,por_serial,por_stream};
 integer edges[0:3],checks=0;
 genvar g;
 for(g=0;g<4;g=g+1)begin:E
  always @(posedge ck[g]) if(dut.u_pll.locked&&por_n) edges[g]=edges[g]+1; else edges[g]=0;
  always @(posedge po[g]) begin
   if(edges[g]!==2)$fatal(1,"domain%0d released after %0d own edges (want 2)",g,edges[g]);
   checks=checks+1;
  end
 end
 task automatic cycle_reset;begin
  #3.3;por_n=0;#0.01;if(po!==4'b0)$fatal(1,"por_n low must assert all resets asynchronously");checks=checks+1;
  #40;if(po!==4'b0)$fatal(1,"released while por_n low");checks=checks+1;
  por_n=1;wait(dut.u_pll.locked);if(po!==4'b0)$fatal(1,"released before lock");checks=checks+1;
  #10;if(po!==4'b1111)$fatal(1,"not all released 10 ns after lock: %b",po);checks=checks+1;
 end endtask
 initial begin
  for(integer k=0;k<4;k=k+1)edges[k]=0;
  repeat(3)cycle_reset;
  $display("CKGEN_PASS checks=%0d domains=4 release_edges=2 async_assert=1",checks);$finish;
 end
endmodule
