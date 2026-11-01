`timescale 1ns/1ps
module tb_tailmax;
reg clk=0; always #5 clk=~clk; reg rst_n=0,launch=0,capture=0; reg [767:0] mixes=0,bases=0; reg [95:0] scales=0; reg [511:0] sy=0;
wire [2:0] ready,rv,fault;wire [767:0] result[0:2];wire [511:0] se[0:2];
ot_gold_static  g(.clk(clk),.rst_n(rst_n),.sk_en(1'b0),.sk_en_sk(1'b0),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.sink_launch(1'b0),.sink_capture(capture),.e_ready(ready[0]),.result_v(rv[0]),.result(result[0]),.fault(fault[0]),.sk_in_e(se[0]),.sk_in_ready(1'b1),.sk_out_valid(1'b1),.sk_fault(1'b0),.sk_y(sy));
ot_hbm_hc_tail_static_rest_ce #(.BALANCED_MAX(1)) c(.clk(clk),.rst_n(rst_n),.sk_en(1'b0),.sk_en_sk(1'b0),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.sink_launch(1'b0),.sink_capture(capture),.e_ready(ready[1]),.result_v(rv[1]),.result(result[1]),.fault(fault[1]),.sk_in_e(se[1]),.sk_in_ready(1'b1),.sk_out_valid(1'b1),.sk_fault(1'b0),.sk_y(sy));
ot_mutant_static #(.BALANCED_MAX(1)) m(.clk(clk),.rst_n(rst_n),.sk_en(1'b0),.sk_en_sk(1'b0),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.sink_launch(1'b0),.sink_capture(capture),.e_ready(ready[2]),.result_v(rv[2]),.result(result[2]),.fault(fault[2]),.sk_in_e(se[2]),.sk_in_ready(1'b1),.sk_out_valid(1'b1),.sk_fault(1'b0),.sk_y(sy));
integer trials=0,mutants=0; bit different;
task tick; begin @(posedge clk); #1; if(rst_n && ({ready[0],rv[0],fault[0],result[0],se[0]} !== {ready[1],rv[1],fault[1],result[1],se[1]})) $fatal(1,"PUBLIC MISMATCH trial %0d",trials); end endtask
initial begin repeat(2)tick; rst_n=1;
for(integer tcase=0;tcase<4000;tcase=tcase+1)begin
for(integer j=0;j<24;j=j+1)begin mixes[32*j+:32]=$urandom; bases[32*j+:32]=$urandom;end
if(tcase<16)for(integer j=8;j<24;j=j+1)mixes[32*j+:32]=((tcase+j)%2==0)?32'h80000000:32'h00000000;
if(tcase>=16 && tcase<32)for(integer j=8;j<24;j=j+1)mixes[32*j+:32]=(j%4==0)?32'h7fc00001:(j%4==1)?32'h7f800001:(j%4==2)?32'hff800001:32'hffc00001;
for(integer j=0;j<3;j=j+1)scales[32*j+:32]=$urandom;
for(integer j=0;j<16;j=j+1)sy[32*j+:32]=$urandom;
launch=1;tick;launch=0;repeat(60)tick;
different=0;for(integer j=0;j<4;j=j+1)begin if(g.mx[j] !== c.mx[j])$fatal(1,"MAX MISMATCH trial %0d group %0d %h %h",tcase,j,g.mx[j],c.mx[j]);if(g.mx[j] !== m.mx[j])different=1;end
if(different)mutants=mutants+1;trials=trials+1;capture=1;tick;capture=0;tick;
end
if(mutants==0)$fatal(1,"MUTANT ESCAPED");$display("PASS actual production max registers %0d trials, 4 groups/trial, signedzero/NaN ties, mutant caught %0d, addedcycles0",trials,mutants);$finish;end
endmodule
