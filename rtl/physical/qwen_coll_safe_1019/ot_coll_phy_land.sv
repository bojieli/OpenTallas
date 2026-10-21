`timescale 1ns/1ps
// QW-COLLIO2 10-21: PHY pin-register REGION of a collective face codec (owner CLOCK RULE 10-20 08:55).
// The codec controller (ot_qwen_static_slot_ctl on codec_ck[0], the codec CORE region beside the banks) and the PHY
// pins (E face) are two clock regions fed by two entries of the same die codec clock (mesochronous, same PLL).
// Every crossing between them lands in a fixed-latency mesochronous landing ring:
//   RX  pins (phy_rx, phy_rx_valid, phy_up) -> ring slots on phy_ck (the slots ARE the pin capture flops) ->
//       read select on codec_ck[0] -> the controller's existing pin registers rf / rv / up_q (the ring output regs).
//       Added: K edges.
//   TX  controller frame/status registers (p_tx_flit, p_tx_v, epoch_abort, fault_cause) -> ring slots on codec_ck[0]
//       -> registered read on phy_ck = the PHY output pin registers.  Added: 1 + K edges.
// Ring: depth D slots, free-running write/read pointers, read offset K set at reset (no flow control, no credits,
// no occupancy).  Slot written at edge j is read at edge j + K and overwritten at j + D: setup window K T, hold
// window (D - K) T for the measured phase between the two region roots (D=2,K=1: |phase| < ~T - tcq - tsu).
// Reset: one 2-edge synchroniser per clock (wrapper), then kept per-ring sync copies (each <= 12 pointer groups),
// identical depth on both sides -> write and read release on the same nominal edge.  Only pointers, warm-up and the
// control bits (valid / fault) reset; slot data and output data are unreset (validity owns observation).
// Fanout: pointers are replicated per G-bit group (kept copies), so no pointer drives more than ~2G loads.
// The calendar consumes the added edges exactly (qfd_coll_static_face PLAND): phy_tx_slot +1+K, expected PHY pin
// cycle +1+K (peer TX), RX CDC write +K, face latency L + 1 + 2K.  Priced in the die schedule (NOTICE QW-TOKSCHED).
// MUT: +define+OT_COLL_MUT_PHYLAND_SHORT reads one slot early (offset K-1): exact-latency bench must FAIL.
module ot_coll_meso_ring #(
    parameter integer W = 8, D = 2, K = 1, C = 1, G = 12, REG_OUT = 0
)(
    input  wire         ck_w, rs_w,          // write region root + its released reset (sync, active low)
    input  wire         ck_r, rs_r,          // read region root + its released reset
    input  wire [W-1:0] d,                   // low C bits = control (valid/fault): gated 0 until warm
    output wire [W-1:0] q
);
    localparam integer NG = (W + G - 1) / G;
    localparam integer A  = (D <= 2) ? 1 : $clog2(D);
    localparam integer RC = (NG + 11) / 12;
`ifdef OT_COLL_MUT_PHYLAND_SHORT
    localparam integer KE = K - 1;
`else
    localparam integer KE = K;
`endif
    localparam integer RP0 = (D - KE) % D;
    // kept sync reset copies (one per <=12 groups), same depth on both sides
    (* keep = "true", dont_touch = "true" *) reg [RC-1:0] rqw;
    (* keep = "true", dont_touch = "true" *) reg [RC:0]   rqr;
    always @(posedge ck_w) rqw <= {RC{rs_w}};
    always @(posedge ck_r) rqr <= {(RC+1){rs_r}};
    // warm-up: control bits read 0 until the first written slot is due (edge K after release)
    reg [3:0] warm_q;
    always @(posedge ck_r)
        if (!rqr[RC]) warm_q <= 4'd0;
        else if (warm_q < KE) warm_q <= warm_q + 4'd1;
    wire warm = (warm_q == KE);
    wire [W-1:0] rd;
    genvar g, s;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        localparam integer LO = g * G;
        localparam integer N  = (W - LO < G) ? (W - LO) : G;
        (* keep = "true", dont_touch = "true" *) reg [A-1:0] wp_q;
        (* keep = "true", dont_touch = "true" *) reg [A-1:0] rp_q;
        reg [D*N-1:0] sl_q;                         // packed slots (no memory inference)
        always @(posedge ck_w)
            if (!rqw[g / 12]) wp_q <= {A{1'b0}};
            else wp_q <= (wp_q == D - 1) ? {A{1'b0}} : wp_q + 1'b1;
        for (s = 0; s < D; s = s + 1) begin : g_slot
            always @(posedge ck_w) if (wp_q == s) sl_q[s*N +: N] <= d[LO +: N];
        end
        always @(posedge ck_r)
            if (!rqr[g / 12]) rp_q <= RP0;
            else rp_q <= (rp_q == D - 1) ? {A{1'b0}} : rp_q + 1'b1;
        assign rd[LO +: N] = sl_q[rp_q*N +: N];
    end endgenerate
    // control bits gated until warm; data bits pass
    wire [W-1:0] rdg = {rd[W-1:C], rd[C-1:0] & {C{warm}}};
    if (REG_OUT) begin : g_reg
        reg [W-1:C] od_q;
        reg [C-1:0] oc_q;
        always @(posedge ck_r) od_q <= rdg[W-1:C];
        always @(posedge ck_r) if (!rqr[RC]) oc_q <= {C{1'b0}}; else oc_q <= rdg[C-1:0];
        assign q = {od_q, oc_q};
    end else begin : g_comb
        assign q = rdg;                            // the destination's own capture registers are the ring output
    end
`ifndef SYNTHESIS
    initial if (D < 2 || K < 1 || K > D - 1 || C < 1 || C >= W) $error("ot_coll_meso_ring: need D>=2, 1<=K<=D-1, 1<=C<W");
`endif
endmodule

// Codec with a separate PHY pin-register region (phy_ck): same ports as ot_qwen_static_slot_link plus phy_ck.
module ot_qwen_static_slot_link_pl #(
    parameter integer FW=548, CW=16, PW=FW+19+CW, MUT=0, SAFE=0, LD=2, LK=1, UP_SYNC=0
)(
    input wire [4:0] ck,
    input wire phy_ck,
    input wire rst_n, epoch_begin,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
    input wire [FW-1:0] wr_flit,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire rx_v,
    output wire [FW-1:0] rx_flit,
    output wire epoch_abort,
    output wire [7:0] fault_cause
);
    localparam integer BW=137;
    wire [4*BW-1:0] wd={{(4*BW-FW){1'b0}},wr_flit};
    wire [4*BW-1:0] rd;
    wire c_abort;
    wire issue_write=wr_v && !c_abort && !epoch_begin;
    for(genvar b=0;b<4;b=b+1)begin:g_bank
`ifdef OT_QFD_FACE_HARD
        ot_qkvd_llr_replay_sram_leaf u_store(
`else
        ot_qkvd_llr_replay_sram_leaf #(.W(BW),.MUT(MUT==3 && b==0)) u_store(
`endif
            .ck(ck[b+1]),.we(issue_write),.wa(wr_slot),.ra(rd_slot),
            .din(wd[b*BW+:BW]),.dout(rd[b*BW+:BW]));
    end
    // region resets: one 2-edge synchroniser per clock, kept copies per ring side
    wire [2:0] rs_c;
    wire [1:0] rs_p;
    ot_qwen_slot_reset_copies #(.COPIES(3)) u_rs_c(.clk(ck[0]),.rst_n(rst_n),.released(rs_c));
    ot_qwen_slot_reset_copies #(.COPIES(2)) u_rs_p(.clk(phy_ck),.rst_n(rst_n),.released(rs_p));
    // PHY-up crosses from its producing PHY clock as a level. Capture it
    // twice on THIS face's codec0p root before carrying it through the existing
    // mesochronous ring to codec0. No shared global-clock status register.
    wire up_phy_local;
    if(UP_SYNC)begin:g_up_sync
        (* ASYNC_REG="TRUE", keep="true", dont_touch="true" *) reg up_meta;
        (* ASYNC_REG="TRUE", keep="true", dont_touch="true" *) reg up_sync;
        always @(posedge phy_ck)begin up_meta<=p_tx_up;up_sync<=up_meta;end
        assign up_phy_local=up_sync;
    end else begin:g_up_direct
        assign up_phy_local=p_tx_up;
    end
    // RX: pins -> ring (phy_ck) -> controller pin registers (ck[0]); +LK edges
    wire [PW-1:0] rx_flit_l;
    wire rx_v_l, up_l;
    ot_coll_meso_ring #(.W(PW+2),.D(LD),.K(LK),.C(2),.REG_OUT(0)) u_rx_land(
        .ck_w(phy_ck),.rs_w(rs_p[0]),.ck_r(ck[0]),.rs_r(rs_c[0]),
        .d({p_rx_flit,up_phy_local,p_rx_v}),.q({rx_flit_l,up_l,rx_v_l}));
    // the expected-frame tokens follow the landed frame by the same LK edges (control bit reset)
    reg [LK-1:0] ev_q;
    reg [6*LK-1:0] es_q;
    always @(posedge ck[0]) if(!rs_c[2]) ev_q<={LK{1'b0}}; else ev_q<={ev_q,rx_expect_v};
    always @(posedge ck[0]) es_q<={es_q,rx_expect_slot};
    wire ev_l=ev_q[LK-1];
    wire [5:0] es_l=es_q[6*LK-1-:6];
    // TX: controller registers (ck[0]) -> ring -> PHY output pin registers (phy_ck); +1+LK edges
    wire c_tx_v;
    wire [PW-1:0] c_tx_flit;
    wire [7:0] c_cause;
    ot_qwen_static_slot_ctl #(.FW(FW),.CW(CW),.PW(PW),.SAFE(SAFE)) u_ctl (
        .clk(ck[0]),.q_data(rd[FW-1:0]),
        .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch(epoch), .wr_v(wr_v), .wr_observed_v(wr_observed_v), .wr_slot(wr_slot),
        .rd_v(rd_v), .rd_slot(rd_slot), .rx_expect_v(ev_l), .rx_expect_slot(es_l), .p_tx_up(up_l), .p_tx_v(c_tx_v),
        .p_tx_flit(c_tx_flit), .p_rx_v(rx_v_l), .p_rx_flit(rx_flit_l), .rx_v(rx_v), .rx_flit(rx_flit),
        .epoch_abort(c_abort), .fault_cause(c_cause));
    ot_coll_meso_ring #(.W(PW+10),.D(LD),.K(LK),.C(10),.REG_OUT(1)) u_tx_land(
        .ck_w(ck[0]),.rs_w(rs_c[1]),.ck_r(phy_ck),.rs_r(rs_p[1]),
        .d({c_tx_flit,c_cause,c_abort,c_tx_v}),.q({p_tx_flit,fault_cause,epoch_abort,p_tx_v}));
endmodule
