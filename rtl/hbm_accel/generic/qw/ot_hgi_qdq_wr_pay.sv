`timescale 1ns/1ps
`default_nettype none
// Distinct opt-in leaf: unchanged real SRAM/write path, no completion feedback.
module ot_hgi_qdq_wr_pay #(
    parameter integer LQ  = 10,
    parameter integer OD  = 64,
    parameter integer RQ  = 16,
    parameter integer EMPTY_BYPASS = 0 // opt-in registered input result bypass
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              m_v,
    input  wire [18:0]       m,           // {O sector 15, sectors 3, last}
    input  wire              i_bad,
    input  wire              vo,
    input  wire              qfault,
    input  wire              dfault,
    input  wire [511:0]      y,
    output wire [8*280-1:0] wwq,
    input  wire [7:0]        wwq_cr,
    output wire wg_req,
    input  wire              wg_gnt,
    input  wire              i_act,
    output reg               o_wf,
    output reg               snapshot_v,
    output reg [63:0]        snapshot,
    output reg               o_bad,
    output reg               o_idle
);
    (* keep="true",dont_touch="true" *) reg [8*280-1:0] wwq_q;
    (* keep="true",dont_touch="true" *) reg wg_req_q;
    assign wwq=wwq_q;
    assign wg_req=wg_req_q;
    localparam integer QW = $clog2(RQ), OW = $clog2(OD), CW = $clog2(LQ + 1);
    reg f_rst, f_wg; reg [7:0] f_wcr; reg [18:0] f_m; reg [511:0] y_f; reg qf_f;
    always @(posedge clk) begin
        f_rst <= rst_n; f_wg <= wg_gnt; f_wcr <= wwq_cr; f_m <= m; y_f <= y; qf_f <= qfault;
    end
    // p12 (Claude group-B4 10-14, p11 route TT -49.51: qf_f -> pl_sel 19 levels / qf_f -> ESL b0,b1 16 levels = the pin
    // capture flops (recipe 2: flops AT the pins) drove the fire cone across the tile).  The result now takes a second
    // register stage placed with the logic: y_f2 and ONE combined bypass-clean flag byp2 = vo & !qfault & !dfault & !i_bad
    // of the pin flops; the fire cone sees only flops of this stage.  +1 edge on the result path (decode latency 26 -> 27),
    // no throughput change.  bad / o_bad are still raised from the pin-capture stage (same cycle as before).
    reg [511:0] y_f2;
    always @(posedge clk) y_f2 <= y_f;
    wire [2:0] rr_n;                                  // 0 control, 1 result FIFO, 2 lanes
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    reg f_m_v, vo_f, df_f, f_act, f_bi, vo2, byp2;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin f_m_v <= 0; vo_f <= 0; df_f <= 0; f_act <= 0; f_bi <= 0; vo2 <= 0; byp2 <= 0; end
        else begin
            f_m_v <= m_v; vo_f <= vo; df_f <= dfault; f_act <= i_act; f_bi <= i_bad;
            vo2 <= vo_f; byp2 <= vo_f && !qf_f && !df_f && !f_bi;
        end
    // Same-edge output launch copy, with a separate reset region. The original
    // f_act is the W-face input capture/private control; wg_req is its own N pin.
    always @(posedge clk or negedge rr_n[2])if(!rr_n[2])wg_req_q<=0;else wg_req_q<=i_act;
    // fired-beat queue (one entry a beat in the decode or the result FIFO)
    reg [14:0] mq_o [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg mq_z [0:OD-1];
    reg [3:0] mq_oh [0:OD-1];                          // p11: one-hot of the entry's sector[1:0], written with the entry
    reg [7:0] mq_hv [0:OD-1];                          // p12: lane-hit vector of the entry, computed at write
    reg [12:0] mq_p1 [0:OD-1];                         // p12: sector[14:2] + 1 of the entry, computed at write
    reg [OW-1:0] mq_t, mq_h; reg [OW:0] infl;         // infl: fired beats not yet out of the decode
    wire od_hv, od_ovf; wire [511:0] od_head;
    reg bad, wg_ok;
    reg [CW-1:0] wcr [0:7]; reg [7:0] wcnt [0:7];
    // head entry in registers (q8b gate, 10-13: the 64:1 head read sat in front of hit -> credit -> fire -> credit update,
    // 15 levels): both candidates (head, head + 1) are read from the registered pointer and the fire selects one.  An
    // entry is written >= 20 cycles (decode latency) before its result can fire, so the one-edge-late copy is always current.
    reg [14:0] mh_o; reg [2:0] mh_n; reg mh_z;
    wire [OW-1:0] mq_h1 = mq_h + 1'b1;
    // p12b (p12 gate: mq_h[1] drove 3,642 mux loads): the head is also kept as a REGISTERED one-hot hoh (rotated on fire,
    // hoh == 1 << mq_h always); every head read is a one-hot AND-OR (no binary 64:1 mux tree on the pointer bits).
    reg [OD-1:0] hoh; wire [OD-1:0] hoh1 = {hoh[OD-2:0], hoh[OD-1]};
    reg [18:0] rd_h0, rd_h1; reg [3:0] rd_o0, rd_o1; reg [12:0] rd_p0, rd_p1; reg [7:0] rd_v0, rd_v1;
    always @* begin
        rd_h0 = '0; rd_h1 = '0; rd_o0 = '0; rd_o1 = '0; rd_p0 = '0; rd_p1 = '0; rd_v0 = '0; rd_v1 = '0;
        for (integer e = 0; e < OD; e = e + 1) begin
            rd_h0 = rd_h0 | ({19{hoh[e]}} & {mq_o[e], mq_n[e], mq_z[e]}); rd_h1 = rd_h1 | ({19{hoh1[e]}} & {mq_o[e], mq_n[e], mq_z[e]});
            rd_o0 = rd_o0 | ({4{hoh[e]}} & mq_oh[e]);   rd_o1 = rd_o1 | ({4{hoh1[e]}} & mq_oh[e]);
            rd_p0 = rd_p0 | ({13{hoh[e]}} & mq_p1[e]);  rd_p1 = rd_p1 | ({13{hoh1[e]}} & mq_p1[e]);
            rd_v0 = rd_v0 | ({8{hoh[e]}} & mq_hv[e]);   rd_v1 = rd_v1 | ({8{hoh1[e]}} & mq_hv[e]);
        end
    end
    // q8e: independent head reads stay in parallel with the fire cone. Keeping the
    // read outputs prevents synthesis from moving fire in front of the 64:1 mux.
    (* keep = 1 *) wire [18:0] mq_head0 = rd_h0;
    (* keep = 1 *) wire [18:0] mq_head1 = rd_h1;
    wire [14:0] w_sec0 = mh_o; wire [2:0] w_n = mh_n;
    (* keep = 1 *) wire [3:0] mq_oh0 = rd_o0;
    (* keep = 1 *) wire [3:0] mq_oh1 = rd_o1;
    (* keep = 1 *) wire [12:0] mq_hp0 = rd_p0, mq_hp1 = rd_p1;
    (* keep = 1 *) wire [7:0] mq_hv0 = rd_v0, mq_hv1 = rd_v1;
    // p12: the lane hits and each lane's credit-zero flag are REGISTERED with the same next-state as mh_o / wcr (one
    // explicit AO22 on fire, ot_qdq_pay_sel); w_hit[b] == (b - mh_o[2:0]) < mh_n and wcr_z[b] == (wcr[b] == 0) always.
    reg [7:0] w_hit_q, wcr_z; reg cr_ok_q;
    wire [7:0] w_hit = w_hit_q;
    // p12b: w_cr_ok itself registered (== ~|(w_hit & wcr_z) of the same edge, loaded through the fire AO22 bank)
    wire w_cr_ok = cr_ok_q;
    wire result_empty,tracker_bad;
    wire re_nf,re_f; // p11: result_empty of the NEXT cycle without / with a fire this cycle (registered payload select)
    wire bypass_eligible=(EMPTY_BYPASS!=0)&&result_empty&&!od_hv&&byp2&&!od_ovf;
    wire w_fire = wg_ok && !bad && !tracker_bad && (od_hv||bypass_eligible) && w_cr_ok;
    wire bypass_fire=w_fire&&!od_hv&&bypass_eligible;
    generate if(EMPTY_BYPASS!=0)begin:g_result_tracker
        // Accepted registered VO minus actual WWQ launches counts every SRAM,
        // prefetch-head and read-pending obligation. Complement rails refuse a
        // shortcut if mutable tracking state disagrees; no raw VO/Y bypass.
        (* keep="true",dont_touch="true" *) reg [OW:0] outstanding,outstanding_n;
        wire [OW:0] next_outstanding=outstanding+(OW+1)'(vo2)-(OW+1)'(w_fire);
        assign tracker_bad=outstanding!=~outstanding_n;
        wire [OW:0] ov=outstanding+(OW+1)'(vo2);
        assign re_nf=ov==0; assign re_f=ov==1;
        // p12: (outstanding == 0) registered: re_q is loaded with next_outstanding == 0 (fire ? re_f : re_nf, one AO22).
        reg re_q; wire re_q_n;
        ot_qdq_pay_sel #(.W(1)) u_re_sel (.s(w_fire), .a0(re_nf), .a1(re_f), .y(re_q_n));
        assign result_empty=re_q&&!tracker_bad;
        always @(posedge clk or negedge rr_n[0])
            if(!rr_n[0])begin outstanding<=0;outstanding_n<='1;re_q<=1'b1;end
            else begin outstanding<=next_outstanding;outstanding_n<=~next_outstanding;re_q<=re_q_n;end
`ifndef SYNTHESIS
        always @(negedge clk)if(rr_n[0]&&rr_n[1]&&!tracker_bad)begin
            if(outstanding !== u_od.in_arr+u_od.oc+u_od.inflight)
                $fatal(1,"PAY outstanding tracker does not equal real SRAM/head/read-pending obligations");
            if(bypass_fire&&(u_od.in_arr!=0||u_od.oc!=0||u_od.inflight))
                $fatal(1,"PAY bypass with stored result obligation");
        end
`endif
    end else begin:g_no_result_tracker
        assign result_empty=1'b0;assign tracker_bad=1'b0;assign re_nf=1'b0;assign re_f=1'b0;
    end endgenerate
    // p12c: PAY-local FWFT (ot_qdq_pay_fwft): same records / order / occupancy as ot_fifo_sram_fwft ESL 128, but it exports
    // the two output-buffer registers (od_b0 / od_b1) so the payload selects b0 / b1 directly with registered one-hot
    // selects that already include the head index (poh mirrors the buffer's oh), and keeps the array count registered.
    wire [511:0] od_b0, od_b1;
    ot_qdq_pay_fwft #(.DEPTH(OD)) u_od (.clk(clk), .rst_n(rr_n[1]), .push(vo2&&!bypass_fire),
        .wdata(y_f2), .pop(w_fire), .hv(od_hv), .head(od_head), .ob0(od_b0), .ob1(od_b1), .ovf(od_ovf));
    reg poh;                                            // == u_od head index (toggles on every pop of a held head)
    always @(posedge clk or negedge rr_n[1]) if (!rr_n[1]) poh <= 1'b0; else if (w_fire && od_hv) poh <= ~poh;
    wire snapshot_push = w_fire && mh_z;
    wire [63:0] snapshot_counts;
    for(genvar q=0;q<8;q=q+1)begin:g_snapshot
        assign snapshot_counts[q*8+:8]=wcnt[q]+8'(w_hit[q]);
    end
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            mq_t <= 0; mq_h <= 0; hoh <= {{(OD-1){1'b0}}, 1'b1}; infl <= 0; bad <= 0; wg_ok <= 0; o_wf <= 0; snapshot_v <= 0; o_bad <= 0; o_idle <= 0;
        end else begin
            wg_ok <= f_act && f_wg;
            if (f_m_v) mq_t <= mq_t + 1'b1;
            if (w_fire) begin mq_h <= mq_h + 1'b1; hoh <= hoh1; end
            infl <= infl + (OW+1)'(f_m_v) - (OW+1)'(vo2);
            if ((vo_f && qf_f) || df_f || od_ovf || f_bi || tracker_bad) bad <= 1'b1;
            if ((vo_f && qf_f) || df_f || od_ovf || tracker_bad) o_bad <= 1'b1;
            o_wf <= w_fire; snapshot_v <= snapshot_push;
            o_idle <= infl == 0 && !f_m_v;
        end
    end
    always @(posedge clk or negedge rr_n[2]) begin
        if (!rr_n[2]) begin
            for (integer b = 0; b < 8; b = b + 1) begin wwq_q[b*280 + 279] <= 1'b0; wcr[b] <= LQ[CW-1:0]; wcnt[b] <= 0; end
            wcr_z <= (LQ == 0) ? 8'hff : 8'h00; cr_ok_q <= (LQ != 0);
        end else begin
            for (integer b = 0; b < 8; b = b + 1) begin : lanes
                reg wr; wr = w_fire && w_hit[b];
                wwq_q[b*280 + 279] <= wr;
                wcr[b] <= wcr[b] + CW'(f_wcr[b]) - CW'(wr);
                wcnt[b] <= wcnt[b] + 8'(wr);
            end
            wcr_z <= wcr_z_n; cr_ok_q <= cr_ok_n;
        end
    end
    localparam integer REP = 4;                        // kept select copies per lane (32 payload bits each)
    (* keep="true",dont_touch="true" *) reg [8*REP*12-1:0] pl_sel;  // per lane/copy: [3:0] y_f2, [7:4] od_b0, [11:8] od_b1 sector
    (* keep="true",dont_touch="true" *) reg [7:0] pl_lt;
    (* keep="true",dont_touch="true" *) reg [12:0] pl_hi, pl_hi1;
    // p12: every fire-selected next state is formed from registered state for BOTH outcomes and picked by one explicit
    // AO22 a bit (ot_qdq_pay_sel): fire is the only late signal and it is never re-folded into the candidate cones.
    localparam integer NSEL = 8*REP*12 + 8 + 13 + 13 + 19 + 8 + 8 + 1;
    reg  [8*REP*12-1:0] sel_a0, sel_a1;
    wire poh1 = poh ^ od_hv;                            // head index after a fire (a fire pops only a held head)
    reg [7:0] lt_a0, lt_a1, z_a0, z_a1;
    wire [7:0] wcr_z_n; wire cr_ok_n;
    always @* begin
        for (integer b = 0; b < 8; b = b + 1) begin
            for (integer g = 0; g < REP; g = g + 1)
                for (integer j = 0; j < 4; j = j + 1) begin
                    sel_a0[(b*REP+g)*12 + j]     = mq_oh0[(b-j)&3] &  ((EMPTY_BYPASS != 0) && re_nf);
                    sel_a0[(b*REP+g)*12 + 4 + j] = mq_oh0[(b-j)&3] & !((EMPTY_BYPASS != 0) && re_nf) & !poh;
                    sel_a0[(b*REP+g)*12 + 8 + j] = mq_oh0[(b-j)&3] & !((EMPTY_BYPASS != 0) && re_nf) &  poh;
                    sel_a1[(b*REP+g)*12 + j]     = mq_oh1[(b-j)&3] &  ((EMPTY_BYPASS != 0) && re_f);
                    sel_a1[(b*REP+g)*12 + 4 + j] = mq_oh1[(b-j)&3] & !((EMPTY_BYPASS != 0) && re_f) & !poh1;
                    sel_a1[(b*REP+g)*12 + 8 + j] = mq_oh1[(b-j)&3] & !((EMPTY_BYPASS != 0) && re_f) &  poh1;
                end
            lt_a0[b] = |(mq_oh0 & ~((4'd2 << (b&3)) - 4'd1));   // b[1:0] < sector[1:0]
            lt_a1[b] = |(mq_oh1 & ~((4'd2 << (b&3)) - 4'd1));
            // wcr[b] next = wcr + credit - (fire && hit): zero flag for no launch / a launch on this lane
            z_a0[b] = (wcr[b] + CW'(f_wcr[b])) == CW'(0);
            z_a1[b] = w_hit[b] ? ((wcr[b] + CW'(f_wcr[b])) == CW'(1)) : z_a0[b];
        end
    end
    wire [NSEL-1:0] sel_y;
    ot_qdq_pay_sel #(.W(NSEL)) u_fire_sel (.s(w_fire),
        .a0({sel_a0, lt_a0, mq_head0[18:6], mq_hp0, mq_head0, mq_hv0, z_a0, ~|(mq_hv0 & z_a0)}),
        .a1({sel_a1, lt_a1, mq_head1[18:6], mq_hp1, mq_head1, mq_hv1, z_a1, ~|(mq_hv1 & z_a1)}), .y(sel_y));
    assign wcr_z_n = sel_y[8:1]; assign cr_ok_n = sel_y[0];
    // Address/payload flops are written separately from resettable valid strobes (no ALDFF feedback on payload bits).
    always @(posedge clk) begin
        if (f_m_v) begin
            mq_o[mq_t] <= f_m[18:4]; mq_n[mq_t] <= f_m[3:1]; mq_z[mq_t] <= f_m[0]; mq_oh[mq_t] <= 4'b0001 << f_m[5:4];
            mq_p1[mq_t] <= f_m[18:6] + 13'd1;
            for (integer b = 0; b < 8; b = b + 1) mq_hv[mq_t][b] <= 3'(b - f_m[6:4]) < f_m[3:1];
        end
        {pl_sel, pl_lt, pl_hi, pl_hi1, mh_o, mh_n, mh_z, w_hit_q} <= sel_y[NSEL-1:9];
        snapshot <= snapshot_counts; // first registered launch, same edge as WWQ
        // p10 (Claude 10-14): payload flops load every edge; the fire cone drives only the 8 valid bits.
        // p11 (Claude group-B3 10-14, p10 route TT -94.77: u_od.oc / ESL oh_c / mh_o -> wwq 14-17 levels = the 512-wide
        // od_hv ? od_head : y_f select and the per-lane sector decode of mh_o, both fanned out to 1,024 payload bits): every
        // select of the payload is now a REGISTERED one-hot, loaded one edge early with the same next-state as mh_o
        // (fire ? head+1 : head) and result_empty (outstanding + vo - fire == 0), REP kept copies per lane; the payload
        // D input is an 8-way AND-OR of {y_f, od_head} sectors, the address a 2:1 of registered sector[14:2] / +1.
        // Same edge, no cycle, identical wwq contents whenever a lane's valid bit is set.
        for (integer b = 0; b < 8; b = b + 1) begin
            begin
                reg [255:0] d; reg [127:0] c;
                for (integer i = 0; i < 128; i = i + 1) begin
                    c[i] = 1'b0;
                    for (integer j = 0; j < 4; j = j + 1)
                        c[i] = c[i] | (pl_sel[(b*REP + i/(128/REP))*12 + j] & y_f2[j*128 + i])
                                    | (pl_sel[(b*REP + i/(128/REP))*12 + 4 + j] & od_b0[j*128 + i])
                                    | (pl_sel[(b*REP + i/(128/REP))*12 + 8 + j] & od_b1[j*128 + i]);
                end
                for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {c[k*16 +: 16], 16'd0};
                wwq_q[b*280 +: 279] <= {(pl_lt[b] ? pl_hi1 : pl_hi), 2'(b), d, 8'hff};
            end
        end
    end
    initial begin
        if ((OD & (OD - 1)) != 0 || (RQ & (RQ - 1)) != 0) $fatal(1, "ot_hgi_qdq_wr: OD / RQ powers of two");
        if (OD < 32) $fatal(1, "ot_hgi_qdq_wr: OD >= 32 (decode latency 26)");
    end
endmodule

// One late select bit -> W next-state bits, each through one instantiated AO22 (y = s & a1 | ~s & a0); same form as
// ot_qdq_fin_sel (ot_hgi_qdq_core_fin2.sv), local name so both leaves can sit in one compile.
module ot_qdq_pay_sel #(parameter integer W = 1) (
    input  wire         s,
    input  wire [W-1:0] a0,
    input  wire [W-1:0] a1,
    output wire [W-1:0] y
);
`ifdef SYNTHESIS
    wire sn;
    INVx2_ASAP7_75t_R u_sn (.A(s), .Y(sn));
    genvar i;
    for (i = 0; i < W; i = i + 1) begin : g_b
        AO22x1_ASAP7_75t_R u_m (.A1(s), .A2(a1[i]), .B1(sn), .B2(a0[i]), .Y(y[i]));
    end
`else
    assign y = s ? a1 : a0;
`endif
endmodule
`default_nettype wire

// PAY-local first-word-fall-through FIFO (p12c): the behaviour of ot_fifo_sram_fwft #(.W(512), .MACRO(0), .ESL(128)) --
// same push / pop / bypass / read issue rules, same order, same 2-register output buffer per 128-b slice with kept copies
// of the head / occupancy / landing state -- with two structural differences: (1) the array count is a REGISTER (na,
// with a registered empty flag ez) instead of wp - rp in front of every bypass / read decision; (2) the landing and
// bypass slots are formed from registered state only (ia = oh ^ oc[0], ib = oh ^ oc[0] ^ inflight: the pop terms
// cancel), and both buffer registers are exported (ob0 / ob1) for consumers that select them with their own one-hot.
module ot_qdq_pay_fwft #(parameter integer DEPTH = 64) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          push,
    input  wire [511:0]  wdata,
    input  wire          pop,
    output wire          hv,
    output wire [511:0]  head,
    output wire [511:0]  ob0,
    output wire [511:0]  ob1,
    output reg           ovf
);
    localparam integer AW = $clog2(DEPTH);
    initial if (DEPTH > 64 || (1 << AW) != DEPTH) $fatal(1, "ot_qdq_pay_fwft: DEPTH must be a power of two <= 64");
    reg  [AW:0]   wp, rp, na;
    reg           ez;                               // na == 0, registered
    wire [AW:0]   in_arr = na;
    reg           inflight;
    wire [511:0]  rq;
    reg  [1:0]    oc;
    assign hv = oc != 0;
    wire          do_pop = pop && hv;
    wire [1:0]    oc_after = oc - (do_pop ? 1'b1 : 1'b0);
    wire          room = (oc_after + (inflight ? 2'd1 : 2'd0)) < 2'd2;
    wire          bypass = push && ez && !inflight && room;
    wire          wr_arr = push && !bypass;
    wire          rd_arr = !ez && room;
    wire [AW:0]   na_n = na + (wr_arr ? 1'b1 : 1'b0) - (rd_arr ? 1'b1 : 1'b0);
    ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(rd_arr), .r_addr_in(6'(rp[AW-1:0])), .rd_out(rq),
        .w_ce_in(wr_arr), .w_addr_in(6'(wp[AW-1:0])), .wd_in(wdata), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [1:0] n_in = (inflight ? 2'd1 : 2'd0) + (bypass ? 2'd1 : 2'd0);
    wire [1:0] oc_nx = oc_after + n_in;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; na <= 0; ez <= 1'b1; inflight <= 1'b0; oc <= 0; ovf <= 1'b0;
        end else begin
            if (wr_arr) begin
                wp <= wp + 1'b1;
                if (na == DEPTH) ovf <= 1'b1;
            end
            if (rd_arr) rp <= rp + 1'b1;
            na <= na_n; ez <= na_n == 0;
            inflight <= rd_arr;
            oc <= oc_nx;
            if (oc_after + n_in > 2) ovf <= 1'b1;
        end
    end
    genvar s;
    for (s = 0; s < 4; s = s + 1) begin : g_s
        (* keep *) reg oh_c, oc0_c, inf_c;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin oh_c <= 1'b0; oc0_c <= 1'b0; inf_c <= 1'b0; end
            else begin oh_c <= do_pop ? ~oh_c : oh_c; oc0_c <= oc_nx[0]; inf_c <= rd_arr; end
        wire ia = oh_c ^ oc0_c;                         // == the post-pop landing slot (pop terms cancel)
        wire ib = oh_c ^ oc0_c ^ inf_c;                 // == the post-pop bypass slot
        reg [127:0] b0, b1;
        always @(posedge clk) begin
            if (inf_c && !ia) b0 <= rq[s*128 +: 128];
            if (inf_c &&  ia) b1 <= rq[s*128 +: 128];
            if (bypass && !ib) b0 <= wdata[s*128 +: 128];
            if (bypass &&  ib) b1 <= wdata[s*128 +: 128];
        end
        assign head[s*128 +: 128] = oh_c ? b1 : b0;
        assign ob0[s*128 +: 128] = b0; assign ob1[s*128 +: 128] = b1;
    end
endmodule
