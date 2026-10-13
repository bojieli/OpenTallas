`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM B2 native MTP SWAP: the cmdproc-side RECORD -> BEAT adapter (el1013-ds-mtp-lead [mtp-rtl] 2026-10-13).
// Turns the sequencer's DMA records of a native DISPATCH GROUP into the beats {v, last, cluster 2, move 227} of
// ot_hgi_b2_swap_disp (S).  Glue of the cmdproc tile, beside S and ot_hgi_b2_disp: no inter-tile wire of its own (the
// record comes from the sequencer / cp_die record register, the cluster links are S's registered dn / up pins).
//
// PROGRAM ENCODING (log line "[mtp-rtl] ENCODING"): a group = consecutive ordinary DMA records (unit 8, STORE = swap-out,
//   LOAD = swap-in; operands A, O) marked in the UOP header param field (hdr [88:64], unused by DMA otherwise):
//     param[0] GRP   1 = member of a native dispatch group        param[1] GLAST 1 = last member: releases the group
//     param[24:2] = 0.   The cluster is NOT encoded: it is the EFFECTIVE HBM-side base bits [36:35] (the sequencer has
//   already added TOKEN x dyn_mul); base[39:37] must be 0 (no STRIPE4 code in a group).
// PINS: rec_v / the record enter an UNCONDITIONAL pin capture stage; the accept is decided one edge later from the
//   captured valid and the ready of that edge; rec_rdy is a flop of internal state only (it cannot see the record in the
//   capture stage nor the one being sent), so the capture stage feeds a 2-entry skid and ready needs the skid empty.
//   wr_quiet therefore falls two edges after a record's accept (the record is unretired until then: CTL.FENCE waits).
// PATH: record (sequencer handshake, one record a cycle at most) -> pin stage / skid -> the REAL ot_hgi_dma_record (pin flops, operand /
//   shape checks, the 227-b move word; LEGACY 0, POSTED 1) -> group checks on the registered move word -> beat into S.
//   One record is in the adapter at a time; a beat leaves 3 edges after its record was accepted and the next record is
//   accepted 3 edges later (6 cycles a member: the record adapter's handshake).
// RETIRE: one DMA retire a member when ITS engine reports the source consumed (STORE, posted) / the move done (LOAD):
//   the adapter queues S's up-link src pulses (its own pin flops of the same up pins) and returns one retire a cycle.
// ONE OWNER A RULE (2026-10-13: rec MUT 3 and MUT 6 survived because the adapter repeated two of S's rules, so neither
//   copy could be shown necessary).  S owns the engines and therefore owns
//     (a) "every released record's source is consumed and every HBM write acknowledged" = S.fence_quiet (its credit
//         count + the relayed engine quiet).  The adapter keeps NO outstanding-member count of its own: DMA.FENCE
//         (op 2, param 0) and wr_quiet (CTL.FENCE) are S.fence_quiet AND the adapter's own pipeline being empty --
//         its retire queue, the record in it, and the beat it handed to S in the last two edges (S's pin capture
//         stage: S.fence_quiet cannot fall earlier; that is this interface's latency, not a second count);
//     (b) "one record a cluster in a group" = S's sticky duplicate-cluster fault (S holds one record a cluster).  The
//         adapter forwards the beat and reports S's fault (s_fault) as the unit fault.
// FAULT (sticky; the unit refuses every later record; one ret_fault pulse): the adapter's OWN rules -- a record that
//   is not a group member or a fence, param[24:2] != 0, an op other than LOAD / STORE in a group, not exactly one HBM
//   side, the STRIPE4 code, members of different ops, the indexed stream form, a fence while a group is open (a dropped
//   GLAST), a fault of the record adapter -- and ANY FAULT OF S (a second record for a cluster in one group, an engine
//   fault).
// MUT (bench): 7 GLAST dropped on cluster 3's beat; 9 retire at the beat (before the source is consumed).  1 .. 5 are
//   S's (ot_hgi_b2_swap_disp); 6 is the composition's (ot_hgi_b2_swap_rgrp: S's fault report does not leave S).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_rec #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // the sequencer's DMA dispatch (effective descriptors)
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a,
    input  wire [255:0]  rec_o,
    input  wire [20:0]   rec_n_a,
    input  wire [20:0]   rec_n_o,
    output reg           ret_done,        // one pulse a retired record
    output reg           ret_fault,       // one pulse (the unit then stays halted)
    output reg           wr_quiet,        // nothing in the adapter, nothing outstanding, S fence-quiet
    output reg           fault,           // sticky
    // S (ot_hgi_b2_swap_disp), same tile
    output wire          g_v,
    input  wire          g_rdy,
    output wire          g_last,
    output wire [1:0]    g_q,
    output wire [226:0]  g_mv,
    input  wire [3:0]    up_src,          // the src bit of the four up links at S's pins (up[3 q])
    input  wire          s_quiet,         // S.fence_quiet
    input  wire          s_fault          // S.fault
);
    // ---------------------------------------------------------------- the record adapter (unchanged, HGI-1 unit 8)
    wire         r_rdy, r_done, r_fault, mv_v, is_v, fence_v;
    // ---------------------------------------------------------------- pin capture stage + 2-entry skid
    reg          p_v, rdy_q, rdy_d, swp, srp; reg [1:0] scnt;
    reg [681:0]  p_d; reg [681:0] sk [0:1];
    wire         spush = p_v && rdy_d;
    wire         sk_v = scnt != 2'd0 && !fault;
    wire [681:0] sk_h = sk[srp];
    wire         spop = sk_v && r_rdy;
    assign rec_rdy = rdy_q;
    wire [226:0] mv;
    wire         acc;                                   // the beat enters S at this edge
    wire         fence_rdy, quiet_core;
    // verilator lint_off UNUSEDSIGNAL
    wire         r_halted, r_quiet, lg_mv_rdy, lg_fence_rdy;   // record-adapter outputs with no use here: LEGACY 0, and
    wire [207:0] is_cmd;                                       // the stream form is refused before its command is read
    // verilator lint_on UNUSEDSIGNAL
    ot_hgi_dma_record #(.LEGACY(0), .POSTED(1), .B2(0)) u_rec (
        .clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(sk_v), .rec_rdy(r_rdy), .rec_hdr(sk_h[127:0]), .rec_a(sk_h[383:128]),
        .rec_o(sk_h[639:384]), .rec_n_a(sk_h[660:640]), .rec_n_o(sk_h[681:661]),
        .rec_pos1(21'd0), .rec_ilist(32'd0),            // KVWB_DS / the indexed stream are not group members (fault below)
        .rec_done(r_done), .rec_fault(r_fault), .halted(r_halted), .wr_quiet(r_quiet),
        .lg_mv_v(1'b0), .lg_mv_rdy(lg_mv_rdy), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(lg_fence_rdy),
        .mv_v(mv_v), .mv_rdy(acc), .mv(mv), .mv_done(acc), .mv_fault(1'b0),
        .mv_src(acc), .mv_pdone(acc), .mv_fdone(1'b0),   // the member is handed to S: its true completion is counted below
        .is_v(is_v), .is_rdy(1'b0), .is_cmd(is_cmd),
        .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(quiet_core));
    // ---------------------------------------------------------------- the header bits of the record in the adapter
    reg [30:0] hp, cur; reg acc_q, inrec;               // {op 6, param 25}: pin flops, then the record's copy
    wire [5:0]  op  = cur[30:25];
    wire [24:0] par = cur[24:0];
    // ---------------------------------------------------------------- group checks on the registered move word
    reg open; reg [5:0] gop;                            // a group is open (a member sent, no GLAST yet); its op
    wire        hs_s = mv[1:0] == 2'd0, hs_d = mv[94:93] == 2'd0;
    wire [4:0]  hb = hs_s ? mv[44:40] : mv[137:133];    // the HBM-side effective base [39:35]
    wire [1:0]  q = hb[1:0];
    wire        bad = !par[0] || par[24:2] != 23'd0 || op[5:1] != 5'd0 || !(hs_s ^ hs_d) || hb[4:2] != 3'd0 ||
                      (open && op != gop);
    assign g_v    = mv_v && !bad && !fault;
    assign g_last = (MUT == 7 && q == 2'd3) ? 1'b0 : par[1];
    assign g_q    = q;
    assign g_mv   = mv;
    assign acc    = g_v && g_rdy;
    assign fence_rdy = !open && par == 25'd0 && !fault;
    // ---------------------------------------------------------------- outstanding members, retires, quiet
    reg [3:0] src_q; reg [3:0] pend;                    // src pulses not yet returned as retires (<= 8 credits + 4)
    reg acc_d1, acc_d2;                                 // a beat entered S's pin stage 1 / 2 edges ago
    wire [2:0] nsrc = {2'd0, src_q[0]} + {2'd0, src_q[1]} + {2'd0, src_q[2]} + {2'd0, src_q[3]};
    assign quiet_core = s_quiet && !acc_d1 && !acc_d2 && pend == 4'd0;
    wire viol = (mv_v && bad) || is_v || (fence_v && (open || par != 25'd0)) || s_fault || r_fault;
    always @(posedge clk) begin
        p_d <= {rec_n_o, rec_n_a, rec_o, rec_a, rec_hdr};
        if (spush) sk[swp] <= p_d;
        hp <= {sk_h[123:118], sk_h[88:64]};
        if (acc_q) cur <= hp;
        if (acc) gop <= op;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p_v <= 1'b0; rdy_q <= 1'b0; rdy_d <= 1'b0; swp <= 1'b0; srp <= 1'b0; scnt <= 2'd0;
            acc_q <= 1'b0; inrec <= 1'b0; open <= 1'b0; src_q <= 4'd0; pend <= 4'd0;
            acc_d1 <= 1'b0; acc_d2 <= 1'b0;
            ret_done <= 1'b0; ret_fault <= 1'b0; wr_quiet <= 1'b0; fault <= 1'b0;
        end else begin
            p_v <= rec_v; rdy_d <= rdy_q;
            if (spush) swp <= ~swp;
            if (spop) srp <= ~srp;
            scnt <= scnt + {1'b0, spush} - {1'b0, spop};
            rdy_q <= (scnt + {1'b0, spush} - {1'b0, spop}) == 2'd0 && !fault;
            acc_q <= spop;
            if (spop) inrec <= 1'b1; else if (r_done || fault) inrec <= 1'b0;
            if (acc) open <= !par[1];
            acc_d1 <= acc; acc_d2 <= acc_d1;
            src_q <= up_src;
            pend  <= pend + {1'b0, nsrc} - {3'd0, pend != 4'd0};
            ret_done  <= (MUT == 9) ? r_done : ((pend != 4'd0) || (r_done && op == 6'd2));
            ret_fault <= viol && !fault;
            if (viol) fault <= 1'b1;
            wr_quiet <= quiet_core && !inrec && !p_v && scnt == 2'd0 && !fault;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// the composition under test: the record adapter + S + 4 x (down relay, E, ot_hgi_dma_back NS 1 / NB 8, up relay).
// In the die the adapter and S sit in the cmdproc tile; each (E, engine) pair beside its cluster's local slice.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_swap_rgrp #(
    parameter integer DHOPS = 10,
    parameter integer VCR = 8,
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               rec_v,
    output wire               rec_rdy,
    input  wire [127:0]       rec_hdr,
    input  wire [255:0]       rec_a,
    input  wire [255:0]       rec_o,
    input  wire [20:0]        rec_n_a,
    input  wire [20:0]        rec_n_o,
    output wire               ret_done,
    output wire               ret_fault,
    output wire               wr_quiet,
    output wire               fault,
    output wire               s_done,      // (bench) S's completed-release pulse
    output wire               s_fault_o,   // (bench) S's own sticky fault
    output wire [3:0]         e_src,       // (bench) the engines' source-consumed pulses
    output wire [3:0]         e_acc,       // (bench) the engines' accept edges
    output wire [4*129-1:0]   vr2q,
    input  wire [4*2065-1:0]  vr2r,
    output wire [4*2312-1:0]  wd,
    input  wire [4*8-1:0]     wd_cr,
    input  wire [4*4-1:0]     wa
);
    wire g_v, g_rdy, g_last, s_quiet; wire [1:0] g_q; wire [226:0] g_mv;
    // MUT 6: S's fault report does not leave S.  For a duplicate cluster this is S's own check removed, as seen from
    // outside S (S stalls on the held cluster either way; only its sticky fault tells the unit) -- the adapter has no
    // check of its own that could cover for it.
    wire s_fault = (MUT == 6) ? 1'b0 : s_fault_o;
    wire [4*228-1:0] dn, dn_e; wire [4*3-1:0] up, up_e;
    ot_hgi_b2_swap_rec #(.MUT(MUT)) u_r (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr),
        .rec_a(rec_a), .rec_o(rec_o), .rec_n_a(rec_n_a), .rec_n_o(rec_n_o), .ret_done(ret_done), .ret_fault(ret_fault),
        .wr_quiet(wr_quiet), .fault(fault), .g_v(g_v), .g_rdy(g_rdy), .g_last(g_last), .g_q(g_q), .g_mv(g_mv),
        .up_src({up[9], up[6], up[3], up[0]}), .s_quiet(s_quiet), .s_fault(s_fault));
    ot_hgi_b2_swap_disp #(.MUT(MUT)) u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_rdy(g_rdy), .g_last(g_last), .g_q(g_q),
        .g_mv(g_mv), .dn(dn), .up(up), .fence_quiet(s_quiet), .done(s_done), .fault(s_fault_o));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_c
        wire mv_v, mv_rdy, mv_src, mv_fault, quiet; wire [226:0] mv;
        // verilator lint_off UNUSEDSIGNAL
        wire mv_done;                                    // the posted engine's done: the group waits on src + quiet
        // verilator lint_on UNUSEDSIGNAL
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
