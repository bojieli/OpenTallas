// Opt-in SPB0 static transport. Data has no reset; only the high control bits reset.
// Width/depth and the exact FF bank coordinates are part of the plan receipt.
(* keep_hierarchy, keep *)
module ot_hbm_spb0_regs #(parameter integer W=514, N=4, CW=2) (
 input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
 wire [W-1:0] chain [0:N];
 assign chain[0]=d;
 for (genvar j=0;j<N;j=j+1) begin:g_stage
  (* keep *) reg [W-1:0] rd;
  if (CW==0) begin:g_data
   always @(posedge clk) rd<=chain[j];
  end else begin:g_control
   always @(posedge clk) rd[W-CW-1:0]<=chain[j][W-CW-1:0];
   always @(posedge clk) if (!rst_n) rd[W-1:W-CW]<='0; else rd[W-1:W-CW]<=chain[j][W-1:W-CW];
  end
  assign chain[j+1]=rd;
 end
 assign q=chain[N];
endmodule
