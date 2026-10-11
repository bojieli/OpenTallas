`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: HBM pseudo-channel service of the hierarchical scan-service slab (successor of
// ot_s81_svcq_pcarb, which picked ALL 14 sources for ALL 32 PCs in one combinational cycle).  Instantiated per PC
// (NP 1, PC0 = local index) in the hardened slice dsfd_svch_pcs, 8 per dsfd_svc_quad (PCs 8 QID .. 8 QID + 7), each
// above its abutted dsfd_svc_pc tile.
// PC side = the ctrl contract, unchanged: rq 341 b {[340:85] wdata, [84:53] wstrb, [52:36] tag 17, [35:32] len,
// [31:2] sector, [1] we, [0] v} launched from a flop, DQ request credits per PC returned on rk pulses, VALID-ONLY
// responses {rv, r_beat, r_tag, r_data}, untagged write completions wd (in order per PC).
// Requesters (per PC, each its own queue -> registered CANDIDATE register):
//   A  index reader lane   (dsfd_svc_idx, per-PC credit lane)  reads, 16-b tag  -> rq tag {0, tag16}
//   B  window stream lane  (Q2 home, per-PC credit lane)       reads, 12-b tag  -> rq tag {1, 4'd0, tag12}
//   G  routed lane         (Q2 home, ONE lane per quadrant, pc decoded at the home): reads and one-sector masked
//                          writes of the window K ports / owned-row fetch -> rq tag {1, port + 1, tag12}
// Pipeline per PC: stage R = the candidate registers (a queue head is loaded into its candidate only when the
// candidate is empty or granted); stage G = 3-way round robin over the REGISTERED candidates (no live upstream
// valid enters the grant) gated by a held credit and, for a read, a LANDING RESERVATION, whose result is the rq
// flop itself.  Landing: A / B responses go straight out on their lane (valid-only, one flop) into the client's
// landing FIFO (DRA / DRB beats) whose pops return as credit pulses; G responses land in a local per-PC FIFO (DRG
// beats) drained by a registered 8-way round robin onto the G response lane.  A read issues only when resv + len <=
// depth, so no landing FIFO can overflow although the PC side has no back-pressure.  Writes: a per-PC FIFO of writer
// ports retires on wd; completions leave as one pulse per port per cycle (counters).
// Faults (sticky): G landing overflow, wd with no write outstanding, credit overflow, G request for a PC of another
// quadrant, response tag of no client, writer FIFO overflow.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_pcsvc #(
    parameter integer QID = 0,
    parameter integer NP = 8,
    parameter integer PC0 = 0,           // local index (0..7) of this instance's first PC (per-PC slices: NP 1)
    parameter integer NG = 13,
    parameter integer DQ = 8,
    parameter integer DRA = 64,
    parameter integer DRB = 64,
    parameter integer DRG = 16,
    parameter integer AW = 30
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // A requests {len 4, addr 30, tag 16} / responses {tag 16, beat 4, data 256} + landing credits
    input  wire [NP-1:0]        a_v,
    output wire [NP-1:0]        a_r,
    input  wire [NP*50-1:0]     a_d,
    output reg  [NP-1:0]        ar_v,
    output reg  [NP*276-1:0]    ar_d,
    input  wire [NP-1:0]        ar_c,
    // B requests {len 4, addr 30, tag 12} / responses {tag 12, beat 4, data 256} + landing credits
    input  wire [NP-1:0]        b_v,
    output wire [NP-1:0]        b_r,
    input  wire [NP*46-1:0]     b_d,
    output reg  [NP-1:0]        br_v,
    output reg  [NP*272-1:0]    br_d,
    input  wire [NP-1:0]        br_c,
    // G requests {pc 5, port 4, we, len 4, addr 30, tag 12, wstrb 32, wdata 256} (344 b)
    input  wire                 g_v,
    output wire                 g_r,
    input  wire [343:0]         g_d,
    // G responses {port 4, tag 12, beat 4, data 256} (276 b), write completions (one pulse per port per cycle)
    output reg                  go_v,
    input  wire                 go_r,
    output reg  [275:0]         go_d,
    output reg  [NG-1:0]        gwd,
    // PC side
    output wire [NP*341-1:0]    rq,
    input  wire [NP-1:0]        rk,
    input  wire [NP-1:0]        rv,
    input  wire [NP*17-1:0]     r_tag,
    input  wire [NP*4-1:0]      r_beat,
    input  wire [NP*256-1:0]    r_data,
    input  wire [NP-1:0]        wd,
    output reg                  fault,
    output reg  [7:0]           fault_code
);
    localparam integer CW = $clog2(DQ + 1);
    localparam integer RA = $clog2(DRA + 1), RB = $clog2(DRB + 1), RG = $clog2(DRG + 1);
    localparam integer GA = (DRG > 1) ? $clog2(DRG) : 1;
    localparam integer WQ = 2 * DQ, WA = $clog2(WQ);
    localparam integer LW = (NP > 1) ? $clog2(NP) : 1;
    genvar gp;
    integer p, k, s;

    // ---------------- stage R: candidate registers ----------------
    reg [NP-1:0] ca_v, cb_v, cg_v;
    reg [49:0]  ca_d [0:NP-1];
    reg [45:0]  cb_d [0:NP-1];
    reg [338:0] cg_d [0:NP-1];       // {port 4, we, len 4, addr 30, tag 12, wstrb 32, wdata 256}
    reg [NP-1:0] ga, gb, gg;         // grants this cycle (from registered candidates)
    wire [2:0] g_lpc = g_d[341:339];
    wire [LW-1:0] g_pc = LW'(32'(g_lpc) - PC0);
    wire g_mine = g_d[343:342] == 2'(QID) && 32'(g_lpc) >= PC0 && 32'(g_lpc) < PC0 + NP;
    assign a_r = ~ca_v | ga;
    assign b_r = ~cb_v | gb;
    assign g_r = !g_mine || !cg_v[g_pc] || gg[g_pc];

    // ---------------- stage G: per-PC 3-way round robin over the candidates ----------------
    reg [CW-1:0] cred [0:NP-1];
    reg [RA-1:0] resa [0:NP-1];
    reg [RB-1:0] resb [0:NP-1];
    reg [RG-1:0] resg [0:NP-1];
    reg [1:0] rr [0:NP-1];
    reg [NP-1:0] gpop;               // G landing pops (egress)
    reg [WA:0] wqn [0:NP-1];
    always @(*) begin : b1
        integer p, k, s;
        for (p = 0; p < NP; p = p + 1) begin
            reg ea, eb, eg; reg [2:0] e; reg [1:0] pick; reg fnd;
            ea = ca_v[p] && 32'(resa[p]) + 32'(ca_d[p][49:46]) <= DRA;
            eb = cb_v[p] && 32'(resb[p]) + 32'(cb_d[p][45:42]) <= DRB;
            eg = cg_v[p] && (cg_d[p][334] ? 32'(wqn[p]) < WQ : 32'(resg[p]) + 32'(cg_d[p][333:330]) <= DRG);
            e = {eg, eb, ea};
            fnd = 1'b0; pick = 2'd0;
            for (s = 0; s < 3; s = s + 1)
                if (!fnd && e[(32'(rr[p]) + s) % 3]) begin fnd = 1'b1; pick = 2'((32'(rr[p]) + s) % 3); end
            if (cred[p] == 0) fnd = 1'b0;
            ga[p] = fnd && pick == 2'd0;
            gb[p] = fnd && pick == 2'd1;
            gg[p] = fnd && pick == 2'd2;
        end
    end

    // ---------------- G landing FIFOs (per PC) ----------------
    reg [275:0] lg [0:NP-1][0:DRG-1];
    reg [GA-1:0] lgw [0:NP-1], lgr [0:NP-1];
    reg [GA:0] lgn [0:NP-1];
    reg [LW-1:0] grr;
    // ---------------- writer FIFOs ----------------
    reg [3:0] wq [0:NP-1][0:WQ-1];
    reg [WA-1:0] wqw [0:NP-1], wqr [0:NP-1];
    reg [NP-1:0] wd_q; reg [3:0] wd_port [0:NP-1];
    reg [4:0] wdc [0:NG-1];

    reg [NP-1:0] rqv; reg [340:1] rqd [0:NP-1];
    genvar gq;
    generate for (gq = 0; gq < NP; gq = gq + 1) begin : g_rq
        assign rq[gq*341 +: 341] = {rqd[gq], rqv[gq]};
    end endgenerate
    // issue word per PC (combinational from the registered candidates and this cycle's grant)
    reg [340:1] iw [0:NP-1];
    reg [NP-1:0] iwe;
    always @(*) begin : b2
        integer p, k, s;
        for (p = 0; p < NP; p = p + 1) begin
            iw[p] = '0; iwe[p] = 1'b0;
            if (ga[p]) begin iw[p][52:36] = {1'b0, ca_d[p][15:0]}; iw[p][31:2] = ca_d[p][45:16]; iw[p][35:32] = ca_d[p][49:46]; end
`ifdef SVCQS_MUT_BTAG
            if (gb[p]) begin iw[p][52:36] = {1'b1, 4'd1, cb_d[p][11:0]}; iw[p][31:2] = cb_d[p][41:12]; iw[p][35:32] = cb_d[p][45:42]; end
`else
            if (gb[p]) begin iw[p][52:36] = {1'b1, 4'd0, cb_d[p][11:0]}; iw[p][31:2] = cb_d[p][41:12]; iw[p][35:32] = cb_d[p][45:42]; end
`endif
            if (gg[p]) begin
                iwe[p] = cg_d[p][334];
                iw[p][52:36] = {1'b1, cg_d[p][338:335] + 4'd1, cg_d[p][299:288]}; iw[p][31:2] = cg_d[p][329:300];
                iw[p][35:32] = cg_d[p][334] ? 4'd1 : cg_d[p][333:330];
                iw[p][84:53] = cg_d[p][287:256]; iw[p][340:85] = cg_d[p][255:0];
            end
            iw[p][1] = iwe[p];
        end
    end
    reg [NP-1:0] lpush;
    always @(*) begin : b3
        integer p;
        for (p = 0; p < NP; p = p + 1) lpush[p] = rv[p] && r_tag[p*17 + 16] && r_tag[p*17 + 12 +: 4] != 4'd0;
    end
    // G egress pick (registered round robin over the landing heads): shared by the pop and the data load
    reg f3; reg [LW-1:0] q3;
    always @(*) begin : b4
        integer p, k, s;
        gpop = 0; f3 = 1'b0; q3 = 0;
        if (!go_v || go_r)
            for (s = 0; s < NP; s = s + 1)
                if (!f3 && lgn[(32'(grr) + s) % NP] != 0) begin f3 = 1'b1; q3 = LW'((32'(grr) + s) % NP); end
        if (f3) gpop[q3] = 1'b1;
    end
    // ---- datapath registers: no reset ----
    always @(posedge clk) begin : b5
        integer p, k, s;
        for (p = 0; p < NP; p = p + 1) begin
            if (a_v[p] && a_r[p]) ca_d[p] <= a_d[p*50 +: 50];
            if (b_v[p] && b_r[p]) cb_d[p] <= b_d[p*46 +: 46];
            if (g_v && g_r && g_mine && 32'(g_pc) == p) cg_d[p] <= g_d[338:0];
            rqd[p] <= iw[p];
            if (gg[p] && iwe[p]) wq[p][wqw[p]] <= cg_d[p][338:335];
            ar_d[p*276 +: 276] <= {r_tag[p*17 +: 16], r_beat[p*4 +: 4], r_data[p*256 +: 256]};
            br_d[p*272 +: 272] <= {r_tag[p*17 +: 12], r_beat[p*4 +: 4], r_data[p*256 +: 256]};
            if (lpush[p]) lg[p][lgw[p]] <= {r_tag[p*17 + 12 +: 4] - 4'd1, r_tag[p*17 +: 12], r_beat[p*4 +: 4], r_data[p*256 +: 256]};
            wd_port[p] <= wq[p][wqr[p]];
        end
        if (f3) go_d <= lg[q3][lgr[q3]];
    end
    // ---- write completions per port this cycle (combinational from registered wd_q / wd_port) ----
    reg [3:0] waddv [0:NG-1];
    always @(*) begin : b6
        integer k, s;
        for (k = 0; k < NG; k = k + 1) begin
            waddv[k] = 0;
            for (s = 0; s < NP; s = s + 1) if (wd_q[s] && 32'(wd_port[s]) == k) waddv[k] = waddv[k] + 1'b1;
        end
    end
    // ---- control registers: async reset ----
    always @(posedge clk or negedge rst_n) begin : b7
        integer p, k, s;
        if (!rst_n) begin
            ca_v <= 0; cb_v <= 0; cg_v <= 0; ar_v <= 0; br_v <= 0; go_v <= 1'b0; gwd <= 0; wd_q <= 0; grr <= 0;
            fault <= 1'b0; fault_code <= 0;
            for (p = 0; p < NP; p = p + 1) begin
                cred[p] <= CW'(DQ); resa[p] <= 0; resb[p] <= 0; resg[p] <= 0; rr[p] <= 0; rqv[p] <= 1'b0;
                lgw[p] <= 0; lgr[p] <= 0; lgn[p] <= 0; wqw[p] <= 0; wqr[p] <= 0; wqn[p] <= 0;
            end
            for (k = 0; k < NG; k = k + 1) wdc[k] <= 0;
        end else begin
            for (p = 0; p < NP; p = p + 1) begin
                if (a_v[p] && a_r[p]) ca_v[p] <= 1'b1; else if (ga[p]) ca_v[p] <= 1'b0;
                if (b_v[p] && b_r[p]) cb_v[p] <= 1'b1; else if (gb[p]) cb_v[p] <= 1'b0;
                if (g_v && g_r && g_mine && 32'(g_pc) == p) cg_v[p] <= 1'b1; else if (gg[p]) cg_v[p] <= 1'b0;
            end
            if (g_v && !g_mine) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
            for (p = 0; p < NP; p = p + 1) begin
                rqv[p] <= ga[p] | gb[p] | gg[p];
                if (ga[p]) rr[p] <= 2'd1;
                if (gb[p]) rr[p] <= 2'd2;
                if (gg[p]) rr[p] <= 2'd0;
                if (gg[p] && iwe[p]) wqw[p] <= wqw[p] + 1'b1;
                cred[p] <= cred[p] - CW'(ga[p] | gb[p] | gg[p]) + CW'(rk[p]);
                if (rk[p] && !(ga[p] | gb[p] | gg[p]) && cred[p] == CW'(DQ)) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
                resa[p] <= resa[p] + (ga[p] ? RA'(ca_d[p][49:46]) : '0) - RA'(ar_c[p]);
                resb[p] <= resb[p] + (gb[p] ? RB'(cb_d[p][45:42]) : '0) - RB'(br_c[p]);
                resg[p] <= resg[p] + ((gg[p] && !iwe[p]) ? RG'(cg_d[p][333:330]) : '0) - RG'(gpop[p]);
                ar_v[p] <= rv[p] && !r_tag[p*17 + 16];
                br_v[p] <= rv[p] && r_tag[p*17 + 16] && r_tag[p*17 + 12 +: 4] == 4'd0;
                if (lpush[p]) begin
                    if (32'(r_tag[p*17 + 12 +: 4]) > NG) begin fault <= 1'b1; fault_code[4] <= 1'b1; end
                    if (32'(lgn[p]) >= DRG && !gpop[p]) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
                    lgw[p] <= (32'(lgw[p]) == DRG - 1) ? '0 : lgw[p] + 1'b1;
                end
                lgn[p] <= lgn[p] + (GA+1)'(lpush[p]) - (GA+1)'(gpop[p]);
                if (gpop[p]) lgr[p] <= (32'(lgr[p]) == DRG - 1) ? '0 : lgr[p] + 1'b1;
                wd_q[p] <= wd[p] && wqn[p] != 0;
                if (wd[p]) begin
                    if (wqn[p] == 0) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
                    else wqr[p] <= wqr[p] + 1'b1;
                end
                wqn[p] <= wqn[p] + (WA+1)'(gg[p] && iwe[p]) - (WA+1)'(wd[p] && wqn[p] != 0);
                if (gg[p] && iwe[p] && 32'(wqn[p]) >= WQ) begin fault <= 1'b1; fault_code[5] <= 1'b1; end
            end
            if (go_v && go_r) go_v <= 1'b0;
            if (f3) begin go_v <= 1'b1; grr <= q3 + 1'b1; end
            for (k = 0; k < NG; k = k + 1) begin
                gwd[k] <= (wdc[k] != 0) || (waddv[k] != 0);
                wdc[k] <= wdc[k] + 5'(waddv[k]) - 5'((wdc[k] != 0) || (waddv[k] != 0));
            end
        end
    end
endmodule
