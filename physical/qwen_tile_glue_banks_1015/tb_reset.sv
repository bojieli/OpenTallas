`timescale 1ns/1ps
module tb_reset;
`ifndef MUT
`define MUT 0
`endif
reg clk=0,rst_n=0;
wire [95:0] resets;
reg [2:0] reference=0;
wire [513:0] q;
reg [513:0] d={257{2'b10}};
integer n,checks=0,errors=0;
ot_qwen_native_reset_tree #(.MUT(`MUT)) tree(.ck_reset({9{clk}}),.rst_n(rst_n),.child_reset_n(resets));
ot_qwen_tile_glue_word #(.W(514),.SPLIT_RESET(1)) bank(.ck_lo(clk),.ck_hi(clk),.rst_n(resets[0]),.rst_hi_n(resets[1]),.d(d),.q(q));
task step;
begin
 #4;clk=1;reference={reference[1:0],rst_n};#1;
 checks=checks+96;
 if(resets !== {96{reference[2]}})errors=errors+1;
 clk=0;
end
endtask
initial begin
 // All constant-reset masters initialize while capturing the asserted reset.
 for(n=0;n<16;n=n+1)begin #4;clk=1;#1;clk=0;end
 reference=0;
 if(resets!==96'd0 || q!==514'd0)errors=errors+1;
 rst_n=1;
 for(n=1;n<=8;n=n+1)begin
  step();checks=checks+514;
  if(n<7 ? q!==514'd0 : q!==d)errors=errors+1;
 end
 for(n=0;n<512;n=n+1)begin
  rst_n=((n%11)>3);step();
 end
 rst_n=0;
 for(n=0;n<16;n=n+1)step();
 if(q!==514'd0)errors=errors+1;
 if(errors)begin $display("FAIL native_reset_tree checks=%0d errors=%0d",checks,errors);$fatal;end
 $display("PASS native_reset_tree checks=%0d fixed_reset_edges=3 first_data_edge=7",checks);$finish;
end
endmodule
