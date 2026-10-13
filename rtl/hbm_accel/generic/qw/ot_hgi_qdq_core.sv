`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q CORE child (q8 re-partition, 2026-10-13): record queue, hazard masks, read walk, lane credit / occupancy,
// beat assembly, result FIFO (64x512 SRAM macro inside) and the write issue.  Pin registers: the S3 bundle from the front
// child (+1 ingress cycle), the popped lane heads hq (+1 cycle pop -> decode: s4), credit / done / grant face flops;
// outputs wrq / wwq / ret / c_pop / d_* / reset relays are flops.  y / vo go to the result FIFO write port (its own
// registers).  MUT (bench): 1 = lane-to-sector map swapped, 2 = hazard masks ignored.
module ot_hgi_qdq_core #(
    parameter integer LQ  = 10,
    parameter integer LD  = 16,
    parameter integer NB  = 32,
    parameter integer OD  = 64,
    parameter integer RQ  = 16,
    parameter integer SPANPIPE = 1,   // ready margin only
    parameter integer MUT = 0
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
    output reg  [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    output reg  [7:0]        c_pop,
    input  wire [7:0]        e_push,
    input  wire [3:0]        e_ovf,
    input  wire [8*256-1:0]  hq,
    output wire              lq_rst_n,
    output wire              dec_rst_n,
    output reg               d_v,
    output reg  [127:0]      d_h,
    output reg  [1023:0]     d_x,
    input  wire              vo,
    input  wire              qfault,
    input  wire              dfault,
    input  wire [511:0]      y
);
    localparam integer QW = $clog2(RQ), SW = $clog2(NB), OW = $clog2(OD), LW = $clog2(LD), CW = $clog2(LQ + 1);
    reg f_rst, f_rg, f_wg; reg [7:0] f_rcr, f_wcr, f_wdone;
    always @(posedge clk) begin
        f_rst <= rst_n; f_rg <= rg_gnt; f_wg <= wg_gnt;
        f_rcr <= wrq_cr; f_wcr <= wwq_cr; f_wdone <= wwq_done;
    end
    wire [5:0] rr_n;                                  // 0 front / queue, 1 walks / lanes, 2 decode tile
    ot_rst_relay #(.REGIONS(6)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign lq_rst_n = rr_n[1]; assign dec_rst_n = rr_n[2];
    // S3 pin flops (the front child's registered bundle, one edge later), accept strobe and sticky record fault
    reg s3_v, f_s1v, f_nf;
    reg el3; reg [17:0] alo3, ahi3, olo3, ohi3; reg [14:0] as3, os3, rs3, ws3; reg [15:0] bpr3; reg [2:0] nsl3;
    reg [19:0] m3; reg [17:0] hd3;
    always @(posedge clk) begin {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3} <= i_s3; f_nf <= i_nfault; end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin s3_v <= 0; f_s1v <= 0; end else begin s3_v <= i_s3_v; f_s1v <= i_s1_v; end
    // popped lane heads: pin flops (lane-pair tile hq -> here), then the beat placement
    reg [8*256-1:0] hq_f; always @(posedge clk) hq_f <= hq;
    // ---------------------------------------------------------------- record queue
    reg [RQ-1:0] q_v, q_rej, q_snv;
    reg [RQ-1:0] q_dep [0:RQ-1];
    reg [17:0] q_alo [0:RQ-1], q_ahi [0:RQ-1], q_olo [0:RQ-1], q_ohi [0:RQ-1];
    reg [14:0] q_as [0:RQ-1], q_os [0:RQ-1], q_rs [0:RQ-1], q_ws [0:RQ-1];
    reg [15:0] q_bpr [0:RQ-1]; reg [2:0] q_nsl [0:RQ-1]; reg [19:0] q_m [0:RQ-1]; reg [17:0] q_hd [0:RQ-1];
    reg [8*8-1:0] q_snap [0:RQ-1];                    // per-lane write count after the record's last write
    reg [QW-1:0] qt, rp, hd;                          // tail, next to start, retire head
    reg [QW:0] occ;                                   // accepted (bound) and not retired
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
    reg r_act; reg [QW-1:0] r_e; reg [19:0] r_row, r_m; reg [15:0] r_beat, r_bpr; reg [2:0] r_nsl;
    reg [14:0] r_rsec, r_osec, r_rs, r_ws;
    reg rg_ok, wg_ok;
    reg [CW-1:0] rcr [0:7], wcr [0:7];
    // lane response FIFOs: 4 hardened lane-pair tiles (ot_hgi_qdq_lq, LD 16 x 256 per lane, ~9.3k sinks each on their
    // own clock trees; textbook audit 10-12 class 1: the 8 x 16 x 256 flop array put 46k flops on the cluster root).
    // The centre keeps occupancy lf_n (from the tiles' registered e_push) and issued-not-popped lf_r, decides pops, and
    // sends registered per-lane pop strobes; the popped heads come back registered two cycles later (hq) and are placed
    // into beat positions here, three cycles after the pop decision (registered select pipeline s1..s3).
    reg [LW:0] lf_n [0:7], lf_r [0:7];
    // (c_pop, e_push, e_ovf, hq are ports: the lane-pair tiles are the cluster's children)
    reg [2:0] bq_l [0:NB-1], bq_n [0:NB-1]; reg [14:0] bq_o [0:NB-1]; reg [QW-1:0] bq_e [0:NB-1]; reg bq_z [0:NB-1];
    reg [SW-1:0] b_t, b_h; reg [SW:0] b_used;
    wire [14:0] r_sec0 = r_rsec + {r_beat[12:0], 2'd0};
    wire r_lastbeat = (r_beat + 16'd1 == r_bpr);
    wire r_lastrow = (r_row + 20'd1 == r_m);
    wire [2:0] r_nsec = r_lastbeat ? r_nsl : 3'd4;
    reg [7:0] r_hit; reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            r_hit[b] = 3'(b - r_sec0[2:0]) < r_nsec;
            if (r_hit[b] && (rcr[b] == 0 || lf_r[b] == LD[LW:0])) r_cr_ok = 1'b0;
        end
    end
    wire r_issue = r_act && rg_ok && !bad && b_used != NB[SW:0] && r_cr_ok;
    wire r_end = r_issue && r_lastbeat && r_lastrow;
    // the next entry may start: bound, eligible, its producers retired
    wire n_ok = q_v[rp] && !q_rej[rp] && ((q_dep[rp] & q_v) == '0 || MUT == 2) && !bad;
    wire n_load = n_ok && (!r_act || r_end);
    wire n_skip = q_v[rp] && q_rej[rp] && (!r_act || r_end) && !n_load;   // a rejected record holds no walk
    // ---------------------------------------------------------------- assembly -> decode
    wire [2:0] h_l = bq_l[b_h], h_n = bq_n[b_h];
    reg [7:0] h_hit; reg h_ok; reg [1023:0] h_x;
    // pop pipeline: s1 (with c_pop) -> s2 (tile i_pop) -> s3 (tile hq) -> d_x / d_v.  The 4 beat positions take a one-hot
    // AND-OR over the 8 popped lane heads, selects decoded from the registered s3 lane / count.
    reg s1_lv, s2_lv, s3_lv, s4_lv; reg [2:0] s1_l, s2_l, s3_l, s4_l, s1_n, s2_n, s3_n, s4_n; reg [17:0] s1_hd, s2_hd, s3_hd, s4_hd;
    always @* begin
        h_ok = b_used != 0; h_x = '0;
        for (integer b = 0; b < 8; b = b + 1) begin
            h_hit[b] = 3'(b - h_l) < h_n;
            if (h_hit[b] && lf_n[b] == 0) h_ok = 1'b0;
        end
        for (integer j = 0; j < 4; j = j + 1) begin
            reg [2:0] l; l = 3'(s4_l + ((MUT == 1) ? (j ^ 1) : j));
            for (integer b = 0; b < 8; b = b + 1)
                h_x[j*256 +: 256] = h_x[j*256 +: 256] | ({256{j < s4_n && l == 3'(b)}} & hq_f[b*256 +: 256]);
        end
    end
    reg [OW:0] resv, od_n;
    wire l_fire = h_ok && resv != OD[OW:0];
    // d_v / d_h / d_x are output flops (to the decode tiles)

    // ---------------------------------------------------------------- result FIFO + write
    reg [14:0] mq_o [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg [QW-1:0] mq_e [0:OD-1]; reg mq_z [0:OD-1];
    // result store (textbook audit 10-12, class 5/6: was a 64 x 512 flop array read 64:1 x 512 b in one cycle): one
    // ot_sram_1r1w_64x512_m1_r2c2 macro behind a 2-entry registered prefetch buffer (ot_fifo_sram_fwft: synchronous macro
    // read issued ahead into capture registers; an empty FIFO shows a push the next cycle, one pop a cycle sustained),
    // so the write issue sees a 2:1 register head instead of the array.  ESL 128: the buffer in 4 x 128-b slices with
    // their own control copies (one slice per sector of the write).  od_n keeps the pushed-not-written count (retire /
    // drain accounting); the write issues on the buffer's head valid.
    wire od_hv, od_ovf; wire [511:0] od_head;
    reg [OW-1:0] mq_t, mq_h;
    wire [14:0] w_sec0 = mq_o[mq_h]; wire [2:0] w_n = mq_n[mq_h];
    reg [7:0] w_hit; reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            w_hit[b] = 3'(b - w_sec0[2:0]) < w_n;
            if (w_hit[b] && wcr[b] == 0) w_cr_ok = 1'b0;
        end
    end
    wire w_fire = wg_ok && !bad && od_hv && w_cr_ok;
    ot_fifo_sram_fwft #(.W(512), .DEPTH(OD), .MACRO(0), .ESL(128)) u_od (.clk(clk), .rst_n(rr_n[1]), .push(vo),
        .wdata(y), .pop(w_fire), .hv(od_hv), .head(od_head), .ovf(od_ovf));
    reg [7:0] wcnt [0:7], dcnt [0:7];
    // ---------------------------------------------------------------- retire (in record order)
    reg r_ready; reg h_fin;
    always @* begin
        h_fin = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) if ($signed(dcnt[b] - q_snap[hd][b*8 +: 8]) < 0) h_fin = 1'b0;
    end
    // after a decode fault (terminal, as nfault): writes stop; every launched beat has come back -> retire the rest faulted
    wire drained = b_used == 0 && !d_v && resv == od_n;
    wire rt_ok = q_v[hd] && (q_rej[hd] || (q_snv[hd] && h_fin) || (bad && drained));
    wire rt_fault = q_rej[hd] || bad;
    always @* begin ret_oh = '0; if (rt_ok) ret_oh[hd] = 1'b1; end
    // ---------------------------------------------------------------- sequential control
    integer b, e, j;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            q_v <= 0; q_rej <= 0; q_snv <= 0; qt <= 0; rp <= 0; hd <= 0; occ <= 0; bad <= 0; ret <= 0;
            rg_req <= 0; wg_req <= 0; rg_ok <= 0; wg_ok <= 0;

        end else begin
            rg_req <= q_v != 0; wg_req <= q_v != 0;
            rg_ok <= rg_req && f_rg; wg_ok <= wg_req && f_wg;
            // enqueue
            if (s3_v) begin
                q_v[qt] <= 1'b1; q_rej[qt] <= !el3; q_snv[qt] <= 1'b0; qt <= qt + 1'b1;
            end

            if (n_load || n_skip) rp <= rp + 1'b1;
            if (w_fire && mq_z[mq_h]) q_snv[mq_e[mq_h]] <= 1'b1;
            if (rt_ok) begin q_v[hd] <= 1'b0; hd <= hd + 1'b1; end
            if (vo && qfault) bad <= 1'b1;
            if (dfault || od_ovf || e_ovf != 0) bad <= 1'b1;   // e_ovf: lane FIFO overrun in a tile   // result-store overrun (bounded by resv; fail closed)
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
            r_act <= 0; r_e <= 0; r_row <= 0; r_m <= 0; r_beat <= 0; r_bpr <= 0; r_nsl <= 0; r_rsec <= 0; r_osec <= 0;
            r_rs <= 0; r_ws <= 0; b_t <= 0; b_h <= 0; b_used <= 0; resv <= 0; od_n <= 0; mq_h <= 0; mq_t <= 0;
            d_v <= 0; s1_lv <= 0; s2_lv <= 0; s3_lv <= 0; s4_lv <= 0;
            for (b = 0; b < 8; b = b + 1) begin
                wrq[b*16 + 15] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
            end
        end else begin
            for (integer qb = 0; qb < 8; qb = qb + 1) begin wrq[qb*16 + 15] <= 1'b0; wwq[qb*280 + 279] <= 1'b0; end
            s1_lv <= l_fire; s2_lv <= s1_lv; s3_lv <= s2_lv; s4_lv <= s3_lv; d_v <= s4_lv;
            // ---- read walk: one beat (<= 4 sectors) a cycle; the next record loads on the last beat
            if (r_issue) begin
                for (b = 0; b < 8; b = b + 1) if (r_hit[b]) wrq[b*16 + 15] <= 1'b1;
                b_t <= b_t + 1'b1;
                if (r_lastbeat) begin r_beat <= 0; r_row <= r_row + 1'b1; r_rsec <= r_rsec + r_rs; r_osec <= r_osec + r_ws; end
                else r_beat <= r_beat + 1'b1;
            end
            if (r_end && !n_load) r_act <= 1'b0;
            if (n_load) begin
                r_act <= 1'b1; r_e <= rp; r_row <= 0; r_beat <= 0; r_m <= q_m[rp]; r_bpr <= q_bpr[rp]; r_nsl <= q_nsl[rp];
                r_rsec <= q_as[rp]; r_osec <= q_os[rp]; r_rs <= q_rs[rp]; r_ws <= q_ws[rp];
            end
            b_used <= b_used + (SW+1)'(r_issue) - (SW+1)'(l_fire);
            if (l_fire) begin b_h <= b_h + 1'b1; mq_t <= mq_t + 1'b1; end
            // ---- decode results -> result FIFO; write the head result on its 1..4 lanes
            od_n <= od_n + (OW+1)'(vo) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            if (w_fire) begin
                for (b = 0; b < 8; b = b + 1) if (w_hit[b]) begin : wr
                    wwq[b*280 + 279] <= 1'b1;
                end
                mq_h <= mq_h + 1'b1;
            end
        end
    end
    generate for (genvar gr = 0; gr < 2; gr = gr + 1) begin : g_credit_region
        always @(posedge clk or negedge rr_n[4+gr]) begin
            if (!rr_n[4+gr]) begin
                for (integer b = gr*4; b < gr*4+4; b = b + 1) begin
                    c_pop[b] <= 0; rcr[b] <= LQ[CW-1:0]; wcr[b] <= LQ[CW-1:0]; lf_n[b] <= 0; lf_r[b] <= 0;
                    wcnt[b] <= 0; dcnt[b] <= 0;
                end
            end else begin
            for (integer b = gr*4; b < gr*4+4; b = b + 1) begin : lanes
                reg push, pop, iss, wr;
                push = e_push[b]; pop = l_fire && h_hit[b]; iss = r_issue && r_hit[b]; wr = w_fire && w_hit[b];
                c_pop[b] <= pop;
                rcr[b] <= rcr[b] + CW'(f_rcr[b]) - CW'(iss);
                wcr[b] <= wcr[b] + CW'(f_wcr[b]) - CW'(wr);
                lf_n[b] <= lf_n[b] + (LW+1)'(push) - (LW+1)'(pop);
                lf_r[b] <= lf_r[b] + (LW+1)'(iss) - (LW+1)'(pop);
                wcnt[b] <= wcnt[b] + 8'(wr); dcnt[b] <= dcnt[b] + 8'(f_wdone[b]);
            end
            end
        end
    end endgenerate
    // Address/payload flops are written separately from resettable valid strobes.  Keeping both slices in one
    // asynchronous always block creates Yosys ALDFF feedback for the unreset payload bits.
    always @(posedge clk) begin
        for (integer b = 0; b < 8; b = b + 1) begin
            if (r_issue && r_hit[b]) wrq[b*16 +: 15] <= 15'(r_sec0 + 15'(3'(b - r_sec0[2:0])));
            if (w_fire && w_hit[b]) begin
                    reg [255:0] d; reg [1:0] s; reg [127:0] c; s = 2'(3'(b - w_sec0[2:0]));
                    // decoded constant-index sector select (one-hot AND-OR, no runtime part-select)
                    c = ({128{s == 2'd0}} & od_head[127:0]) | ({128{s == 2'd1}} & od_head[255:128]) |
                        ({128{s == 2'd2}} & od_head[383:256]) | ({128{s == 2'd3}} & od_head[511:384]);
                    for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {c[k*16 +: 16], 16'd0};
                    wwq[b*280 +: 279] <= {15'(w_sec0 + 15'(s)), d, 8'hff};
            end
        end
    end
    // ---------------------------------------------------------------- storage (no reset)
    always @(posedge clk) begin
        if (s3_v) begin
            q_alo[qt] <= alo3; q_ahi[qt] <= ahi3; q_olo[qt] <= olo3; q_ohi[qt] <= ohi3; q_as[qt] <= as3; q_os[qt] <= os3;
            q_rs[qt] <= rs3; q_ws[qt] <= ws3; q_bpr[qt] <= bpr3; q_nsl[qt] <= nsl3; q_m[qt] <= m3; q_hd[qt] <= hd3;
        end
        if (r_issue) begin
            bq_l[b_t] <= r_sec0[2:0]; bq_n[b_t] <= r_nsec; bq_o[b_t] <= r_osec + {r_beat[12:0], 2'd0}; bq_e[b_t] <= r_e;
            bq_z[b_t] <= r_lastbeat && r_lastrow;
        end
        s1_l <= h_l; s1_n <= h_n; s1_hd <= q_hd[bq_e[b_h]];
        s2_l <= s1_l; s2_n <= s1_n; s2_hd <= s1_hd; s3_l <= s2_l; s3_n <= s2_n; s3_hd <= s2_hd; s4_l <= s3_l; s4_n <= s3_n; s4_hd <= s3_hd;
        // Decoder consumes data only when d_v: no 2k-load data enable is needed.
        d_x <= h_x; d_h <= {s4_hd[17:8], 46'd0, s4_hd[7:0], 64'd0};
        if (l_fire) begin
            mq_o[mq_t] <= bq_o[b_h]; mq_n[mq_t] <= h_n; mq_e[mq_t] <= bq_e[b_h]; mq_z[mq_t] <= bq_z[b_h];
        end
        if (w_fire && mq_z[mq_h])
            for (integer q = 0; q < 8; q = q + 1) q_snap[mq_e[mq_h]][q*8 +: 8] <= wcnt[q] + 8'(w_hit[q]);
    end
    initial begin
        if ((RQ & (RQ - 1)) != 0 || RQ < 8) $fatal(1, "ot_hgi_qdq_q: RQ must be a power of two >= 8");
        if ((NB & (NB - 1)) != 0 || (OD & (OD - 1)) != 0 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_qdq_q: NB / OD / LD powers of two");
        if (OD < 32) $fatal(1, "ot_hgi_qdq_q: OD >= 32 (decode latency 26)");
    end
endmodule
`default_nettype wire
