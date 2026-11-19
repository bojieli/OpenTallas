`timescale 1ns/1ps
// Reference for unit/test/run_mu_hwin_eq.sh: dsdv_mu_hwin exactly as on main before FABLE-FIX-S81-SEQHOST (2026-11-19),
// file sha256 fe83722aed98 lines 30..168, only the module name changed.  Not bound, not synthesised.
module dsdv_mu_hwin_ref_1119 #(parameter integer NSLOT = 47, parameter integer NEV = 8, parameter integer NEP = 4,
                      parameter integer NRT = 2, parameter integer MUT = 0) (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [52:0]       f_ks,            // tap of the unit start pin {start, user 10, tok 21, pos 21}
    input  wire [25:0]       f_mc,            // hslot boot words {v, sel, d 24} (S / RL)
    input  wire [25:0]       f_mw,            // window boot words {v, 0, d 24}
    output wire [NEP*34-1:0] mu_c,            // per end slice: TX tag window {pos 21, user 10, land, ab, v}
    output wire [NEP*11-1:0] mu_rc,           // per end slice: landing replay {user 10, v}
    input  wire [NRT*32-1:0] mu_rt,           // per returning end slice: RX tag {v, user 10, pos 21}
    output reg  [1:0]        t_wf             // sticky faults
);
    localparam integer SI = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer SJ = SI + 1;
    localparam integer EI = (NEV > 1) ? $clog2(NEV) : 1;
    localparam integer PI = (NEP > 1) ? $clog2(NEP) : 1;
`ifndef SYNTHESIS
    initial if (NSLOT < 2 || NSLOT > 1023 || NEV < 1 || NEV > 32) $fatal(1, "dsdv_mu_hwin_ref_1119: NSLOT 2..1023, NEV 1..32");
`endif
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // ---- pin flops (valid bits gated by the relayed reset, payload not)
    reg [52:0] ks_q; reg [25:0] mc_q, mw_q; reg [NRT*32-1:0] rt_q; integer r;
    always @(posedge ck) begin
        ks_q <= {rn & f_ks[52], f_ks[51:0]}; mc_q <= {rn & f_mc[25], f_mc[24:0]}; mw_q <= {rn & f_mw[25], f_mw[24:0]};
        rt_q <= mu_rt;
        for (r = 0; r < NRT; r = r + 1) rt_q[32*r + 31] <= rn & mu_rt[32*r + 31];
    end
    wire st = ks_q[52]; wire [9:0] su = ks_q[51:42]; wire [20:0] sp = ks_q[20:0];
    // ---- start table: the same record rule / slot timer / due edge as dsdv_mu_hslot
    reg [23:0] cs, crl; reg [31:0] tm; reg armed; reg [23:0] ph; reg [SI-1:0] sl, rp;
    // MU-S81-2/SEQ (10-19): slot gap table, the same as dsdv_mu_hslot's (same f_mc words, same walk).  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.
    reg [23:0] gt [0:NSLOT-1]; reg [SI:0] gn; reg [SI-1:0] gx, lw; reg [23:0] cg, ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; reg [31:0] ts [0:NSLOT-1];
    wire [SI-1:0] ss = armed ? sl : {SI{1'b0}};
    wire on_cal = !armed || ph == 24'd0;
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == su) udup = 1'b1; end
    wire col = vld[ss];
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use (= calendar slots per period)
    wire hcfg_bad = gn == 0 || cs < nw || crl <= nw;                     // hslot's own arming rule
    wire rec = st && on_cal && !col && !udup && !(!armed && hcfg_bad);
    wire due = vld[rp] && ts[rp] + {8'd0, crl} - 32'd1 == tm;             // hslot's return edge: the entry retires
    function automatic [SI-1:0] nxt(input [SI-1:0] p);
        nxt = (p == lw) ? {SI{1'b0}} : p + 1'b1;
    endfunction
    wire [SI-1:0] gxn = (MUT == 5 || {1'b0, gx} == gn - 1'b1) ? {SI{1'b0}} : gx + 1'b1;   // MUT 5: gap table index stuck at 0
    always @(posedge ck) ng <= gt[gx] - 24'd1;          // next slot's gap, prefetched (gx = the slot after the current one)
    always @(posedge ck) if (mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)) gt[gn[SI-1:0]] <= mc_q[23:0];
    // ---- event rows
    reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1]; reg [EI-1:0] esel;
    reg [1:0] eat [0:NEV-1][0:NSLOT-1];                  // {land / replay-en, ab} per event and calendar slot
    reg [NSLOT-1:0] fd [0:NEV-1];                         // fired flags
    reg [SI-1:0] pe [0:NEV-1];
    integer e, p;
    reg bad_d; reg [NEV-1:0] fire, lt;
    always @* begin
        bad_d = cs <= nw + 24'd1;
        for (e = 0; e < NEV; e = e + 1)
            if ({3'd0, eD[e]} < nw + 24'd2 || {3'd0, eD[e]} + 24'd2 > crl) bad_d = 1'b1;
        for (e = 0; e < NEV; e = e + 1) begin
            fire[e] = vld[pe[e]] && !fd[e][pe[e]] && ts[pe[e]] + {11'd0, eD[e]} == tm;
            lt[e] = vld[pe[e]] && !fd[e][pe[e]] && (ts[pe[e]] + {11'd0, eD[e]} - tm) > 32'h7fffffff;
        end
    end
    reg rtbad, m; reg [NEP*34-1:0] c_n, c_q; reg [NEP*11-1:0] rc_n, rc_q; reg col_w;
    assign mu_c = c_q; assign mu_rc = rc_q;
    always @* begin
        rtbad = 1'b0;
        for (r = 0; r < NRT; r = r + 1) begin
            m = 1'b0;
            for (p = 0; p < NSLOT; p = p + 1)
                if (vld[p] && eu[p] == rt_q[32*r + 21 +: 10] && ep[p] == rt_q[32*r +: 21]) m = 1'b1;
            if (rt_q[32*r + 31] && !m) rtbad = 1'b1;
        end
        c_n = {NEP*34{1'b0}}; rc_n = {NEP*11{1'b0}}; col_w = 1'b0;
        for (e = 0; e < NEV; e = e + 1) if (fire[e]) begin
            if (!ek[e]) begin
                if (c_n[34*eep[e]]) col_w = 1'b1;
                c_n[34*eep[e] +: 34] = {ep[pe[e]], eu[pe[e]], eat[e][pe[e]][1], (MUT == 3) ? 1'b0 : eat[e][pe[e]][0], 1'b1};
            end else if (eat[e][pe[e]][1] || MUT == 4) begin
                if (rc_n[11*eep[e]]) col_w = 1'b1;
                rc_n[11*eep[e] +: 11] = {eu[pe[e]], 1'b1};
            end
        end
    end
    wire wv = mw_q[25];
    wire idle = !armed && !(|vld);
    // event-row config + entry payload (no reset: written before arming / at the start that sets vld)
    always @(posedge ck) begin
        if (rec) begin eu[ss] <= su; ep[ss] <= sp; ts[ss] <= tm; end
        if (wv && idle)
            case (mw_q[22:21])
                2'd0: begin esel <= mw_q[EI-1:0]; ek[mw_q[EI-1:0]] <= mw_q[8]; eep[mw_q[EI-1:0]] <= mw_q[9 +: PI]; end
                2'd1: eD[esel] <= mw_q[20:0];
                2'd2: eat[esel][mw_q[SI-1:0]] <= mw_q[11:10];
                default: ;
            endcase
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin
            tm <= 32'd0; armed <= 1'b0; ph <= 24'd0; sl <= {SI{1'b0}}; rp <= {SI{1'b0}}; vld <= {NSLOT{1'b0}};
            cs <= 24'd0; crl <= 24'd0; t_wf <= 2'd0; gn <= {SJ{1'b0}}; gx <= {SI{1'b0}}; lw <= SI'(NSLOT - 1); cg <= 24'd0; c_q <= {NEP*34{1'b0}}; rc_q <= {NEP*11{1'b0}};
            for (e = 0; e < NEV; e = e + 1) begin pe[e] <= {SI{1'b0}}; fd[e] <= {NSLOT{1'b0}}; end
        end else begin
            tm <= tm + 32'd1;
            if (mc_q[25] && idle) begin if (mc_q[24]) crl <= mc_q[23:0]; else begin
                    if (gn != SJ'(NSLOT)) begin
                        gn <= gn + 1'b1;
                        if (gn == 0 || mc_q[23:0] < cs) cs <= mc_q[23:0];
                        lw <= (gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0];             // nw = n for n >= 2
                    end
                end end
            if (armed) begin
                if (ph == cg) begin ph <= 24'd0; sl <= nxt(sl); cg <= ng; gx <= gxn; end else ph <= ph + 24'd1;
            end
            if (st && !armed) begin
                if (bad_d) t_wf[1] <= 1'b1;
                if (!hcfg_bad) begin armed <= 1'b1; ph <= 24'd1; cg <= ng; gx <= gxn; end
            end
            if (due) begin vld[rp] <= 1'b0; rp <= nxt(rp); end
            else if (!vld[rp] && !(rec && ss == rp)) rp <= nxt(rp);
            if (rec) vld[ss] <= 1'b1;
            c_q <= c_n; rc_q <= rc_n;
            for (e = 0; e < NEV; e = e + 1) begin
                if (rec) fd[e][ss] <= 1'b0;
                if (fire[e]) begin fd[e][pe[e]] <= 1'b1; pe[e] <= nxt(pe[e]); end
                else if ((!vld[pe[e]] || fd[e][pe[e]]) && !(rec && ss == pe[e])) pe[e] <= nxt(pe[e]);
            end
            if (rtbad || (|lt)) t_wf[0] <= 1'b1;
            if ((wv && (!idle || mw_q[22:21] == 2'd3)) || col_w) t_wf[1] <= 1'b1;
        end
endmodule

