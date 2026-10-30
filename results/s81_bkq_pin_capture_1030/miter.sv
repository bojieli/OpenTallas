`timescale 1ns/1ps
module tb;
reg clk=0;always #1 clk=~clk;
reg rst_n=1;reg [514:0]lane=0;reg[543:0]rnd;
wire [620:0]g,d;
gold_hq_in gold(.clk(clk),.rst_n(rst_n),.lane(lane),.b_v(g[620]),.b_lv(g[619:604]),.b_val(g[603:348]),.b_idx(g[347:28]),.b_last(g[27]),.h_v(g[26]),.h_k(g[25:16]),.h_tag(g[15:8]),.h_q(g[7:6]),.act(g[5]),.act_q(g[4:3]),.e_fmt(g[2]),.e_orphan(g[1]),.e_link(g[0]));
gate_hq_in gate(.clk(clk),.rst_n(rst_n),.lane(lane),.b_v(d[620]),.b_lv(d[619:604]),.b_val(d[603:348]),.b_idx(d[347:28]),.b_last(d[27]),.h_v(d[26]),.h_k(d[25:16]),.h_tag(d[15:8]),.h_q(d[7:6]),.act(d[5]),.act_q(d[4:3]),.e_fmt(d[2]),.e_orphan(d[1]),.e_link(d[0]));

integer cyc=0,checks=0,resets=0,xwords=0,j;
task check;
begin
checks=checks+1;
`ifdef OT_S81PH_HQ_PIN_CAPTURE_MUT
if(cyc>16 && (g !== d || {gold.s0,gold.s0c,gold.s0d,gold.raw_type} !== {gate.s0,gate.s0c,gate.s0d,gate.raw_type})) begin
`else
if(g !== d || {gold.s0,gold.s0c,gold.s0d,gold.raw_type} !== {gate.s0,gate.s0c,gate.s0d,gate.raw_type}) begin
`endif
$display("HQ_PIN DIFF cycle=%0d outputs=%b capture=%b",cyc,g!==d,{gold.s0,gold.s0c,gold.s0d,gold.raw_type}!=={gate.s0,gate.s0c,gate.s0d,gate.raw_type});$fatal(1);
end
end endtask
always @(posedge clk)begin check;#0.01;check;end
always @(negedge rst_n)begin #0.01;check;end
initial begin
#0.2;rst_n=0;#0.4;rst_n=1;
for(cyc=0;cyc<12000;cyc=cyc+1)begin
@(negedge clk);for(j=0;j<17;j=j+1)rnd[32*j+:32]=$random;
lane=rnd[514:0];
if(cyc<512)begin lane[512:509]=cyc%16;lane[0]=1;end
if(cyc%31==0)begin lane[1+cyc%482]=1'bx;xwords=xwords+1;end
if(cyc%83==0)begin #0.2;rst_n=0;resets=resets+1;end
if(cyc%83==3)begin #0.2;rst_n=1;end
end
#1;$display("HQ_PIN PASS cycles=%0d checks=%0d resets=%0d xwords=%0d cutbits563 outputs621 cycles_added0",cyc,checks,resets,xwords);$finish;
end
endmodule
