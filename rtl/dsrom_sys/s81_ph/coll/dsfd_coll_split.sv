`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_coll_split (redesign-ds 2026-10-09, coordinator: "a 1.36 mm tile with 1,151 ps clock insertion is the root
// problem"): the S81 collective core column (dsfd_coll_core, 540 x 1360.8 um, measured CTS insertion 1,151 ps, every
// route lost to the insertion / hold window) split into THREE abutted hard tiles with registered boundaries
// (Tensix / Cerebras pattern), stacked S -> N in the same column (width CW, the column widened so the engine tile keeps
// its 24 FIFO SRAMs at <= 60 % utilisation):
//
//   dsfd_coll_cb  (bottom, CW x 340.2)  VM side: f_vm / ts / t_vm (S face, the slab's VM interface), the OUTPUT queue
//                                       (16 deep, sliced, push replicas) + t_vm register; relays of lanes 0 (W0) and
//                                       4 (E0) between their lane tiles and the engine tile.
//   dsfd_coll_ce  (middle, CW x 680.4)  ot_s81ph_coll_core (EXT 1, OQX 1): TP4 engine + receive FIFO SRAMs, the 6 VM
//                                       input queues, packer, credits; lanes 1, 2 (W) and 5, 6 (E) at its own faces.
//   dsfd_coll_ct  (top, CW x 340.2)     relays of lanes 3 (W3) and 7 (E3).
//
// Every crossing is latency insensitive: lane streams pass through 2-slot skids (ot_s81ph_skid2: valid, data and
// ready all registered) at BOTH sides of every tile face; the packer word goes down as a registered stream into the
// remote output queue under credits (OQX: the counter starts at the queue depth, the queue returns one pulse a pop);
// f_vm / flt / faults cross as plain pin registers (the VM sends only with credits, so the f_vm pipe never needs a
// ready).  Exact: per-lane order and the engine's reduce / gather sequence are unchanged (transaction level; bench
// tb_s81ph_coll_sys with +define+OT_S81PH_COLL_SPLIT).  Cycle cost vs dsfd_coll_core: f_vm -> queues +2, packer word
// -> t_vm +2, lanes 0 / 3 / 4 / 7 +2 each way (lanes 1 / 2 / 5 / 6 unchanged).
// ---------------------------------------------------------------------------------------------------------------

// ---- two skids in series: one at each face of a relay tile
module ot_s81ph_relay2 #(parameter integer W = 8) (
    input  wire clk, input wire rst_n,
    input  wire in_v, output wire in_r, input wire [W-1:0] in_d,
    output wire out_v, input wire out_r, output wire [W-1:0] out_d
);
    wire m_v, m_r; wire [W-1:0] m_d;
    ot_s81ph_skid2 #(.W(W)) u_a (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_r(in_r), .in_d(in_d), .out_v(m_v), .out_r(m_r), .out_d(m_d));
    ot_s81ph_skid2 #(.W(W)) u_b (.clk(clk), .rst_n(rst_n), .in_v(m_v), .in_r(m_r), .in_d(m_d), .out_v(out_v), .out_r(out_r), .out_d(out_d));
endmodule

// ---- bottom tile: VM interface, output queue, lanes 0 / 4 relays
module dsfd_coll_cb #(parameter integer OD = 16) (
    input  wire [0:0]     ck,
    input  wire [0:0]     rs,
    // S face: the slab VM interface
    input  wire [591:0]   f_vm,
    input  wire [2:0]     ts,
    output reg  [2099:0]  t_vm,
    // W face: lane 0 (W0) tile;  E face: lane 4 (E0) tile
    output wire [0:0] wlo_v,  input wire [0:0] wlo_r, output wire [552:0] wlo_d,
    input wire [0:0] wli_v,  output wire [0:0] wli_r, input  wire [552:0] wli_d,
    input  wire [2:0]     wflt,
    output wire [0:0] elo_v,  input wire [0:0] elo_r, output wire [552:0] elo_d,
    input wire [0:0] eli_v,  output wire [0:0] eli_r, input  wire [552:0] eli_d,
    input  wire [2:0]     eflt,
    // N face: seam to dsfd_coll_ce
    output reg  [591:0]   fvm_u,
    output reg  [5:0]     flt_u,        // {lane 4 flt, lane 0 flt}
    input wire [0:0] lo0_v,  output wire [0:0] lo0_r, input  wire [552:0] lo0_d,
    output wire [0:0] li0_v,  input wire [0:0] li0_r, output wire [552:0] li0_d,
    input wire [0:0] lo4_v,  output wire [0:0] lo4_r, input  wire [552:0] lo4_d,
    output wire [0:0] li4_v,  input wire [0:0] li4_r, output wire [552:0] li4_d,
    input wire [0:0] bw_v,
    input  wire [2099:1]  bw_d,
    output reg [0:0] bw_cr,
    output reg [0:0] bw_flt
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // VM input: pin register, then the seam register (two edges, no handshake: the VM sends only with credits)
    reg [591:0] fv_r; reg [2:0] ts_r; reg [5:0] flt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv_r <= 0; fvm_u <= 0; ts_r <= 0; flt_r <= 0; flt_u <= 0; end
        else begin fv_r <= f_vm; fvm_u <= fv_r; ts_r <= ts; flt_r <= {eflt, wflt}; flt_u <= flt_r; end
    // lane relays (lane-face skid + seam-face skid)
    ot_s81ph_relay2 #(.W(553)) u_lo0 (.clk(clk), .rst_n(rst_n), .in_v(lo0_v), .in_r(lo0_r), .in_d(lo0_d), .out_v(wlo_v), .out_r(wlo_r), .out_d(wlo_d));
    ot_s81ph_relay2 #(.W(553)) u_li0 (.clk(clk), .rst_n(rst_n), .in_v(wli_v), .in_r(wli_r), .in_d(wli_d), .out_v(li0_v), .out_r(li0_r), .out_d(li0_d));
`ifdef OT_S81PH_MUT_SPLIT_LO4FLIP
    // negative control: the lane 4 outbound relay flips data bit 0 (a corrupted relay)
    ot_s81ph_relay2 #(.W(553)) u_lo4 (.clk(clk), .rst_n(rst_n), .in_v(lo4_v), .in_r(lo4_r), .in_d(lo4_d ^ 553'd1), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
`else
    ot_s81ph_relay2 #(.W(553)) u_lo4 (.clk(clk), .rst_n(rst_n), .in_v(lo4_v), .in_r(lo4_r), .in_d(lo4_d), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
`endif
    ot_s81ph_relay2 #(.W(553)) u_li4 (.clk(clk), .rst_n(rst_n), .in_v(eli_v), .in_r(eli_r), .in_d(eli_d), .out_v(li4_v), .out_r(li4_r), .out_d(li4_d));
    // packer word: seam pin register, then the output queue (sliced, push replicated per slice; OD 16 = the local
    // queue's 4 + the credit loop: push issue -> ce reg -> pin reg -> queue -> pop -> bw_cr -> ce cred = 6 edges, + margin)
    reg          bw_vq; reg [2099:1] bw_dq;
    always @(posedge clk or negedge rst_n) if (!rst_n) bw_vq <= 1'b0; else bw_vq <= bw_v;
    always @(posedge clk) bw_dq <= bw_d;
    localparam integer OSW = 256, ONS = (2099 + OSW - 1) / OSW;
    (* keep *) reg [ONS-1:0] pq;
    reg [2099:1] wq;
    always @(posedge clk or negedge rst_n) if (!rst_n) pq <= {ONS{1'b0}}; else pq <= {ONS{bw_vq}};
    always @(posedge clk) wq <= bw_dq;
    wire [ONS-1:0] s_hv, s_flt; wire [2099:1] oq_hd;
    genvar j;
    generate for (j = 0; j < ONS; j = j + 1) begin : g_s
        localparam integer LO = j * OSW, WS = ((2099 - LO) < OSW) ? (2099 - LO) : OSW;
        ot_s81ph_rfifo #(.W(WS), .D(OD)) u_oq (.clk(clk), .rst_n(rst_n), .push(pq[j]), .wd(wq[1 + LO +: WS]),
            .pop(s_hv[0] && ts_r[0]), .hv(s_hv[j]), .hd(oq_hd[1 + LO +: WS]), .room(), .room2(), .fault(s_flt[j]));
    end endgenerate
    wire pop = s_hv[0] && ts_r[0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin t_vm <= 0; bw_cr <= 1'b0; bw_flt <= 1'b0; end
        else begin
            t_vm <= pop ? {oq_hd, 1'b1} : 2100'd0;
            bw_cr <= pop;
            if (|s_flt) bw_flt <= 1'b1;
        end
    wire unused_ok = &{1'b0, ts_r[2:1]};
endmodule

// ---- middle tile: the collective core (engine, input queues, packer) + lanes 1, 2 (W) / 5, 6 (E)
module dsfd_coll_ce #(
`ifdef OT_S81PH_COLL_QPIPE
    parameter integer QPIPE = 1,
`else
    parameter integer QPIPE = 0,
`endif
    parameter integer OD = 16
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rs,
    // W face: lanes 1, 2;  E face: lanes 5, 6  (index 0 = the lower lane)
    output wire [1:0]       wlo_v,  input  wire [1:0] wlo_r, output wire [2*553-1:0] wlo_d,
    input  wire [1:0]       wli_v,  output wire [1:0] wli_r, input  wire [2*553-1:0] wli_d,
    input  wire [5:0]       wflt,
    output wire [1:0]       elo_v,  input  wire [1:0] elo_r, output wire [2*553-1:0] elo_d,
    input  wire [1:0]       eli_v,  output wire [1:0] eli_r, input  wire [2*553-1:0] eli_d,
    input  wire [5:0]       eflt,
    // S face: seam to dsfd_coll_cb
    input  wire [591:0]     fvm_u,
    input  wire [5:0]       flt_u,
    output wire [0:0] lo0_v,  input wire [0:0] lo0_r, output wire [552:0] lo0_d,
    input wire [0:0] li0_v,  output wire [0:0] li0_r, input  wire [552:0] li0_d,
    output wire [0:0] lo4_v,  input wire [0:0] lo4_r, output wire [552:0] lo4_d,
    input wire [0:0] li4_v,  output wire [0:0] li4_r, input  wire [552:0] li4_d,
    output reg [0:0] bw_v,
    output reg  [2099:1]    bw_d,
    input wire [0:0] bw_cr,
    input wire [0:0] bw_flt,
    // N face: seam to dsfd_coll_ct
    output wire [0:0] lo3_v,  input wire [0:0] lo3_r, output wire [552:0] lo3_d,
    input wire [0:0] li3_v,  output wire [0:0] li3_r, input  wire [552:0] li3_d,
    output wire [0:0] lo7_v,  input wire [0:0] lo7_r, output wire [552:0] lo7_d,
    input wire [0:0] li7_v,  output wire [0:0] li7_r, input  wire [552:0] li7_d,
    input  wire [5:0]       flt_d          // {lane 7 flt, lane 3 flt}
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [591:0] fv_r; reg [23:0] flt_r; reg bw_crq, bw_fltq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv_r <= 0; flt_r <= 0; bw_crq <= 1'b0; bw_fltq <= 1'b0; end
        else begin
            fv_r <= fvm_u; bw_crq <= bw_cr; bw_fltq <= bw_flt;
            // lane order 0..7 (3 bits each): 0 / 4 from the S seam, 1 / 2 / 5 / 6 local, 3 / 7 from the N seam
            flt_r <= {flt_d[5:3], eflt[5:3], eflt[2:0], flt_u[5:3], flt_d[2:0], wflt[5:3], wflt[2:0], flt_u[2:0]};
        end
    // core <-> the 8 lane streams, each through one skid at this tile's face
    wire [7:0] x_lo_v, x_lo_r, x_lo_l, x_li_v, x_li_r, x_li_l;
    wire [8*552-1:0] x_lo_d, x_li_d;
    // face-side stream ends, per lane (lo: out of the tile; li: into the tile)
    wire [7:0] f_lo_v, f_lo_r, f_li_v, f_li_r;
    wire [552:0] f_lo_d [0:7];
    wire [552:0] f_li_d [0:7];
    assign lo0_v = f_lo_v[0]; assign f_lo_r[0] = lo0_r; assign lo0_d = f_lo_d[0];
    assign f_li_v[0] = li0_v; assign li0_r = f_li_r[0]; assign f_li_d[0] = li0_d;
    assign lo4_v = f_lo_v[4]; assign f_lo_r[4] = lo4_r; assign lo4_d = f_lo_d[4];
    assign f_li_v[4] = li4_v; assign li4_r = f_li_r[4]; assign f_li_d[4] = li4_d;
    assign lo3_v = f_lo_v[3]; assign f_lo_r[3] = lo3_r; assign lo3_d = f_lo_d[3];
    assign f_li_v[3] = li3_v; assign li3_r = f_li_r[3]; assign f_li_d[3] = li3_d;
    assign lo7_v = f_lo_v[7]; assign f_lo_r[7] = lo7_r; assign lo7_d = f_lo_d[7];
    assign f_li_v[7] = li7_v; assign li7_r = f_li_r[7]; assign f_li_d[7] = li7_d;
    genvar l;
    generate for (l = 0; l < 2; l = l + 1) begin : g_loc
        assign wlo_v[l] = f_lo_v[1 + l]; assign f_lo_r[1 + l] = wlo_r[l]; assign wlo_d[l*553 +: 553] = f_lo_d[1 + l];
        assign f_li_v[1 + l] = wli_v[l]; assign wli_r[l] = f_li_r[1 + l]; assign f_li_d[1 + l] = wli_d[l*553 +: 553];
        assign elo_v[l] = f_lo_v[5 + l]; assign f_lo_r[5 + l] = elo_r[l]; assign elo_d[l*553 +: 553] = f_lo_d[5 + l];
        assign f_li_v[5 + l] = eli_v[l]; assign eli_r[l] = f_li_r[5 + l]; assign f_li_d[5 + l] = eli_d[l*553 +: 553];
    end endgenerate
    generate for (l = 0; l < 8; l = l + 1) begin : g_l
        ot_s81ph_skid2 #(.W(553)) u_so (.clk(clk), .rst_n(rst_n), .in_v(x_lo_v[l]), .in_r(x_lo_r[l]),
            .in_d({x_lo_l[l], x_lo_d[l*552 +: 552]}), .out_v(f_lo_v[l]), .out_r(f_lo_r[l]), .out_d(f_lo_d[l]));
        ot_s81ph_skid2 #(.W(553)) u_si (.clk(clk), .rst_n(rst_n), .in_v(f_li_v[l]), .in_r(f_li_r[l]), .in_d(f_li_d[l]),
            .out_v(x_li_v[l]), .out_r(x_li_r[l]), .out_d({x_li_l[l], x_li_d[l*552 +: 552]}));
    end endgenerate
    wire c_bw_v; wire [2099:1] c_bw_d;
    ot_s81ph_coll_core #(.EXT(1), .OQPIPE(1), .QPIPE(QPIPE), .OQX(1), .OQX_D(OD)) u_core (.clk(clk), .rst_n(rst_n),
        .lane_rx({8*515{1'b0}}), .lane_tx(), .f_vm(fv_r), .ts(3'd0), .t_vm(), .fault(), .rank(), .eng_en(),
        .x_lo_v(x_lo_v), .x_lo_r(x_lo_r), .x_lo_d(x_lo_d), .x_lo_l(x_lo_l),
        .x_li_v(x_li_v), .x_li_r(x_li_r), .x_li_d(x_li_d), .x_li_l(x_li_l), .x_lflt(flt_r),
        .bw_v(c_bw_v), .bw_d(c_bw_d), .bw_cr(bw_crq), .bw_flt(bw_fltq));
    // packer word: one more register at the S face pins
    always @(posedge clk or negedge rst_n) if (!rst_n) bw_v <= 1'b0; else bw_v <= c_bw_v;
    always @(posedge clk) bw_d <= c_bw_d;
endmodule

// ---- top tile: lanes 3 / 7 relays
module dsfd_coll_ct (
    input  wire [0:0]     ck,
    input  wire [0:0]     rs,
    output wire [0:0] wlo_v,  input wire [0:0] wlo_r, output wire [552:0] wlo_d,
    input wire [0:0] wli_v,  output wire [0:0] wli_r, input  wire [552:0] wli_d,
    input  wire [2:0]     wflt,
    output wire [0:0] elo_v,  input wire [0:0] elo_r, output wire [552:0] elo_d,
    input wire [0:0] eli_v,  output wire [0:0] eli_r, input  wire [552:0] eli_d,
    input  wire [2:0]     eflt,
    // S face: seam to dsfd_coll_ce
    input wire [0:0] lo3_v,  output wire [0:0] lo3_r, input  wire [552:0] lo3_d,
    output wire [0:0] li3_v,  input wire [0:0] li3_r, output wire [552:0] li3_d,
    input wire [0:0] lo7_v,  output wire [0:0] lo7_r, input  wire [552:0] lo7_d,
    output wire [0:0] li7_v,  input wire [0:0] li7_r, output wire [552:0] li7_d,
    output reg  [5:0]     flt_d
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [5:0] flt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin flt_r <= 0; flt_d <= 0; end
        else begin flt_r <= {eflt, wflt}; flt_d <= flt_r; end
    ot_s81ph_relay2 #(.W(553)) u_lo3 (.clk(clk), .rst_n(rst_n), .in_v(lo3_v), .in_r(lo3_r), .in_d(lo3_d), .out_v(wlo_v), .out_r(wlo_r), .out_d(wlo_d));
    ot_s81ph_relay2 #(.W(553)) u_li3 (.clk(clk), .rst_n(rst_n), .in_v(wli_v), .in_r(wli_r), .in_d(wli_d), .out_v(li3_v), .out_r(li3_r), .out_d(li3_d));
    ot_s81ph_relay2 #(.W(553)) u_lo7 (.clk(clk), .rst_n(rst_n), .in_v(lo7_v), .in_r(lo7_r), .in_d(lo7_d), .out_v(elo_v), .out_r(elo_r), .out_d(elo_d));
    ot_s81ph_relay2 #(.W(553)) u_li7 (.clk(clk), .rst_n(rst_n), .in_v(eli_v), .in_r(eli_r), .in_d(eli_d), .out_v(li7_v), .out_r(li7_r), .out_d(li7_d));
endmodule
