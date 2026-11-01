`timescale 1ns/1ps
module tb_split;
parameter MUT=0;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;reg [767:0] mixes=0,bases=0;reg [95:0] scales=0;
wire av,bv,af,bf;wire [767:0] ar,br;wire en,iv,ird,ov,sf;wire [511:0] ie,y;
ot_hbm_hc_tail_unit_static_se gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(av),.result(ar),.fault(af));
ot_hbm_hc_tail_rest_core_ce #(.MUT_EN(MUT)) cut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(bv),.result(br),.fault(bf),.sk_en_sk(en),.sk_in_valid(iv),.sk_in_e(ie),.sk_in_ready(ird),.sk_out_valid(ov),.sk_fault(sf),.sk_y(y));
ot_hdc_sinkhorn_se sink(.clk(clk),.rst_n(rst_n),.sk_en(en),.in_valid(iv),.in_ready(ird),.in_e(ie),.out_valid(ov),.y(y),.fault(sf),.busy());
integer i,j,n=0,errors=0,edges=0,seed=19;
always @(negedge clk)if(rst_n)begin
 edges=edges+1;if(av!==bv||af!==bf||(av&&ar!==br))begin errors=errors+1;if(errors<5)$display("DIFF edge%0d",edges);end
 if(av)n=n+1;
end
initial begin
 repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
 for(i=0;i<40;i=i+1)begin
  for(j=0;j<24;j=j+1)begin mixes[j*32+:32]={1'b0,8'd126,23'($random(seed))};bases[j*32+:32]={1'b0,8'd125,23'($random(seed))};end
  for(j=0;j<3;j=j+1)scales[j*32+:32]={1'b0,8'd126,23'($random(seed))};
  launch=1;@(negedge clk);launch=0;repeat(530)@(negedge clk);
 end
 repeat(20)@(negedge clk);
 $display("SPLIT %s MUT=%0d errors=%0d results=%0d edges=%0d",errors==0&&n==40?"PASS":"FAIL",MUT,errors,n,edges);$finish;
end
endmodule
