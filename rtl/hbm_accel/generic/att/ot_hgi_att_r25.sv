`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// R25 ATT CONTROLLER (hgi-1010/att 2026-10-11, lead-approved P1-P3): runs HGI ATT.QK / ATT.PV records (unit 5, the
// ot_hgi_att_unit record interface) on the die's real attention: the hfd_attn_half_lo / _hi tiles (KVIB = 1) fed by
// svc PS rows through one ot_hgi_att_stager per active entry.  Exact against hgi_sim machine.u_att_qk / u_att_pv.
//
// DATAFLOW (one stack, NA active entries = the inner pair of tile rows 0 .. NA-1, svc groups 2a = PCs 8a .. 8a+3):
//   tile: out[slot] = csum4x8_k(A[bank][slot][k] (BF16, ld) x deq(B[k]) (ib)), 16 slots, 5 banks, k < 32.
//   rows: T = n_B + n_C rows of hd FP8 elements in LIST order, laid out by the compiler (--attps) in the stack's ATT
//     region (B.base, 1 MiB aligned) as BLOCKS of 32 row-words (32 rows x one 32-dim slice, tile-native, see the
//     stager); NB = ceil(T / 32) row blocks padded to NBp = 2^k, RB = max(1, NBp / NA) blocks a RUN, entry a owns run a
//     (blocks [a RB, (a+1) RB), zero-filled past T) as local blocks lb = beta_l x S + s (S = hd / 32 slices).
//   QK: q[h] slice s -> bank s >> lgG, slot (s mod G) Lp + h (G = 16 / Lp slices a bank, Lp = lanes rounded to 2^k),
//     q-mode ld words, loaded once.  Beat r of block (beta, s) = row 32 beta + r, slice s; the slot's 32-dim node of
//     the score; the S nodes of a row merge in-entry by the binary counter (padded to 2^k: the golden's pairwise of
//     64-slices == csum8 over hd) -> O[h][t].
//   PV: p[h][32 rows of block beta] -> slot a Lp + h of bank beta_l mod 5 (q-mode words, one per lane, reloaded per
//     block after the bank's previous block's results all landed); the stager transposes, beat d of block (beta, s) =
//     dim 32 s + d over the block's 32 rows.  Nodes beta of (h, d) merge in-entry by the binary counter (RB nodes, an
//     aligned subtree), then the NA run roots by the pairwise tree (the golden's csum8 over positions: 32-row blocks =
//     4 chunks, aligned nodes) -> O[h][d].
//   ld words reach the tiles on the corner's q port; a block TOKEN to the entry's stager follows LDLAT cycles after
//   its last ld word (the ld path's longest latency), so a beat never reads a bank before its load.
// PORTS: record (as ot_hgi_att_unit); VM lgE client 1 (read group: rg_req / rg_gnt, rq 32 x {v, sector 15}, rq_cr,
//   rr 32 x {v, data 256}; write group: wg_req / wg_gnt, wq 32 x {v, sector 15, data 256, mask 8}, wq_cr, wq_done);
//   tq = the corner tile's q port (the ld word in [525:0]); e2 = t_hgi_e2<st> {fclk, e[127:0]} (g3's format); kd;
//   bt = block tokens a stager; ro = the row-end result words {v, oy 512, oflt 16} of the NA tile rows.
// Mutants: OT_ATT_R25_MUT_KQORD (QK nodes merged in reverse slice order -> wrong tree).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_att_r25_add #(parameter integer N = 1) (     // N lanes of the golden's binary32 add, latency 3
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [N*32-1:0] a,
    input  wire [N*32-1:0] b,
    output wire [N*32-1:0] y,
    output wire          e
);
    wire [N-1:0] ee;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_l
        wire [1:0] er; wire vo;
        ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a[g*32 +: 32]), .b(b[g*32 +: 32]),
            .y(y[g*32 +: 32]), .err(er), .valid_out(vo));
        assign ee[g] = vo && er != 2'd0;
    end endgenerate
    assign e = |ee;
endmodule

// The in-entry binary-counter merger: node n of key `addr` (per lane h: memory [l][h][addr]); levels nl; fin = the
// last real node (missing right siblings are +0 nodes: cur = add(cur, +0)).  Each stage is 3 cycles; a key's next
// node arrives >= 32 cycles after its previous one, so a stage's read and its write never race.
module ot_hgi_att_r25_merge #(
    parameter integer L = 4,
    parameter integer LV = 6,
    parameter integer AW = 9,
    parameter integer MW = 16          // passthrough metadata
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          iv,
    input  wire [L*32-1:0] ival,
    input  wire [AW-1:0] iaddr,
    input  wire [6:0]    inode,
    input  wire [2:0]    inl,
    input  wire          ifin,
    input  wire [MW-1:0] imeta,
    output wire          ov,
    output wire [L*32-1:0] oval,
    output wire [MW-1:0] ometa,
    output reg           oerr
);
    localparam integer TW = 1 + AW + 7 + 3 + 1 + MW;
    wire [TW-1:0]  tk [0:LV];
    wire [L*32-1:0] cv [0:LV];
    assign tk[0] = {iv, iaddr, inode, inl, ifin, imeta};
    assign cv[0] = ival;
    wire [LV-1:0] se;
    genvar l, h;
    generate for (l = 0; l < LV; l = l + 1) begin : g_s
        wire          tv; wire [AW-1:0] ta; wire [6:0] tn; wire [2:0] tl; wire tf; wire [MW-1:0] tm;
        assign {tv, ta, tn, tl, tf, tm} = tk[l];
        wire act = tv && (l < tl);
        wire add = act && (tn[l] || tf);
        wire sto = act && !tn[l] && !tf;
        reg [31:0] m [0:L-1][0:(1<<AW)-1];
        wire [L*32-1:0] lft;
        for (h = 0; h < L; h = h + 1) begin : g_h
            assign lft[h*32 +: 32] = tn[l] ? m[h][ta] : 32'd0;    // fin with a clear bit: add(cur, +0)
            always @(posedge clk) if (sto) m[h][ta] <= cv[l][h*32 +: 32];
        end
        // three-cycle stage: the adder or a delay line, the token beside it
        wire [L*32-1:0] ay; wire ae;
        ot_hgi_att_r25_add #(.N(L)) u_a (.clk(clk), .rst_n(rst_n), .v(add), .a(lft), .b(cv[l]), .y(ay), .e(ae));
        reg [TW-1:0] t1, t2, t3; reg [L*32-1:0] c1, c2, c3; reg a1, a2, a3;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin t1 <= '0; t2 <= '0; t3 <= '0; a1 <= 1'b0; a2 <= 1'b0; a3 <= 1'b0; end
            else begin
                t1 <= sto ? '0 : tk[l]; t2 <= t1; t3 <= t2; a1 <= add; a2 <= a1; a3 <= a2;
            end
        always @(posedge clk) begin c1 <= cv[l]; c2 <= c1; c3 <= c2; end
        assign tk[l+1] = t3;
        assign cv[l+1] = a3 ? ay : c3;
        assign se[l] = ae;
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) oerr <= 1'b0; else if (|se) oerr <= 1'b1;
    assign ov = tk[LV][TW-1];
    assign oval = cv[LV];
    assign ometa = tk[LV][MW-1:0];
endmodule

module ot_hgi_att_r25 #(
    parameter integer NA = 4,           // active entries (1, 2 or 4)
    parameter integer LMAX = 4,         // lanes the merge hardware carries
    parameter integer LVM = 6,          // merge levels (QK S <= 16 needs 4; PV RB <= 64 needs 6)
    parameter integer LQ = 8,           // VM lane credits
    parameter integer LDLAT = 48,       // cycles from an ld word on tq to its arrival at the farthest entry tile (+ margin)
    parameter integer WFD = 256         // write FIFO depth
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_o,
    input  wire [20:0]   rec_n_b, rec_n_c, rec_pos1,
    output reg           rec_done,
    output reg           rec_fault,
    // VM lgE read group (client 1)
    output reg           rg_req,
    input  wire          rg_gnt,
    output reg  [32*16-1:0]  rq,
    input  wire [31:0]       rq_cr,
    input  wire [32*257-1:0] rr,
    // VM lgE write group (client 1)
    output reg           wg_req,
    input  wire          wg_gnt,
    output reg  [32*280-1:0] wq,
    input  wire [31:0]       wq_cr,
    input  wire [31:0]       wq_done,
    // tiles / svc / stagers
    output reg  [581:0]  tq,
    output wire [128:0]  e2,
    input  wire [1:0]    kd,
    output wire [NA*2-1:0] bt,
    input  wire [NA*529-1:0] ro
);
    // ---------------------------------------------------------------- record decode
    function automatic [39:0] mbase(input [255:0] d); mbase = d[47:8]; endfunction
    function automatic [19:0] mn(input [255:0] d); mn = d[67:48]; endfunction
    function automatic [31:0] mst(input [255:0] d); mst = d[119:88]; endfunction
    function automatic [15:0] mist(input [255:0] d); mist = (d[135:120] == 16'd0) ? 16'd1 : d[135:120]; endfunction
    reg [127:0] hdr; reg [255:0] da, db, dc, dout; reg [20:0] nb_r, nc_r;
    reg busy, raw_v;
    assign rec_rdy = !busy && !raw_v;
    wire [5:0] op = hdr[123:118];
    wire [6:0] opnd = hdr[99:93];
    wire [24:0] prm = hdr[88:64];
    reg qk; reg [4:0] L; reg [4:0] Lp; reg [2:0] lgLp; reg [9:0] hd; reg [4:0] S; reg [4:0] Sp; reg [2:0] lgSp;
    reg [20:0] T; reg [15:0] NB; reg [6:0] RB; reg [2:0] lgRB; reg [2:0] lgG;
    reg [17:0] abase, astr, obase, ostr, oist; reg [14:0] row0; reg ph;
    // ---------------------------------------------------------------- states
    localparam [3:0] S_IDLE = 0, S_DEC = 1, S_DEC2 = 2, S_CHK = 3, S_RUN = 4, S_WAIT = 5, S_DONE = 6, S_FAULT = 7;
    reg [3:0] st;
    reg flt;
    // ---------------------------------------------------------------- ld job generator
    // job = {word addr 18, valid words 6, bank 3, grp 8, entry 2, last-of-block 1}
    localparam integer JW = 18 + 6 + 3 + 8 + 2 + 1;
    reg [JW-1:0] jq [0:15]; reg [4:0] jw, jr;
    wire [4:0] jn = jw - jr;
    // QK generator
    reg [4:0] gs; reg [4:0] gh; reg qk_gen_done;
    // PV generator: per entry next block beta_l to load; results landed per entry
    reg [6:0] pb [0:NA-1];
    reg [20:0] rcnt [0:NA-1];                                  // result beats received per entry
    reg [4:0] pvh; reg [1:0] pva; reg pv_inblk;
    // ---------------------------------------------------------------- e2 / tokens
    reg e2v; reg [127:1] e2p; reg e2_sent; reg kd_seen;
    wire e2fck; ot_fwd_clk_inv u_e2f (.a(clk), .y(e2fck));
    assign e2 = {e2fck, e2p, e2v};
    reg [NA-1:0] dl [0:LDLAT];                                 // token release delay line (one bit an entry a block)
    reg qk_rel; reg [7:0] qrel_t;                              // QK: release every entry's RB S tokens
    reg [12:0] tdue [0:NA-1];
    reg [NA-1:0] btv;
    genvar ga;
    generate for (ga = 0; ga < NA; ga = ga + 1) begin : g_bt
        wire f; ot_fwd_clk_inv u_f (.a(clk), .y(f));
        assign bt[ga*2 +: 2] = {f, btv[ga]};
    end endgenerate
    // ---------------------------------------------------------------- VM read engine
    reg [3:0] lo [0:31];                                       // outstanding a lane
    reg [7:0] lc [0:31];                                       // credits a lane
    reg [255:0] rf [0:31][0:1]; reg rfw [0:31]; reg rfr [0:31]; reg [1:0] rfn [0:31];
    // issue: head-of-issue job pointer ji (jobs issued, not yet assembled: between jr and ji)
    reg [4:0] ji;
    wire [JW-1:0] jiq = jq[ji[3:0]];
    wire [17:0] jwa = jiq[JW-1 -: 18];
    wire [14:0] js0 = jwa[17:3];
    wire [2:0]  jns = (jwa[2:0] == 3'd0) ? 3'd4 : 3'd5;
    reg jfree; integer k;
    always @* begin
        jfree = 1'b1;
        for (k = 0; k < 5; k = k + 1) if (k < jns) begin
            if (lo[(js0 + k) % 32] >= 4'd2 || lc[(js0 + k) % 32] == 8'd0) jfree = 1'b0;
        end
    end
    wire j_iss = rg_gnt && rg_req && (ji != jw) && jfree;
    // assemble: head job jr (issued) when all its sectors' responses are present
    wire [JW-1:0] jrq = jq[jr[3:0]];
    wire [17:0] jra = jrq[JW-1 -: 18];
    wire [14:0] jr0 = jra[17:3];
    wire [2:0]  jrn = (jra[2:0] == 3'd0) ? 3'd4 : 3'd5;
    reg jrdy; reg [255:0] jsec [0:4];
    always @* begin
        jrdy = (jr != ji);
        for (k = 0; k < 5; k = k + 1) begin
            jsec[k] = rf[(jr0 + k) % 32][rfr[(jr0 + k) % 32]];
            if (k < jrn && rfn[(jr0 + k) % 32] == 2'd0) jrdy = 1'b0;
        end
    end
    wire j_asm = jrdy;
    reg [511:0] ldw; reg ldbad;
    integer e;
    always @* begin
        ldw = 512'd0; ldbad = 1'b0;
        for (e = 0; e < 32; e = e + 1) begin : w
            reg [5:0] off; reg [31:0] wd;
            off = jra[2:0] + e;
            wd = jsec[off >> 3][32 * (off % 8) +: 32];
            if (e < jrq[JW-19 -: 6]) begin
                ldw[16*e +: 16] = wd[31:16];
                if (wd[15:0] != 16'd0) ldbad = 1'b1;
            end
        end
    end
    // ---------------------------------------------------------------- result path: per entry beat counters -> mergers
    wire [NA-1:0] mo_v; wire [NA*LMAX*32-1:0] mo_val; wire [NA*16-1:0] mo_meta; wire [NA-1:0] mo_err;
    reg [NA-1:0] rflt;
    reg [4:0] rb_i [0:NA-1]; reg [4:0] rb_s [0:NA-1]; reg [6:0] rb_b [0:NA-1];
    generate for (ga = 0; ga < NA; ga = ga + 1) begin : g_m
        wire [528:0] w = ro[ga*529 +: 529];
        wire rv = w[528];
        wire [511:0] oy = w[527:16]; wire [15:0] of = w[15:0];
        wire [4:0] i = rb_i[ga], s = rb_s[ga]; wire [6:0] bl = rb_b[ga];
        reg [LMAX*32-1:0] vals; reg bad; integer h;
        always @* begin
            vals = '0; bad = 1'b0;
            for (h = 0; h < LMAX; h = h + 1) if (h < L) begin : sl
                reg [4:0] slot;
                slot = qk ? ((s & ((5'd1 << lgG) - 5'd1)) << lgLp) + h : (ga << lgLp) + h;
                vals[h*32 +: 32] = oy[slot*32 +: 32];
                if (of[slot]) bad = 1'b1;
            end
        end
        wire [8:0] addr = qk ? {4'd0, i} : {s[3:0], i};
`ifdef OT_ATT_R25_MUT_KQORD
        wire [6:0] node = qk ? {2'd0, Sp - 5'd1 - s} : bl;
`else
        wire [6:0] node = qk ? {2'd0, s} : bl;
`endif
        wire [2:0] nl = qk ? lgSp : lgRB;
        wire fin = qk ? (s == S - 5'd1) : (bl == RB - 7'd1);
        // meta: QK t = 32 (a RB + bl) + i (rows >= T dropped at the writer); PV d = 32 s + i
        wire [15:0] meta = qk ? 16'((ga * RB + bl) * 32 + i) : {7'd0, s[3:0], i};
        ot_hgi_att_r25_merge #(.L(LMAX), .LV(LVM), .AW(9), .MW(16)) u_mg (.clk(clk), .rst_n(rst_n),
            .iv(rv && busy && st == S_RUN), .ival(vals), .iaddr(addr), .inode(node), .inl(nl), .ifin(fin),
            .imeta(meta), .ov(mo_v[ga]), .oval(mo_val[ga*LMAX*32 +: LMAX*32]),
            .ometa(mo_meta[ga*16 +: 16]), .oerr(mo_err[ga]));
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rb_i[ga] <= 5'd0; rb_s[ga] <= 5'd0; rb_b[ga] <= 7'd0; rcnt[ga] <= 21'd0; rflt[ga] <= 1'b0; end
            else if (st == S_DEC) begin rb_i[ga] <= 5'd0; rb_s[ga] <= 5'd0; rb_b[ga] <= 7'd0; rcnt[ga] <= 21'd0; rflt[ga] <= 1'b0; end
            else if (rv && st == S_RUN) begin
                rcnt[ga] <= rcnt[ga] + 21'd1;
                if (bad) rflt[ga] <= 1'b1;
                rb_i[ga] <= i + 5'd1;
                if (i == 5'd31) begin
                    if (s == S - 5'd1) begin rb_s[ga] <= 5'd0; rb_b[ga] <= bl + 7'd1; end
                    else rb_s[ga] <= s + 5'd1;
                end
            end
    end endgenerate
    // ---------------------------------------------------------------- PV cross-entry tree (NA run roots, pairwise)
    reg [31:0] X [0:NA-1][0:LMAX-1][0:511];
    reg [NA-1:0] xm [0:511];
    reg [8:0] cf [0:511]; reg [9:0] cfw, cfr;
    integer a2, h2;
    reg [8:0] cfq; reg [9:0] cfn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cfw <= 10'd0; for (a2 = 0; a2 < 512; a2 = a2 + 1) xm[a2] <= '0; end
        else if (st == S_DEC) begin cfw <= 10'd0; for (a2 = 0; a2 < 512; a2 = a2 + 1) xm[a2] <= '0; end
        else if (!qk) begin : cx
            reg [9:0] w_;
            w_ = cfw;
            for (a2 = 0; a2 < NA; a2 = a2 + 1) if (mo_v[a2]) begin
                cfq = mo_meta[a2*16 +: 9];
                for (h2 = 0; h2 < LMAX; h2 = h2 + 1) X[a2][h2][cfq] <= mo_val[(a2*LMAX + h2)*32 +: 32];
            end
            for (a2 = 0; a2 < NA; a2 = a2 + 1) if (mo_v[a2]) begin
                cfq = mo_meta[a2*16 +: 9];
                xm[cfq] = xm[cfq] | (NA'(1) << a2);
                if (xm[cfq] == {NA{1'b1}}) begin cf[w_[8:0]] <= cfq; w_ = w_ + 10'd1; end
            end
            cfw <= w_;
        end
    end
    // tree unit: pop one d a cycle, two add levels (NA 4), one (NA 2), none (NA 1)
    wire cx_pop = !qk && st == S_RUN && cfr != cfw;
    wire [8:0] cx_d = cf[cfr[8:0]];
    reg [LMAX*32-1:0] x0, x1, x2, x3; reg x_v; reg [8:0] x_d;
    always @(posedge clk) begin
        for (h2 = 0; h2 < LMAX; h2 = h2 + 1) begin
            x0[h2*32 +: 32] <= X[0][h2][cx_d];
            x1[h2*32 +: 32] <= (NA > 1) ? X[(NA > 1) ? 1 : 0][h2][cx_d] : 32'd0;
            x2[h2*32 +: 32] <= (NA > 2) ? X[(NA > 2) ? 2 : 0][h2][cx_d] : 32'd0;
            x3[h2*32 +: 32] <= (NA > 3) ? X[(NA > 3) ? 3 : 0][h2][cx_d] : 32'd0;
        end
        x_d <= cx_d;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin x_v <= 1'b0; cfr <= 10'd0; end
        else begin x_v <= cx_pop; if (st == S_DEC) cfr <= 10'd0; else if (cx_pop) cfr <= cfr + 10'd1; end
    wire [LMAX*32-1:0] y01, y23, yr; wire e01, e23, er_;
    ot_hgi_att_r25_add #(.N(LMAX)) u_t01 (.clk(clk), .rst_n(rst_n), .v(x_v && NA > 1), .a(x0), .b(x1), .y(y01), .e(e01));
    ot_hgi_att_r25_add #(.N(LMAX)) u_t23 (.clk(clk), .rst_n(rst_n), .v(x_v && NA > 2), .a(x2), .b(x3), .y(y23), .e(e23));
    reg [2:0] xv_d; reg [8:0] xd_d [0:5]; reg [LMAX*32-1:0] x0_d [0:2];
    always @(posedge clk) begin
        xd_d[0] <= x_d; for (a2 = 1; a2 < 6; a2 = a2 + 1) xd_d[a2] <= xd_d[a2-1];
        x0_d[0] <= x0; x0_d[1] <= x0_d[0]; x0_d[2] <= x0_d[1];
    end
    ot_hgi_att_r25_add #(.N(LMAX)) u_tr (.clk(clk), .rst_n(rst_n), .v(NA > 2), .a(y01), .b(y23), .y(yr), .e(er_));
    reg [5:0] xvs;
    always @(posedge clk or negedge rst_n) if (!rst_n) xvs <= 6'd0; else xvs <= {xvs[4:0], x_v};
    wire          pvo_v = (NA == 1) ? x_v : (NA == 2) ? xvs[2] : xvs[5];
    wire [LMAX*32-1:0] pvo_y = (NA == 1) ? x0 : (NA == 2) ? y01 : yr;
    wire [8:0]    pvo_d = (NA == 1) ? x_d : (NA == 2) ? xd_d[2] : xd_d[5];
    // ---------------------------------------------------------------- writer: coalescing streams -> write FIFO
    // streams: QK: one an entry (the merger roots, t ascending a lane); PV: one (the tree, d of a slice ascending)
    // a stream lane keeps one open sector {sector, data, mask}; a word to another sector flushes it first.
    localparam integer NS = NA;
    reg [14:0] os [0:NS-1][0:LMAX-1]; reg [255:0] od [0:NS-1][0:LMAX-1]; reg [7:0] om [0:NS-1][0:LMAX-1];
    reg [279:0] wf [0:WFD-1]; reg [8:0] wfw, wfr; reg [20:0] wwords, wiss, wdone;
    reg [20:0] want;                                           // O words expected
    reg wovf; reg [1:0] fl_st;
    integer sx, hx;
    reg [NS-1:0] sv_; reg [NS*LMAX*32-1:0] sy_; reg [NS*21-1:0] sj_; reg flush_all;
    always @* begin
        sv_ = '0; sy_ = '0; sj_ = '0;
        if (qk) begin
            for (sx = 0; sx < NS; sx = sx + 1) begin
                sv_[sx] = mo_v[sx] && mo_meta[sx*16 +: 16] < T;
                sy_[sx*LMAX*32 +: LMAX*32] = mo_val[sx*LMAX*32 +: LMAX*32];
                sj_[sx*21 +: 21] = {5'd0, mo_meta[sx*16 +: 16]};
            end
        end else begin
            sv_[0] = pvo_v; sy_[0 +: LMAX*32] = pvo_y; sj_[0 +: 21] = {12'd0, pvo_d};
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wfw <= 9'd0; wwords <= 21'd0; wovf <= 1'b0;
            for (sx = 0; sx < NS; sx = sx + 1) for (hx = 0; hx < LMAX; hx = hx + 1) om[sx][hx] <= 8'd0;
        end else if (st == S_DEC) begin
            wfw <= 9'd0; wwords <= 21'd0; wovf <= 1'b0;
            for (sx = 0; sx < NS; sx = sx + 1) for (hx = 0; hx < LMAX; hx = hx + 1) om[sx][hx] <= 8'd0;
        end else begin : wr
            reg [8:0] w_; reg [20:0] nw; reg [7:0] tm; reg [31:0] wa; reg [14:0] sec; reg [2:0] wi;
            w_ = wfw; nw = wwords;
            for (sx = 0; sx < NS; sx = sx + 1) for (hx = 0; hx < LMAX; hx = hx + 1) if (hx < L) begin
                wa = {14'd0, obase} + hx * {14'd0, ostr} + sj_[sx*21 +: 21] * {14'd0, oist};
                sec = wa[17:3]; wi = wa[2:0];
                tm = om[sx][hx];
                if ((sv_[sx] && tm != 8'd0 && os[sx][hx] != sec) || (flush_all && tm != 8'd0)) begin
                    wf[w_] <= {1'b1, os[sx][hx], od[sx][hx], tm}; w_ = w_ + 9'd1;
                    tm = 8'd0;
                end
                if (sv_[sx]) begin
                    os[sx][hx] <= sec;
                    od[sx][hx][32*wi +: 32] <= sy_[(sx*LMAX + hx)*32 +: 32];
                    tm = tm | (8'd1 << wi);
                    nw = nw + 21'd1;
                end
                om[sx][hx] <= tm;
            end
            if (9'(w_ - wfr) >= 9'(WFD - 1) && w_ != wfw) wovf <= 1'b1;
            wfw <= w_; wwords <= nw;
        end
    end
    // issue: the FIFO head on its lane (one a cycle)
    wire [279:0] wh = wf[wfr];
    wire [4:0] wl = wh[264 +: 5];                                // sector[4:0] (sector at [278:264])
    reg [7:0] wc [0:31];
    wire w_iss = wg_gnt && wg_req && wfr != wfw && wc[wl] != 8'd0;
    // ---------------------------------------------------------------- main
    integer x, y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; busy <= 1'b0; raw_v <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0; flt <= 1'b0;
            rg_req <= 1'b0; wg_req <= 1'b0; rq <= '0; wq <= '0; tq <= '0; e2v <= 1'b0; e2p <= '0; e2_sent <= 1'b0;
            kd_seen <= 1'b0; jw <= 5'd0; jr <= 5'd0; ji <= 5'd0; ph <= 1'b0; qk_rel <= 1'b0; qrel_t <= 8'd0; btv <= '0;
            wfr <= 9'd0; wiss <= 21'd0; wdone <= 21'd0; flush_all <= 1'b0; qk_gen_done <= 1'b0; fl_st <= 2'd0;
            for (x = 0; x < 32; x = x + 1) begin lo[x] <= 4'd0; lc[x] <= 8'(LQ); wc[x] <= 8'(LQ); rfw[x] <= 1'b0; rfr[x] <= 1'b0; rfn[x] <= 2'd0; end
            for (x = 0; x <= LDLAT; x = x + 1) dl[x] <= '0;
            for (x = 0; x < NA; x = x + 1) begin tdue[x] <= 13'd0; pb[x] <= 7'd0; end
        end else begin
            rec_done <= 1'b0; rec_fault <= 1'b0; e2v <= 1'b0; tq[525] <= 1'b0; rq <= '0; wq <= '0; btv <= '0;
            flush_all <= 1'b0;
            if (rec_v && rec_rdy) begin
                raw_v <= 1'b1; hdr <= rec_hdr; da <= rec_a; db <= rec_b; dc <= rec_c; dout <= rec_o;
                nb_r <= rec_n_b; nc_r <= rec_n_c;
            end
            if (kd[0]) kd_seen <= 1'b1;
            // ---- VM read issue
            if (j_iss) begin
                for (x = 0; x < 5; x = x + 1) if (x < jns) begin
                    rq[((js0 + x) % 32) * 16 +: 16] <= {1'b1, 15'(js0 + x)};
                end
                ji <= ji + 5'd1;
            end
            for (x = 0; x < 32; x = x + 1) begin : ln
                reg iss_l, ret_l, pop_l; integer kk;
                iss_l = 1'b0;
                for (kk = 0; kk < 5; kk = kk + 1) if (j_iss && kk < jns && ((js0 + kk) % 32) == x) iss_l = 1'b1;
                ret_l = rr[x*257 + 256];
                pop_l = 1'b0;
                for (kk = 0; kk < 5; kk = kk + 1) if (j_asm && kk < jrn && ((jr0 + kk) % 32) == x) pop_l = 1'b1;
                lc[x] <= lc[x] - (iss_l ? 8'd1 : 8'd0) + (rq_cr[x] ? 8'd1 : 8'd0);
                lo[x] <= lo[x] + (iss_l ? 4'd1 : 4'd0) - (pop_l ? 4'd1 : 4'd0);
                if (ret_l) begin rf[x][rfw[x]] <= rr[x*257 +: 256]; rfw[x] <= ~rfw[x]; end
                if (pop_l) rfr[x] <= ~rfr[x];
                rfn[x] <= rfn[x] + (ret_l ? 2'd1 : 2'd0) - (pop_l ? 2'd1 : 2'd0);
                wc[x] <= wc[x] - ((w_iss && wl == x[4:0]) ? 8'd1 : 8'd0) + (wq_cr[x] ? 8'd1 : 8'd0);
            end
            // ---- assemble -> ld word on the q port; token release
            for (x = LDLAT; x > 0; x = x - 1) dl[x] <= dl[x-1];
            dl[0] <= '0;
            if (j_asm) begin
                jr <= jr + 5'd1;
                tq[525:0] <= {1'b1, 1'b0, jrq[JW-25 -: 3], jrq[JW-28 -: 8], ldw, 1'b0};
                if (ldbad) flt <= 1'b1;
                if (jrq[0]) dl[0] <= NA'(1) << jrq[2:1];
            end
            // QK: one release of every entry's RB S block tokens, LDLAT after the last q word
            if (st == S_RUN && qk && qk_gen_done && jn == 5'd0 && !qk_rel) begin qk_rel <= 1'b1; qrel_t <= 8'(LDLAT); end
            else if (qk_rel && qrel_t != 8'd0) qrel_t <= qrel_t - 8'd1;
            for (x = 0; x < NA; x = x + 1) begin : tk
                reg [12:0] add_;
                add_ = (dl[LDLAT][x] ? 13'(S) : 13'd0) + ((qk_rel && qrel_t == 8'd1) ? 13'(RB * S) : 13'd0);
                tdue[x] <= tdue[x] + add_ - ((tdue[x] != 13'd0) ? 13'd1 : 13'd0);
                if (tdue[x] != 13'd0) btv[x] <= 1'b1;
            end
            // ---- write issue / dones
            if (w_iss) begin wq[wl*280 +: 280] <= wh; wfr <= wfr + 9'd1; wiss <= wiss + 21'd1; end
            begin : dn
                integer c_; c_ = 0;
                for (x = 0; x < 32; x = x + 1) if (wq_done[x]) c_ = c_ + 1;
                wdone <= wdone + 21'(c_);
            end
            if (|rflt || |mo_err || e01 || e23 || er_ || wovf) flt <= 1'b1;
            // ---- control
            case (st)
                S_IDLE: if (raw_v) begin raw_v <= 1'b0; busy <= 1'b1; st <= S_DEC; end
                S_DEC: begin
                    qk <= (op == 6'd0);
                    L <= (prm[3:0] == 4'd0) ? 5'd16 : {1'b0, prm[3:0]};
                    hd <= (op == 6'd0) ? mn(da)[9:0] : mn(dout)[9:0];
                    T <= nb_r + (opnd[2] ? nc_r : 21'd0);
                    abase <= mbase(da)[17:0]; astr <= mst(da)[17:0]; obase <= mbase(dout)[17:0];
                    ostr <= mst(dout)[17:0]; oist <= {2'b00, mist(dout)};
                    row0 <= mbase(db)[34:20];
                    jw <= 5'd0; jr <= 5'd0; ji <= 5'd0; e2_sent <= 1'b0; kd_seen <= 1'b0; gs <= 5'd0; gh <= 5'd0;
                    qk_gen_done <= 1'b0; qk_rel <= 1'b0; pva <= 2'd0; pvh <= 5'd0; pv_inblk <= 1'b0;
                    wfr <= 9'd0; wiss <= 21'd0; wdone <= 21'd0; flt <= 1'b0;
                    for (x = 0; x < NA; x = x + 1) begin pb[x] <= 7'd0; tdue[x] <= 13'd0; end
                    st <= S_DEC2;
                end
                S_DEC2: begin : d2
                    reg [4:0] lp; reg [2:0] llp; reg [4:0] s_; reg [4:0] sp_; reg [2:0] lsp; reg [15:0] nb_; reg [15:0] nbp;
                    reg [15:0] rb_; reg [2:0] lrb;
                    lp = (L <= 1) ? 5'd1 : (L <= 2) ? 5'd2 : (L <= 4) ? 5'd4 : (L <= 8) ? 5'd8 : 5'd16;
                    llp = (L <= 1) ? 3'd0 : (L <= 2) ? 3'd1 : (L <= 4) ? 3'd2 : (L <= 8) ? 3'd3 : 3'd4;
                    s_ = hd[9:5];
                    sp_ = (s_ <= 1) ? 5'd1 : (s_ <= 2) ? 5'd2 : (s_ <= 4) ? 5'd4 : (s_ <= 8) ? 5'd8 : 5'd16;
                    lsp = (s_ <= 1) ? 3'd0 : (s_ <= 2) ? 3'd1 : (s_ <= 4) ? 3'd2 : (s_ <= 8) ? 3'd3 : 3'd4;
                    nb_ = 16'((T + 21'd31) >> 5);
                    nbp = 16'd1; for (x = 0; x < 16; x = x + 1) if (nbp < nb_) nbp = nbp << 1;
                    rb_ = (nbp > NA) ? nbp / NA : 16'd1;
                    lrb = 3'd0; for (x = 0; x < 7; x = x + 1) if ((16'd1 << x) == rb_) lrb = 3'(x);
                    Lp <= lp; lgLp <= llp; S <= s_; Sp <= sp_; lgSp <= lsp; NB <= nb_; RB <= 7'(rb_); lgRB <= lrb;
                    lgG <= 3'd4 - llp;
                    want <= qk ? L * T : L * hd;
                    st <= S_CHK;
                end
                S_CHK: begin
                    if (hdr[127:124] != 4'd5 || op > 6'd1 || !opnd[0] || !opnd[1] || !opnd[4] || da[1:0] != 2'd1 ||
                        dout[1:0] != 2'd1 || db[1:0] != 2'd0 || hd == 10'd0 || hd > 10'd512 || hd[4:0] != 5'd0 ||
                        T == 21'd0 || L > LMAX || (qk && mn(dout) != T[19:0]) || (!qk && mn(da) != T[19:0]) ||
                        mbase(db)[19:0] != 20'd0 || RB * S > 127 || lgRB > LVM || lgSp > LVM ||
                        (!qk && Lp * NA > 16) || (!qk && L * hd > 512) || (qk && S * Lp > 80))
                        st <= S_FAULT;
                    else begin
                        st <= S_RUN; rg_req <= 1'b1; wg_req <= 1'b1; ph <= ~ph;
                    end
                end
                S_RUN: begin
                    // e2 stream: QK after the q load is generated and released; PV at once
                    if (!e2_sent) begin : e2s
                        reg [126:0] p; reg [31:0] msk;
                        msk = 32'd0;
                        for (x = 0; x < NA; x = x + 1) msk = msk | (32'hF << (8 * x));
                        p = '0;
                        p[1:0] = 2'd1; p[16:2] = row0; p[28:17] = 12'(32 * RB * S); p[60:29] = msk;
                        p[83:71] = {~qk, (qk ? lgG : 3'd0), 4'(S - 5'd1), ph, 4'd0};
                        p[125] = 1'b0; p[126] = 1'b1;
                        e2p <= p; e2v <= 1'b1; e2_sent <= 1'b1;
                    end
                    // ld job generation (one a cycle into the 16-deep job queue)
                    if (jn < 5'd15) begin : gen
                        reg pushj; reg [JW-1:0] jj; reg [6:0] bl; reg ok;
                        pushj = 1'b0; jj = '0;
                        if (qk && !qk_gen_done) begin
                            jj = {18'(abase + gh * astr + 32 * gs), 6'd32, 3'(gs >> lgG),
                                  8'(((gs & ((5'd1 << lgG) - 5'd1)) << lgLp) + gh), 2'd0, 1'b0};
                            pushj = 1'b1;
                            if (gh == L - 5'd1) begin gh <= 5'd0; if (gs == S - 5'd1) qk_gen_done <= 1'b1; else gs <= gs + 5'd1; end
                            else gh <= gh + 5'd1;
                        end else if (!qk) begin
                            bl = pb[pva];
                            // the bank (bl mod 5) is free when the entry's block bl - 5 has all its results
                            ok = (bl < RB) && (bl < 7'd5 || rcnt[pva] >= 21'(bl - 7'd4) * S * 32);
                            if (ok) begin : pj
                                reg [20:0] r0_; reg [5:0] nv;
                                r0_ = 21'((pva * RB + bl) * 32);
                                nv = (T > r0_ + 21'd32) ? 6'd32 : (T > r0_) ? 6'(T - r0_) : 6'd0;
                                jj = {18'(abase + pvh * astr + r0_), nv, 3'(bl % 5), 8'((pva << lgLp) + pvh), 2'(pva),
                                      pvh == L - 5'd1};
                                pushj = 1'b1;
                                if (pvh == L - 5'd1) begin pvh <= 5'd0; pb[pva] <= bl + 7'd1; pva <= (pva == NA - 1) ? 2'd0 : pva + 2'd1; end
                                else pvh <= pvh + 5'd1;
                            end else if (pvh == 5'd0) pva <= (pva == NA - 1) ? 2'd0 : pva + 2'd1;
                        end
                        if (pushj) begin jq[jw[3:0]] <= jj; jw <= jw + 5'd1; end
                    end
                    // QK tokens: every block of every entry once the q load has been released (LDLAT after the last word)
                    if (qk && qk_gen_done && jr == jw && !qk_rel) begin qk_rel <= 1'b1; end
                    // completion
                    begin : cmp
                        reg all_r;
                        all_r = 1'b1;
                        for (x = 0; x < NA; x = x + 1) if (rcnt[x] != 21'(RB * S * 32)) all_r = 1'b0;
                        if (all_r && kd_seen && e2_sent) begin st <= S_WAIT; end
                    end
                end
                S_WAIT: begin
                    // drain the merger / tree pipelines, flush the open sectors, wait for every write's done
                    case (fl_st)
                        2'd0: if (wwords == want) begin flush_all <= 1'b1; fl_st <= 2'd1; end
                        2'd1: fl_st <= 2'd2;
                        2'd2: if (wfw == wfr && wdone == wiss) begin st <= S_DONE; fl_st <= 2'd0; end
                        default: fl_st <= 2'd0;
                    endcase
                end
                S_DONE: begin
                    rec_done <= 1'b1; rec_fault <= flt; busy <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE;
                end
                S_FAULT: begin
                    rec_done <= 1'b1; rec_fault <= 1'b1; busy <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; st <= S_IDLE;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
