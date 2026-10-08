`timescale 1ps/1fs
// Plesiochronous idle-insertion bench: the TX runs PPM faster than the RX (PPM < 0: slower) and offers a flit every
// cycle; ot_hbm_coll_idle_insert forces an idle after M flits; the receiver's elastic buffer is the committed
// protected CDC (II1 refill, W 64, AW 6 = 64 entries) written with flits only, read every RX cycle.
// Checks: no overflow (IDLE_RX_OVERFLOW), order (IDLE_ORDER), and that the spacing rule held (IDLE_SPACING in RTL).
module tb_coll_idle_insert;
 parameter integer M=1024, PPM=200, NFLITS=1500000, CHECK_M=1;
 localparam real TR=833.333;
 localparam real TT=TR*(1.0-PPM*1.0e-6);
 reg tclk=0,rclk=0;
 initial begin #(100); forever #(TT/2.0) tclk=~tclk; end
 initial begin #(377); forever #(TR/2.0) rclk=~rclk; end
 reg por=1;wire wrst_n,rrst_n;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) u_r(.clk_stream(tclk),.clk_link(rclk),.por_stream(por),.por_link(por),.rst_n(wrst_n),.prst_n(rrst_n));
 wire slot,send;reg in_v=0;
 ot_hbm_coll_idle_insert #(.M(M),.PPM((PPM<0)?-PPM:PPM),.CHECK(CHECK_M)) dut(.clk(tclk),.rst_n(wrst_n),.in_v(in_v),.slot(slot),.send(send));
 integer tx=0,rx=0,occ_max=0;reg [63:0] din=0;
 wire in_r,out_v,we,re,f;wire [63:0] dout;
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(64),.AW(6)) u_eb(.wclk(tclk),.wrst_n(wrst_n),.in_v(send),.in_r(in_r),.in_d(din),
  .rclk(rclk),.rrst_n(rrst_n),.out_v(out_v),.out_r(1'b1),.out_d(dout),.wempty(we),.rempty(re),.fault(f));
 always @(negedge tclk)begin in_v=wrst_n&&rrst_n&&tx<NFLITS;din=tx;end
 always @(posedge tclk)if(wrst_n&&send)begin
  if(!in_r)$fatal(1,"IDLE_RX_OVERFLOW elastic buffer full after %0d flits (M=%0d, %0d ppm)",tx,M,PPM);
  tx=tx+1;
 end
 always @(posedge rclk)if(rrst_n&&out_v)begin
  if(dout!==rx)$fatal(1,"IDLE_ORDER got %0d expected %0d",dout,rx);
  rx=rx+1;
  if(tx-rx>occ_max)occ_max=tx-rx;
 end
 initial begin
  repeat(4)@(posedge rclk);por=0;
  wait(rx==NFLITS);
  if(f)$fatal(1,"IDLE_CDC_FAULT");
  $display("PASS_IDLE flits=%0d M=%0d ppm=%0d occupancy_max=%0d idle_fraction_x1e6=%0d",NFLITS,M,PPM,occ_max,(M>0)?1000000/(M+1):0);
  $finish;
 end
endmodule
