`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q CORE child (q8b four-leaf partition, 2026-10-13; S band beside the front child): record queue, hazard
// masks, read walk, read-lane credits, wrq issue, in-order retire and ret.  Every port is a flop at the pin:
//   in : S3 bundle / strobes from ot_hgi_qdq_fr; wrq_cr / rg_gnt face flops; from the assembly leaf its registered pop
//        strobes (i_pop, i_fire: beat-queue and lane-FIFO space come back two edges after the pop decision, conservative),
//        fault / idle; from the write leaf one pulse a finished record (i_fin), fault / idle.
//   out: ret, wrq, rg_req, the issued-beat bundle bp {lane 3, sectors 3, O sector 15, last 1, header 18} for the assembly
//        leaf's beat queue (the lane round trip hides its two edges), o_act (-> the write leaf's wg_req), reset relay.
// Retire: non-rejected records finish in queue order, so a count of finish pulses replaces the snapshot compare (which
// lives beside the done pins in the write leaf); the first finish capture is fin_c / ret (fin_c != 0 || i_fin).
// After a fault: the rest retires faulted once every leaf has been idle for 8 cycles (covers the seam transits).
// MUT (bench): 2 = hazard masks ignored.
module ot_hgi_qdq_core #(
    parameter integer LQ  = 10,
    parameter integer LD  = 16,
    parameter integer NB  = 32,
    parameter integer RQ  = 16,
    parameter integer SPANPIPE = 1,   // ready margin only
    parameter integer MUT = 0,
    parameter integer FIN_BYPASS = 0 // native candidate only; closed default stays unchanged
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              i_s1_v,
    input  wire              i_s3_v,
    input  wire [189:0]      i_s3,
    input  wire              i_nfault,
    output reg  [2:0]        ret,
    output reg  [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    output reg               rg_req,
    input  wire              rg_gnt,
    output wire              asm_rst_n,
    output reg               bp_v,
    output reg  [39:0]       bp,
    input  wire [7:0]        i_pop,
    input  wire              i_fire,
    input  wire              i_abad,
    input  wire              i_aidle,
    output reg               o_act,
    input  wire              i_fin,
    input  wire              i_wbad,
    input  wire              i_widle
);
    localparam integer QW = $clog2(RQ), SW = $clog2(NB), LW = $clog2(LD), CW = $clog2(LQ + 1);
    reg f_rst, f_rg; reg [7:0] f_rcr; reg f_aidle, f_widle;
    always @(posedge clk) begin f_rst <= rst_n; f_rg <= rg_gnt; f_rcr <= wrq_cr; f_aidle <= i_aidle; f_widle <= i_widle; end
    wire [5:0] rr_n;                                  // 0 queue, 1 walk, 2 -> assembly leaf, 3 q_dep, 4-5 lane credits
    ot_rst_relay #(.REGIONS(6)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign asm_rst_n = rr_n[2];
    // S3 pin flops (the front child's registered bundle, one edge later), accept strobe and sticky record fault
    reg s3_v, f_s1v, f_nf, f_fin, f_abad, f_wbad, f_fire; reg [7:0] f_pop;
    reg el3; reg [17:0] alo3, ahi3, olo3, ohi3; reg [14:0] as3, os3, rs3, ws3; reg [15:0] bpr3; reg [2:0] nsl3;
    reg [19:0] m3; reg [17:0] hd3;
    always @(posedge clk) begin {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3} <= i_s3; f_nf <= i_nfault; end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin s3_v <= 0; f_s1v <= 0; f_fin <= 0; f_abad <= 0; f_wbad <= 0; end
        else begin s3_v <= i_s3_v; f_s1v <= i_s1_v; f_fin <= i_fin; f_abad <= i_abad; f_wbad <= i_wbad; end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin f_fire <= 0; f_pop <= 0; end else begin f_fire <= i_fire; f_pop <= i_pop; end
    // ---------------------------------------------------------------- record queue
    reg [RQ-1:0] q_v, q_rej;
    reg [RQ-1:0] q_dep [0:RQ-1];
    reg [17:0] q_alo [0:RQ-1], q_ahi [0:RQ-1], q_olo [0:RQ-1], q_ohi [0:RQ-1];
    reg [14:0] q_as [0:RQ-1], q_os [0:RQ-1], q_rs [0:RQ-1], q_ws [0:RQ-1];
    reg [15:0] q_bpr [0:RQ-1]; reg [2:0] q_nsl [0:RQ-1]; reg [19:0] q_m [0:RQ-1]; reg [17:0] q_hd [0:RQ-1];
    reg [RQ-1:0] q_lb, q_lr; reg [7:0] q_hit [0:RQ-1];   // first-beat flags of an entry, computed at enqueue
    reg [QW-1:0] qt, rp, hd;                          // tail, next to start, retire head
    reg [QW:0] occ;                                   // accepted (bound) and not retired
    reg [QW:0] fin_c;                                 // finished (all writes done), not yet retired
    reg bad;
    // dependency of the S3 record on every valid entry (RAW: its A vs their O; WAR: its O vs their A; WAW: O vs O)
    reg [RQ-1:0] dep3; reg [RQ-1:0] ret_oh;
    always @* begin
        for (integer e = 0; e < RQ; e = e + 1)
            dep3[e] = q_v[e] && !ret_oh[e] && !q_rej[e] &&
                      ((alo3 <= q_ohi[e] && q_olo[e] <= ahi3) || (olo3 <= q_ahi[e] && q_alo[e] <= ohi3) ||
                       (olo3 <= q_ohi[e] && q_olo[e] <= ohi3));
    end
    // ---------------------------------------------------------------- read walk
    reg r_act; reg [19:0] r_row, r_m; reg [15:0] r_beat, r_bpr; reg [2:0] r_nsl;
    reg [14:0] r_rsec, r_osec, r_rs, r_ws; reg [17:0] r_hd;
    reg rg_ok;
    reg [CW-1:0] rcr [0:7];
    reg [LW:0] lf_r [0:7];                            // issued, pop not yet seen (lane FIFO space, LD a lane)
    reg [SW:0] b_used;                                // issued, fire not yet seen (the assembly leaf's beat queue space)
    wire [14:0] r_sec0 = r_rsec + {r_beat[12:0], 2'd0};
    // The beat's last-beat / last-row flags and its lane hit mask are STATE (q8b gate, 10-13: computed in the cycle they
    // sat in front of the issue decision: 16-b / 20-b increment-compare -> sector count -> hit -> credit -> issue -> load,
    // -205 ps at 770 on 622 endpoints).  Their next values are computed beside the decision and selected by it.
    reg r_lb, r_lr; reg [7:0] r_hit;                  // r_beat + 1 == r_bpr, r_row + 1 == r_m, lanes of the current beat
    wire r_lastbeat = r_lb, r_lastrow = r_lr;
    wire [2:0] r_nsec = r_lb ? r_nsl : 3'd4;
    function automatic [7:0] hit8(input [2:0] l, input [2:0] n);
        for (integer b = 0; b < 8; b = b + 1) hit8[b] = 3'(b - l) < n;
    endfunction
    wire r_lb_adv = (r_beat + 16'd2 == r_bpr);        // next beat of this row is its last
    wire r_lb_row = (r_bpr == 16'd1);                 // a row's first beat is its last
    wire r_lr_adv = (r_row + 20'd2 == r_m);
    wire [2:0] r_l_row = 3'(r_rsec[2:0] + r_rs[2:0]); // first lane of the next row
    wire [7:0] r_hit_adv = hit8(r_sec0[2:0] ^ 3'd4, r_lb_adv ? r_nsl : 3'd4);
    wire [7:0] r_hit_row = hit8(r_l_row, r_lb_row ? r_nsl : 3'd4);
    reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1)
            if (r_hit[b] && (rcr[b] == 0 || lf_r[b] == LD[LW:0])) r_cr_ok = 1'b0;
    end
    wire r_issue = r_act && rg_ok && !bad && b_used != NB[SW:0] && r_cr_ok;
    wire r_end = r_issue && r_lastbeat && r_lastrow;
    // the next entry may start: bound, eligible, its producers retired
    wire n_ok = q_v[rp] && !q_rej[rp] && ((q_dep[rp] & q_v) == '0 || MUT == 2) && !bad;
    wire n_load = n_ok && (!r_act || r_end);
    wire n_skip = q_v[rp] && q_rej[rp] && (!r_act || r_end) && !n_load;   // a rejected record holds no walk
    // ---------------------------------------------------------------- retire (in record order)
    reg [3:0] qc;                                     // consecutive all-idle cycles (fault drain)
    wire drained = qc[3];
    // The first capture of the registered WR finish pulse is the credit/retire
    // boundary itself. No combinational finish output or CDC bypass is added.
    wire fin_edge = FIN_BYPASS ? i_fin : f_fin;
    wire fin_av = fin_c != 0 || fin_edge;
    wire rt_ok = q_v[hd] && (q_rej[hd] || fin_av || (bad && drained));
    wire rt_fault = q_rej[hd] || bad;
    wire rt_fin = rt_ok && !q_rej[hd] && fin_av;
    always @* begin ret_oh = '0; if (rt_ok) ret_oh[hd] = 1'b1; end
    // ---------------------------------------------------------------- sequential control
    integer b;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            q_v <= 0; q_rej <= 0; qt <= 0; rp <= 0; hd <= 0; occ <= 0; bad <= 0; ret <= 0; fin_c <= 0; qc <= 0;
            rg_req <= 0; rg_ok <= 0; o_act <= 0;
        end else begin
            rg_req <= q_v != 0; o_act <= q_v != 0;
            rg_ok <= rg_req && f_rg;
            if (s3_v) begin q_v[qt] <= 1'b1; q_rej[qt] <= !el3; qt <= qt + 1'b1; end
            if (n_load || n_skip) rp <= rp + 1'b1;
            if (rt_ok) begin q_v[hd] <= 1'b0; hd <= hd + 1'b1; end
            fin_c <= fin_c + (QW+1)'(fin_edge) - (QW+1)'(rt_fin);
            if (f_abad || f_wbad) bad <= 1'b1;
            qc <= (!bp_v && f_aidle && f_widle && b_used == 0) ? (qc[3] ? qc : qc + 4'd1) : 4'd0;
            occ <= occ + (QW+1)'(f_s1v) - (QW+1)'(rt_ok);
            ret <= {rt_ok && rt_fault || f_nf, rt_ok, (occ + (QW+1)'(f_s1v) - (QW+1)'(rt_ok)) <= (QW+1)'(RQ - (SPANPIPE ? 12 : 6))};
        end
    end
    // Queue dependency masks have a separate, equally staged reset root (256 sinks at RQ16).
    always @(posedge clk or negedge rr_n[3]) begin
        if (!rr_n[3]) begin for (integer qe = 0; qe < RQ; qe = qe + 1) q_dep[qe] <= '0; end
        else begin
            if (s3_v) q_dep[qt] <= el3 ? dep3 : '0;
            for (integer qe = 0; qe < RQ; qe = qe + 1) if (rt_ok) q_dep[qe][hd] <= 1'b0;
            if (s3_v && rt_ok) q_dep[qt][hd] <= 1'b0;
        end
    end
    always @(posedge clk or negedge rr_n[1]) begin
        if (!rr_n[1]) begin
            r_act <= 0; r_row <= 0; r_m <= 0; r_beat <= 0; r_bpr <= 0; r_nsl <= 0; r_rsec <= 0; r_osec <= 0;
            r_rs <= 0; r_ws <= 0; b_used <= 0; bp_v <= 0; r_lb <= 0; r_lr <= 0; r_hit <= 0;
            for (b = 0; b < 8; b = b + 1) wrq[b*16 + 15] <= 1'b0;
        end else begin
            for (integer qb = 0; qb < 8; qb = qb + 1) wrq[qb*16 + 15] <= 1'b0;
            bp_v <= r_issue;
            // ---- read walk: one beat (<= 4 sectors) a cycle; the next record loads on the last beat
            if (r_issue) begin
                for (b = 0; b < 8; b = b + 1) if (r_hit[b]) wrq[b*16 + 15] <= 1'b1;
                if (r_lastbeat) begin
                    r_beat <= 0; r_row <= r_row + 1'b1; r_rsec <= r_rsec + r_rs; r_osec <= r_osec + r_ws;
                    r_lb <= r_lb_row; r_lr <= r_lr_adv; r_hit <= r_hit_row;
                end else begin r_beat <= r_beat + 1'b1; r_lb <= r_lb_adv; r_hit <= r_hit_adv; end
            end
            if (r_end && !n_load) r_act <= 1'b0;
            if (n_load) begin
                r_act <= 1'b1; r_row <= 0; r_beat <= 0; r_m <= q_m[rp]; r_bpr <= q_bpr[rp]; r_nsl <= q_nsl[rp];
                r_rsec <= q_as[rp]; r_osec <= q_os[rp]; r_rs <= q_rs[rp]; r_ws <= q_ws[rp];
                r_lb <= q_lb[rp]; r_lr <= q_lr[rp]; r_hit <= q_hit[rp];
            end
            b_used <= b_used + (SW+1)'(r_issue) - (SW+1)'(f_fire);
        end
    end
    generate for (genvar gr = 0; gr < 2; gr = gr + 1) begin : g_credit_region
        always @(posedge clk or negedge rr_n[4+gr]) begin
            if (!rr_n[4+gr]) begin
                for (integer b = gr*4; b < gr*4+4; b = b + 1) begin rcr[b] <= LQ[CW-1:0]; lf_r[b] <= 0; end
            end else begin
                for (integer b = gr*4; b < gr*4+4; b = b + 1) begin : lanes
                    reg iss; iss = r_issue && r_hit[b];
                    rcr[b] <= rcr[b] + CW'(f_rcr[b]) - CW'(iss);
                    lf_r[b] <= lf_r[b] + (LW+1)'(iss) - (LW+1)'(f_pop[b]);
                end
            end
        end
    end endgenerate
    // Address/payload flops are written separately from resettable valid strobes (no ALDFF feedback on payload bits).
    always @(posedge clk) begin
        for (integer b = 0; b < 8; b = b + 1)
            if (r_issue && r_hit[b]) wrq[b*16 +: 15] <= 15'(r_sec0 + 15'(3'(b - r_sec0[2:0])));
        bp <= {r_sec0[2:0], r_nsec, 15'(r_osec + {r_beat[12:0], 2'd0}), r_lastbeat && r_lastrow, r_hd};
        if (n_load) r_hd <= q_hd[rp];
    end
    // ---------------------------------------------------------------- storage (no reset)
    always @(posedge clk) begin
        if (s3_v) begin
            q_alo[qt] <= alo3; q_ahi[qt] <= ahi3; q_olo[qt] <= olo3; q_ohi[qt] <= ohi3; q_as[qt] <= as3; q_os[qt] <= os3;
            q_rs[qt] <= rs3; q_ws[qt] <= ws3; q_bpr[qt] <= bpr3; q_nsl[qt] <= nsl3; q_m[qt] <= m3; q_hd[qt] <= hd3;
            q_lb[qt] <= bpr3 == 16'd1; q_lr[qt] <= m3 == 20'd1; q_hit[qt] <= hit8(as3[2:0], (bpr3 == 16'd1) ? nsl3 : 3'd4);
        end
    end
`ifndef SYNTHESIS
    // the registered walk flags equal their definitions on every active cycle (every bench carries this check)
    always @(posedge clk) if (rr_n[1] && r_act) begin
        if (r_lb !== (r_beat + 16'd1 == r_bpr) || r_lr !== (r_row + 20'd1 == r_m) ||
            r_hit !== hit8(r_sec0[2:0], (r_beat + 16'd1 == r_bpr) ? r_nsl : 3'd4))
            $fatal(1, "FATAL: ot_hgi_qdq_core walk flags diverged (beat %0d row %0d)", r_beat, r_row);
    end
`endif
    initial begin
        if ((RQ & (RQ - 1)) != 0 || RQ < 8) $fatal(1, "ot_hgi_qdq_q: RQ must be a power of two >= 8");
        if ((NB & (NB - 1)) != 0 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_qdq_q: NB / LD powers of two");
    end
endmodule
`default_nettype wire
