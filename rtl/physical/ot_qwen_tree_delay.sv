// Exact fixed-cycle tree padding. Every stage is a full-width register.
// LAT=0 is an analytical/bench identity; physical leaf jobs require LAT>=1.
module ot_qwen_tree_delay #(parameter integer DW=512, LAT=21)
  (input wire clk, input wire [DW-1:0] d, output wire [DW-1:0] q);
  generate if(LAT==0) begin:g_identity
    assign q=d;
  end else begin:g_delay
    (* keep *) reg [DW-1:0] stage [0:LAT-1];
    integer i;
    always @(posedge clk) begin
      stage[0]<=d;
      for(i=1;i<LAT;i=i+1) stage[i]<=stage[i-1];
    end
`ifdef OT_QTREE_MUT_DROP
    if(LAT==1) assign q=d;
    else assign q=stage[LAT-2];
`elsif OT_QTREE_MUT_FLIP
    assign q=stage[LAT-1] ^ {{(DW-1){1'b0}},1'b1};
`else
    assign q=stage[LAT-1];
`endif
  end endgenerate
endmodule
