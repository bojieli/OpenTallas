`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK (2026-10-17): the V-rung data plane of the S81-DV bk units (dsdv_bk_sel on column 4, dsdv_bk_col on column 1).
// S81-DV p4h gives both units ONLY their column's 276-b V rung (plan links tvN_* / tvS_*), so the old slab's four die
// lanes in and the vd lane out ride the rung as V beats, through the shared stop leaf ot_dsdv_vstop.  Static schedule
// only: no credit, ready or arbitration on any unit port.  The compiler places every beat; violations are sticky faults.
//
// BK beat (one V beat, kind = strap ik on ingress / ek on egress; ingress kinds are SUNK by the vstop, so the slot is
// free downstream; the beat never travels on a ring line, so bits [19:4] are unit-defined):
//   [0] valid  [3:1] kind  [5:4] lane (ingress; 0 on egress)  [6] part  [7] single (part 0 only)
//   [8]      part 1: the word's lane fault flag (an upstream link / service fault, carried in band)
//   [19:8]   part 0: data[511:500] (type 4, tag 8)
//   [275:20] part 0: data[255:0]   part 1: data[511:256]
// A lane word {fault, live, data 512, valid} crosses as part 0 then part 1 of the same lane (any later slot, either
// direction, but one lane's words on one direction at a time); a word with data[499:256] == 0 and no fault may cross as
// ONE single beat (part 0, single 1: data = {[19:8], 244'b0, [275:20]}), e.g. selector headers / rebases.
// Egress words always cross as 2 beats (part 0, part 1) in consecutive slots of a compiled drain window.
//
// CTL drain command (kind 0, tapped NOT sunk: it travels on to the slices; only the addressed unit acts on it):
//   [28:21] dst uid  [31:29] op (1 = DRAIN)  [39:32] n window slots  [47:40] d extra delay
//   The window is the n consecutive slots of the egress direction whose first slot leaves the vo pin LW + d edges after
//   the CTL beat itself leaves its vo pin (LW = 7, dsdv_bk_vout); a word is started only when >= 2 window slots remain.
//   The compiler keeps those slots free (no forwarded beat), so the vstop never sees a collision.
// ---------------------------------------------------------------------------------------------------------------------

// Per-lane live flag (S81-BKG 10-18): reset 0, then 1 from the 2nd edge after reset release (the old shared live -> lane
// register pair, 2 flops).  One instance per lane word: the 4 lanes' live bits were structurally identical, so synthesis
// merged them into ONE flop driving the W and E face pins (dsdv_bk_g native launch 247.0 ps on ln3[513] / ln1[513]).
// Unparameterised and kept as hierarchy (kit route.synth_keep_modules) so each lane pin keeps its own launch flop.
module dsdv_bk_live (
    input  wire clk,
    input  wire rst_n,
    output reg  q
);
    reg l0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin l0 <= 1'b0; q <= 1'b0; end
        else begin l0 <= 1'b1; q <= l0; end
endmodule

// V ingress: tapped beats -> 4 lane words (registered, fixed latency: V pin -> lane word 3 edges) + drain commands
module dsdv_bk_vin #(
    parameter integer V   = 276,
    parameter integer MUT = 0,            // bench only: 1 = part 1 written into the low half, 2 = single drops type/tag
    // LPIPE (DIE-S81-51/RF-D 11-03, S81-062 RE-FORM form 2; RF-D build 1 CTS TT -152.5 on u_vs.dl_n -> kind/lane compare
    // AND5 -> 515-b lane mux / hold fanout -> lanes[*]): 1 = the deliveries land in a register stage first (beat copies
    // + pre-decoded one-hot lane hits pn / ps), so the lane mux selects from flops.  Lane words (incl. live and the
    // sticky fault) leave +1 edge (V pin -> lane word 3 -> 4); the drain command (dr_*) timing is UNCHANGED (window LW,
    // CTL-relative, unchanged).  0 = the old form.
    // LPIPE 2 (S81-062 form 7, 11-03, owner: two strikes -> pay a cycle; rfd5 TT -17.79 pn_q[l] -> 515-b lane word
    // through ~600 ps of select fanout): LPIPE 1 + ONE more per-lane register stage: the selected beat (pn ? bn : bs),
    // its valid (pn | ps) and the two-beat error (pn & ps) are registered per lane (lb_r / lv_r / l2_r) next to the lane
    // logic, so the lane word / hd / part-0 logic and their 512-b fanout start from per-lane flops.  Lane words, live and
    // the sticky fault leave +1 edge more (V pin -> lane word +1, inside dsdv_bk_sel); the drain command (dr_*) unchanged.
    parameter integer LPIPE = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2:0]        ik,          // captured strap: ingress kind
    input  wire [7:0]        uid,         // captured strap: this unit's CTL address
    input  wire              dl_nv,       // vstop deliveries (northbound arrivals / southbound arrivals)
    input  wire [V-1:0]      dl_n,
    input  wire              dl_sv,
    input  wire [V-1:0]      dl_s,
    output wire [4*515-1:0]  lanes,       // per lane {fault, live, data 512, valid}; lane 0 SW, 1 SE, 2 NW, 3 NE
    output reg               dr_v,        // drain command
    output reg  [7:0]        dr_n,
    output reg  [7:0]        dr_d,
    output reg               fault        // sticky protocol fault
);
    wire dn = dl_nv && dl_n[3:1] == ik, ds = dl_sv && dl_s[3:1] == ik;
    wire cn = dl_nv && dl_n[3:1] == 3'd0 && dl_n[28:21] == uid && dl_n[31:29] == 3'd1;
    wire cs = dl_sv && dl_s[3:1] == 3'd0 && dl_s[28:21] == uid && dl_s[31:29] == 3'd1;
    // lane-path view of the deliveries: pn[l] / ps[l] = a N / S ingress beat of lane l; bn / bs the beats
    wire [3:0] pn, ps; wire [V-1:0] bn, bs; wire cc;
    generate if (LPIPE != 0) begin : g_lp
        reg [3:0] pn_q, ps_q; reg [V-1:0] bn_q, bs_q; reg cc_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin pn_q <= 4'd0; ps_q <= 4'd0; cc_q <= 1'b0; end
            else for (integer l = 0; l < 4; l = l + 1) begin
                pn_q[l] <= dn && dl_n[5:4] == l; ps_q[l] <= ds && dl_s[5:4] == l; cc_q <= cn && cs;
            end
        always @(posedge clk) begin bn_q <= dl_n; bs_q <= dl_s; end
        assign pn = pn_q; assign ps = ps_q; assign cc = cc_q;
`ifdef OT_RFD_MUT_VIN   // bench mutant: the beat data bypass the stage (select from flops, data one edge early)
        assign bn = dl_n; assign bs = dl_s;
`else
        assign bn = bn_q; assign bs = bs_q;
`endif
    end else begin : g_lw
        for (genvar l = 0; l < 4; l = l + 1) begin : g_h
            assign pn[l] = dn && dl_n[5:4] == l; assign ps[l] = ds && dl_s[5:4] == l;
        end
        assign bn = dl_n; assign bs = dl_s; assign cc = cn && cs;
    end endgenerate
    // per-lane view of the deliveries: valid, two beats, the beat (LPIPE 2: one more register stage)
    wire [3:0] lvw, l2w; wire [V-1:0] lbw [0:3]; wire ccw;
    generate if (LPIPE >= 2) begin : g_l2
        reg [3:0] lv_r, l2_r; reg cc_r; reg [V-1:0] lb_r [0:3];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin lv_r <= 4'd0; l2_r <= 4'd0; cc_r <= 1'b0; end
            else begin lv_r <= pn | ps; l2_r <= pn & ps; cc_r <= cc; end
        always @(posedge clk) for (integer l = 0; l < 4; l = l + 1) lb_r[l] <= pn[l] ? bn : bs;
`ifdef OT_RFD_MUT_LPS   // bench mutant: lane 0 valid bypasses the stage (one edge early against its beat)
        assign lvw = {lv_r[3:1], pn[0] | ps[0]};
`else
        assign lvw = lv_r;
`endif
        assign l2w = l2_r; assign ccw = cc_r;
        for (genvar l = 0; l < 4; l = l + 1) begin : g_b assign lbw[l] = lb_r[l]; end
    end else begin : g_l0
        assign lvw = pn | ps; assign l2w = pn & ps; assign ccw = cc;
        for (genvar l = 0; l < 4; l = l + 1) begin : g_b assign lbw[l] = pn[l] ? bn : bs; end
    end endgenerate
    reg [3:0]   hv;                       // part 0 held per lane
    reg [255:0] hd [0:3];
    reg [3:0]   wv, err;                  // this cycle: word complete / protocol error, per lane
    reg [511:0] wd [0:3];
    reg [3:0]   wf;
    always @(*) begin
        for (integer l = 0; l < 4; l = l + 1) begin : g_ln
            reg [V-1:0] b;                    // the lane beat, assigned on every pass (comb temporary, no latch)
            b = lbw[l];
            wv[l] = 1'b0; err[l] = 1'b0; wf[l] = 1'b0; wd[l] = 512'd0;
            if (lvw[l]) begin
                if (l2w[l]) err[l] = 1'b1;                              // two beats of one lane in a cycle
                if (!b[6]) begin
                    if (b[7]) begin
                        wv[l] = 1'b1;
                        wd[l] = {(MUT == 2) ? 12'd0 : b[19:8], 244'd0, b[275:20]};
                        if (hv[l]) err[l] = 1'b1;                                // single inside a split word
                    end else if (hv[l]) err[l] = 1'b1;                           // part 0 twice
                end else begin
                    if (!hv[l] || b[7]) err[l] = 1'b1;                           // part 1 without part 0
                    wv[l] = hv[l];
                    wf[l] = b[8];
                    wd[l] = (MUT == 1) ? {hd[l], b[275:20]} : {b[275:20], hd[l]};
                end
            end
        end
    end
    reg [4*515-1:0] lq;                   // lane registers; bit 515*l+513 (live) comes from lv_q[l] instead
    // S81-KITS-RTLC 10-25: one KEPT live chain per lane (the 4 identical chains were merged into one flop that fed all
    // four ln*[513] pins); the data bits load the word and are 0 when no word arrives (no hold self-loop at the pin)
    (* keep = "true" *) reg [3:0] lv_0, lv_1, lv_2, lv_q;   // LPIPE 1: one more live stage (lane words +1 edge)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lv_0 <= 4'd0; lv_1 <= 4'd0; lv_2 <= 4'd0; lv_q <= 4'd0; end
        else begin lv_0 <= 4'hf; lv_1 <= lv_0; lv_2 <= lv_1; lv_q <= (LPIPE >= 2) ? lv_2 : (LPIPE != 0) ? lv_1 : lv_0; end
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_live
        assign lanes[515 * gl +: 515] = {lq[515 * gl + 514], lv_q[gl], lq[515 * gl + 1 +: 512], lq[515 * gl]};
    end endgenerate
`ifdef OT_DSDV_BK_TRACE
    integer tc = 0;
    always @(posedge clk) begin tc <= tc + 1; if (tc < 120 && (dl_nv || dl_sv)) $display("DSDV_BK_VIN t %0d n %0d/%h s %0d/%h", tc, dl_nv, dl_n[19:0], dl_sv, dl_s[19:0]); end
    always @(posedge clk) if (rst_n && (cc || err != 4'd0))
        $display("DSDV_BK_VIN fault err %b n %0d/%h s %0d/%h hv %b", err, dl_nv, dl_n[19:0], dl_sv, dl_s[19:0], hv);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            hv <= 4'd0; fault <= 1'b0; dr_v <= 1'b0;
            for (integer l = 0; l < 4; l = l + 1) begin lq[515 * l] <= 1'b0; lq[515 * l + 514] <= 1'b0; end
        end else begin
            dr_v <= cn | cs;
            if (ccw || err != 4'd0) fault <= 1'b1;
            for (integer l = 0; l < 4; l = l + 1) begin
                if (lvw[l] && !lbw[l][6] && !lbw[l][7])
                    hv[l] <= 1'b1;
                else if (wv[l]) hv[l] <= 1'b0;
                lq[515 * l]       <= wv[l];
                lq[515 * l + 514] <= (wv[l] && wf[l]) || fault;
            end
        end
    always @(posedge clk) begin
        dr_n <= cn ? dl_n[39:32] : dl_s[39:32];
        dr_d <= cn ? dl_n[47:40] : dl_s[47:40];
        for (integer l = 0; l < 4; l = l + 1) begin
`ifdef OT_RTLC_MUT_BKLN   // bench mutant: lane 1 keeps its previous word on a new word
            lq[515 * l + 1 +: 512] <= (wv[l] && l != 1) ? wd[l] : (l == 1 ? lq[515 * l + 1 +: 512] : 512'd0);
`else
            lq[515 * l + 1 +: 512] <= wv[l] ? wd[l] : 512'd0;     // wd[l] is 0 when !wv[l] (comb default)
`endif
            if (lvw[l] && !lbw[l][6])
                hd[l] <= lbw[l][275:20];
        end
    end
endmodule

// V egress: the unit's vd words -> SRAM buffer (128 x 512 on two ot_sram_1r1w_128x256_m1_r2c2) -> 2-beat words in the
// compiled drain windows.  Decision -> vo pin: 4 edges (decision flop, macro read, read register, vstop inject + output);
// a CTL at its vo pin edge e opens the window at vo edge e + LW + d, LW = 7 (vstop deliver 1, vin decode 1, window arm 1,
// decision 4).  The next CTL may arrive while a window is open (one command waits, armed); sticky faults: a word into a
// full buffer (the compiler drained too little; the word is dropped, fail closed), a CTL while another one waits, and a
// window that would open before the previous one closed.
module dsdv_bk_vout #(
    parameter integer V   = 276,
    parameter integer MUT = 0             // bench only: 3 = part 1 may leave after the window (start on its last slot),
                                          //             4 = part 1 carries the low half
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2:0]        ek,          // captured strap: egress kind
    input  wire              w_v,         // the unit's vd word (from the merger / selector flops)
    input  wire [511:0]      w_d,
    input  wire              dr_v,
    input  wire [7:0]        dr_n,
    input  wire [7:0]        dr_d,
    output wire              o_v,         // to the vstop inject port of the egress direction
    output wire [V-1:0]      o_b,
    output reg               fault
);
    reg  [6:0] wp, rp; reg [7:0] cnt;
    reg        arm, ph; reg [7:0] dly, wpn, wn;
    wire       go0 = wn != 8'd0 && !ph && cnt != 8'd0 && (wn >= 8'd2 || MUT == 3);
    wire       wr  = w_v && cnt != 8'd128;
    reg        p1v, p1s, p2v, p2s;                     // decision / read-register stage: valid, part
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wp <= 7'd0; rp <= 7'd0; cnt <= 8'd0; arm <= 1'b0; ph <= 1'b0; dly <= 8'd0; wpn <= 8'd0; wn <= 8'd0;
            p1v <= 1'b0; p2v <= 1'b0; p1s <= 1'b0; p2s <= 1'b0; fault <= 1'b0;
        end else begin
            if (wr) wp <= wp + 7'd1;
            if (go0) rp <= rp + 7'd1;
            cnt <= cnt + (wr ? 8'd1 : 8'd0) - (go0 ? 8'd1 : 8'd0);
            if (w_v && cnt == 8'd128) fault <= 1'b1;
            // one command may wait (armed) while the previous window is still open; windows never overlap
            if (wn != 8'd0) wn <= wn - 8'd1;
            if (dr_v) begin
                if (arm) fault <= 1'b1;
                arm <= 1'b1; dly <= dr_d; wpn <= dr_n;
            end else if (arm) begin
                if (dly == 8'd0) begin
                    arm <= 1'b0; wn <= wpn;
                    if (wn > 8'd1) fault <= 1'b1;
                end else dly <= dly - 8'd1;
            end
            if (wn != 8'd0 || MUT == 3) ph <= go0;
            p1v <= go0 || ((wn != 8'd0 || MUT == 3) && ph); p1s <= ph;
            p2v <= p1v; p2s <= p1s;
        end
    wire [255:0] rlo, rhi;
    ot_sram_1r1w_128x256_m1_r2c2 u_lo (.clk(clk), .r_ce_in(go0), .r_addr_in(rp), .rd_out(rlo), .w_ce_in(wr),
        .w_addr_in(wp), .wd_in(w_d[255:0]), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00),
        .cr_sel(16'd0));
    ot_sram_1r1w_128x256_m1_r2c2 u_hi (.clk(clk), .r_ce_in(go0), .r_addr_in(rp), .rd_out(rhi), .w_ce_in(wr),
        .w_addr_in(wp), .wd_in(w_d[511:256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00),
        .cr_sel(16'd0));
    reg [255:0] qlo, qhi;                              // macro outputs registered at the macro (rule 5)
    always @(posedge clk) if (p1v && !p1s) begin qlo <= rlo; qhi <= rhi; end
    assign o_v = p2v;
    assign o_b = !p2v ? {V{1'b0}}
               : !p2s ? {qlo, qhi[255:244], 1'b0, 1'b0, 2'b00, ek, 1'b1}
               :        {(MUT == 4) ? qlo : qhi, 12'd0, 1'b0, 1'b1, 2'b00, ek, 1'b1};
endmodule

// dsdv_bk_vin3 (DIE-S81-51/RF-D form 8, 11-03, OWNER 18:57 conservative form + COORD 18:59 bk_g ruling): dsdv_bk_vin LPIPE 2
// with every per-lane state / select copied LOCALLY per slice, so no cross-slice combinational term reaches a flop.
// rfd6 TT -124.58 was u_vin q0 copy -> shared hv_n -> q1/q2 copies (one recurrence across the tile).  The part-0-held
// recurrence is LOCAL: hv' = lv ? (!b6 && !b7) : hv needs only this lane's own registered beat bits and its own hv, so
// each slice keeps its OWN hv copy, updated from its OWN registered copies of lv / b6 / b7 (no slice reads another
// slice's new state; copies agree by construction; OT_RFD_CHK8 = bench assertion that all 9 copies of a lane agree).
// Per lane: 4 data slices k (beat bits [20+64k +: 64]) x 2 control copies (lo: hd[64k +: 64] + word bits [64k +: 64],
// hi: word bits [256+64k +: 64]) + 1 control copy (valid / fault / protocol error) = 9 copies.  Stage A also keeps one
// beat register pair per face side (W: lanes 0 / 2, E: lanes 1 / 3).  Timing is cycle-identical to dsdv_bk_vin LPIPE 2
// (V pin -> lane word +2 vs LPIPE 0; drain command unchanged).  Mutant OT_RFD_MUT_HD8: slice 1 loads hd without valid.
module dsdv_bk_vin3 #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2:0]        ik,
    input  wire [7:0]        uid,
    input  wire              dl_nv,
    input  wire [V-1:0]      dl_n,
    input  wire              dl_sv,
    input  wire [V-1:0]      dl_s,
    output wire [4*515-1:0]  lanes,
    output reg               dr_v,
    output reg  [7:0]        dr_n,
    output reg  [7:0]        dr_d,
    output reg               fault
);
    localparam integer NC = 9;            // copies per lane: 2k = slice k lo, 2k+1 = slice k hi, 8 = control
    wire dn = dl_nv && dl_n[3:1] == ik, ds = dl_sv && dl_s[3:1] == ik;
    wire cn = dl_nv && dl_n[3:1] == 3'd0 && dl_n[28:21] == uid && dl_n[31:29] == 3'd1;
    wire cs = dl_sv && dl_s[3:1] == 3'd0 && dl_s[28:21] == uid && dl_s[31:29] == 3'd1;
    // ---------------------------------------------------------------- stage A: per-copy lane hits, per-side beats
    (* keep = "true" *) reg [4*NC-1:0] pa, sa;
    (* keep = "true" *) reg [V-1:0] bn_w, bs_w, bn_e, bs_e;
    reg cc_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pa <= {4*NC{1'b0}}; sa <= {4*NC{1'b0}}; cc_q <= 1'b0; end
        else begin
            cc_q <= cn && cs;
            for (integer l = 0; l < 4; l = l + 1) for (integer c = 0; c < NC; c = c + 1) begin
                pa[NC * l + c] <= dn && dl_n[5:4] == l; sa[NC * l + c] <= ds && dl_s[5:4] == l;
            end
        end
    always @(posedge clk) begin bn_w <= dl_n; bs_w <= dl_s; bn_e <= dl_n; bs_e <= dl_s; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) dr_v <= 1'b0; else dr_v <= cn | cs;
    always @(posedge clk) begin dr_n <= cn ? dl_n[39:32] : dl_s[39:32]; dr_d <= cn ? dl_n[47:40] : dl_s[47:40]; end
    // ---------------------------------------------------------------- live chain (as LPIPE 2)
    (* keep = "true" *) reg [3:0] lv_0, lv_1, lv_2, lv_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lv_0 <= 4'd0; lv_1 <= 4'd0; lv_2 <= 4'd0; lv_q <= 4'd0; end
        else begin lv_0 <= 4'hf; lv_1 <= lv_0; lv_2 <= lv_1; lv_q <= lv_2; end
    reg cc_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) cc_r <= 1'b0; else cc_r <= cc_q;
    wire [3:0] errv; wire [3:0] wvc;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0; else if (cc_r || errv != 4'd0) fault <= 1'b1;
    genvar gl, gk;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_l
        wire [V-1:0] bn = (gl == 0 || gl == 2) ? bn_w : bn_e, bs = (gl == 0 || gl == 2) ? bs_w : bs_e;
        wire [NC-1:0] p = pa[NC * gl +: NC], s = sa[NC * gl +: NC];
        // ------------------------------------------------------------ control copy (valid, fault flag, protocol error)
        reg lvc, l2c, hvc; reg b6c, b7c, b8c;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin lvc <= 1'b0; l2c <= 1'b0; end else begin lvc <= p[8] | s[8]; l2c <= p[8] & s[8]; end
        always @(posedge clk) begin b6c <= p[8] ? bn[6] : bs[6]; b7c <= p[8] ? bn[7] : bs[7]; b8c <= p[8] ? bn[8] : bs[8]; end
        always @(posedge clk or negedge rst_n) if (!rst_n) hvc <= 1'b0; else if (lvc) hvc <= !b6c && !b7c;
        assign wvc[gl] = lvc && (b6c ? hvc : b7c);
        assign errv[gl] = lvc && (l2c || (!b6c ? hvc : (!hvc || b7c)));
        reg q_v, q_f;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin q_v <= 1'b0; q_f <= 1'b0; end else begin q_v <= wvc[gl]; q_f <= (wvc[gl] && b6c && b8c) || fault; end
        wire [511:0] q_d;
        // ------------------------------------------------------------ data slices
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_k
            reg [63:0] bd, hd; reg [11:0] bt;
            reg lvL, b6L, b7L, hvL, lvH, b6H, b7H, hvH;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin lvL <= 1'b0; lvH <= 1'b0; end
                else begin lvL <= p[2 * gk] | s[2 * gk]; lvH <= p[2 * gk + 1] | s[2 * gk + 1]; end
            always @(posedge clk) begin
                bd  <= p[2 * gk] ? bn[20 + 64 * gk +: 64] : bs[20 + 64 * gk +: 64];
                b6L <= p[2 * gk] ? bn[6] : bs[6];         b7L <= p[2 * gk] ? bn[7] : bs[7];
                b6H <= p[2 * gk + 1] ? bn[6] : bs[6];     b7H <= p[2 * gk + 1] ? bn[7] : bs[7];
                bt  <= p[2 * gk + 1] ? bn[19:8] : bs[19:8];
            end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin hvL <= 1'b0; hvH <= 1'b0; end
                else begin if (lvL) hvL <= !b6L && !b7L; if (lvH) hvH <= !b6H && !b7H; end
`ifdef OT_RFD_MUT_HD8   // bench mutant: slice 1 loads hd without its valid
            always @(posedge clk) if ((lvL || gk == 1) && !b6L) hd <= bd;
`else
            always @(posedge clk) if (lvL && !b6L) hd <= bd;
`endif
            wire wvL = lvL && (b6L ? hvL : b7L), wvH = lvH && (b6H ? hvH : b7H);
            reg [63:0] qL, qH;
            always @(posedge clk) begin
                qL <= !wvL ? 64'd0 : (b6L && MUT != 1) ? hd : bd;
                qH <= !wvH ? 64'd0 : b6H ? ((MUT == 1) ? hd : bd)
                    : (gk == 3) ? {((MUT == 2) ? 12'd0 : bt), 52'd0} : 64'd0;
            end
            assign q_d[64 * gk +: 64] = qL; assign q_d[256 + 64 * gk +: 64] = qH;
        end
        assign lanes[515 * gl +: 515] = {q_f, lv_q[gl], q_d, q_v};
`ifdef OT_RFD_CHK8
        always @(posedge clk) if (rst_n && ({g_k[0].hvL, g_k[0].hvH, g_k[1].hvL, g_k[1].hvH, g_k[2].hvL, g_k[2].hvH,
                g_k[3].hvL, g_k[3].hvH} != {8{hvc}}))
            $display("DSDV_BK_VIN3 HV COPY MISMATCH lane %0d", gl);
`endif
    end endgenerate
endmodule
