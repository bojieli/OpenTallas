`timescale 1ns/1ps
// The actual hardened two-ROM pair. Native IDs are compile-time constants.
// A case cohort aliases exact immutable target masks to this one identical
// physical circuit; the case receipt records the original tile/bank IDs.
module tb_code_pair;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,ce=0,any_row=0,slot=0;
reg [11:0] address=0;
wire [1023:0] result;
ot_qwen_tile_rpair #(.ROM_TILE(0),.ROM_BANK(0)) dut(
 .clk(clk),.rst_n(rst_n),.ce_d(ce),.any_d(any_row),.ad_d(address),.r_q(result));
reg [511:0] expected_code[0:4095];reg [15:0] expected_bf16[0:255];
reg [8191:0] path,lookup_path;
reg [6:0] pending=0,read_expected=0;
reg [11:0] delayed[0:6];
integer checked=0,errors=0,i,b;
reg [1023:0] golden;
always @(posedge clk)begin
 pending<={pending[5:0],slot};read_expected<={read_expected[5:0],ce};delayed[0]<=address;
 for(integer j=1;j<7;j=j+1)delayed[j]<=delayed[j-1];
 #0.1;
 if(pending[6])begin
  golden=0;
  if(read_expected[6])for(b=0;b<64;b=b+1)golden[16*b+:16]=expected_bf16[expected_code[delayed[6]][8*b+:8]];
  if(result!==golden)begin
   errors=errors+1;
   if(errors<4)$display("MISMATCH addr=%0d read=%0d got=%h expected=%h",delayed[6],read_expected[6],result,golden);
  end
  checked=checked+1;
 end
end
initial begin
 if(!$value$plusargs("EXPECTED=%s",path)||!$value$plusargs("LOOKUP=%s",lookup_path))$fatal(1,"missing observer input");
 $readmemh(path,expected_code);$readmemh(lookup_path,expected_bf16);
 repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 for(i=0;i<4096;i=i+1)begin address=12'(i);ce=1;any_row=1;slot=1;@(negedge clk);end
 for(i=0;i<4;i=i+1)begin ce=0;any_row=1;slot=1;@(negedge clk);end
 ce=0;any_row=0;slot=0;repeat(10)@(negedge clk);
 if(checked!=4100)begin errors=errors+1;$display("COUNT checked=%0d",checked);end
 if(errors)$display("FAIL released_code_pair errors=%0d checked=%0d fixed_latency7",errors,checked);
 else $display("PASS released_code_pair checked4100 codewords4096 physicalROM2 int8codes64 fixed_latency7");
 $finish;
end
endmodule
