`timescale 1ns/1ps
module tb;
reg clk=0;reg[5:0]addr=0;wire[63:0]q,mq;reg[63:0]words[0:63];integer i,bad=0,mbad=0;
ot_rom_64x64_m2 #(.INSTANCE("qc_dcal_image"),.VIAMAP("not_used.hex")) d(.clk(clk),.ce_in(1'b1),.addr_in(addr),.rd_out(q));
ot_rom_64x64_m2 #(.INSTANCE("mutant_control"),.VIAMAP("not_used.hex")) m(.clk(clk),.ce_in(1'b1),.addr_in(addr),.rd_out(mq));
always #1 clk=~clk;
initial begin
$readmemh("words.hex",words);
for(i=0;i<64;i=i+1) begin @(negedge clk);addr=i;@(posedge clk);#0.1;if(q!==words[i])bad=bad+1;if(mq!==words[i])mbad=mbad+1;end
$display("RUNTIME_ALIAS width=64 words=64 mismatches=%0d mutant=%0d",bad,mbad);
if(bad||!mbad)$fatal(1,"runtime alias failure");$finish;
end
endmodule
