`timescale 1ns/1ps
// Opt-in SYSFACE reset forest. Every parent drives at most 32 asynchronous
// leaf-reset pins; every exposed leaf is budgeted for <=32 functional sinks.
// Release: two synchronization stages, parent, then leaf. The original SYSFACE
// has two synchronization stages plus region, so this adds one boot-only edge.
module qfd_sysface_reset32 #(parameter integer LEAVES=512)(
 input wire ck, input wire rst_n, output wire [LEAVES-1:0] leaf_n
);
 localparam integer GROUPS=(LEAVES+31)/32;
 (* async_reg="true", keep="true", dont_touch="true" *) reg [1:0] sync_q;
 (* keep="true", dont_touch="true" *) reg [GROUPS-1:0] parent_q;
 initial begin
  if (LEAVES<1 || LEAVES>960) $fatal(1,"SYSFACE_RESET32 bad LEAVES");
 end
 always @(posedge ck or negedge rst_n) begin
  if (!rst_n) begin sync_q<=2'b0; parent_q<={GROUPS{1'b0}}; end
  else begin sync_q<={sync_q[0],1'b1}; parent_q<={GROUPS{sync_q[1]}}; end
 end
 for (genvar g=0;g<GROUPS;g=g+1) begin: g_parent
  localparam integer N=((LEAVES-32*g)>32)?32:(LEAVES-32*g);
  (* keep="true", dont_touch="true" *) reg [N-1:0] q;
  always @(posedge ck or negedge parent_q[g])
   if (!parent_q[g]) q<={N{1'b0}}; else q<={N{1'b1}};
  assign leaf_n[32*g+:N]=q;
 end
endmodule
