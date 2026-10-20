`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_coll_lane_safe4 (S81-COLL bank64 safe source, LEAD-S81 decision 10-19): the collective link lane tile
// rebuilt to the owner safe-design checklist, cycle-identical at every port to the legacy P1 lane
// (ot_s81ph_coll_lane GFMT 1 / EPPIPE 2 / LCR 1 / RXSRAM 1; lane-pair miter tb_coll_safe4_boundary).  Fixed
// configuration (the production tile options): FB 69, SEQW 10, CREDITS 512, UPGATE 1, SAFE reset relays.
// All storage on the 64-bit native bank family (<= 6 pins/um faces):
//   endpoint replay 553x512 + receive FIFO 553x512: ot_sram_oldread_b64, 2 x 18 ot_sram_1r1w2c_256x64_m1
//   core landing (credit rx) 553x8:                  ot_link_credit_rx_b64,   9 ot_sram_1r1w2c_32x64_m1
//   gearbox slot store 595x4:                        ot_s81ph_link_gbx_safe3, 10 ot_sram_1r1w2c_32x64_m1
// = 55 macros (was 10 x 512x128 + 5 x 32x128 + a 2,380-bit runtime-indexed flop array).
// Control fanout: registered one-hot selects / kept same-edge copies (see the gearbox and endpoint safe4 headers);
// credit tx DFREE with registered ready copies.  Reset: one balanced 3-edge tree (ot_rst_relay_tree3, same release
// depth as safe2: edges 1/2/3), every leaf drives <= ~32 reset pins.  0 added data / control cycles vs P1.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_coll_lane_safe4 #(
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 700,
    parameter integer IDLE_P = 1024,
    parameter integer TF_CLEANUP = 0,
    // REACH (S81-TILES-E 10-20, opt-in, default 0 = the v8 safe4 netlist): forwarded relay hops so no single-cycle wire
    // crosses the tile (s6c actual GRT native reach: 5,403 pairs > 405 um, max 757 um, receive control c_diff / c_crc_ok /
    // xp_v at the gearbox -> the 18 RX FIFO address groups at the core face).  REACH = 1:
    //   rx landing 2 stages (lr -> lr2, pin flop at the link face, second flop beside the gearbox)            +1 RX
    //   endpoint RX_STAGES 3 -> 5 (two forwarded frame hops gearbox -> receive control beside the RX FIFO)       +2 RX
    //   reverse (ACK / credit) frame relay 2 stages endpoint -> gearbox (reset-free; consumed only under lk1)   +2 ACK
    //   core landing lo_v / lo_d 1 stage at the core face before the credit-rx landing flops                    +1 core->link
    // Every hop is a plain register (no flow control); the credit / ACK protocol absorbs the extra edges (ACK timeout
    // derives from RTT incl. RX_STAGES, margin 2*KEEPALIVE+32 >> 2; core credits 8 >> landing RTT).
    parameter integer REACH = 0
) (
    input  wire          clk,
    input  wire          rs_n,
    input  wire          ch_b,
    input  wire [514:0]  rx,
    output wire [511:0]  tx,
    output wire          tf,
    input  wire          lo_v,
    output wire          lo_r,
    input  wire [552:0]  lo_d,
    output wire          li_v,
    input  wire          li_r,
    output wire [552:0]  li_d,
    output reg  [2:0]    flt
);
    localparam integer FB = 69, CREDITS = 512, SEQW = 10;
    localparam integer W = FB * 8;
    localparam integer FFW = SEQW + 1 + W + 32;
    localparam integer RFW = 1 + SEQW + $clog2(CREDITS + 1) + 32;
    localparam integer PNUM = FB * 3 * (IDLE_P - 1);
    localparam integer PDEN = 4 * IDLE_P;
    // reset leaves
    localparam integer HEAD_NS = (W + 1 + 15) / 16;          // credit rx forwarding slices (35)
    localparam integer HEAD_RL = (HEAD_NS + 7) / 8;          // leaves for them (8 slices x 2 flags each)
    localparam integer MEM_NS = (W + 1 + 7) / 8, MEM_NA = (MEM_NS + 3) / 4, MEM_RST = 2 * (MEM_NS + MEM_NA);
    `ifdef OT_COLL_NATIVE32
    localparam integer EP_RN = 16, GB_RN = 22;
`else
    localparam integer EP_RN = 12, GB_RN = 22;
`endif   // = ot_s81ph_link_gbx_safe3 RN (checked there)
    localparam integer R_LOC = 0, R_CRX = 1, R_CTX = 2, R_HEAD = 3, R_EP = R_HEAD + HEAD_RL, R_MEM = R_EP + EP_RN,
                       R_GB = R_MEM + MEM_RST, NREG = R_GB + GB_RN;
    wire [NREG-1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(NREG)) u_rr (.clk(clk), .rst_n_in(rs_n), .rst_n(rr));
    wire rst_n = rr[R_LOC];
    wire [HEAD_NS-1:0] head_rst_n;
    genvar k;
    generate for (k = 0; k < HEAD_NS; k = k + 1) begin : g_hr
        assign head_rst_n[k] = rr[R_HEAD + k / 8];
    end endgenerate
    // rx pin landing: reset only on the three flag bits
    reg [2:0] lr_f0; reg [511:0] lr_d0;
    always @(posedge clk or negedge rst_n) if (!rst_n) lr_f0 <= 3'b000; else lr_f0 <= {rx[514], rx[513], rx[0]};
    always @(posedge clk) lr_d0 <= rx[512:1];
    wire [2:0] lr_f; wire [511:0] lr_d;
    generate if (REACH != 0) begin : g_lr2
        reg [2:0] lr_f2; reg [511:0] lr_d2;
        always @(posedge clk or negedge rst_n) if (!rst_n) lr_f2 <= 3'b000; else lr_f2 <= lr_f0;
`ifdef OT_COLL_REACH_MUT_LR
        always @(posedge clk) lr_d2 <= lr_d2;   // mutant: the second rx landing hop never loads its beat
`else
        always @(posedge clk) lr_d2 <= lr_d0;
`endif
        assign lr_f = lr_f2; assign lr_d = lr_d2;
    end else begin : g_lr1
        assign lr_f = lr_f0; assign lr_d = lr_d0;
    end endgenerate
    // core -> link: credit landing on bank64 SRAM
    wire iv, ir, il; wire [W-1:0] id;
    reg  lk1, up;
    wire ir_g = ir && up;
    wire lcf;
    wire lo_vl; wire [W:0] lo_dl;
    generate if (REACH != 0) begin : g_lo2
        reg lo_vq; reg [W:0] lo_dq;
        always @(posedge clk or negedge rr[R_CRX]) if (!rr[R_CRX]) lo_vq <= 1'b0; else lo_vq <= lo_v;
`ifdef OT_COLL_REACH_MUT_LO
        always @(posedge clk) lo_dq <= lo_dq;   // mutant: landing data never loads
`else
        always @(posedge clk) lo_dq <= lo_d;
`endif
        assign lo_vl = lo_vq; assign lo_dl = lo_dq;
    end else begin : g_lo1
        assign lo_vl = lo_v; assign lo_dl = lo_d;
    end endgenerate
    ot_link_credit_rx_b64 #(.W(W + 1), .DEPTH(8), .WFREE(1), .LOCAL_HIT(1)) u_ski (
        .clk(clk), .rst_n(rr[R_CRX]), .head_rst_n(head_rst_n), .l_valid(lo_vl), .l_data(lo_dl),
        .l_credit(lo_r), .o_valid(iv), .o_ready(ir_g), .o_data({il, id}), .fault(lcf));
    // link -> core: credit tx with registered ready copies
    wire ov, ol; wire [W-1:0] od; wire [2:0] orr;
    ot_link_credit_tx_rc #(.W(W + 1), .CRED(8), .NR(3)) u_sko (.clk(clk), .rst_n(rr[R_CTX]), .i_valid(ov), .i_ready(orr),
        .i_data({ol, od}), .l_valid(li_v), .l_data(li_d), .l_credit(li_r));
    wire ftv, rtv, rtv0, frv, rrv; wire [FFW-1:0] ft, fr; wire [RFW-1:0] rt, rt0, rrf; wire ep_f, gb_f, gb_l;
    generate if (REACH != 0) begin : g_rt2
        // reverse frame relay, reset-free: the gearbox consumes r_tx_v only under lk1 (cleared by every lane reset and
        // set only once the gearbox has locked, many edges after the 2-stage relay has flushed)
        reg rv1, rv2; reg [RFW-1:0] rf1, rf2;
`ifdef OT_COLL_REACH_MUT_RT
        always @(posedge clk) begin rv1 <= rtv0; rv2 <= 1'b0; rf1 <= rt0; rf2 <= rf1; end   // mutant: the relay drops every reverse frame
`else
        always @(posedge clk) begin rv1 <= rtv0; rv2 <= rv1; rf1 <= rt0; rf2 <= rf1; end
`endif
        assign rtv = rv2; assign rt = rf2;
    end else begin : g_rt1
        assign rtv = rtv0; assign rt = rt0;
    end endgenerate
    ot_s81ph_link_ep_safe4 #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(REACH != 0 ? 5 : 3), .CHANNEL_CYCLES(CH_UCIE), .CHANNEL_CYCLES_B(CH_BOARD),
        .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(1), .PIPE(2), .RXPIPE(1), .TOREG(1), .MWR(1),
        .DNR(1), .OLDREAD(1), .RN(EP_RN), .ORN(3)) u_ep (
        .clk(clk), .rst_v(rr[R_EP +: EP_RN]), .mem_rst_n(rr[R_MEM +: MEM_RST]), .ch_b(ch_b),
        .in_valid(iv && up), .in_ready(ir), .in_data(id), .in_last(il),
        .out_valid(ov), .out_ready_v(orr), .out_data(od), .out_last(ol),
        .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv0), .r_tx(rt0), .r_rx_v(rrv), .r_rx(rrf),
        .credit_stalls(), .fault(ep_f), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
        .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
    ot_s81ph_link_gbx_safe3 #(.FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .RN(GB_RN),
`ifdef OT_S81PH_GBX3_MUT
        .MUT(`OT_S81PH_GBX3_MUT)
`else
        .MUT(0)
`endif
    ) u_gb (
        .clk(clk), .rst_n(rr[R_GB +: GB_RN]), .f_tx_v(ftv), .f_tx(ft), .r_tx_v(rtv && lk1), .r_tx(rt), .beat_tx(tx),
        .beat_rx_v(lr_f[0] && lr_f[1]), .beat_rx(lr_d), .f_rx_v(frv), .f_rx(fr), .r_rx_v(rrv), .r_rx(rrf),
        .locked(gb_l), .fault(gb_f));
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 3'b000; else flt <= {lr_f[2], gb_f, ep_f};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lk1 <= 1'b0; up <= 1'b0; end
        else begin if (gb_l) lk1 <= 1'b1; if (rrv) up <= 1'b1; end
    generate if (TF_CLEANUP == 0) begin : g_tf_legacy
        ot_s81ph_ckbuf u_tf (.a(clk), .y(tf));
    end else begin : g_no_tf
        assign tf = 1'b0;
    end endgenerate
endmodule

// tile tops: the safe2 tile ports (tf present unless OT_S81PH_COLL_TF_CLEANUP)
module dsfd_coll_lane_w_safe4 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
`ifdef OT_S81PH_COLL_TF_CLEANUP
    wire tf_unused;
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf_unused), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`else
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(0)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf[0]), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`endif
endmodule
module dsfd_coll_lane_e_safe4 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
`ifdef OT_S81PH_COLL_TF_CLEANUP
    wire tf_unused;
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf_unused), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`else
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(0)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf[0]), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`endif
endmodule

// S81-TILES-E 10-20: REACH = 1 tile tops (COLL s7 kits dscoll_lane_{w,e}_s7*), ports identical to the safe4 tops (tf present unless OT_S81PH_COLL_TF_CLEANUP)
module dsfd_coll_lane_w_safe7 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
`ifdef OT_S81PH_COLL_TF_CLEANUP
    wire tf_unused;
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(1), .REACH(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf_unused), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`else
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(0), .REACH(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf[0]), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`endif
endmodule
module dsfd_coll_lane_e_safe7 #(parameter integer CH_BOARD = 700) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
`ifndef OT_S81PH_COLL_TF_CLEANUP
    output wire [0:0] tf,
`endif
    input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
`ifdef OT_S81PH_COLL_TF_CLEANUP
    wire tf_unused;
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(1), .REACH(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf_unused), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`else
    ot_s81ph_coll_lane_safe4 #(.CH_BOARD(CH_BOARD), .TF_CLEANUP(0), .REACH(1)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx),
        .tf(tf[0]), .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
`endif
endmodule

