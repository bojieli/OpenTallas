`timescale 1ps/1fs
module tb;
  parameter integer MUTANT=0; // 1: rsel_oh loaded from rbin (one edge late)
  reg wclk=0,rclk=0; always #500 wclk=~wclk; always #683 rclk=~rclk;
  reg wrst_n=0,rrst_n=0; reg we=0,re=0; reg [287:0] wdata=0;
  wire full0,full1,empty0,empty1; wire [287:0] rd0,rd1; wire [2:0] f0,f1;
  ot_wbq_root_s7_rr_fifo #(.W(288),.AW(2),.RSEL(0)) a(.wclk(wclk),.wrst_n(wrst_n),.we(we),.wdata(wdata),.full(full0),.rd_freed(f0),.rclk(rclk),.rrst_n(rrst_n),.re(re),.rdata(rd0),.empty(empty0));
  ot_wbq_root_s7_rr_fifo #(.W(288),.AW(2),.RSEL(1)) b(.wclk(wclk),.wrst_n(wrst_n),.we(we),.wdata(wdata),.full(full1),.rd_freed(f1),.rclk(rclk),.rrst_n(rrst_n),.re(re),.rdata(rd1),.empty(empty1));
  integer errs=0,cyc=0,beats=0;
  always @(posedge rclk) if(rrst_n) begin
    cyc=cyc+1;
    if(rd0!==rd1 || empty0!==empty1 || full0!==full1 || f0!==f1) errs=errs+1;
    if(!empty0 && re) beats=beats+1;
  end
  always @(posedge wclk) begin we<=($urandom%3!=0); wdata<={9{$urandom}}; end
  always @(posedge rclk) re<=($urandom%2);
  // async reset pulses in both clock domains at random times, mid-run
  initial begin repeat(20) begin #($urandom_range(20000,60000)); rrst_n=0; wrst_n=0; #($urandom_range(300,3000)); wrst_n=1; #($urandom_range(0,900)); rrst_n=1; end end
  initial begin repeat(8) @(posedge wclk); wrst_n=1; rrst_n=1; repeat(40000) @(posedge rclk); $display("RSEL_BENCH errs=%0d cycles=%0d beats=%0d",errs,cyc,beats); $finish; end
endmodule
