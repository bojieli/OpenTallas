`timescale 1ns/1ps
// Functional non-inverting BUF model only; actual Liberty Y function A is
// checked by the source gate. This fixture provides no buffer timing credit.
module BUFx4_ASAP7_75t_R(input wire A,output wire Y);
assign Y=A;
endmodule
module tb_qwen_rom_bank5_distribution;
reg [4:0] read_n,term;
reg [11:0] address;
reg reset_n;
wire [84:0] read_sink;
wire [79:0] term_sink;
wire [119:0] macro_addr;
wire [89:0] reset_sink;
integer k,b,i,checks=0;
ot_qwen_rom_bank5_control_distribution dut(read_n,term,address,reset_n,read_sink,term_sink,macro_addr,reset_sink);
task check;
begin
#1;
for(b=0;b<5;b=b+1) begin
 for(i=0;i<17;i=i+1) if(read_sink[17*b+i] !== read_n[b]) $fatal(1,"read bank ownership");
 for(i=0;i<16;i=i+1) if(term_sink[16*b+i] !== term[b]) $fatal(1,"term bank ownership");
end
for(i=0;i<10;i=i+1) if(macro_addr[12*i+:12] !== address) $fatal(1,"address bit ownership");
for(i=0;i<90;i=i+1) if(reset_sink[i] !== reset_n) $fatal(1,"reset distribution");
checks=checks+1;
end
endtask
initial begin
read_n=0;term=0;address=0;reset_n=0;check();
for(k=0;k<12;k=k+1) begin address=1<<k;read_n=1<<(k%5);term=~read_n;reset_n=k%2;check();end
address=12'hfff;read_n=5'h1f;term=0;reset_n=1;check();
address=12'hxxx;read_n=5'bx0x1x;term=5'b1x0xz;reset_n=1'bx;check();
$display("PASS_BANK5_DISTRIBUTION checks=%0d no_timing_credit",checks);$finish;
end
endmodule
