`timescale 1ps/1fs
`default_nettype none
// hbm-phys-1010 [idx] (R25GQ 12-lane grid): atomic three-tap join + 12 -> 16 lane gearbox behind the UNCHANGED native
// 16-lane score boundary (s = {idx20 x16, score16 x16, kv16, fault16, last, v}, 610 b, one credit a beat), so
// hfd_idx_sel / _native_qend and the die nets see the same block-aligned 16-key beats as the L16 grid.
//
// The three L4 taps (hfd_idx_score #(.L(4), .BK(12), .LANE0(4t))) score the 12-key beats 12b .. 12b+11 (tap t: lanes
// 4t .. 4t+3).  Their beats land in one FIFO each (CRED credits a tap, as hfd_idx_t4_join) and are joined atomically
// (all three heads, same last).  The gearbox keeps a 0/4/8/12-lane remainder H: the 12 new lanes append to H and every
// complete 16-lane group (keys 16m .. 16m+15: block aligned) is a candidate output beat.  A group is sent iff its lane 0
// holds a valid key (kv) or it is the frame's first beat (the empty frame's single beat); the svc frame is
// 8 * ceil(nq / 16) lines and the taps' 6 * ceil(nl / 6), so the groups sent are exactly the ceil(nq / 16) beats (>= 1)
// the L16 grid sends, the key-valid lanes being a prefix.  At the tap's last beat the remainder (padded with zero
// lanes) is a second candidate group; when both go, the second leaves the next cycle (input held one cycle), and the
// last one sent carries `last`.  fault: taps out of step, a FIFO overflow, a credit over-return, a frame end that
// sends nothing.
module hfd_idx_t3_join #(parameter integer AW = 7, CRED = 128) (
  input  wire          ck, rst,
  input  wire [461:0]  taps,          // 3 x {beat153, v}
  output reg  [2:0]    tap_credit,
  output wire [609:0]  s,
  input  wire          sc,
  output reg           fault
);
  localparam integer LN = 38;         // a lane {idx20, score16, kv, fault}
  reg rs1, rs2;
  always @(posedge ck or negedge rst) if (!rst) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
`ifndef SYNTHESIS
  reg mut_gb;   // negative control: the remainder lanes are dropped (H not kept)
  initial mut_gb = $test$plusargs("MUT_GB");
`else
  localparam mut_gb = 1'b0;
`endif
  wire [2:0] ne; wire [152:0] head [0:2]; wire [AW:0] occ [0:2];
  generate for (genvar t = 0; t < 3; t = t + 1) begin : gt
    hfd_idx_fifo #(.W(153), .AW(AW)) u_q (.ck(ck), .rst_n(rn), .we(taps[t*154]), .wd(taps[t*154+1 +: 153]),
      .re(fire), .rd(head[t]), .ne(ne[t]), .cnt(occ[t]));
  end endgenerate
  // the 12 new lanes
  wire [LN-1:0] bl [0:11];
  generate for (genvar l = 0; l < 12; l = l + 1) begin : gb
    localparam integer T = l / 4, I = l % 4;
    assign bl[l] = {head[T][73 + 20*I +: 20], head[T][9 + 16*I +: 16], head[T][5 + I], head[T][1 + I]};
  end endgenerate
  wire blast = head[0][0];
  wire last_ok = (head[0][0] == head[1][0]) && (head[0][0] == head[2][0]);
  reg [LN-1:0] hl [0:11];             // remainder lanes
  reg [3:0] h;                        // 0, 4, 8, 12
  reg sent;                           // a beat of this frame went
  reg pend; reg [16*LN-1:0] pg;       // second group of a frame end, sent the next cycle
  reg [8:0] credits; reg scq;
  reg sv; reg [608:0] sd;
  wire fire = (&ne) && !pend && credits >= 9'd2 && !fault && last_ok;
  // C = H[0 .. h-1] ++ B[0 .. 11] ++ zero lanes (32 lanes)
  reg [LN-1:0] c [0:31];
  integer i;
  always @* begin
    for (i = 0; i < 32; i = i + 1)
      c[i] = (i < h) ? hl[i < 12 ? i : 0] : ((i - h) < 12 ? bl[(i - h) < 12 ? i - h : 0] : {LN{1'b0}});
  end
  wire full0 = h != 4'd0;                         // h + 12 >= 16  <=>  h >= 4 (h is 0, 4, 8 or 12)
  wire [4:0] tot = {1'b0, h} + 5'd12;
  wire e0 = fire && (blast ? 1'b1 : full0) && (c[0][1] || !sent);              // c[i][1] = kv
  wire e1 = fire && blast && tot > 5'd16 && c[16][1];
  function automatic [608:0] pack(input integer base, input lst);
    integer z; reg [608:0] r;
    begin
      r = 609'd0; r[0] = lst;
      for (z = 0; z < 16; z = z + 1) begin
        r[1 + z] = c[base + z][0];
        r[17 + z] = c[base + z][1];
        r[33 + 16*z +: 16] = c[base + z][17:2];
        r[289 + 20*z +: 20] = c[base + z][37:18];
      end
      pack = r;
    end
  endfunction
  integer k;
  always @(posedge ck or negedge rn) begin
    if (!rn) begin
      credits <= 9'(CRED); scq <= 1'b0; sv <= 1'b0; tap_credit <= 3'd0; fault <= 1'b0; h <= 4'd0; sent <= 1'b0;
      pend <= 1'b0;
    end else begin
      scq <= sc;
      tap_credit <= {3{fire}};
      sv <= e0 || pend;
      credits <= credits - {8'd0, e0 || pend} + {8'd0, scq};
      if (scq && credits >= 9'(CRED)) fault <= 1'b1;
      if ((&ne) && !last_ok) fault <= 1'b1;
      for (k = 0; k < 3; k = k + 1) if (taps[k*154] && occ[k] == (1 << AW) && !fire) fault <= 1'b1;
      if (pend) pend <= 1'b0;
      if (fire) begin
        if (blast) begin
          h <= 4'd0; sent <= 1'b0; pend <= e1;
          if (!e0 && !e1) fault <= 1'b1;
        end else begin
          if (e0) sent <= 1'b1;
          h <= mut_gb ? 4'd0 : (full0 ? h - 4'd4 : 4'd12);
        end
      end
    end
  end
  always @(posedge ck) begin
    if (fire && !blast)
      for (k = 0; k < 12; k = k + 1) hl[k] <= full0 ? c[16 + k] : c[k];
    if (e0) sd <= pack(0, !e1 && blast);
    else if (pend) sd <= pg;
    if (e1) pg <= pack(16, 1'b1);
  end
  assign s = {sd, sv};
endmodule
`default_nettype wire
