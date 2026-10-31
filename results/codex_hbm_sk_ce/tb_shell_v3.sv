`timescale 1ns/1ps
module tb_shell_v3;
parameter LAND=1,ADV=0,CAPADD=0,DELAY=2;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;reg [767:0] mixes=0,bases=0;reg [95:0] scales=0;
wire av,bv,af,bf;wire [767:0] ar,br;wire en,iv,ird,ov,sf;wire [511:0] ie,y;
ot_hbm_hc_tail_unit_static_se gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(av),.result(ar),.fault(af));
tail_shell_v3#(.LAND(LAND),.ADV(ADV),.CAPADD(CAPADD),.DELAY(DELAY))cut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(bv),.result(br),.fault(bf));
localparam D=2+CAPADD;reg[767:0]ard[0:D-1];reg avd[0:D-1],afd[0:D-1];integer z;always@(posedge clk)begin ard[0]<=ar;avd[0]<=av;afd[0]<=af;for(z=1;z<D;z=z+1)begin ard[z]<=ard[z-1];avd[z]<=avd[z-1];afd[z]<=afd[z-1];end end
integer i,j,n=0,errors=0,edges=0,seed=19;
always @(negedge clk)if(rst_n)begin
 edges=edges+1;if(avd[D-1]!==bv||afd[D-1]!==bf||(avd[D-1]&&ard[D-1]!==br))begin errors=errors+1;if(errors<5)$display("DIFF edge%0d valid=%b/%b fault=%b/%b data=%b",edges,avd[D-1],bv,afd[D-1],bf,ard[D-1]===br);end
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
 $display("SHELL %s LAND=%0d ADV=%0d CAPADD=%0d DELAY=%0d errors=%0d results=%0d edges=%0d",errors==0&&n==40?"PASS":"FAIL",LAND,ADV,CAPADD,DELAY,errors,n,edges);$finish;
end
endmodule
