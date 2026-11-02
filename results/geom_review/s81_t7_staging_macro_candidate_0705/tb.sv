`timescale 1ps/1ps
module tb;
reg clk=0; always #416.5 clk=~clk;
reg [3:0] we=0; reg [7:0] wa=0,ra=0;reg [1059:0] wd=0;
wire [1059:0] qb,qm,qbad;wire [7:0] badra=(ra==159)?0:ra+1'b1;
ot_hdc_v41x_attn_staging #(.D(32),.NL(4),.TROWS(640),.SRAM_MACRO(0)) a(clk,we,wa,wd,ra,qb);
ot_hdc_v41x_attn_staging #(.D(32),.NL(4),.TROWS(640),.SRAM_MACRO(1)) b(clk,we,wa,wd,ra,qm);
ot_hdc_v41x_attn_staging #(.D(32),.NL(4),.TROWS(640),.SRAM_MACRO(1)) bad(clk,we,wa,wd,badra,qbad);
reg [264:0] oracle[0:3][0:159];reg[1059:0] expectq;integer i,j,k,c,checks=0,mut=0,collisions=0;reg[31:0] rng=32'h9f48201a;
task randomdata;begin for(k=0;k<1060;k=k+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);wd[k]=rng[0];end end endtask
initial begin
// Initialize every legal row in both implementations; power-up state is outside claim.
for(i=0;i<160;i=i+1)begin @(negedge clk);we=15;wa=i;ra=i;randomdata();@(posedge clk);#1;for(j=0;j<4;j=j+1)oracle[j][i]=wd[j*265+:265];end
for(c=0;c<2400;c=c+1)begin
 @(negedge clk);randomdata();we=c%16;wa=(rng>>8)%160;ra=rng%160;if(c%3==0)begin ra=wa;collisions=collisions+1;end
 for(j=0;j<4;j=j+1)expectq[j*265+:265]=oracle[j][ra];
 @(posedge clk);#1;
 if(qb!==expectq || qm!==expectq)begin $display("FAIL cycle%0d ra%0d wa%0d we%h",c,ra,wa,we);$fatal(1);end
 if(qbad!==expectq)mut=mut+1;
 for(j=0;j<4;j=j+1)if(we[j])oracle[j][wa]=wd[j*265+:265];
 checks=checks+1060;
end
if(mut==0)$fatal(1,"MUTANT_NOT_CAUGHT");
$display("PASS D32_NL4_TROWS640 SRAM8 legal_initialized_rows checks=%0d cycles=%0d collisions=%0d wrong_address_mutant=%0d",checks,c,collisions,mut);$finish;
end
endmodule
