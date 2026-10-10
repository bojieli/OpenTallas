`timescale 1ps/1fs
`default_nettype none
// hbm-phys-1010 [idx] (lead decision 10-10, R25GQ: index score lanes 12 a stack = 48 a die, NOT 8): the LINE REGROUP of
// one stack's 12-lane native score grid.  The svc's key-line service is unchanged (8 ports, port p carries lines
// p, p+8, ... of the stack's key region, a frame = 8 * ceil(nq / 16) lines, 2^FA credits a port); the grid scores 12
// keys a beat in three L4 column taps (hfd_idx_score #(.L(4), .BK(12), .LANE0(4t))), so a beat is the 6 lines
// 6b .. 6b+5 and tap t's port j takes line 6b + 2t + j.  This block lands the 8 svc ports (one FIFO each, credit
// return), and issues one 6-line group a cycle in line order (line n sits at the head of port n % 8 when every
// earlier line has gone; the group base 6b % 8 cycles 0, 6, 4, 2), padding the frame's last group with zero lines
// (tag = line number) up to 6 * ceil(nl / 6) lines so the taps' beats stay whole.  The frame size comes from the
// stack's q bus (kind 1 config, n_q12), which lands here and leaves as one registered copy per tap (the slot is a column
// of this block beside the three stacked taps, each tap's W face abutting this block's E face: no q chain through the
// taps).
//
// Ports (every input lands in a flop, every output leaves a flop):
//   ik   8 x {data1088, tag10, v} from the svc; ikc 8 credit pulses back (one line freed)
//   q    {payload568, kind2, v} from hfd_idx_sel; qx 3 registered copies, copy t to tap t
//   lo   6 x {data1088, tag10, v} to the taps (lo port 2t + j -> tap t port j); loc 6 credit pulses from the taps
//        (2^FT credits a port = the taps' landing FIFO depth)
//   st   {fault, active} (registered): fault = a q config while a frame is still issuing
module hfd_idx_lrg #(
  parameter integer FA = 6,          // svc-side landing FIFO address bits (the svc holds 2^FA credits a port)
  parameter integer FT = 4           // tap-side credits a port = the taps' FIFO depth (hfd_idx_score FA)
) (
  input  wire              ck,
  input  wire              rst,
  input  wire [8*1099-1:0] ik,
  output reg  [7:0]        ikc,
  input  wire [570:0]      q,
  output wire [3*571-1:0]  qx,
  output wire [6*1099-1:0] lo,
  input  wire [5:0]        loc,
  output reg  [1:0]        st
);
  localparam integer NI = 8, NO = 6, LW = 1098;
  reg rs1, rs2;
  always @(posedge ck or negedge rst) if (!rst) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
  // ------------------------------------------------------------------ q bus pin register, one output copy per tap
  reg qv; reg [1:0] qk; reg [567:0] qp;
  always @(posedge ck or negedge rn) if (!rn) qv <= 1'b0; else qv <= q[0];
  always @(posedge ck) begin qk <= q[2:1]; qp <= q[570:3]; end
  genvar t;
  generate for (t = 0; t < 3; t = t + 1) begin : gq
    reg ov_; reg [569:0] od_;
    always @(posedge ck or negedge rn) if (!rn) ov_ <= 1'b0; else ov_ <= qv;
    always @(posedge ck) od_ <= {qp, qk};
    assign qx[t*571 +: 571] = {od_, ov_};
  end endgenerate
  // ------------------------------------------------------------------ svc line landing
  wire [NI-1:0] lne; wire [LW-1:0] lrd [0:NI-1];
  reg  [NI-1:0] pop;
  genvar p;
  generate for (p = 0; p < NI; p = p + 1) begin : gp
    reg cv; reg [LW-1:0] cd;
    always @(posedge ck or negedge rn) if (!rn) cv <= 1'b0; else cv <= ik[p*1099];
    always @(posedge ck) cd <= ik[p*1099+1 +: LW];
    wire [FA:0] cnt_;
    hfd_idx_fifo #(.W(LW), .AW(FA)) u_f (.ck(ck), .rst_n(rn), .we(cv), .wd(cd), .re(pop[p]), .rd(lrd[p]), .ne(lne[p]),
      .cnt(cnt_));
  end endgenerate
  // ------------------------------------------------------------------ frame + group issue
  reg active, fault;
  reg [10:0] ln, nl;                       // next line to issue, lines of the frame (8 * ceil(nq / 16))
  (* keep *) reg [1:0] ph [0:NO-1];        // (ln / 2) % 4 per output lane (replicated: each drives a 1,098-bit 4:1 mux)
  reg [5:0] cred [0:NO-1];
  reg [NO-1:0] locq;
  wire [NO-1:0] need, ok, hascred;
  wire [2:0] port [0:NO-1];
  genvar j;
  generate for (j = 0; j < NO; j = j + 1) begin : gj
    assign port[j] = 3'({ph[j], 1'b0} + 3'(j));
    assign need[j] = (ln + 11'(j)) < nl;
    assign ok[j] = !need[j] || lne[port[j]];
    assign hascred[j] = cred[j] != 6'd0;
  end endgenerate
  wire fire = active && (ln < nl) && (&ok) && (&hascred);
  integer k, m;
  always @* begin
    pop = {NI{1'b0}};
    for (k = 0; k < NO; k = k + 1) if (fire && need[k]) pop[port[k]] = 1'b1;
  end
  // output pin registers
  reg [NO-1:0] ov; reg [LW-1:0] od [0:NO-1];
  always @(posedge ck) if (fire)
    for (k = 0; k < NO; k = k + 1)
      od[k] <= need[k] ? {lrd[port[k]][LW-1:10], 10'(ln + 11'(k))} : {1088'd0, 10'(ln + 11'(k))};
  generate for (j = 0; j < NO; j = j + 1) begin : go
    assign lo[j*1099 +: 1099] = {od[j], ov[j]};
  end endgenerate
  always @(posedge ck or negedge rn) begin
    if (!rn) begin
      active <= 1'b0; fault <= 1'b0; ln <= 11'd0; nl <= 11'd0; ov <= {NO{1'b0}}; ikc <= 8'd0; locq <= {NO{1'b0}};
      st <= 2'd0;
      for (m = 0; m < NO; m = m + 1) begin ph[m] <= 2'd0; cred[m] <= 6'(1 << FT); end
    end else begin
      ikc <= pop;
      locq <= loc;
      ov <= {NO{fire}};
      for (m = 0; m < NO; m = m + 1) cred[m] <= cred[m] - {5'd0, fire} + {5'd0, locq[m]};
      if (qv && qk == 2'd1) begin                 // frame config: n_q12 = qp[29:18]
        if (active && ln < nl) fault <= 1'b1;
        active <= 1'b1; ln <= 11'd0; nl <= {8'((qp[29:18] + 12'd15) >> 4), 3'b000};
        for (m = 0; m < NO; m = m + 1) ph[m] <= 2'd0;
      end else if (fire) begin
        ln <= ln + 11'd6;
        for (m = 0; m < NO; m = m + 1) ph[m] <= ph[m] + 2'd3;   // (ln + 6) / 2 = ln / 2 + 3
        if (ln + 11'd6 >= nl) active <= 1'b0;
      end
      st <= {fault, active};
    end
  end
endmodule
`default_nettype wire
