`timescale 1ns/1ps
module tb_shell;
parameter LAND=1,ADV=0;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;reg [767:0] mixes=0,bases=0;reg [95:0] scales=0;
wire av,bv,af,bf;wire [767:0] ar,br;wire en,iv,ird,ov,sf;wire [511:0] ie,y;
ot_hbm_hc_tail_unit_static_se gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(av),.result(ar),.fault(af));
tail_shell#(.LAND(LAND),.ADV(ADV))cut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(bv),.result(br),.fault(bf));
reg[767:0]ard0,ard1;reg avd0,avd1,afd0,afd1;always@(posedge clk)begin ard0<=ar;ard1<=ard0;avd0<=av;avd1<=avd0;afd0<=af;afd1<=afd0;end
integer i,j,n=0,errors=0,edges=0,seed=19;
always @(negedge clk)if(rst_n)begin
 edges=edges+1;if(avd1!==bv||afd1!==bf||(avd1&&ard1!==br))begin errors=errors+1;if(errors<5)$display("DIFF edge%0d",edges);end
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
 $display("SHELL %s LAND=%0d ADV=%0d errors=%0d results=%0d edges=%0d",errors==0&&n==40?"PASS":"FAIL",LAND,ADV,errors,n,edges);$finish;
end
endmodule
