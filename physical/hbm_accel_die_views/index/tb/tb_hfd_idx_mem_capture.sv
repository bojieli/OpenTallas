`timescale 1ns/1ps
module tb_hfd_idx_mem_capture;
  reg ck=0; always #0.5 ck=~ck;
  reg we=0,re=0; reg [9:0] wa=0,ra=0;
  reg [591:0] wd=0;
  wire [591:0] direct, captured;
  wire [67:0] cdirect, ccaptured;
  reg [591:0] expected;
  reg [67:0] cexpected;
  hfd_idx_mem #(.W(592),.AW(8),.READLAT(1)) a (ck,we,wa[7:0],wd,re,ra[7:0],direct);
  hfd_idx_mem #(.W(592),.AW(8),.READLAT(2)) b (ck,we,wa[7:0],wd,re,ra[7:0],captured);
  hfd_idx_mem #(.W(68),.AW(10),.READLAT(1)) c (ck,we,wa,wd[67:0],re,ra,cdirect);
  hfd_idx_mem #(.W(68),.AW(10),.READLAT(2)) d (ck,we,wa,wd[67:0],re,ra,ccaptured);
  always @(posedge ck) begin expected <= direct; cexpected <= cdirect; end
  integer i;
  initial begin
    for(i=0;i<256;i=i+1) begin
      @(negedge ck); we=1; wa=i; wd={18{32'h76543210 ^ (32'(i)*32'h10203)}};
    end
    @(negedge ck); we=0;
    for(i=0;i<1024;i=i+1) begin
      re=(i%7!=0); ra=i%256;
      @(negedge ck);
      if (i>2 && (captured !== expected || ccaptured !== cexpected))
        $fatal(1,"macro capture latency/data mismatch at beat %0d",i);
    end
    $display("PASS_HFD_IDX_MEM_CAPTURE continuous/gapped reads widths592/68 depth256/1024");
    $finish;
  end
endmodule
