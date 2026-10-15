`timescale 1ns/1ps
// All24physical result-port groups,4columns/group,4actualROMmacros/column.
// Each request is a fixed slot. Golden words observe results only.
module tb_scale_masks;
parameter integer WORDS=30576;
reg clk=0;always #1 clk=~clk;
reg valid=0;reg [23:0] address=0;
wire [6143:0] responses;
reg [255:0] expected[0:WORDS-1];
reg [8191:0] expected_path;
genvar port,column;
generate for(port=0;port<24;port=port+1)begin:g_port
 wire [1023:0] columns;
 for(column=0;column<4;column=column+1)begin:g_column
  ot_qwen_slab_pg_col #(.ROM_INSTANCE($sformatf("qslab_b%0d_h%0d_g%0d_c%0d",port/8,(port%8)/4,port%4,column))) dut (
   .clk(clk),.gre1(valid),.addr1(address),.cid(4'(column)),.m5(columns[256*column+:256]));
 end
 // The actual qfd_slab_result_half registered group merge,unchanged.
 reg [255:0] merged;
 always @(posedge clk)merged<=columns[255:0]|columns[511:256]|columns[767:512]|columns[1023:768];
 assign responses[256*port+:256]=merged;
end endgenerate
integer checked=0,errors=0,i,p;
reg [6:0] pending=0;
reg [23:0] delayed[0:6];
always @(posedge clk)begin
 pending<={pending[5:0],valid};delayed[0]<=address;
 for(integer j=1;j<7;j=j+1)delayed[j]<=delayed[j-1];
 #0.1;
 if(pending[6])begin
  for(p=0;p<24;p=p+1)begin
   if(responses[256*p+:256]!==expected[delayed[6]])begin
    errors=errors+1;
    if(errors<6)$display("MISMATCH addr=%0d port=%0d got=%h expected=%h",delayed[6],p,responses[256*p+:256],expected[delayed[6]]);
   end
  end
  checked=checked+1;
 end
end
initial begin
 if(!$value$plusargs("EXPECTED=%s",expected_path))$fatal(1,"missing declared observer expected words");
 $readmemh(expected_path,expected);
 repeat(8)@(negedge clk);
 for(i=0;i<WORDS;i=i+1)begin address=24'(i);valid=1;@(negedge clk);end
 valid=0;repeat(10)@(negedge clk);
 if(checked!=WORDS)begin errors=errors+1;$display("COUNT checked=%0d expected=%0d",checked,WORDS);end
 if(errors)$display("FAIL released_scale_masks errors=%0d checked=%0d macro_instances=384 fixed_group_latency=7",errors,checked);
 else $display("PASS released_scale_masks checked=%0d words lanes16 ports24 macro_instances384 fixed_group_latency7",checked);
 $finish;
end
endmodule
