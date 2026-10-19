`default_nettype none
// Kept onehot SOP leaves prevent a shared binary selector from becoming a
// thousand-load control. Payload and selector FFs are deliberately unreset:
// the caller must issue open_d before sampling any row after reset.
(* keep_hierarchy = "yes" *)
module ot_hbm_cache_kept_read16 (
 input wire clk,
 input wire [31:0] select_next,
 input wire [511:0] quarter_slices,
 output wire [15:0] data
);
 (* keep = "true" *) reg [31:0] select_q;
 always @(posedge clk) select_q <= select_next;
 genvar b,k;
 generate for(b=0;b<16;b=b+1)begin:g_bit
  wire [31:0] terms;
  for(k=0;k<32;k=k+1)begin:g_term
   assign terms[k]=quarter_slices[k*16+b]&select_q[k];
  end
  assign data[b]=|terms;
 end endgenerate
endmodule

// OFFSET is the output quarter (0..16). Each row advances exactly 17 quarters
// modulo32, equivalent to native8's sector-head plus phase*64 gather.
// open_d / advance_d are predictions for the following cycle's local
// controls. They enter native local Q here. Open has priority over advance.
// Following an open_d sampling edge N, pointer and all four leaf selectors
// initialize together at N+1; output is valid combinationally after N+1.
// A caller capturing that data at N+2 therefore gets normal single-edge paths.
(* keep_hierarchy = "yes" *)
module ot_hbm_cache_kept_read64 #(
 parameter integer OFFSET=0,
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire open_d,advance_d,
 input wire [2047:0] ring_data,
 output wire [63:0] data
);
 (* keep = "true" *) reg open_q,advance_q;
 (* keep = "true" *) reg [31:0] pointer_q;
 localparam [31:0] INITIAL=32'b1<<((OFFSET+(MUT==1?1:0))%32);
 wire [31:0] advanced={pointer_q[14:0],pointer_q[31:15]};
 wire [31:0] pointer_next=open_q?INITIAL:(advance_q?advanced:pointer_q);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin open_q<=0;advance_q<=0;end
  else begin open_q<=open_d;advance_q<=advance_d;end
 end
 // Copy the NEXT expression into parent and child FFs on the same edge.
 // Copying pointer_q instead would add an accidental selector-delay edge.
 always @(posedge clk) pointer_q<=pointer_next;
 genvar s,q;
 generate for(s=0;s<4;s=s+1)begin:g_slice
  wire [511:0] slices;
  for(q=0;q<32;q=q+1)begin:g_quarter
   assign slices[q*16+:16]=ring_data[q*64+s*16+:16];
  end
  ot_hbm_cache_kept_read16 u_slice(
   .clk(clk),.select_next(pointer_next),.quarter_slices(slices),
   .data(data[s*16+:16]));
 end endgenerate
endmodule
`default_nettype wire
