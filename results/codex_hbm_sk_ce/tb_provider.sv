`timescale 1ns/1ps
module tb_provider;
localparam CAPADD=3;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;reg [767:0] mixes=0,bases=0;reg [95:0] scales=0;
wire av,bv,af,bf;wire [767:0] ar,br;wire en,iv,ird,ov,sf;wire [511:0] ie,y;
ot_hbm_hc_tail_unit_static_se gold(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(av),.result(ar),.fault(af));
ot_hbm_hc_tail_unit_static_ce_phys cut(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(mixes),.bases(bases),.scales(scales),.result_v(bv),.result(br),.fault(bf));
localparam D=2+CAPADD;reg[767:0]ard[0:D-1];reg avd[0:D-1],afd[0:D-1];integer z;always@(posedge clk)begin ard[0]<=ar;avd[0]<=av;afd[0]<=af;for(z=1;z<D;z=z+1)begin ard[z]<=ard[z-1];avd[z]<=avd[z-1];afd[z]<=afd[z-1];end end
integer age=0;always@(posedge clk)if(!rst_n||launch)age<=0;else age<=age+1;wire due_fault,early_fault;root_consumer_probe due(clk,rst_n,launch,{1'b0,bv},age==508,due_fault);root_consumer_probe early(clk,rst_n,launch,{1'b0,bv},age==507,early_fault);
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
 $display("PROVIDER %s errors=%0d results=%0d edges=%0d due509_fault=%b early508_fault=%b",errors==0&&n==40&&!due_fault&&early_fault?"PASS":"FAIL",errors,n,edges,due_fault,early_fault);$finish;
end
endmodule

module root_consumer_probe(input clk,rst_n,launch,input[1:0]tv,input e_emit,output reg tail_fault);
wire rst_c=rst_n,e_tl=launch;wire e_tunit=0,e_eunit=0;wire[2:0]e_tpos=0;wire[191:0]have={192{1'b1}};reg[2:0]tpos[0:1];reg[1:0]tready;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin tready <= 0; tail_fault <= 0; end
        else begin
            for (integer u = 0; u < 2; u = u + 1) begin
                if (tv[u]) tready[u] <= 1'b1;
                if (e_tl && e_tunit == u) begin tready[u] <= 1'b0; tpos[u] <= e_tpos; end
            end
            if (e_tl && have[e_tpos*24 +: 24] != 24'hffffff) tail_fault <= 1'b1;
            if (e_emit && !tready[e_eunit]) tail_fault <= 1'b1;
        end
    end

endmodule
