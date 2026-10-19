module controller_vehicle(input wire clk,rst_n,start,q_word,go,output reg eq_v,output reg [9:0] rc,output reg [4:0] q_have,output reg run,output reg [31:0] fc);
localparam [9:0] nbeat=0;
always @(posedge clk or negedge rst_n) begin
 if (!rst_n) begin q_have<=0; run<=0; rc<=0; eq_v<=0; fc<=0; end
 else begin
  if(start) q_have<=0;
  if (q_word && !start) q_have <= q_have + 1'b1;
  eq_v<=0;
  if(go) begin
   run <= 1'b1; rc <= 10'd1;
   if (q_have != 5'd16) fc[9] <= 1'b1;
  end else if(run) begin
   eq_v <= rc <= 10'd16;
   if (rc >= 10'd16 && rc >= nbeat) run <= 1'b0;
   rc <= rc + 1'b1;
  end
 end
end
endmodule
