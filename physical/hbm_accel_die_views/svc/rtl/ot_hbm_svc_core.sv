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
//   forwarded inputs (row-1 SM requests, e) land through ot_hbm_accel_cdc_fifo written on the FALLING edge of their
//     forwarded clock (the data changes on its rising edge, as ot_fwd_link_stage launches);
//   forwarded outputs (row-1 lines, kv, ik) carry ck as their forwarded clock (ot_svc_fclk_buf).
// Every die input lands in a flop (or a FIFO write port), every die output leaves a flop.
// MARGIN (owner rule 2026-10-06): every face is register-to-register with no logic between pin and
//   flop (forwarded inputs: a capture register on the forwarded clock's falling edge before the two-clock FIFO; PHY
//   control inputs k_rdy / w_rdy / w_room / kr_v / wr_v and local SM request valids: raw capture registers, gating
//   after the flop; k_v / w_v present for one cycle and are dropped while the registered ready of that cycle
//   decides: accepted -> done, else present again), and every wire-stage chain carries XST (2) extra stages.
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
module ot_svc_vpipe #(parameter integer W = 1, parameter integer N = 0, parameter integer X = 0) (   // N + X stages
  input wire ck, input wire rst_n, input wire v, input wire [W-1:0] d, output wire qv, output wire [W-1:0] q);
  // stage registers are per-stage generate blocks (gn.st[k].r), not an unpacked array: iverilog mis-evaluates
  // r[NT-1] of an unpacked array inside the full svc design (q stays X while the last word is valid)
  localparam integer NT = N + X;
  generate if (NT == 0) begin : g0
    assign qv = v; assign q = d;
  end else begin : gn
    reg [NT-1:0] rv;
    always @(posedge ck or negedge rst_n)
      if (!rst_n) rv <= {NT{1'b0}};
      else rv <= {rv, v};
    genvar k;
    for (k = 0; k < NT; k = k + 1) begin : st
      reg [W-1:0] r;
      if (k == 0) begin : h always @(posedge ck) r <= d; end
      else begin : t always @(posedge ck) r <= st[k-1].r; end
    end
    assign qv = rv[NT-1]; assign q = st[NT-1].r;
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
  parameter integer E_ST = 0,             // wire stages e port -> PHY request side
  parameter integer XST = 2,              // MARGIN: extra wire stages on every chain (route at <= 770 ps)
  // hbm-system 2026-10-08 (T3 gap 3): WRITE path.  WB = 1 adds the forwarded sector-write link of the hub
  // write-back unit (rtl/hbm_accel/service/ot_hbm_kvwb_hub.sv) and drives k_we / k_wdata / k_wstrb; WB = 0 (default)
  // is the read-only service, bit for bit.
  parameter integer WB = 0,
  parameter integer WB_SOURCE_ACK = 0, // opt-in source-owned per-PC DRAM completions
  parameter integer WQ_ST = 0,            // wire stages, wq port -> the PC request registers (and back)
  // hbm-system 2026-10-08 (coordinator: one fixed KV_PC per stack cannot reach the >= 90 % KV bandwidth rule):
  // KVS = 1 turns e kind 1 into a PER-PC KV STREAM.  Descriptor ed: [1:0] = 1, [16:2] row0 (15 b), [28:17] nsec
  // (sectors per PC; the last read of a PC is 4 sectors, pad sectors are dropped), [60:29] PC mask, [70:61] tag.  Every PC in the mask streams its sectors
  // j = 0 .. nsec-1 of the region (the dskv_wb / stream-PC j order: bank {j[9:7], j[1:0]}, column j[6:2],
  // row row0 + (j >> 10), K address by ot_hbm_kport_map), up to KNO 4-sector reads outstanding per PC, and its
  // beats leave on its OWN lane kvs[p] = {data256, j12, v} (one sector a clock a PC: the PHY rate), so a stack
  // delivers up to 32 sectors a clock.  kvs_done pulses when every PC finished.  KVS = 0: the single-PC kind 1.
  parameter integer KVS = 0,
  parameter integer IK_CRED = 64, // production scorer FA6: line credits independent of64sector slots/PC
  parameter integer IK_DEPTH = 64, // opt-in return retention; default retains measured64-slot implementation
  parameter integer IKS = 0, // opt-in kind2 stripe: blocks chd[69:61], row0 chd[16:2], all32PCs
  parameter integer IK_SRAM = 0, // opt-in protected native SRAM return store; DEPTH64 only
  parameter integer IK_SRAM_ROTATE = 0, // opt-in structured gather remap, same bytes and pipeline
  parameter integer IK_PREFETCH = 0, // dedicated already-protected decoded99 descriptor portal

  parameter integer KNO = 15              // 4-sector reads outstanding per PC (60 of the controller's 64 queued beats)
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
  input  wire [2047:0] wr_data,
  // WB = 1: sector writes {data256, addr30, pc5, v} forwarded with wq_fclk; returns {ack_gray8, pop_gray8} on ck
  input  wire [291:0] wq_d, input wire wq_fclk, output wire [15:0] wq_g, input wire [NPC-1:0] k_wr_done,
  input wire [1:0] wq_source, output wire [31:0] wq_source_g, output wire wq_source_fault, output wire [NPC-1:0] wq_source_busy, output wire wq_pending,
  // KVS = 1: per-PC KV stream lanes (launched on ck, forwarded with fclk) and the stream-complete pulse
  output wire [NPC*269-1:0] kvs, output wire kvs_done,
  input wire [7:0] ik_credit, output wire [8791:0] ik_lines, output wire ik_done,ik_fault,
  input wire ip_v, input wire [98:0] ip_d, input wire ip_fault,
  output wire ip_take
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
  // WB: one sector write in flight per stack (shared landing register; window rows are one PC anyway)
  wire [NPC-1:0] wreq;                 // the landed write targets PC p (reads on p hold off)
  wire [NPC-1:0] wacc;                 // PC p's write was accepted by the PHY this cycle
  wire [255:0] wl_d;                   // landed write data (shared by every PC's k_wdata)
  wire [29:0] wl_a;
  wire [NPC-1:0] sreq;                 // KVS: PC p's stream wants to present a read (reads of SMs hold off)
  wire [NPC-1:0] sacc;                 // KVS: PC p's stream read was accepted
  wire [NPC*30-1:0] s_addr;            // KVS: PC p's next stream read address
  wire [NPC*10-1:0] s_jt;              // KVS: its j >> 2 (carried in the read's tag)
  wire index_stream;
  wire c_kvs, c_kvs_legacy, c_index_prefetch;
  wire index_data_fault;
  reg index_portal_fault;
  always @(posedge ck or negedge rn)
    if (!rn) index_portal_fault <= 1'b0;
    else if ((IK_PREFETCH != 0) && (ip_fault || (ip_v &&
      (ip_d[1:0] != 2'd2 || ip_d[10:2] == 0 || ip_d[10:2] > 9'd342))))
      index_portal_fault <= 1'b1;
  assign ik_fault = index_data_fault || index_portal_fault;
  assign ip_take = c_index_prefetch;
  reg rdy_q; always @(posedge ck or negedge rn) if (!rn) rdy_q <= 1'b0; else rdy_q <= 1'b1;
  // MARGIN: PHY control inputs land in raw capture flops at the pin; all gating happens after them
  reg [NPC-1:0] k_rdy_q, kr_v_q; reg w_rdy_q; reg [7:0] w_room_q, wr_v_q; reg rdy_q2;
  always @(posedge ck or negedge rn)
    if (!rn) begin k_rdy_q <= 0; kr_v_q <= 0; w_rdy_q <= 1'b0; w_room_q <= 8'h00; wr_v_q <= 8'h00; rdy_q2 <= 1'b0; end
    else begin k_rdy_q <= k_rdy; kr_v_q <= kr_v; w_rdy_q <= w_rdy; w_room_q <= w_room; wr_v_q <= wr_v; rdy_q2 <= rdy_q; end

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
      reg fv; reg [41:0] fd;                                 // MARGIN: capture flop at the pin (falling edge)
      wire wck = ~q_fclk[i];                                 // one inverted clock net for capture and FIFO write
      always @(posedge wck or negedge rst) if (!rst) fv <= 1'b0; else fv <= q_v[i];
      always @(posedge wck) fd <= q_d[i*42 +: 42];
      ot_hbm_accel_cdc_fifo #(.W(42), .AW(2)) u_x (.wclk(wck), .wrst_n(rst), .we(fv),
        .wdata(fd), .full(full_), .rd_freed(fr_), .rclk(ck), .rrst_n(rn), .re(iv),
        .rdata(id_), .empty(empty_));
      assign ine = !empty_;
      assign q_rdy[i] = 1'b0;
    end else begin : loc                                     // row-0 request: registered port + FIFO, registered ready
      reg v_q; reg [41:0] d_q; wire rdy_;
      reg v_r, rdy_d; reg [41:0] d_r;                        // MARGIN: raw capture at the pin, gate one cycle later
      always @(posedge ck or negedge rn) if (!rn) begin v_r <= 1'b0; rdy_d <= 1'b0; end else begin v_r <= q_v[i]; rdy_d <= rdy_; end
      always @(posedge ck) d_r <= q_d[i*42 +: 42];
      always @(posedge ck or negedge rn) if (!rn) v_q <= 1'b0; else v_q <= v_r && rdy_d;
      always @(posedge ck) d_q <= d_r;
      ot_svc_fifo #(.W(42), .AW(3), .AF(5)) u_f (.ck(ck), .rst_n(rn), .we(v_q), .wd(d_q), .rdy(rdy_),
        .re(iv), .rd(id_), .ne(ine));
      assign q_rdy[i] = rdy_;
    end
    // one request travels down the wire stages at a time; the PC side returns rq_take
    assign iv = ine && !pend;
    always @(posedge ck or negedge rn) if (!rn) pend <= 1'b0; else if (iv) pend <= 1'b1; else if (tk_back) pend <= 1'b0;
    ot_svc_vpipe #(.W(1), .N(REQ_ST[i*4 +: 4]), .X(XST)) u_tb (.ck(ck), .rst_n(rn), .v(rq_take[i]), .d(1'b0), .qv(tk_back), .q());
    ot_svc_vpipe #(.W(42), .N(REQ_ST[i*4 +: 4]), .X(XST)) u_rq (.ck(ck), .rst_n(rn), .v(iv), .d(id_), .qv(sv), .q(sd));
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
  reg [127:0] e_f;                                           // MARGIN: capture flop at the pin (falling edge)
  wire e_wck = ~e_fclk;                                      // one inverted clock net for capture and FIFO write
  always @(posedge e_wck or negedge rst) if (!rst) e_f[0] <= 1'b0; else e_f[0] <= e_d[0];
  always @(posedge e_wck) e_f[127:1] <= e_d[127:1];
  ot_hbm_accel_cdc_fifo #(.W(127), .AW(2)) u_e (.wclk(e_wck), .wrst_n(rst), .we(e_f[0]), .wdata(e_f[127:1]),
    .full(e_full), .rd_freed(e_fr), .rclk(ck), .rrst_n(rn), .re(e_re), .rdata(ed), .empty(e_empty));
  always @(posedge ck or negedge rn) if (!rn) cpend <= 1'b0; else if (e_re) cpend <= 1'b1; else if (cb) cpend <= 1'b0;
  ot_svc_vpipe #(.W(127), .N(E_ST), .X(XST)) u_ep (.ck(ck), .rst_n(rn), .v(e_re), .d(ed), .qv(cv), .q(cd));
  ot_svc_vpipe #(.W(1), .N(E_ST), .X(XST)) u_eb (.ck(ck), .rst_n(rn), .v(c_take), .d(1'b0), .qv(cb), .q());
  always @(posedge ck or negedge rn) if (!rn) chv <= 1'b0; else if (cv) chv <= 1'b1; else if (c_take) chv <= 1'b0;
  always @(posedge ck) if (cv) chd <= cd;
  wire [1:0] c_kind = chd[1:0];
  wire [29:0] c_addr = chd[31:2];
  wire [9:0] c_tag = chd[47:38];

  // ---------------------------------------------------------------- W port (kind 0): one request outstanding per lane
  reg [7:0] lane_busy;
  reg wv_q; reg [23:0] wa_q; reg [9:0] wt_q;
  reg wp_pend, wv_d;                                          // MARGIN: present-and-drop against w_rdy_q
  wire w_issue = chv && (c_kind == 2'd0) && !wp_pend && !lane_busy[c_tag[2:0]] && w_room_q[c_tag[2:0]];
  always @(posedge ck or negedge rn)
    if (!rn) begin wv_q <= 1'b0; lane_busy <= 8'h00; wp_pend <= 1'b0; wv_d <= 1'b0; end
    else begin
      wv_d <= wv_q;
      if (w_issue) begin wv_q <= 1'b1; wp_pend <= 1'b1; end
      else if (wv_q) wv_q <= 1'b0;                              // presented one cycle: drop, w_rdy_q decides
      else if (wp_pend && wv_d && w_rdy_q) wp_pend <= 1'b0;     // accepted last presentation
      else if (wp_pend && !wv_d) wv_q <= 1'b1;                  // not accepted: present again
      lane_busy <= (lane_busy | (w_issue ? (8'h01 << c_tag[2:0]) : 8'h00)) & ~lane_done;
    end
  always @(posedge ck) if (w_issue) begin wa_q <= c_addr[23:0]; wt_q <= c_tag; end
  assign w_v = wv_q; assign w_addr = wa_q; assign w_len = 6'd5; assign w_tag = wt_q;

  // ---------------------------------------------------------------- K port: one request register per PC
  wire c_kv = (KVS == 0) && chv && (c_kind == 2'd1) && !pc_busy[KV_PC] && !wreq[KV_PC];
  wire c_ik = (IKS == 0) && chv && (c_kind == 2'd2) && !pc_busy[IK_PC] && !wreq[IK_PC];
  assign c_take = w_issue || c_kv || c_kvs_legacy || c_ik || (chv && (c_kind == 2'd3));
  generate for (i = 0; i < NSM; i = i + 1) begin : gd       // SM i: round robin over its four PCs
    localparam integer B = SM_PC0[i*5 +: 5];
    wire [3:0] fr;
    reg [1:0] rr;
    for (p = 0; p < 4; p = p + 1) begin : gf
      assign fr[p] = !pc_busy[B+p] && !wreq[B+p] && !sreq[B+p] && !((B+p == KV_PC) && c_kv) && !((B+p == IK_PC) && c_ik);
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
    wire wiss = (WB != 0) && wreq[p] && !busy;                    // reads hold off while wreq[p]: any = 0 here
    wire siss = ((KVS != 0) || (IKS != 0)) && sreq[p] && !busy && !wreq[p];        // stream read (SM reads hold off while sreq[p])
    reg v, busy, pend, v_d, we, sr; reg [29:0] a; reg [3:0] ln; reg [16:0] t;
    assign wacc[p] = pend && v_d && k_rdy_q[p] && we;
    assign sacc[p] = pend && v_d && k_rdy_q[p] && sr;
    always @(posedge ck or negedge rn)
      if (!rn) begin v <= 1'b0; busy <= 1'b0; pend <= 1'b0; v_d <= 1'b0; we <= 1'b0; sr <= 1'b0; end
      else begin
        v_d <= v;                                                 // MARGIN: present-and-drop against k_rdy_q
        if (any || wiss || siss) begin v <= 1'b1; pend <= 1'b1; end
        else if (v) v <= 1'b0;
        else if (pend && v_d && k_rdy_q[p]) pend <= 1'b0;
        else if (pend && !v_d) v <= 1'b1;
        if (any || wiss || siss) busy <= 1'b1; else if (pc_done[p] || wacc[p] || sacc[p]) busy <= 1'b0;
        if (wiss) we <= 1'b1; else if (any || wacc[p]) we <= 1'b0;
        if (siss) sr <= 1'b1; else if (any || wiss || sacc[p]) sr <= 1'b0;
      end
    always @(posedge ck)
      if (ckv || cik) begin a <= c_addr; ln <= 4'd4; t <= {ckv ? 2'b01 : 2'b10, 5'd0, c_tag}; end
      else if (sm_iss[p]) begin a <= rq_d[S*42 +: 30]; ln <= 4'd5; t <= {2'b00, 3'(S), 2'b00, rq_d[S*42+32 +: 10]}; end
      else if (wiss) begin a <= wl_a; ln <= 4'd1; t <= {2'b11, 15'd0}; end
      else if (siss) begin a <= s_addr[p*30 +: 30]; ln <= 4'd4; t <= {index_stream ? 2'b10 : 2'b01, s_jt[p*10 +: 10], 5'd0}; end
    if (WB != 0) begin : gw
      assign k_we[p] = we; assign k_wdata[p*256 +: 256] = wl_d; assign k_wstrb[p*32 +: 32] = {32{we}};
    end else begin : gnw
      assign k_we[p] = 1'b0; assign k_wdata[p*256 +: 256] = 256'd0; assign k_wstrb[p*32 +: 32] = 32'd0;
    end
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
    always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= kr_v_q[p] && rdy_q2;   // MARGIN: +1 cycle
    reg [16:0] t_r; reg [3:0] bt_r; reg [255:0] d_r;          // MARGIN: raw capture at the pin, aligned with kr_v_q
    always @(posedge ck) begin t_r <= kr_tag[p*17 +: 17]; bt_r <= kr_beat[p*4 +: 4]; d_r <= kr_data[p*256 +: 256]; end
    always @(posedge ck) begin t <= t_r; bt <= bt_r; d <= d_r; end
    assign b_v[p] = v; assign b_t[p*17 +: 17] = t; assign b_b[p*4 +: 4] = bt; assign b_d[p*256 +: 256] = d;
  end endgenerate
  always @(posedge ck or negedge rn) if (!rn) wr_q_v <= 8'h00; else wr_q_v <= wr_v_q & {8{rdy_q2}};   // MARGIN: +1 cycle
  reg [79:0] wr_r_t; reg [39:0] wr_r_b; reg [2047:0] wr_r_d;
  always @(posedge ck) begin wr_r_t <= wr_tag; wr_r_b <= wr_beat; wr_r_d <= wr_data; end
  always @(posedge ck) begin wr_q_t <= wr_r_t; wr_q_b <= wr_r_b; wr_q_d <= wr_r_d; end

  // ---------------------------------------------------------------- SM lines: 4 K + 1 W assembler, round robin
  generate for (i = 0; i < NSM; i = i + 1) begin : gl
    localparam integer B = SM_PC0[i*5 +: 5];
    wire [4:0] full; wire [9:0] tg [0:4]; wire [1279:0] dt [0:4];
    for (p = 0; p < 4; p = p + 1) begin : ga
      wire sv; wire [276:0] sq; wire [12:0] t13;
      ot_svc_vpipe #(.W(277), .N(RSP_ST[(B+p)*4 +: 4]), .X(XST)) u_bp (.ck(ck), .rst_n(rn),
        .v(b_v[B+p] && (b_t[(B+p)*17+15 +: 2] == 2'b00)),
        .d({b_t[(B+p)*17 +: 17], b_b[(B+p)*4 +: 4], b_d[(B+p)*256 +: 256]}), .qv(sv), .q(sq));
      ot_svc_asm #(.NB(5), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
        .bdata(sq[255:0]), .full(full[p]), .tag(t13), .data(dt[p]), .take(k_take[B+p]));
      assign tg[p] = t13[9:0];
      ot_svc_vpipe #(.W(1), .N(RSP_ST[(B+p)*4 +: 4]), .X(XST)) u_dn (.ck(ck), .rst_n(rn), .v(k_take[B+p]), .d(1'b0),
        .qv(pc_done_sm[B+p]), .q());
    end
    wire wsv; wire [270:0] wsq; wire [9:0] t10;
    ot_svc_vpipe #(.W(271), .N(W_ST[i*4 +: 4]), .X(XST)) u_wp (.ck(ck), .rst_n(rn), .v(wr_q_v[i]),
      .d({wr_q_t[i*10 +: 10], wr_q_b[i*5 +: 5], wr_q_d[i*256 +: 256]}), .qv(wsv), .q(wsq));
    ot_svc_asm #(.NB(5), .TW(10)) u_wa (.ck(ck), .rst_n(rn), .bv(wsv), .btag(wsq[270:261]), .bbeat(wsq[260:256]),
      .bdata(wsq[255:0]), .full(full[4]), .tag(t10), .data(dt[4]), .take(w_take[i]));
    assign tg[4] = t10;
    ot_svc_vpipe #(.W(1), .N(W_ST[i*4 +: 4]), .X(XST)) u_wdn (.ck(ck), .rst_n(rn), .v(w_take[i]), .d(1'b0), .qv(lane_done[i]), .q());
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
    ot_svc_vpipe #(.W(277), .N(KV_ST), .X(XST)) u_p (.ck(ck), .rst_n(rn), .v((KVS == 0) && b_v[KV_PC] && (b_t[KV_PC*17+15 +: 2] == 2'b01)),
      .d({b_t[KV_PC*17 +: 17], b_b[KV_PC*4 +: 4], b_d[KV_PC*256 +: 256]}), .qv(sv), .q(sq));
    ot_svc_asm #(.NB(4), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
      .bdata(sq[255:0]), .full(full_), .tag(t13), .data(dd), .take(1'b1));
    reg v; reg [12:0] t; reg [1023:0] d;
    always @(posedge ck or negedge rn) if (!rn) v <= 1'b0; else v <= full_;
    always @(posedge ck) if (full_) begin t <= t13; d <= dd; end
    assign kv = {d, t, v};
    ot_svc_vpipe #(.W(1), .N(KV_ST), .X(XST)) u_dn (.ck(ck), .rst_n(rn), .v(full_), .d(1'b0), .qv(kv_dn), .q());
  end endgenerate
  generate if (1) begin : gik
    wire sv; wire [276:0] sq; wire full_; wire [12:0] t13; wire [1023:0] dd;
    ot_svc_vpipe #(.W(277), .N(IK_ST), .X(XST)) u_p (.ck(ck), .rst_n(rn), .v((IKS == 0) && b_v[IK_PC] && (b_t[IK_PC*17+15 +: 2] == 2'b10)),
      .d({b_t[IK_PC*17 +: 17], b_b[IK_PC*4 +: 4], b_d[IK_PC*256 +: 256]}), .qv(sv), .q(sq));
    ot_svc_asm #(.NB(4), .TW(13)) u_a (.ck(ck), .rst_n(rn), .bv(sv), .btag(sq[272:260]), .bbeat({1'b0, sq[259:256]}),
      .bdata(sq[255:0]), .full(full_), .tag(t13), .data(dd), .take(1'b1));
    reg [1023:0] d;
    always @(posedge ck) if (full_) d <= dd;
    assign ik = d;
    ot_svc_vpipe #(.W(1), .N(IK_ST), .X(XST)) u_dn (.ck(ck), .rst_n(rn), .v(full_), .d(1'b0), .qv(ik_dn), .q());
  end endgenerate

  // ---------------------------------------------------------------- WB: sector-write ingress, landing, completions
  generate if (WB != 0) begin : gwb
    // forwarded link: capture on the falling edge of wq_fclk, two-clock FIFO (the hub holds SO_DEPTH = 8 credits)
    localparam integer WFW = (WB_SOURCE_ACK != 0) ? 293 : 291;
    reg wf_v; reg [WFW-1:0] wf_d;
    wire wq_wck = ~wq_fclk;
    always @(posedge wq_wck or negedge rst) if (!rst) wf_v <= 1'b0; else wf_v <= wq_d[0];
    always @(posedge wq_wck) wf_d <= (WB_SOURCE_ACK != 0) ? {wq_source,wq_d[291:1]} : wq_d[291:1];
    wire w_empty, w_full; wire [2:0] w_fr; wire [WFW-1:0] wh;
    reg wbusy;                                         // one write between the FIFO and the PHY
    wire w_pop = !w_empty && !wbusy;
    // Conservative global hazard includes queued, in-flight pipeline and landing writes.
    // Native read admission must additionally fence outer producer/link debt.
    assign wq_pending = !w_empty || wbusy || hv || wf_v;
    ot_hbm_accel_cdc_fifo #(.W(WFW), .AW(3)) u_wq (.wclk(wq_wck), .wrst_n(rst), .we(wf_v), .wdata(wf_d),
      .full(w_full), .rd_freed(w_fr), .rclk(ck), .rrst_n(rn), .re(w_pop), .rdata(wh), .empty(w_empty));
    // to the PC request registers through WQ_ST (+ XST) wire stages; the accept token returns the same way
    wire lv, back; wire [WFW-1:0] ld;
    ot_svc_vpipe #(.W(WFW), .N(WQ_ST), .X(XST)) u_wp (.ck(ck), .rst_n(rn), .v(w_pop), .d(wh), .qv(lv), .q(ld));
    ot_svc_vpipe #(.W(1), .N(WQ_ST), .X(XST)) u_wb (.ck(ck), .rst_n(rn), .v(|wacc), .d(1'b0), .qv(back), .q());
    always @(posedge ck or negedge rn) if (!rn) wbusy <= 1'b0; else if (w_pop) wbusy <= 1'b1; else if (back) wbusy <= 1'b0;
    reg [1:0] hsource; wire [NPC-1:0] source_room;
    reg hv; reg [4:0] hpc; reg [29:0] ha; reg [255:0] hd;
    always @(posedge ck or negedge rn) if (!rn) hv <= 1'b0; else if (lv) hv <= 1'b1; else if (|wacc) hv <= 1'b0;
    always @(posedge ck) if (lv) begin hpc <= ld[4:0]; ha <= ld[34:5]; hd <= ld[290:35]; end
    if (WB_SOURCE_ACK != 0) begin : source_capture
      always @(posedge ck) if(lv) hsource <= ld[292:291];
    end else begin : legacy_source
      always @* hsource = 0;
    end
    for (p = 0; p < NPC; p = p + 1) begin : gq
      assign wreq[p] = hv && (hpc == p) && source_room[p];
    end
    assign wl_d = hd; assign wl_a = ha;
    // completions: raw capture of k_wr_done, count, Gray token counter (moves <= 1 a cycle toward the total)
    reg [NPC-1:0] wd_q; reg [15:0] ack_tot, ack_tok, pop_cnt; reg [15:0] g_q;
    integer c; reg [5:0] nd;
    always @* begin nd = 0; for (c = 0; c < NPC; c = c + 1) nd = nd + 6'(wd_q[c]); end
    always @(posedge ck or negedge rn)
      if (!rn) begin wd_q <= 0; ack_tot <= 0; ack_tok <= 0; pop_cnt <= 0; g_q <= 0; end
      else begin
        wd_q <= k_wr_done;
        ack_tot <= ack_tot + 16'(nd);
        if (ack_tok != ack_tot) ack_tok <= ack_tok + 16'd1;
        if (w_pop) pop_cnt <= pop_cnt + 16'd1;
        g_q <= {ack_tok[7:0] ^ (ack_tok[7:0] >> 1), pop_cnt[7:0] ^ (pop_cnt[7:0] >> 1)};
      end
    assign wq_g = g_q;
    if (WB_SOURCE_ACK != 0) begin : source_ack
      wire [17:0] deltas;
      reg [15:0] total [0:2], token [0:2];
      reg [31:0] gray;
      ot_hbm_write_source_pc #(.DEPTH(8)) u_source (
        .ck(ck),.rst_n(rn),.issue_v(wacc),.issue_source(hsource),
        .issue_rdy(source_room),.done_v(wd_q),.ack_n(deltas),.fault(wq_source_fault),.busy_pc(wq_source_busy));
      integer a;
      always @(posedge ck or negedge rn)
        if(!rn) begin
          for(a=0;a<3;a=a+1) begin total[a]<=0;token[a]<=0;end
          gray<=0;
        end else begin
          for(a=0;a<3;a=a+1) begin
            total[a]<=total[a]+16'(deltas[6*a +: 6]);
            if(token[a]!=total[a]) token[a]<=token[a]+16'd1;
            gray[8+8*a +: 8]<=token[a][7:0]^(token[a][7:0]>>1);
          end
          gray[7:0]<=pop_cnt[7:0]^(pop_cnt[7:0]>>1);
        end
      assign wq_source_g=gray;
    end else begin : legacy_ack
      assign source_room={NPC{1'b1}};
      assign wq_source_g=0; assign wq_source_fault=1'b0; assign wq_source_busy=0;
    end
  end else begin : gnwb
    assign wreq = {NPC{1'b0}}; assign wl_d = 256'd0; assign wl_a = 30'd0; assign wq_g = 16'd0;
    assign wq_source_g=0; assign wq_source_fault=1'b0; assign wq_source_busy=0; assign wq_pending=0;
  end endgenerate

  // ---------------------------------------------------------------- KVS: per-PC KV stream engine
  generate if ((KVS != 0) || (IKS != 0)) begin : gkvs
    wire idx_busy;
    reg act,idx;
    assign index_stream=idx;
    reg [8:0] blocks; reg [14:0] row0; reg [11:0] nsec; reg [NPC-1:0] mask; reg dn;
    wire [11:0] nsec4 = (nsec + 12'd3) & ~12'd3;     // reads are 4 sectors; a partial last group reads pad sectors
    wire [NPC-1:0] pdone;
    assign c_kvs_legacy = chv && (((KVS != 0) && (c_kind == 2'd1)) || ((IKS != 0) && (c_kind == 2'd2))) && !act && !dn && !idx_busy;
    assign c_index_prefetch = (IK_PREFETCH != 0) && (IKS != 0) && ip_v &&
      ip_d[1:0] == 2'd2 && ip_d[10:2] != 0 && ip_d[10:2] <= 9'd342 &&
      !ip_fault && !ik_fault && !chv && !cpend && !cv && !act && !dn && !idx_busy;
    assign c_kvs = c_kvs_legacy || c_index_prefetch;
    wire launch_idx = c_index_prefetch || c_kind == 2'd2;
    wire [8:0] launch_blocks = c_index_prefetch ? ip_d[10:2] : chd[69:61];
    wire [14:0] launch_row = c_index_prefetch ? ip_d[25:11] : chd[16:2];
    wire [NPC*269-1:0] sectors;wire [63:0] idx_pop;
    wire [31:0] idx_v;wire [383:0] idx_j;wire [8191:0] idx_data;
    for(genvar ip=0;ip<32;ip=ip+1)begin
      assign idx_v[ip]=idx && sectors[ip*269];
      assign idx_j[ip*12+:12]=sectors[ip*269+1+:12];
      assign idx_data[ip*256+:256]=sectors[ip*269+13+:256];
    end
    if (IKS != 0) begin : gi
    ot_hbm_index_lines #(.ENABLE(IKS),.CRED(IK_CRED),.DEPTH(IK_DEPTH)) idx_lines(.clk(ck),.rst_n(rn),.start(c_kvs && c_kind==2'd2),
      .blocks(chd[69:61]),.sector_v(idx_v),.sector_j(idx_j),.sector_data(idx_data),.credit(ik_credit),
      .lines(ik_lines),.pop(idx_pop),.done(ik_done),.fault(ik_fault),.retained(idx_busy));
    end else begin : gni
      assign ik_lines=0;assign ik_done=0;assign index_data_fault=0;assign idx_busy=0;assign idx_pop=0;
    end
    always @(posedge ck or negedge rn)
      if (!rn) begin act <= 1'b0; dn <= 1'b0; idx <= 1'b0; blocks <= 0; end
      else begin
        dn <= 1'b0;
        if (c_kvs) begin act <= 1'b1; idx <= launch_idx; blocks <= launch_blocks; end
        else if (act && &pdone) begin act <= 1'b0; dn <= 1'b1; end
      end
    always @(posedge ck) if (c_kvs) begin row0 <= launch_row; nsec <= launch_idx ? 12'((17*launch_blocks+31)/32) : chd[28:17]; mask <= launch_idx ? {NPC{1'b1}} : chd[60:29]; end
    assign kvs_done = dn;
    for (p = 0; p < NPC; p = p + 1) begin : gs
      reg [11:0] jn;          // reads requested x 4
      // issue order = j order (a bank-set-interleaved order was measured WORSE: 0.22-0.23 of peak vs 0.80-0.86 at
      // 1,024-2,048 sectors a PC, results/rtl/hbm_system_20261008/svc_kvs.json note)
      wire [9:0] rq = jn[11:2];
      wire [11:0] jq = {rq, 2'b00};
      reg [12:0] jr;          // beats received
      localparam SC=$clog2(IK_DEPTH+1);
      reg [SC-1:0] slots;
      reg [6:0] nob;          // beats requested (accepted) and not yet returned
      wire on = act && mask[p];
      assign sreq[p] = on && (jn < nsec) && (nob <= 7'(4 * KNO - 4)) && (!idx || (slots >= 4)) && !ik_fault;
      wire [29:0] sa; wire sf;
      ot_hbm_kport_map u_m (.pc(5'(p)), .bank({jq[9:7], jq[1:0]}), .row({4'd0, row0} + 19'(jq >> 10)), .col(jq[6:2]),
        .s(sa), .fault(sf));
      assign s_addr[p*30 +: 30] = {sa[29:2], 2'b00};               // 4-aligned: one read = j[1:0] 0..3
      assign s_jt[p*10 +: 10] = rq;
      // a returned beat: tag 01 + j >> 2 (reads may return out of order under FR-FCFS: j comes from the tag)
      wire bv = b_v[p] && (b_t[p*17+15 +: 2] == (idx ? 2'b10 : 2'b01));
      wire [11:0] bj4 = {b_t[p*17+5 +: 10], 2'b00};
      wire [14:0] rr = row0 + 15'(bj4 >> 10);
      always @(posedge ck or negedge rn)
        if (!rn) begin jn <= 0; jr <= 0; nob <= 0; slots <= IK_DEPTH; end
        else if (c_kvs) begin jn <= 0; jr <= 0; nob <= 0; slots <= IK_DEPTH; end
        else begin
          if (sacc[p]) jn <= jn + 12'd4;
          if(idx)slots <= slots - (sacc[p] ? SC'(4) : SC'(0)) + SC'(idx_pop[p*2+:2]);
          if (bv) jr <= jr + 13'd1;
          nob <= nob + (sacc[p] ? 7'd4 : 7'd0) - (bv ? 7'd1 : 7'd0);
        end
      assign pdone[p] = !mask[p] || (jr >= {1'b0, nsec4});
      // lane: j = (tag j >> 2) * 4 + (beat ^ row[1:0]) (the read returns its sectors in s order)
      reg lv; reg [11:0] lj; reg [255:0] ld;
      wire [11:0] bj = {bj4[11:2], b_b[p*4 +: 2] ^ rr[1:0]};
      always @(posedge ck or negedge rn) if (!rn) lv <= 1'b0; else lv <= bv && (idx || (bj < nsec));   // pad sectors dropped
      always @(posedge ck) if (bv) begin lj <= bj; ld <= b_d[p*256 +: 256]; end
      assign sectors[p*269 +: 269] = {ld, lj, lv};
      assign kvs[p*269 +: 269] = {ld, lj, lv && !idx};
    end
  end else begin : gnkvs
    assign sreq = {NPC{1'b0}}; assign s_addr = {NPC*30{1'b0}}; assign s_jt = {NPC*10{1'b0}}; assign c_kvs = 1'b0;
    assign c_kvs_legacy=0; assign c_index_prefetch=0;
    assign kvs = {NPC*269{1'b0}}; assign kvs_done = 1'b0;
    assign ik_lines=0;assign ik_done=0;assign index_data_fault=0;assign index_stream=0;
  end endgenerate
endmodule
`default_nettype wire
