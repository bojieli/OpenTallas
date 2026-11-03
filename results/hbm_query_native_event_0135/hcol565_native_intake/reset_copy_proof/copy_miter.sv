module copy_miter(input clk,input rst_n,output mismatch);
wire[0:0]gold;wire[8:0]gate;
ot_rst_delivered3 #(.REGIONS(1)) g(.clk(clk),.rst_n_in(rst_n),.rst_n(gold));
ot_rst_delivered3 #(.REGIONS(9)) t(.clk(clk),.rst_n_in(rst_n),.rst_n(gate));
reg[2:0]warm=0;
always @(posedge clk)warm<={warm[1:0],1'b1};
assign mismatch=warm[2] && (gate!={9{gold[0]}});
endmodule
