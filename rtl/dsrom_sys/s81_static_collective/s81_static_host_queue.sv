`timescale 1ns/1ps
`default_nettype none
// s81_static_host_queue (S-BIND r6 2026-10-15; owner static-cycle rule 2026-10-14 18:59: no credits / backpressure):
// the host face of the static S81 collective.  The layer-die host (dsfd_host_c +DSFD_HOST_C_STATIC) drives
// f_host[76:0] = {alive, status 11, completion {v, d 64}}: alive / status are levels, a completion is a single-edge
// pulse emitted whenever the ingest finishes one -- the host needs neither a credit nor knowledge of the calendar.
// Every f_host bit is pin-registered (+1 edge); a completion pulse is queued (DEPTH entries) and the channel takes the
// head on the COMPILED host tx slot: host_tx_valid is asserted exactly on the slot (dsfd_coll_static_channels faults on
// any other edge), with the current status and either the queued completion {1, d} or {0, 64'd0} (status-only beat).
// A completion that finds the queue full, or a host slot while the host is not alive, is a sticky fault (the image
// compiler sizes the host slots to the completion rate); nothing stalls, nothing is retimed.
// MUT 2 (negative control): the queue never pops -- the completion is never sent.
module s81_static_host_queue #(parameter integer DEPTH=16, parameter integer MUT=0)(
 input wire clk, input wire rst_n,
 input wire[76:0] f_host, input wire slot,
 output wire host_tx_valid, output wire[10:0] host_status, output wire[64:0] host_completion,
 output reg fault
);
 localparam integer AW=$clog2(DEPTH);
 reg[76:0] p;
 always @(posedge clk or negedge rst_n) if(!rst_n) p<=77'd0; else p<=f_host;
 reg[63:0] q[0:DEPTH-1];
 reg[AW:0] n; reg[AW-1:0] wp, rp;
 wire pop = slot && (n!=0) && (MUT!=2);
 wire full = (n==DEPTH);
 wire push = p[64] && !(full && !pop);
 always @(posedge clk) if(push) q[wp]<=p[63:0];
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin n<=0; wp<=0; rp<=0; fault<=1'b0; end
  else begin
   if(push) wp<=wp+1'b1;
   if(pop) rp<=rp+1'b1;
   n<=n+(push?1'b1:1'b0)-(pop?1'b1:1'b0);
   if((p[64] && full && !pop) || (slot && !p[76])) fault<=1'b1;
  end
 assign host_tx_valid = slot && p[76];
 assign host_status = p[75:65];
 assign host_completion = (n!=0) ? {1'b1, q[rp]} : 65'd0;
endmodule
`default_nettype wire
