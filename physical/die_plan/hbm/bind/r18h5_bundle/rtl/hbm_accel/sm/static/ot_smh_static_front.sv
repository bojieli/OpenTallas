`timescale 1ns/1ps
module ot_smh_static_front(
 input wire clk,rst_n,input wire [82:0] command,input wire [1098:0] packet,
 output wire [42:0] expected_request,output wire schedule_fault,
 input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
 output wire [4*818-1:0] rl,rr,output wire [2*2069-1:0] bl,br,
 input wire [4*46-1:0] ql,qr,output wire rv,output wire [11:0] rrow,
 output wire [255:0] rdata,output wire fault
);
 localparam integer SUB=4,LBS=2,LSB=16,NC=8,IL=8,RMAX=4096,XD=128,
   RPT=2,PIO=2,PT4=1,RESULT_VALID=1,SW=3,RW=12,XW=7,TAGW=16,
   CW=22,RBW=818,BBW=2069,NBEAT=13,QLW=46,NL=4,NR=4,NH=4;
 wire [818-1:0] fi_row0,r3a,fi_row3,r0a_e,r3a_e;
 wire [2068:0] fx_b,xw_w,xw_e,xr_w,xr_e;
 wire [1081:0] lt0,lt1;wire [569:0] lb0,lb1,lbr0,lbr1;
 wire [11:0] fm;wire [2:0] fmr0,fmr1;
 ot_smh_static_feed u_feed(.clk(clk),.rst_n(rst_n),.command(command),.packet(packet),
   .expected_request(expected_request),.fault(schedule_fault),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
    // ---------------- x-write beat at the pins (sm_pq's w0): wl, wm, w0 as in m2 ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;
    reg [2047:0]     w0_data;
    integer gq;
    reg              wl_en, wm_en;
    reg [XW-1:0]     wl_addr, wm_addr;
    reg [6:0]        wl_grp, wm_grp;
    reg [2047:0]     wl_data, wm_data;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_en <= 1'b0; wm_en <= 1'b0; w0_en <= 1'b0; end
        else begin wl_en <= xw_en; wm_en <= wl_en; w0_en <= wm_en; end
    always @(posedge clk) begin
        wl_addr <= xw_addr; wl_grp <= xw_grp; wl_data <= xw_data;
        wm_addr <= wl_addr; wm_grp <= wl_grp; wm_data <= wl_data;
        w0_addr <= wm_addr; w0_data <= wm_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (wm_grp == 7'(gq));
    end
    wire [BBW-1:0] w0_b = {w0_en, w0_addr, w0_oh, w0_data};
    // tile row 1's beat: its m2 A stage, launched at the south face
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_fxv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
        .q(fx_b[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_fxd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
        .q(fx_b[BBW-2:0]));
    // tile row 0's beat: A, M, O per side (m2)
    genvar sd;
    wire [2*BBW-1:0] o_b;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_side
        wire [BBW-1:0] a_b, m_b;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bav (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
            .q(a_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bad (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
            .q(a_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-1]),
            .q(m_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bmd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-2:0]),
            .q(m_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-1]),
            .q(o_b[sd*BBW + BBW - 1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bod (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-2:0]),
            .q(o_b[sd*BBW +: BBW-1]));
    end endgenerate
    assign bl[0+:BBW] = o_b[0 +: BBW];
    assign br[0+:BBW] = o_b[BBW +: BBW];
    // row 0's bundle: landed in one copy PER SIDE (hbm-blocks 2026-10-07: m3f u_rl -> u_ol -108.56 ps / 5 levels, one
    // south-face copy feeding both edge registers; each copy now sits between the face and its side, 0 cycles), then
    // the O register per side at its pins
    wire [RBW-1:0] r0l_l, r0l_r;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rl (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rr (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_r));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_ol (.clk(clk), .rst_n(rst_n),
        .d(r0l_l), .q(rl[0+:RBW]));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_or (.clk(clk), .rst_n(rst_n),
        .d(r0l_r), .q(rr[0+:RBW]));
wire [817:0] r0a;
    ot_hbm_accel_smh_fc_xl #(.TAGW(TAGW)) u_xl (.clk(clk), .rst_a(rst_n), .fx_b(fx_b), .xw_w(xw_w), .xw_e(xw_e), .r0a(r0a),
        .fo_row0(fi_row0));
    ot_hbm_accel_smh_fc_t #(.ENABLE_INT8(0),.TAGW(TAGW)) u_tw (.clk(clk), .rst_a(rst_n), .li(lt0), .fi(fm[2:0]), .rout(rl[RBW+:RBW]), .r0a(r0a));
    ot_hbm_accel_smh_fc_t #(.ENABLE_INT8(0),.TAGW(TAGW)) u_te (.clk(clk), .rst_a(rst_n), .li(lt1), .fi(fm[8:6]), .rout(rr[RBW+:RBW]), .r0a(r0a_e));
    ot_hbm_accel_smh_fc_xr #(.TAGW(TAGW)) u_rw (.clk(clk), .rst_a(rst_n), .xi(xw_w), .xo(xr_w), .li(lb0), .lo(lbr0), .fi(fm[5:3]), .fo(fmr0));
    ot_hbm_accel_smh_fc_xr #(.TAGW(TAGW)) u_re (.clk(clk), .rst_a(rst_n), .xi(xw_e), .xo(xr_e), .li(lb1), .lo(lbr1), .fi(fm[11:9]), .fo(fmr1));
    ot_hbm_accel_smh_fc_b #(.ENABLE_INT8(0),.TAGW(TAGW)) u_bw (.clk(clk), .rst_a(rst_n), .li(lbr0), .fi(fmr0), .xi(xr_w), .bout(bl[BBW+:BBW]),
        .rout(rl[2*RBW+:RBW]), .r3a(r3a));
    ot_hbm_accel_smh_fc_b #(.ENABLE_INT8(0),.TAGW(TAGW)) u_be (.clk(clk), .rst_a(rst_n), .li(lbr1), .fi(fmr1), .xi(xr_e), .bout(br[BBW+:BBW]),
        .rout(rr[2*RBW+:RBW]), .r3a(r3a_e));

ot_hbm_accel_smh_bundle_reg #(.W(818),.V(20),.NV(2),.X(7)) u_m3(.clk(clk),.rst_n(rst_n),.d(r3a),.q(fi_row3));
    // row 3's bundle: landed at the north face, O per side at its pins
    wire [RBW-1:0] r3l;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_r3l (.clk(clk), .rst_n(rst_n),
        .d(fi_row3), .q(r3l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o3l (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rl[3*RBW+:RBW]));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o3r (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rr[3*RBW+:RBW]));
    // ---------------- results: lane landing, deskew, pins (m2, unchanged) ----------------
    // el1013-smh-r14 OT_SMH_PINREG: the gated tile lands rin / bin in its own pin registers (+1 row-bundle register per
    // tile hop), so a column's results arrive 1 more cycle per hop: the deskew is (5 + PT4 + PINR) a hop
    // OT_SMH_MUT_PINR_DESKEW (bench mutant only): the front keeps the 5 + PT4 deskew against pin-registered tiles
    localparam integer PINR =
`ifdef OT_SMH_MUT_PINR_DESKEW
        0;
`elsif OT_SMH_PINREG
        1;
`else
        0;
`endif
    wire fsv;
    wire [NC*QLW-1:0] al;
    genvar ln;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_qs
        for (ln = 0; ln < NH; ln = ln + 1) begin : g_ln
            localparam integer COLN = (sd == 0) ? NL - 1 - ln : NL + ln;
            if (COLN >= 0 && COLN < NC && ((sd == 0 && ln < NL) || (sd == 1 && ln < NR))) begin : g_use
                wire [QLW-1:0] lin = (sd == 0) ? ql[ln*QLW +: QLW] : qr[ln*QLW +: QLW];
                wire [QLW-1:0] land;
                ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_lv (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-1 -: 2]), .q(land[QLW-1 -: 2]));
                ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_ld (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-3:0]), .q(land[QLW-3:0]));
                ot_hbm_accel_smv_chain #(.W(2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(1)) u_dv (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-1 -: 2]), .q(al[COLN*QLW + QLW - 2 +: 2]));
                ot_hbm_accel_smv_chain #(.W(QLW-2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(0)) u_dd (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-3:0]), .q(al[COLN*QLW +: QLW-2]));
            end
        end
    end endgenerate
    wire [NC-1:0]    cf_a;
    wire [NC-1:0]    cv_a;
    wire result_v, result_fault;
    wire [NC*32-1:0] cy_a;
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_al
        assign cf_a[cc] = al[cc*QLW + QLW - 2];
        assign cv_a[cc] = al[cc*QLW + QLW - 1];
        assign cy_a[32*cc +: 32] = al[cc*QLW + RW +: 32];
    end endgenerate
    ot_hbm_accel_smh_result_valid #(.NC(NC), .ENABLE(RESULT_VALID)) u_result_valid (
        .valids(cv_a), .faults(cf_a), .row_valid(result_v), .fault_event(result_fault));
    // retire: stage 1 of m2's three, at the north face (front_c lands it and adds the third beside the issue)
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(result_v), .q(fsv));
    reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= fault_q | result_fault
            ;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d(result_v), .q(rv));
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_pfo (.clk(clk), .rst_n(rst_n), .d(fault_q), .q(fault));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({al[RW-1:0], cy_a}), .q({rrow, rdata}));
endmodule
