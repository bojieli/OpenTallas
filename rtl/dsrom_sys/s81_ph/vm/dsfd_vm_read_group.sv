`timescale 1ns/1ps
// One-client VM response regrouping. SU/HC issue batches as contiguous prefixes
// containing slot 0; returning slot-0's credit only after the whole batch keeps
// one batch in flight. Backend responses can arrive independently or reordered.
// The original request mask/data leave together: RB/QR pairs and wide HC/SU
// beats therefore retain the existing arithmetic grouping under real VM timing.
module dsfd_vm_read_group #(parameter integer NR=16, MUT_EARLY=0)(
 input wire ck, rst_n,
 input wire [NR-1:0] rq_v, input wire [NR*14-1:0] rq_row,
 output reg [NR-1:0] rq_credit, output reg [NR-1:0] rs_v,
 output reg [NR*512-1:0] rs_d,
 output reg [NR-1:0] b_rq_v, output reg [NR*14-1:0] b_rq_row,
 input wire [NR-1:0] b_rq_credit, b_rs_v,
 input wire [NR*512-1:0] b_rs_d,
 output reg fault
);
 reg online, active;
 reg [NR-1:0] init_tokens, mask, seen;
 reg [NR*512-1:0] data;
 always @(posedge ck or negedge rst_n) begin : run
  integer s;
  reg [NR-1:0] got;
  reg [NR*512-1:0] assembled;
  if (!rst_n) begin
   online<=0; active<=0; init_tokens<=0; mask<=0; seen<=0;
   rq_credit<=0; rs_v<=0; b_rq_v<=0; fault<=0; data<=0; rs_d<=0; b_rq_row<=0;
  end else begin
   rq_credit<=0; rs_v<=0; b_rq_v<=0;
   if (!online) begin
    init_tokens<=init_tokens|b_rq_credit;
    if (&(init_tokens|b_rq_credit)) begin online<=1; rq_credit<={NR{1'b1}}; end
    if (|rq_v || |b_rs_v) fault<=1;
   end else begin
    if (|rq_v) begin
     // Native clients use contiguous slot prefixes: otherwise an unused slot-0
     // token could permit another batch before this one had completed.
     if (active || !rq_v[0] || ((rq_v & (rq_v + {{(NR-1){1'b0}},1'b1})) != 0)) fault<=1;
     else begin
      active<=1; mask<=rq_v; seen<=0; b_rq_v<=rq_v; b_rq_row<=rq_row;
     end
    end
    if (|b_rs_v) begin
     if (!active || |(b_rs_v & ~mask) || |(b_rs_v & seen)) fault<=1;
     else begin
      got=seen|b_rs_v; assembled=data;
      for (s=0;s<NR;s=s+1) if (b_rs_v[s]) assembled[512*s+:512]=b_rs_d[512*s+:512];
      seen<=got; data<=assembled;
      if (MUT_EARLY) begin rs_v<=b_rs_v; rs_d<=b_rs_d; rq_credit<=b_rs_v; end
      if (got==mask) begin
       active<=0;
       if (!MUT_EARLY) begin rs_v<=mask; rs_d<=assembled; rq_credit<=mask; end
      end
     end
    end
   end
  end
 end
endmodule
