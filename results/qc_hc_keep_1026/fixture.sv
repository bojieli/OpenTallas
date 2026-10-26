module keep_hc(input ck,input a,input b,input [3:0] d,output [15:0] p,output [8:0] pool,output [15:0] words);
(* keep = "true" *) reg [15:0] PDc;
(* keep = "true" *) reg [8:0] POOLc;
(* keep = "true" *) reg [3:0] grid[0:1][0:1];
always @(posedge ck) begin
 PDc <= {16{a}};POOLc <= {9{b}};
 grid[0][0]<=d;grid[0][1]<=d;grid[1][0]<=d;grid[1][1]<=d;
end
assign p=PDc;assign pool=POOLc;
assign words={grid[1][1],grid[1][0],grid[0][1],grid[0][0]};
endmodule
