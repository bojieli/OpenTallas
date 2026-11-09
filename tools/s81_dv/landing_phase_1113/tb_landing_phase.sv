module tb_landing_phase(input wire fclk,clk,rst_n,input wire[176:0]d,
 output reg[176:0]q,bad_q,output wire ready,fault);
 reg[176:0]source_q;
 wire[176:0]landed,bad_landed;
 always@(posedge fclk)source_q<=d;
 ot_dp_clk_landing #(.W(177),.WNEG(1)) good(.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(source_q),.q(landed),.ready(ready),.fault(fault));
 ot_dp_clk_landing #(.W(177),.WNEG(0)) wrongedge(.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(source_q),.q(bad_landed),.ready(),.fault());
 always@(posedge clk)begin q<=landed;bad_q<=bad_landed;end
endmodule
