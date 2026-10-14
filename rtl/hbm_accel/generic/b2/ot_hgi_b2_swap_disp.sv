`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM B2 native MTP SWAP DISPATCHER (el1013-ds-mtp-lead [mtp-dispatch] 2026-10-13).
// Physical / cut / transaction spec: el1013-ds-mtp-lead.log "[mtp-dispatch] PHYSICAL/CUT/TRANSACTION SPEC".
// Budget: MTP.VERIFY swapout = h (20,480 FP32) + PRE (8 words) + CTL.FENCE in 248 cycles (immutable; limit 1.10 x = 272).
//
// The compiler (tools/hgi_b2/mtp_swap.py) lowers the legacy STRIPE4 h record into ONE dispatch group of four linear
// own-stack records (cluster q: source rows q + 4j of its LOCAL slice -> stack q) and PRE into a one-record group on
// cluster 0.  Three modules:
//   ot_hgi_b2_swap_disp  (S, spine side: glue of the cmdproc tile, beside ot_hgi_b2_disp)
//     in   beats {v, last, cluster 2, move 227} (ot_hgi_dma_mover move word, TOKEN already resolved), one a cycle.
//          REGISTER AT THE PIN ([mtp-phys] pin audit 2026-10-13): g_v / g_last / g_q / g_mv enter an UNCONDITIONAL
//          capture stage (no logic before the flop); the accept is decided one edge later from the captured valid and
//          the ready of the edge it was sent on (rdy_d); g_rdy is a flop computed from internal state only, so it cannot
//          see the beat in the capture stage nor the one being sent: the FIFO is 4 deep and ready needs <= 2 occupied;
//          a beat for a cluster that already holds one in the open group (a duplicate cluster) is a sticky FAULT (S
//          holds one record a cluster; it used to stall);
//     hold a group's beats, one slot a cluster; the beat flagged LAST releases every held beat and itself on the SAME
//          edge (one registered down link a cluster: {v, move}); a cluster is never made to wait for another cluster;
//     credit 2 a cluster (the endpoint station depth), returned by the engine's mv_src: outstanding = 2 - credit;
//     join cluster q is done when nothing is outstanding and its relayed quiet is high.  quiet and src return through the
//          same up relay (equal delay), so once the last src is back every quiet sample post-dates the last accept;
//          fence_quiet = flop(AND of the four, nothing held, no fault); done = one pulse when it rises after a release.
//   ot_hgi_b2_swap_ep    (E, cluster side: glue of the cluster DMA unit tile, at the engine's mv pin)
//     a 2-entry move station written from the pin, valid / ready to ot_hgi_dma_back; up {src, quiet & station empty,
//     fault} flops.
//   ot_hgi_b2_swap_relay the <= 500 um wire stages between them (HOPS a direction; in the die: ot_fwd_link_stage).
// Wires a cluster: down 228 b, up 3 b.  Cross-cluster payload: none.
// MUT (bench): 1 the records of clusters 1 and 2 swapped; 2 cluster 2's HBM base + one row (256 B); 5 cluster 2's HBM
//   base + one sector (32 B); 3 the join ignores the outstanding count (stale quiet: early fence); 4 SERIALIZED group:
//   a cluster's record is released only when no other record is outstanding (exact, but must fail the throughput check).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_disp #(
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    // command side: one beat a cycle
    input  wire               g_v,
    output wire               g_rdy,
    input  wire               g_last,
    input  wire [1:0]         g_q,
    input  wire [226:0]       g_mv,
    // per cluster: down {move 227, v}, up {fault, quiet, src}
    output wire [4*228-1:0]   dn,
    input  wire [4*3-1:0]     up,
    output reg                fence_quiet,     // every released record's every HBM write acknowledged, nothing held
    output reg                done,            // one pulse a completed release (the CTL.FENCE answer)
    output reg                fault            // sticky
);
    // ---------------------------------------------------------------- pin capture stage + FIFO (4 entries)
    reg p_v, p_l, rdy_d; reg [1:0] p_q; reg [226:0] p_mv;
    reg [226:0] f_mv [0:3]; reg [1:0] f_q [0:3]; reg [3:0] f_l;
    reg [1:0] wp, rp; reg [2:0] cnt; reg rdy_q;
    assign g_rdy = rdy_q;
    wire push = p_v && rdy_d;
    wire [1:0] hq = f_q[rp]; wire hl = f_l[rp]; wire [226:0] hmv = f_mv[rp];
    // ---------------------------------------------------------------- hold slots, credits, up pin flops
    reg [3:0] hv; reg [226:0] h_mv [0:3];
    reg [1:0] cred [0:3];
    reg [3:0] u_src, u_quiet, u_fault;
    reg       dirty;
    reg [3:0] dv; reg [226:0] d_mv [0:3];
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_dn
        assign dn[gq*228 +: 228] = {d_mv[gq], dv[gq]};
    end endgenerate
    // ---------------------------------------------------------------- release decision (registers only)
    reg [3:0] tgt;                               // the clusters a release at the head would send
    reg [3:0] none_out;
    reg       cr_ok, pop, rel;
    reg [3:0] snd;
    integer q;
    always @* begin
        for (q = 0; q < 4; q = q + 1) none_out[q] = cred[q] == 2'd2;
        tgt = hv | (4'b0001 << hq);
        cr_ok = 1'b1;
        for (q = 0; q < 4; q = q + 1) if (tgt[q] && cred[q] == 2'd0) cr_ok = 1'b0;
        pop = 1'b0; rel = 1'b0; snd = 4'd0;
        if (MUT == 4) begin
            // serialized mutant: every beat goes to its hold slot; one held record leaves when nothing is outstanding
            pop = cnt != 3'd0 && !hv[hq];
            if (&none_out && !(|dv)) begin
                if (hv[0]) snd = 4'b0001; else if (hv[1]) snd = 4'b0010; else if (hv[2]) snd = 4'b0100; else if (hv[3]) snd = 4'b1000;
            end
        end else if (cnt != 3'd0 && !hv[hq]) begin
            if (!hl) pop = 1'b1;
            else if (cr_ok) begin pop = 1'b1; rel = 1'b1; snd = tgt; end
        end
    end
    // the record a cluster's down link carries (mutants act here)
    reg [226:0] s_mv [0:3];
    always @* begin
        for (q = 0; q < 4; q = q + 1) s_mv[q] = (rel && hq == q[1:0]) ? hmv : h_mv[q];
        if (MUT == 1) begin : m1
            reg [226:0] t; t = s_mv[1]; s_mv[1] = s_mv[2]; s_mv[2] = t;
        end
        if (MUT == 2) s_mv[2][134:98] = s_mv[2][134:98] + 37'd256;
        if (MUT == 5) s_mv[2][134:98] = s_mv[2][134:98] + 37'd32;
    end
    wire [3:0] snd_x = (MUT == 1) ? {snd[3], snd[1], snd[2], snd[0]} : snd;      // MUT 1: the valids follow the records
    // ---------------------------------------------------------------- join
    reg [3:0] ok_c;
    always @* for (q = 0; q < 4; q = q + 1) ok_c[q] = ((MUT == 3) || none_out[q]) && u_quiet[q];
    wire fq_c = &ok_c && cnt == 3'd0 && !p_v && hv == 4'd0 && dv == 4'd0 && !fault && !(|u_fault);
    // ---------------------------------------------------------------- data (no reset)
    always @(posedge clk) begin
        p_mv <= g_mv; p_q <= g_q; p_l <= g_last;
        if (push) begin f_mv[wp] <= p_mv; f_q[wp] <= p_q; f_l[wp] <= p_l; end
        if (pop && !rel) h_mv[hq] <= hmv;
        for (q = 0; q < 4; q = q + 1) if (snd_x[q]) d_mv[q] <= s_mv[q];
    end
    // ---------------------------------------------------------------- control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 2'd0; rp <= 2'd0; cnt <= 3'd0; rdy_q <= 1'b0; rdy_d <= 1'b0; p_v <= 1'b0; hv <= 4'd0; dv <= 4'd0; dirty <= 1'b0;
            u_src <= 4'd0; u_quiet <= 4'd0; u_fault <= 4'd0; fence_quiet <= 1'b0; done <= 1'b0; fault <= 1'b0;
            for (q = 0; q < 4; q = q + 1) cred[q] <= 2'd2;
        end else begin
            for (q = 0; q < 4; q = q + 1) begin u_src[q] <= up[q*3]; u_quiet[q] <= up[q*3 + 1]; u_fault[q] <= up[q*3 + 2]; end
            p_v <= g_v; rdy_d <= rdy_q;
            if (push) wp <= wp + 2'd1;
            if (pop) rp <= rp + 2'd1;
            cnt <= cnt + {2'd0, push} - {2'd0, pop};
            rdy_q <= (cnt + {2'd0, push} - {2'd0, pop}) <= 3'd2;
            if (MUT != 4 && cnt != 3'd0 && hv[hq]) fault <= 1'b1;        // a second record for a cluster in one group
            for (q = 0; q < 4; q = q + 1) begin
                if (snd[q]) hv[q] <= 1'b0;
                else if (pop && !rel && hq == q[1:0]) hv[q] <= 1'b1;
                cred[q] <= cred[q] - {1'b0, snd[q]} + {1'b0, u_src[q]};
            end
            dv <= snd_x;
            if (|u_fault) fault <= 1'b1;
            fence_quiet <= fq_c;
            done <= 1'b0;
            if (|snd) dirty <= 1'b1;
            else if (dirty && fq_c) begin dirty <= 1'b0; done <= 1'b1; end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// E: the cluster-side move station (2 entries = the dispatcher's credit), at the engine's mv pin
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_ep (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [227:0]  dn,          // {move 227, v}
    output wire [2:0]    up,          // {fault, quiet, src}
    output wire          mv_v,
    input  wire          mv_rdy,
    output wire [226:0]  mv,
    input  wire          mv_src,
    input  wire          mv_fault,
    input  wire          quiet
);
    reg [226:0] s_mv [0:1]; reg wp, rp; reg [1:0] cnt;
    reg src_q, quiet_q, fault_q;
    assign mv_v = cnt != 2'd0; assign mv = s_mv[rp];
    wire pop = mv_v && mv_rdy;
    assign up = {fault_q, quiet_q, src_q};
    always @(posedge clk) if (dn[0]) s_mv[wp] <= dn[227:1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wp <= 1'b0; rp <= 1'b0; cnt <= 2'd0; src_q <= 1'b0; quiet_q <= 1'b0; fault_q <= 1'b0; end
        else begin
            if (dn[0]) wp <= ~wp;
            if (pop) rp <= ~rp;
            cnt <= cnt + {1'b0, dn[0]} - {1'b0, pop};
            src_q <= mv_src; fault_q <= mv_fault;
            quiet_q <= quiet && cnt == 2'd0 && !dn[0];
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// the wire stages of one link direction: N registered stages (<= 500 um each); the low CW bits are control (reset)
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_relay #(
    parameter integer W = 228,
    parameter integer CW = 1,
    parameter integer N = 10
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [W-1:0]  d,
    output wire [W-1:0]  q
);
    genvar gi;
    generate
        if (N == 0) begin : g_thru
            assign q = d;
        end else begin : g_st
            reg [CW-1:0] sc [0:N-1];
            for (gi = 0; gi < N; gi = gi + 1) begin : g_c
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) sc[gi] <= {CW{1'b0}}; else sc[gi] <= (gi == 0) ? d[CW-1:0] : sc[(gi == 0) ? 0 : gi - 1];
            end
            assign q[CW-1:0] = sc[N-1];
            if (W > CW) begin : g_d
                reg [W-CW-1:0] sd [0:N-1];
                for (gi = 0; gi < N; gi = gi + 1) begin : g_s
                    always @(posedge clk) sd[gi] <= (gi == 0) ? d[W-1:CW] : sd[(gi == 0) ? 0 : gi - 1];
                end
                assign q[W-1:CW] = sd[N-1];
            end
        end
    endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// the composition under test: S + 4 x (down relay, E, ot_hgi_dma_back NS 1 / NB 8, up relay).  In the die S sits in the
// cmdproc tile and each (E, engine) pair beside its cluster's local slice; this module only exists to bench / size them.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_grp #(
    parameter integer DHOPS = 10,         // relay stages a direction, spine <-> cluster engine
    parameter integer VCR = 8,
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               g_v,
    output wire               g_rdy,
    input  wire               g_last,
    input  wire [1:0]         g_q,
    input  wire [226:0]       g_mv,
    output wire               fence_quiet,
    output wire               done,
    output wire               fault,
    output wire [3:0]         e_src,       // (bench) the engines' source-consumed pulses
    output wire [3:0]         e_acc,       // (bench) the engines' accept edges
    output wire [4*129-1:0]   vr2q,
    input  wire [4*2065-1:0]  vr2r,
    output wire [4*2312-1:0]  wd,
    input  wire [4*8-1:0]     wd_cr,
    input  wire [4*4-1:0]     wa
);
    wire [4*228-1:0] dn, dn_e; wire [4*3-1:0] up, up_e;
    ot_hgi_b2_swap_disp #(.MUT(MUT)) u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy), .g_last(g_last), .g_q(g_q),
        .g_mv(g_mv), .dn(dn), .up(up), .fence_quiet(fence_quiet), .done(done), .fault(fault));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_c
        wire mv_v, mv_rdy, mv_src, mv_done, mv_fault, quiet; wire [226:0] mv;
        ot_hgi_b2_swap_relay #(.W(228), .CW(1), .N(DHOPS)) u_rd (.clk(clk), .rst_n(rst_n), .d(dn[gq*228 +: 228]), .q(dn_e[gq*228 +: 228]));
        ot_hgi_b2_swap_relay #(.W(3), .CW(3), .N(DHOPS)) u_ru (.clk(clk), .rst_n(rst_n), .d(up_e[gq*3 +: 3]), .q(up[gq*3 +: 3]));
        ot_hgi_b2_swap_ep u_e (.clk(clk), .rst_n(rst_n), .dn(dn_e[gq*228 +: 228]), .up(up_e[gq*3 +: 3]), .mv_v(mv_v), .mv_rdy(mv_rdy),
            .mv(mv), .mv_src(mv_src), .mv_fault(mv_fault), .quiet(quiet));
        ot_hgi_dma_back #(.NS(1), .STK(gq), .NB(8), .VCR(VCR)) u_b (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv),
            .mv_src(mv_src), .mv_done(mv_done), .mv_fault(mv_fault), .quiet(quiet), .vr2q(vr2q[gq*129 +: 129]),
            .vr2r(vr2r[gq*2065 +: 2065]), .wd(wd[gq*2312 +: 2312]), .wd_cr(wd_cr[gq*8 +: 8]), .wa(wa[gq*4 +: 4]));
        assign e_src[gq] = mv_src; assign e_acc[gq] = mv_v && mv_rdy;
    end endgenerate
endmodule
`default_nettype wire
