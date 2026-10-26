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
    parameter integer MUT = 0             // bench only: 1 = part 1 written into the low half, 2 = single drops type/tag
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
    reg [3:0]   hv;                       // part 0 held per lane
    reg [255:0] hd [0:3];
    reg [3:0]   wv, err;                  // this cycle: word complete / protocol error, per lane
    reg [511:0] wd [0:3];
    reg [3:0]   wf;
    integer l;
    always @(*) begin
        for (l = 0; l < 4; l = l + 1) begin
            wv[l] = 1'b0; err[l] = 1'b0; wf[l] = 1'b0; wd[l] = 512'd0;
            if ((dn && dl_n[5:4] == l) || (ds && dl_s[5:4] == l)) begin : g_hit
                reg [V-1:0] b;
                b = (dn && dl_n[5:4] == l) ? dl_n : dl_s;
                if (dn && ds && dl_n[5:4] == dl_s[5:4]) err[l] = 1'b1;          // two beats of one lane in a cycle
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
    (* keep = "true" *) reg [3:0] lv_0, lv_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lv_0 <= 4'd0; lv_q <= 4'd0; end
        else begin lv_0 <= 4'hf; lv_q <= lv_0; end
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_live
        assign lanes[515 * gl +: 515] = {lq[515 * gl + 514], lv_q[gl], lq[515 * gl + 1 +: 512], lq[515 * gl]};
    end endgenerate
`ifdef OT_DSDV_BK_TRACE
    integer tc = 0;
    always @(posedge clk) begin tc <= tc + 1; if (tc < 120 && (dl_nv || dl_sv)) $display("DSDV_BK_VIN t %0d n %0d/%h s %0d/%h", tc, dl_nv, dl_n[19:0], dl_sv, dl_s[19:0]); end
    always @(posedge clk) if (rst_n && ((cn && cs) || err != 4'd0))
        $display("DSDV_BK_VIN fault err %b n %0d/%h s %0d/%h hv %b", err, dl_nv, dl_n[19:0], dl_sv, dl_s[19:0], hv);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            hv <= 4'd0; fault <= 1'b0; dr_v <= 1'b0;
            for (l = 0; l < 4; l = l + 1) begin lq[515 * l] <= 1'b0; lq[515 * l + 514] <= 1'b0; end
        end else begin
            dr_v <= cn | cs;
            if ((cn && cs) || err != 4'd0) fault <= 1'b1;
            for (l = 0; l < 4; l = l + 1) begin
                if ((dn && dl_n[5:4] == l && !dl_n[6] && !dl_n[7]) || (!(dn && dl_n[5:4] == l) && ds && dl_s[5:4] == l && !dl_s[6] && !dl_s[7]))
                    hv[l] <= 1'b1;
                else if (wv[l]) hv[l] <= 1'b0;
                lq[515 * l]       <= wv[l];
                lq[515 * l + 514] <= (wv[l] && wf[l]) || fault;
            end
        end
    always @(posedge clk) begin
        dr_n <= cn ? dl_n[39:32] : dl_s[39:32];
        dr_d <= cn ? dl_n[47:40] : dl_s[47:40];
        for (l = 0; l < 4; l = l + 1) begin
`ifdef OT_RTLC_MUT_BKLN   // bench mutant: lane 1 keeps its previous word on a new word
            lq[515 * l + 1 +: 512] <= (wv[l] && l != 1) ? wd[l] : (l == 1 ? lq[515 * l + 1 +: 512] : 512'd0);
`else
            lq[515 * l + 1 +: 512] <= wv[l] ? wd[l] : 512'd0;     // wd[l] is 0 when !wv[l] (comb default)
`endif
            if ((dn && dl_n[5:4] == l && !dl_n[6]) || (!(dn && dl_n[5:4] == l) && ds && dl_s[5:4] == l && !dl_s[6]))
                hd[l] <= (dn && dl_n[5:4] == l) ? dl_n[275:20] : dl_s[275:20];
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
