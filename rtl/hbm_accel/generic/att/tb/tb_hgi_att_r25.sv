`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// hgi-1010/att 2026-10-11: R25 ATT transaction bench.  record -> ot_hgi_att_r25 -> e2 -> svc PS model (per-PC streams,
// random latency, out-of-order rows within a PC, random group round robin, CRR 16 line credits a PC returned in arrival
// order as ot_svs_grp maps them) -> ot_hgi_att_stager (N9 kq credit) -> REAL tiles (hfd_attn_half_lo KVIB = 1 +
// hfd_attn_half_hi: per active tile row the entry and its partner) -> row-end result words -> controller -> VM lgE.
// Checks every O word against hgi_sim's ATT golden (tools/hgi_att_r25_vectors.py) and rec_fault == 0.
// Vehicles (VEH): 0 = NA tile rows, entry a on row a (production rule P3); 3 = B3 mutant: entry 1 on row 0's second pair.
// Defines for mutants: OT_ATTN_MUT_KVIB_PARTNER (B1), OT_ATT_STG_MUT_TAG (B2), OT_ATT_STG_MUT_TP (B4),
// OT_ATT_STG_MUT_KQ, OT_ATT_STG_MUT_BANK, OT_ATT_R25_MUT_KQORD.  Plusargs: +vec=DIR +seed=N +inorder (svc delivers in order).
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_att_r25 #(
    parameter integer NA = 4,
    parameter integer VEH = 0,
    parameter integer LDLAT = 48
) (input wire clk);
    reg rst_n = 1'b0;
    integer cyc = 0;
    integer err = 0;
    always @(posedge clk) cyc <= cyc + 1;
    // ---------------------------------------------------------------- DUT
    reg rec_v = 1'b0; wire rec_rdy, rec_done, rec_fault;
    reg [127:0] hdr; reg [255:0] ra, rb_, rc, ro_; reg [20:0] nb, nc;
    wire rg_req, wg_req; reg rg_gnt = 1'b0, wg_gnt = 1'b0;
    wire [32*16-1:0] rq; reg [31:0] rq_cr = 0; reg [32*257-1:0] rr = 0;
    wire [32*280-1:0] wq; reg [31:0] wq_cr = 0, wq_done = 0;
    wire [581:0] tq; wire [128:0] e2; reg [1:0] kd = 0; wire [NA*2-1:0] bt; wire [NA*529-1:0] ro;
    ot_hgi_att_r25 #(.NA(NA), .LDLAT(LDLAT)) u_c (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(hdr), .rec_a(ra), .rec_b(rb_), .rec_c(rc), .rec_o(ro_), .rec_n_b(nb), .rec_n_c(nc), .rec_pos1(21'd0),
        .rec_done(rec_done), .rec_fault(rec_fault), .rg_req(rg_req), .rg_gnt(rg_gnt), .rq(rq), .rq_cr(rq_cr), .rr(rr),
        .wg_req(wg_req), .wg_gnt(wg_gnt), .wq(wq), .wq_cr(wq_cr), .wq_done(wq_done), .tq(tq), .e2(e2), .kd(kd), .bt(bt),
        .ro(ro));
    // ---------------------------------------------------------------- stagers
    wire [NA*1102-1:0] ks_svc; wire [NA*2-1:0] kq; wire [NA*1102-1:0] ks_t; wire [NA-1:0] sflt;
    genvar a;
    generate for (a = 0; a < NA; a = a + 1) begin : g_st
        ot_hgi_att_stager u_s (.clk(clk), .rst_n(rst_n), .ks_i(ks_svc[a*1102 +: 1102]), .kq_o(kq[a*2 +: 2]),
            .bt_i(bt[a*2 +: 2]), .ks_o(ks_t[a*1102 +: 1102]), .flt(sflt[a]));
    end endgenerate
    // ---------------------------------------------------------------- tiles: NR rows x NT tiles (inner -> outer)
    localparam integer NR = (VEH == 3) ? 1 : NA;
    localparam integer NT = (VEH == 3) ? 4 : 2;
    wire [1617:0] rf [0:NR-1][0:NT-1]; wire [1617:0] cf [0:NR-1][0:NT-1];
    wire [528:0] o [0:NR-1][0:NT-1];
    genvar r, t;
    generate for (r = 0; r < NR; r = r + 1) begin : g_r
        for (t = 0; t < NT; t = t + 1) begin : g_t
            localparam integer ENT = (t % 2 == 0);
            localparam integer EID = (VEH == 3) ? t / 2 : r;            // which stager feeds this entry
            wire [1618:0] xp; wire [271:0] xr; wire [1:0] kq_un;
            wire [1617:0] ci = (t == 0 && r > 0) ? cf[r-1][0] : 1618'd0;
            wire [1617:0] ri = (t > 0) ? rf[r][t-1] : 1618'd0;
            wire [581:0] qq = (t == 0 && r == 0) ? tq : 582'd0;
            wire [1101:0] kss = ENT ? ks_t[EID*1102 +: 1102] : 1102'd0;
            hfd_attn_half_lo #(.KVIB(1)) u_lo (.ci(ci), .ck(clk), .k(1041'd0), .ks(kss), .ldk(ENT[0]), .kq(kq_un),
                .q(qq), .rf(rf[r][t]), .ri(ri), .rst(rst_n), .xp(xp), .xr(xr));
            wire [528:0] ii = (t < NT - 1) ? o[r][t+1] : 529'd0;
            hfd_attn_half_hi u_hi (.cf(cf[r][t]), .ck(clk), .i(ii), .o(o[r][t]), .xp(xp), .xr(xr));
        end
        assign ro[r*529 +: 529] = o[r][0];
    end
    if (VEH == 3) begin : g_r3
        for (a = 1; a < NA; a = a + 1) begin : g_z assign ro[a*529 +: 529] = 529'd0; end
    end endgenerate
    // ---------------------------------------------------------------- VM model (lgE client 1: read + write groups)
    reg [31:0] vm [0:262143];
    localparam integer RL = 6;
    reg [256:0] rpipe [0:RL-1][0:31];
    integer x, y;
    always @(posedge clk) begin
        rg_gnt <= rg_req; wg_gnt <= wg_req;
        rq_cr <= 32'd0; wq_cr <= 32'd0; wq_done <= 32'd0;
        for (x = 0; x < 32; x = x + 1) begin
            // read lane x
            for (y = RL - 1; y > 0; y = y - 1) rpipe[y][x] <= rpipe[y-1][x];
            rpipe[0][x] <= 257'd0;
            if (rq[x*16 + 15]) begin
                if (rq[x*16 +: 5] != x[4:0]) begin $display("TB_ERR read lane %0d sector bank %0d", x, rq[x*16 +: 5]); err = err + 1; end
                rpipe[0][x] <= {1'b1, vm[{rq[x*16 +: 15], 3'd7}], vm[{rq[x*16 +: 15], 3'd6}], vm[{rq[x*16 +: 15], 3'd5}],
                    vm[{rq[x*16 +: 15], 3'd4}], vm[{rq[x*16 +: 15], 3'd3}], vm[{rq[x*16 +: 15], 3'd2}],
                    vm[{rq[x*16 +: 15], 3'd1}], vm[{rq[x*16 +: 15], 3'd0}]};
                rq_cr[x] <= 1'b1;
            end
            rr[x*257 +: 257] <= rpipe[RL-1][x];
            // write lane x
            if (wq[x*280 + 279]) begin
                if (wq[x*280 + 264 +: 5] != x[4:0]) begin $display("TB_ERR write lane %0d", x); err = err + 1; end
                for (y = 0; y < 8; y = y + 1) if (wq[x*280 + y]) vm[{wq[x*280 + 264 +: 15], y[2:0]}] <= wq[x*280 + 8 + 32*y +: 32];
                wq_cr[x] <= 1'b1; wq_done[x] <= 1'b1;
            end
        end
    end
    // ---------------------------------------------------------------- svc PS model
    bit [255:0] hbm [int];
    integer seed = 1; bit inorder = 0;
    // stream state
    reg s_act = 0; reg [14:0] s_row0; reg [11:0] s_nsec; reg [31:0] s_mask; reg [12:0] s_tag;
    integer pc_next [0:31];       // next row to fetch a PC
    integer pc_cred [0:31];
    integer pc_sent [0:31];       // rows delivered
    integer pc_rdy_t [0:31][0:3]; integer pc_rdy_rq [0:31][0:3]; bit pc_rdy_v [0:31][0:3];
    integer cq_pc [0:NA-1][0:255]; integer cq_h [0:NA-1], cq_t [0:NA-1];
    reg [1101:0] ksr [0:NA-1];
    generate for (a = 0; a < NA; a = a + 1) begin : g_ks assign ks_svc[a*1102 +: 1102] = ksr[a]; end endgenerate
    integer kd_t = -1;
    function automatic integer rnd(input integer n); rnd = $urandom % n; endfunction
    always @(posedge clk) begin : svc
        integer g, c, p, k, slot, pick, nrdy, cand [0:15];
        for (g = 0; g < NA; g = g + 1) ksr[g] <= 1102'd0;
        kd <= 2'd0;
        if (e2[0]) begin
            if (s_act) begin $display("TB_ERR e2 stream while one is active"); err = err + 1; end
            s_act <= 1'b1; s_row0 <= e2[17:3]; s_nsec <= e2[29:18]; s_mask <= e2[61:30]; s_tag <= e2[84:72];
            if (e2[127] !== 1'b1 || e2[126] !== 1'b0 || e2[2:1] != 2'd1) begin $display("TB_ERR e2 format"); err = err + 1; end
            for (p = 0; p < 32; p = p + 1) begin pc_next[p] = 0; pc_sent[p] = 0;
                for (k = 0; k < 4; k = k + 1) pc_rdy_v[p][k] = 0; end
        end else if (s_act) begin
            // fetch: a PC with a free slot and an outstanding credit window starts a row fetch (latency 40..200)
            for (p = 0; p < 32; p = p + 1) if (s_mask[p] && pc_next[p] < s_nsec / 4) begin
                for (k = 0; k < 4; k = k + 1)
                    if (!pc_rdy_v[p][k] && pc_next[p] < s_nsec / 4 && (pc_next[p] - pc_sent[p]) < 4 && rnd(3) == 0) begin
                        pc_rdy_v[p][k] = 1; pc_rdy_rq[p][k] = pc_next[p];
                        pc_rdy_t[p][k] = cyc + (inorder ? 60 : 40 + rnd(160)) + (inorder ? 4 * pc_next[p] : 0);
                        pc_next[p] = pc_next[p] + 1;
                    end
            end
            // deliver: per group port one row a cycle from a random PC whose row is ready and that holds a credit
            for (g = 0; g < NA; g = g + 1) begin
                nrdy = 0;
                for (c = 0; c < 4; c = c + 1) begin
                    p = 8 * g + c;
                    if (s_mask[p] && pc_cred[p] > 0)
                        for (k = 0; k < 4; k = k + 1)
                            if (pc_rdy_v[p][k] && pc_rdy_t[p][k] <= cyc && (!inorder || pc_rdy_rq[p][k] == pc_sent[p]))
                                begin cand[nrdy] = p * 4 + k; nrdy = nrdy + 1; end
                end
                if (nrdy > 0) begin
                    pick = cand[inorder ? 0 : rnd(nrdy)];
                    p = pick / 4; k = pick % 4;
                    begin : row
                        reg [1023:0] w; integer q;
                        for (q = 0; q < 4; q = q + 1) begin
                            int key; key = ((s_row0 * 32 + p) * 4096) + 4 * pc_rdy_rq[p][k] + q;
                            w[256*q +: 256] = hbm.exists(key) ? hbm[key] : 256'd0;
                        end
                        ksr[g] <= {3'b000, 31'd0, s_tag, 1'b0, 5'(p), 4'hF, 10'd0, w, 10'(pc_rdy_rq[p][k]), 1'b1};
                    end
                    pc_rdy_v[p][k] = 0; pc_cred[p] = pc_cred[p] - 1; pc_sent[p] = pc_sent[p] + 1;
                    cq_pc[g][cq_t[g] % 256] = p; cq_t[g] = cq_t[g] + 1;
                end
            end
            // done: every PC's rows delivered
            begin : dn
                bit all; all = 1;
                for (p = 0; p < 32; p = p + 1) if (s_mask[p] && pc_sent[p] < s_nsec / 4) all = 0;
                if (all) begin s_act <= 1'b0; kd_t = cyc + 20; end
            end
        end
        if (kd_t == cyc) kd <= 2'b01;
        // credits from the stagers, in arrival order
        for (g = 0; g < NA; g = g + 1) if (kq[g*2]) begin
            if (cq_h[g] == cq_t[g]) begin $display("TB_ERR surplus credit port %0d", g); err = err + 1; end
            else begin pc_cred[cq_pc[g][cq_h[g] % 256]] = pc_cred[cq_pc[g][cq_h[g] % 256]] + 1; cq_h[g] = cq_h[g] + 1; end
        end
    end
    // ---------------------------------------------------------------- driver / checker
    integer fd, nrec, ri, nvm, nexp, i, addr, val, t0, nbad, fd2, nh, wd;
    reg [255:0] hb; string vec;
    integer exp_a [0:65535]; integer exp_v [0:65535];
    initial begin
        if (!$value$plusargs("vec=%s", vec)) vec = "vec";
        if ($value$plusargs("seed=%d", seed)) ;
        inorder = $test$plusargs("inorder");
        void'($urandom(seed));
        for (i = 0; i < 32; i = i + 1) pc_cred[i] = 16;
        for (i = 0; i < NA; i = i + 1) begin cq_h[i] = 0; cq_t[i] = 0; end
        for (i = 0; i < 262144; i = i + 1) vm[i] = 32'd0;
        fd2 = $fopen({vec, "/hbm.txt"}, "r");
        void'($fscanf(fd2, "%h\n", nh));
        for (i = 0; i < nh; i = i + 1) begin void'($fscanf(fd2, "%h %h\n", addr, hb)); hbm[addr] = hb; end
        $fclose(fd2);
        fd = $fopen({vec, "/recs.txt"}, "r");
        void'($fscanf(fd, "%h\n", nrec));
        repeat (8) @(posedge clk);
        rst_n = 1'b1;
        repeat (8) @(posedge clk);
        for (ri = 0; ri < nrec; ri = ri + 1) begin
            void'($fscanf(fd, "%h %h %h %h %h %h %h %h %h\n", hdr, ra, rb_, rc, ro_, nb, nc, nvm, nexp));
            for (i = 0; i < nvm; i = i + 1) begin void'($fscanf(fd, "%h %h\n", addr, val)); vm[addr] = val; end
            for (i = 0; i < nexp; i = i + 1) begin void'($fscanf(fd, "%h %h\n", addr, val)); exp_a[i] = addr; exp_v[i] = val; end
            @(posedge clk);
            while (!rec_rdy) @(posedge clk);
            rec_v <= 1'b1; t0 = cyc;
            @(posedge clk); rec_v <= 1'b0;
            while (!rec_done) begin
                @(posedge clk);
                if (cyc - t0 > 400000) begin $display("TB_ERR rec %0d timeout", ri); $display("ATT_R25 FAIL"); $finish; end
            end
            nbad = 0;
            for (i = 0; i < nexp; i = i + 1) if (vm[exp_a[i]] !== exp_v[i]) begin
                if (nbad < 5) $display("TB_MISMATCH rec %0d addr %h got %h exp %h", ri, exp_a[i], vm[exp_a[i]], exp_v[i]);
                nbad = nbad + 1;
            end
            $display("ATT_R25 REC %0d cycles %0d words %0d mismatches %0d fault %0d stager_flt %b", ri, cyc - t0, nexp, nbad,
                     rec_fault, sflt);
            if (nbad != 0 || rec_fault || |sflt) err = err + 1;
            for (i = 0; i < nexp; i = i + 1) vm[exp_a[i]] = 32'd0;
        end
        repeat (50) @(posedge clk);
        if (err == 0) $display("ATT_R25 PASS"); else $display("ATT_R25 FAIL errors %0d", err);
        $finish;
    end
endmodule
