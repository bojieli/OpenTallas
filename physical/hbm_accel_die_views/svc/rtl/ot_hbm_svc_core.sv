`timescale 1ps/1fs
`default_nettype none
// CLAUDE HBM-ABSTRACTS (svcidx) 2026-10-06: thin registered stream service of one HBM stack for the r16g die view
// (hfd_svc_<st>).  Default-off: nothing instantiates it outside physical/hbm_accel_die_views/svc.
//
// One clock: ck = clk_hbm (the generator gives the service no clk_stream pin; see the view record's defects).  The
// PHY abstract ot_hbm3e_phy_v41x_aw30_e8p5 is "PHY + controller" with request-level K (32 pseudo-channel) and W
// (8-lane weight) ports, so the service carries no DRAM sequencer; it is the request / response fabric between the
// eight SMs of the stack, the expert / KV / index-key command input (e) and the PHY:
//   SM i request (addr32, tag10) -> one of its four K pseudo-channels (SM_PC0[i] + 0..3, one read of 5 sectors, one
//     request outstanding per PC) -> 5 beats -> line {v, tag10, data1088 = beats 0..3, beat4[63:0]} on lsm i;
//   e command {kind[1:0], addr30, len6, tag10} (e[0] = valid): kind 0 W-port read returned on lane tag[2:0] as a line
//     to SM tag[2:0]; kind 1 KV row read (4 sectors on KV_PC) -> kv {v, tag13, data1024}; kind 2 index-key read
//     (4 sectors on IK_PC) -> ik data1024;
//   every path that crosses the 8.5 mm block is pipelined (wire stages, *_ST, <= 430 um a stage);
//   forwarded inputs (row-1 SM requests, e) land through ot_hbm_accel_cdc_fifo clocked by their forwarded clock;
//   forwarded outputs (row-1 lines, kv, ik) carry ck as their forwarded clock (ot_svc_fclk_buf).
// Every die input lands in a flop (or a FIFO write port), every die output leaves a flop.
module ot_svc_fclk_buf (input wire a, output wire y);  // kept: the forwarded clock / PHY clock driver
  assign y = a;
endmodule

module ot_svc_pipe #(parameter integer W = 1, parameter integer N = 0) (
  input wire ck, input wire [W-1:0] d, output wire [W-1:0] q);
  generate if (N == 0) begin : g0
    assign q = d;
  end else begin : gn
    reg [W-1:0] r [0:N-1];
    integer k;
    always @(posedge ck) begin
      r[0] <= d;
      for (k = 1; k < N; k = k + 1) r[k] <= r[k-1];
    end
    assign q = r[N-1];
  end endgenerate
endmodule

// valid-qualified pipe: the valid bit is reset, the payload is not
module ot_svc_vpipe #(parameter integer W = 1, parameter integer N = 0) (
  input wire ck, input wire rst_n, input wire v, input wire [W-1:0] d, output wire qv, output wire [W-1:0] q);
  generate if (N == 0) begin : g0
    assign qv = v; assign q = d;
  end else begin : gn
    reg [N-1:0] rv;
    reg [W-1:0] r [0:N-1];
    integer k;
    always @(posedge ck or negedge rst_n)
      if (!rst_n) rv <= {N{1'b0}};
      else rv <= (N == 1) ? v : {rv[N-2:0], v};
    always @(posedge ck) begin
      r[0] <= d;
      for (k = 1; k < N; k = k + 1) r[k] <= r[k-1];
    end
    assign qv = rv[N-1]; assign q = r[N-1];
  end endgenerate
endmodule

// small synchronous FIFO, registered almost-full ready (AF free slots kept for the in-flight round trip)
module ot_svc_fifo #(parameter integer W = 8, parameter integer AW = 2, parameter integer AF = 2) (
  input wire ck, input wire rst_n, input wire we, input wire [W-1:0] wd, output reg rdy,
  input wire re, output wire [W-1:0] rd, output wire ne);
  localparam integer D = 1 << AW;
  reg [W-1:0] m [0:D-1];
  reg [AW:0] wp, rp;
  wire [AW:0] n = wp - rp;
  assign ne = (n != 0);
  assign rd = m[rp[AW-1:0]];
  always @(posedge ck) if (we) m[wp[AW-1:0]] <= wd;
  always @(posedge ck or negedge rst_n)
    if (!rst_n) begin wp <= 0; rp <= 0; rdy <= 1'b0; end
    else begin
      wp <= wp + (we ? 1'b1 : 1'b0);
      rp <= rp + ((re && ne) ? 1'b1 : 1'b0);
      rdy <= ((wp + (we ? 1'b1 : 1'b0)) - (rp + ((re && ne) ? 1'b1 : 1'b0))) <= (D - AF);
    end
endmodule

// beat assembler: collects NB 256-bit beats (by beat index) of one read, then holds the word until taken
module ot_svc_asm #(parameter integer NB = 5, parameter integer TW = 13) (
  input wire ck, input wire rst_n,
  input wire bv, input wire [TW-1:0] btag, input wire [4:0] bbeat, input wire [255:0] bdata,
  output wire full, output wire [TW-1:0] tag, output wire [NB*256-1:0] data, input wire take);
  reg [NB-1:0] have;
  reg [TW-1:0] t;
  reg [255:0] b [0:NB-1];
  integer k;
  assign full = &have;
  assign tag = t;
  genvar g;
  generate for (g = 0; g < NB; g = g + 1) begin : gd
    assign data[g*256 +: 256] = b[g];
  end endgenerate
  always @(posedge ck) if (bv) begin b[bbeat] <= bdata; t <= btag; end
  always @(posedge ck or negedge rst_n)
    if (!rst_n) have <= {NB{1'b0}};
    else if (full && take) have <= {NB{1'b0}};
    else if (bv) for (k = 0; k < NB; k = k + 1) if (bbeat == k) have[k] <= 1'b1;
endmodule

module ot_hbm_svc_core #(
  parameter integer NSM = 8, NPC = 32,
  parameter [NSM*5-1:0] SM_PC0 = 0,       // first of SM i's four K pseudo-channels
  parameter [NPC*4-1:0] RSP_ST = 0,       // wire stages, PC p response ingress -> its SM's assembler
  parameter [NSM*4-1:0] REQ_ST = 0,       // wire stages, SM i request port -> its PCs
  parameter [NSM*4-1:0] W_ST = 0,         // wire stages, W lane l -> SM l
  parameter [NSM-1:0] FWD = 0,            // SM i link forwarded (row 1): request with fclk, no ready; line with fclk
  parameter integer KV_PC = 0, IK_PC = 0,
  parameter integer KV_ST = 0, IK_ST = 0, // wire stages KV_PC / IK_PC -> kv / ik ports
  parameter integer E_ST = 0              // wire stages e port -> PHY request side
)(
  input  wire ck, input wire rst,          // rst: active-low die reset (por_hbm)
  input  wire [NSM*42-1:0] q_d, input wire [NSM-1:0] q_v, input wire [NSM-1:0] q_fclk, output wire [NSM-1:0] q_rdy,
  output wire [NSM*1099-1:0] line, output wire fclk,
  input  wire [127:0] e_d, input wire e_fclk,
  output wire [1037:0] kv, output wire [1023:0] ik,
  output wire phy_clk, output wire phy_rst_n,
  output wire [NPC-1:0] k_v, input wire [NPC-1:0] k_rdy, output wire [NPC*30-1:0] k_addr, output wire [NPC*4-1:0] k_len,
  output wire [NPC*17-1:0] k_tag, output wire [NPC-1:0] k_we, output wire [NPC*256-1:0] k_wdata,
  output wire [NPC*32-1:0] k_wstrb,
  input  wire [NPC-1:0] kr_v, output wire [NPC-1:0] kr_rdy, input wire [NPC*17-1:0] kr_tag, input wire [NPC*4-1:0] kr_beat,
  input  wire [NPC*256-1:0] kr_data,
  output wire w_v, input wire w_rdy, output wire [23:0] w_addr, output wire [5:0] w_len, output wire [9:0] w_tag,
  input  wire [7:0] w_room,
  input  wire [7:0] wr_v, output wire [7:0] wr_rdy, input wire [79:0] wr_tag, input wire [39:0] wr_beat,
  input  wire [2047:0] wr_data
);
  genvar i, p;
  // ---------------------------------------------------------------- clock / reset
  reg rs1, rs2;
  always @(posedge ck or negedge rst) if (!rst) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
  ot_svc_fclk_buf u_phy_ck (.a(ck), .y(phy_clk));
  ot_svc_fclk_buf u_fclk   (.a(ck), .y(fclk));
  reg prst; always @(posedge ck or negedge rn) if (!rn) prst <= 1'b0; else prst <= 1'b1;
  assign phy_rst_n = prst;
  assign k_we = {NPC{1'b0}}; assign k_wdata = {NPC*256{1'b0}}; assign k_wstrb = {NPC*32{1'b0}};
  reg rdy_q; always @(posedge ck or negedge rn) if (!rn) rdy_q <= 1'b0; else rdy_q <= 1'b1;

  // shared nets
  wire [NSM-1:0] rq_v;                 // request held at the PC side of its wire stages
  wire [NSM*42-1:0] rq_d;
  wire [NSM-1:0] rq_take;
  wire [NPC-1:0] kv_q, pc_busy, pc_done, pc_done_sm, sm_iss, k_take;
  wire [7:0] lane_done, w_take;
  wire kv_dn, ik_dn;
  reg [7:0] wr_q_v; reg [79:0] wr_q_t; reg [39:0] wr_q_b; reg [2047:0] wr_q_d;

  // ---------------------------------------------------------------- SM request ingress
  generate for (i = 0; i < NSM; i = i + 1) begin : gq
    wire iv, ine, tk_back, sv; wire [41:0] id_, sd;
    reg pend, hv; reg [41:0] hd;
    if (FWD[i]) begin : fwd                                  // forwarded row-1 request: two-clock FIFO
      wire full_, empty_; wire [2:0] fr_;
      ot_hbm_accel_cdc_fifo #(.W(42), .AW(2)) u_x (.wclk(q_fclk[i]), .wrst_n(rst), .we(q_v[i]),
        .wdata(q_d[i*42 +: 42]), .full(full_), .rd_freed(fr_), .rclk(ck), .rrst_n(rn), .re(iv),
        .rdata(id_), .empty(empty_));
      assign ine = !empty_;
      assign q_rdy[i] = 1'b0;
    end else begin : loc                                     // row-0 request: registered port + FIFO, registered ready
      reg v_q; reg [41:0] d_q; wire rdy_;
      always @(posedge ck or negedge rn) if (!rn) v_q <= 1'b0; else v_q <= q_v[i] && rdy_;
      always @(posedge ck) d_q <= q_d[i*42 +: 42];
      ot_svc_fifo #(.W(42), .AW(3), .AF(4)) u_f (.ck(ck), .rst_n(rn), .we(v_q), .wd(d_q), .rdy(rdy_),
        .re(iv), .rd(id_), .ne(ine));
      assign q_rdy[i] = rdy_;
    end
    // one request travels down the wire stages at a time; the PC side returns rq_take
    assign iv = ine && !pend;
    always @(posedge ck or negedge rn) if (!rn) pend <= 1'b0; else if (iv) pend <= 1'b1; else if (tk_back) pend <= 1'b0;
    ot_svc_vpipe #(.W(1), .N(REQ_ST[i*4 +: 4])) u_tb (.ck(ck), .rst_n(rn), .v(rq_take[i]), .d(1'b0), .qv(tk_back), .q());
    ot_svc_vpipe #(.W(42), .N(REQ_ST[i*4 +: 4])) u_rq (.ck(ck), .rst_n(rn), .v(iv), .d(id_), .qv(sv), .q(sd));
    always @(posedge ck or negedge rn) if (!rn) hv <= 1'b0; else if (sv) hv <= 1'b1; else if (rq_take[i]) hv <= 1'b0;
    always @(posedge ck) if (sv) hd <= sd;
    assign rq_v[i] = hv; assign rq_d[i*42 +: 42] = hd;
  end endgenerate

  // ---------------------------------------------------------------- e command ingress (forwarded) and decode
  // e[0] valid; ed = e[127:1]: kind ed[1:0], addr ed[31:2], len ed[37:32] (W only), tag ed[47:38]
  wire [126:0] ed; wire e_empty, e_full; wire [2:0] e_fr;
  reg cpend, chv; reg [126:0] chd;
  wire e_re = !e_empty && !cpend;
  wire c_take, cb, cv; wire [126:0] cd;
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_fclk), .wrst_n(rst), .we(e_d[0]), .wdata(e_d[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  always @(posedge ck or negedge rn) if (!rn) cpend <= 1'b0; else if (e_re) cpend <= 1'b1; else if (cb) cpend <= 1'b0;
  ot_svc_vpipe #(.W(127), .N(E_ST)) u_ep (.ck(ck), .rst_n(rn), .v(e_re), .d(ed), .qv(cv), .q(cd));
  ot_svc_vpipe #(.W(1), .N(E_ST)) u_eb (.ck(ck), .rst_n(rn), .v(c_take), .d(1'b0), .qv(cb), .q());
  always @(posedge ck or negedge rn) if (!rn) chv <= 1'b0; else if (cv) chv <= 1'b1; else if (c_take) chv <= 1'b0;
  always @(posedge ck) if (cv) chd <= cd;
  wire [1:0] c_kind = chd[1:0];
  wire [29:0] c_addr = chd[31:2];
  wire [9:0] c_tag = chd[47:38];

  // ---------------------------------------------------------------- W port (kind 0): one request outstanding per lane
  reg [7:0] lane_busy;
  reg wv_q; reg [23:0] wa_q; reg [9:0] wt_q;
  wire w_issue = chv && (c_kind == 2'd0) && !wv_q && !lane_busy[c_tag[2:0]] && w_room[c_tag[2:0]];
  always @(posedge ck or negedge rn)
    if (!rn) begin wv_q <= 1'b0; lane_busy <= 8'h00; end
    else begin
      if (w_issue) wv_q <= 1'b1; else if (w_rdy) wv_q <= 1'b0;
      lane_busy <= (lane_busy | (w_issue ? (8'h01 << c_tag[2:0]) : 8'h00)) & ~lane_done;
    end
  always @(posedge ck) if (w_issue) begin wa_q <= c_addr[23:0]; wt_q <= c_tag; end
  assign w_v = wv_q; assign w_addr = wa_q; assign w_len = 6'd5; assign w_tag = wt_q;

  // ---------------------------------------------------------------- K port: one request register per PC
  wire c_kv = chv && (c_kind == 2'd1) && !pc_busy[KV_PC];
  wire c_ik = chv && (c_kind == 2'd2) && !pc_busy[IK_PC];
  assign c_take = w_issue || c_kv || c_ik || (chv && (c_kind == 2'd3));    // kind 3: reserved, dropped
  generate for (i = 0; i < NSM; i = i + 1) begin : gd       // SM i: round robin over its four PCs
    localparam integer B = SM_PC0[i*5 +: 5];
    wire [3:0] fr;
    reg [1:0] rr;
    for (p = 0; p < 4; p = p + 1) begin : gf
      assign fr[p] = !pc_busy[B+p] && !((B+p == KV_PC) && c_kv) && !((B+p == IK_PC) && c_ik);
    end
    wire [7:0] f2 = {fr, fr};
    wire [3:0] rot = f2 >> rr;
    wire [1:0] off = rot[0] ? 2'd0 : rot[1] ? 2'd1 : rot[2] ? 2'd2 : 2'd3;
    wire [1:0] sel = rr + off;
    assign rq_take[i] = rq_v[i] && (|fr);
    for (p = 0; p < 4; p = p + 1) begin : gi
      assign sm_iss[B+p] = rq_take[i] && (sel == p);
    end
    always @(posedge ck or negedge rn) if (!rn) rr <= 2'd0; else if (rq_take[i]) rr <= sel + 2'd1;
  end endgenerate
  function automatic integer own(input integer pc);
    integer s;
    begin own = 0; for (s = 0; s < NSM; s = s + 1) if (pc >= SM_PC0[s*5 +: 5] && pc < SM_PC0[s*5 +: 5] + 4) own = s; end
  endfunction
  generate for (p = 0; p < NPC; p = p + 1) begin : gk
    localparam integer S = own(p);
    wire ckv = (p == KV_PC) && c_kv, cik = (p == IK_PC) && c_ik, any = ckv || cik || sm_iss[p];
    reg v, busy; reg [29:0] a; reg [3:0] ln; reg [16:0] t;
    always @(posedge ck or negedge rn)
      if (!rn) begin v <= 1'b0; busy <= 1'b0; end
      else begin
        if (any) v <= 1'b1; else if (k_rdy[p]) v <= 1'b0;
        if (any) busy <= 1'b1; else if (pc_done[p]) busy <= 1'b0;
      end
    always @(posedge ck)
      if (ckv || cik) begin a <= c_addr; ln <= 4'd4; t <= {ckv ? 2'b01 : 2'b10, 5'd0, c_tag}; end
      else if (sm_iss[p]) begin a <= rq_d[S*42 +: 30]; ln <= 4'd5; t <= {2'b00, 3'(S), 2'b00, rq_d[S*42+32 +: 10]}; end
    assign kv_q[p] = v; assign pc_busy[p] = busy;
    assign k_v[p] = v; assign k_addr[p*30 +: 30] = a; assign k_len[p*4 +: 4] = ln; assign k_tag[p*17 +: 17] = t;
    assign pc_done[p] = pc_done_sm[p] || ((p == KV_PC) && kv_dn) || ((p == IK_PC) && ik_dn);
  end endgenerate

  // ---------------------------------------------------------------- K responses: ingress register, route by source
  // kr_rdy / wr_rdy are 1 after reset: one read per PC / lane is outstanding and its destination holds a whole read
  assign kr_rdy = {NPC{rdy_q}};
  assign wr_rdy = {8{rdy_q}};
  wire [NPC-1:0] b_v; wire [NPC*17-1:0] b_t; wire [NPC*4-1:0] b_b; wire [NPC*256-1:0] b_d;
  generate for (p = 0; p < NPC; p = p + 1) begin : gr
    reg v; reg [16:0] t; reg [3:0] bt; reg [255:0] d;
    always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= kr_v[p] && rdy_q;
    always @(posedge ck) begin t <= kr_tag[p*17 +: 17]; bt <= kr_beat[p*4 +: 4]; d <= kr_data[p*256 +: 256]; end
    assign b_v[p] = v; assign b_t[p*17 +: 17] = t; assign b_b[p*4 +: 4] = bt; assign b_d[p*256 +: 256] = d;
  end endgenerate
  always @(posedge ck or negedge rn) if (!rn) wr_q_v <= 8'h00; else wr_q_v <= wr_v & {8{rdy_q}};
  always @(posedge ck) begin wr_q_t <= wr_tag; wr_q_b <= wr_beat; wr_q_d <= wr_data; end

  // ---------------------------------------------------------------- SM lines: 4 K + 1 W assembler, round robin
  generate for (i = 0; i < NSM; i = i + 1) begin : gl
    localparam integer B = SM_PC0[i*5 +: 5];
    wire [4:0] full; wire [9:0] tg [0:4]; wire [1279:0] dt [0:4];
    for (p = 0; p < 4; p = p + 1) begin : ga
      wire sv; wire [276:0] sq; wire [12:0] t13;
      ot_svc_vpipe #(.W(277), .N(RSP_ST[(B+p)*4 +: 4])) u_bp (.ck(ck), .rst_n(rn),
        .v(b_v[B+p] && (b_t[(B+p)*17+15 +: 2] == 2'b00)),
        .d({b_t[(B+p)*17 +: 17], b_b[(B+p)*4 +: 4], b_d[(B+p)*256 +: 256]}), .qv(sv), .q(sq));
      ot_svc_asm #(.NB(5), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
        .bdata(sq[255:0]), .full(full[p]), .tag(t13), .data(dt[p]), .take(k_take[B+p]));
      assign tg[p] = t13[9:0];
      ot_svc_vpipe #(.W(1), .N(RSP_ST[(B+p)*4 +: 4])) u_dn (.ck(ck), .rst_n(rn), .v(k_take[B+p]), .d(1'b0),
        .qv(pc_done_sm[B+p]), .q());
    end
    wire wsv; wire [270:0] wsq; wire [9:0] t10;
    ot_svc_vpipe #(.W(271), .N(W_ST[i*4 +: 4])) u_wp (.ck(ck), .rst_n(rn), .v(wr_q_v[i]),
      .d({wr_q_t[i*10 +: 10], wr_q_b[i*5 +: 5], wr_q_d[i*256 +: 256]}), .qv(wsv), .q(wsq));
    ot_svc_asm #(.NB(5), .TW(10)) u_wa (.ck(ck), .rst_n(rn), .bv(wsv), .btag(wsq[270:261]), .bbeat(wsq[260:256]),
      .bdata(wsq[255:0]), .full(full[4]), .tag(t10), .data(dt[4]), .take(w_take[i]));
    assign tg[4] = t10;
    ot_svc_vpipe #(.W(1), .N(W_ST[i*4 +: 4])) u_wdn (.ck(ck), .rst_n(rn), .v(w_take[i]), .d(1'b0), .qv(lane_done[i]), .q());
    reg [2:0] lr;
    wire [9:0] fx = {full, full};
    wire [4:0] rot = fx >> lr;
    wire [3:0] off = rot[0] ? 4'd0 : rot[1] ? 4'd1 : rot[2] ? 4'd2 : rot[3] ? 4'd3 : 4'd4;
    wire [3:0] s0 = {1'b0, lr} + off;
    wire [2:0] sel = (s0 >= 4'd5) ? 3'(s0 - 4'd5) : s0[2:0];
    wire any = |full;
    for (p = 0; p < 4; p = p + 1) begin : gt
      assign k_take[B+p] = any && (sel == p);
    end
    assign w_take[i] = any && (sel == 3'd4);
    reg lv; reg [9:0] lt; reg [1087:0] ld;
    always @(posedge ck or negedge rn)
      if (!rn) begin lv <= 1'b0; lr <= 3'd0; end
      else begin lv <= any; if (any) lr <= (sel == 3'd4) ? 3'd0 : sel + 3'd1; end
    always @(posedge ck) if (any) begin lt <= tg[sel]; ld <= dt[sel][1087:0]; end
    assign line[i*1099 +: 1099] = {ld, lt, lv};
  end endgenerate

  // ---------------------------------------------------------------- KV / index-key assemblers (4 beats)
  generate if (1) begin : gkv
    wire sv; wire [276:0] sq; wire full_; wire [12:0] t13; wire [1023:0] dd;
    ot_svc_vpipe #(.W(277), .N(KV_ST)) u_p (.ck(ck), .rst_n(rn), .v(b_v[KV_PC] && (b_t[KV_PC*17+15 +: 2] == 2'b01)),
      .d({b_t[KV_PC*17 +: 17], b_b[KV_PC*4 +: 4], b_d[KV_PC*256 +: 256]}), .qv(sv), .q(sq));
    ot_svc_asm #(.NB(4), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
      .bdata(sq[255:0]), .full(full_), .tag(t13), .data(dd), .take(1'b1));
    reg v; reg [12:0] t; reg [1023:0] d;
    always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= full_;
    always @(posedge ck) if (full_) begin t <= t13; d <= dd; end
    assign kv = {d, t, v};
    ot_svc_vpipe #(.W(1), .N(KV_ST)) u_dn (.ck(ck), .rst_n(rn), .v(full_), .d(1'b0), .qv(kv_dn), .q());
  end endgenerate
  generate if (1) begin : gik
    wire sv; wire [276:0] sq; wire full_; wire [12:0] t13; wire [1023:0] dd;
    ot_svc_vpipe #(.W(277), .N(IK_ST)) u_p (.ck(ck), .rst_n(rn), .v(b_v[IK_PC] && (b_t[IK_PC*17+15 +: 2] == 2'b10)),
      .d({b_t[IK_PC*17 +: 17], b_b[IK_PC*4 +: 4], b_d[IK_PC*256 +: 256]}), .qv(sv), .q(sq));
    ot_svc_asm #(.NB(4), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
      .bdata(sq[255:0]), .full(full_), .tag(t13), .data(dd), .take(1'b1));
    reg [1023:0] d;
    always @(posedge ck) if (full_) d <= dd;
    assign ik = d;
    ot_svc_vpipe #(.W(1), .N(IK_ST)) u_dn (.ck(ck), .rst_n(rn), .v(full_), .d(1'b0), .qv(ik_dn), .q());
  end endgenerate
endmodule
`default_nettype wire
