`timescale 1ns/1ps
module tb_qwen_dspark_w1_dequant;
 parameter integer MUT=0;
 reg clk=0,rst=0,iv=0,orr=0;always #0.555555 clk=~clk;
 reg [511:0] codes;reg [15:0] scale;reg [63:0] id=0;reg [1:0] quarter;reg last;
 wire ready,ov,fault;wire [2047:0] vals;wire [63:0] oid;wire [1:0] oq;wire ol;
 ot_qwen_dspark_w1_dequant #(.ENABLE(1),.MUT_SIGN(MUT)) dut(.clk(clk),.rst_n(rst),.i_v(iv),.i_r(ready),.i_codes(codes),.i_scale(scale),.i_id(id),.i_quarter(quarter),.i_last(last),
  .o_v(ov),.o_r(orr),.o_values(vals),.o_id(oid),.o_quarter(oq),.o_last(ol),.fault(fault));
 integer f,scan,bad,packets=0,t;reg [2047:0] expected;reg [4095:0] path;
 initial begin
  if(!$value$plusargs("VECTORS=%s",path))$fatal(1,"missing vectors");
  f=$fopen(path,"r");if(!f)$fatal(1,"cannot open vectors");
  repeat(4)@(negedge clk);rst=1;repeat(3)@(negedge clk);
  while(!$feof(f))begin
   scan=$fscanf(f,"%h %h %h %d\n",codes,scale,expected,bad);
   if(scan==4)begin
    @(negedge clk);if(!ready)$fatal(1,"no finite credit");id=id+1;quarter=id[1:0];last=quarter==3;iv=1;
    @(negedge clk);iv=0;t=0;while(!ov&&!fault&&t<8)begin @(negedge clk);t=t+1;end
    if(bad)begin
     if(!fault||ov)$fatal(1,"nonfinite/overflow silently delivered scale=%h",scale);
     rst=0;repeat(2)@(negedge clk);rst=1;repeat(2)@(negedge clk);
    end else begin
     if(fault||!ov||vals!==expected||oid!==id||oq!==quarter||ol!==last)$fatal(1,"dequant mutant/golden mismatch scale=%h packet=%0d",scale,packets);
     if(packets%257==0)repeat(5)begin @(negedge clk);if(!ov||ready||vals!==expected||oid!==id)$fatal(1,"held response/identity unstable");end
     orr=1;@(negedge clk);orr=0;
    end
    packets=packets+1;
   end
  end
  if(packets!=262144)$fatal(1,"incomplete allINT8/allBF16 gate %0d",packets);
  $display("QWEN_W1_DEQUANT_PASS packets=%0d exact_or_quarantined_products=%0d allBF16=65536 allINT8=256 native64lanes=1 stall_identity=1",packets,packets*64);
  $finish;
 end
endmodule
