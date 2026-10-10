module reset_identity(input clk,rst_n,eng_en,output erst_n_out,output [3:0] eg_out);
(* keep *) reg erst_n; reg [3:0] eg; always @(posedge clk or negedge rst_n) if(!rst_n) begin erst_n<=0;eg<=0;end else begin erst_n<=eng_en;eg<={eg[2:0],eng_en};end assign erst_n_out=erst_n;assign eg_out=eg; endmodule
