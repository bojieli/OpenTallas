`timescale 1ns/1ps
// Bench: ot_hgi_b2_disp + RL relay stages + 4 x ot_hgi_b2_rq + mock units (random ready / latency / faults).
// Exactness: every record reaches exactly the clusters of an INDEPENDENT TB route model, bit-exact, in program order per
// (cluster, unit); every retire to the CP side is the unit's oldest record, only after all its clusters finished it, with
// fault = OR of theirs.  Mutants: DMUT 1 slice bit, 3 early retire (dispatcher); RMUT 2 youngest-first (stations).
// Plusargs: +N=<records> +SEED=<n>.  Prints B2DISP PASS / FAIL.
module tb_hgi_b2_disp;
    parameter integer DMUT = 0, RMUT = 0, RL = 6, BW = 1024;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    localparam integer W0 = 939, W1 = 2198, W2 = 1174, W3 = 1472, W4 = 704;
    reg [938:0] sm_rec = 0; reg [2197:0] su_rec = 0; reg [1173:0] sfu_rec = 0; reg [1471:0] att_rec = 0; reg [703:0] dma_rec = 0;
    wire [2:0] sm_ret, su_ret, sfu_ret, att_ret, dma_ret;
    wire [BW+8:0] cb; wire [39:0] rb;
    localparam [17:0] MLO = 18'h3C000, MHI = 18'h3E000;
    reg [4:0] r_v = 0; reg [2197:0] r_p = 0;          // cp_die's shared record register
    ot_hgi_b2_disp #(.MUT(DMUT), .BW(BW)) dut (.clk(clk), .rst_n(rst_n), .r_v(r_v), .r_pa(r_p[1098:0]), .r_pb(r_p[2197:1099]), .sm_ret(sm_ret),
        .su_ret(su_ret), .sfu_ret(sfu_ret), .att_ret(att_ret), .dma_ret(dma_ret), .mlo(MLO), .mhi(MHI), .cb(cb), .rb(rb), .busy());
    // relays (die distance)
    reg [BW+8:0] cbr [0:RL]; reg [39:0] rbr [0:RL]; wire [9:0] rbq [0:3];
    integer i;
    always @* begin cbr[0] = cb; rbr[0] = {rbq[3], rbq[2], rbq[1], rbq[0]}; end
    genvar g;
    generate for (g = 1; g <= RL; g = g + 1) begin : rl
        always @(posedge clk) begin cbr[g] <= rst_n ? cbr[g-1] : '0; rbr[g] <= rst_n ? rbr[g-1] : '0; end
    end endgenerate
    assign rb = rbr[RL];
    // ---------------------------------------------------------------- reference model state
    localparam integer MAXR = 70000;
    reg [2197:0] rp [0:MAXR-1]; reg [2:0] ru [0:MAXR-1]; reg [3:0] rm [0:MAXR-1];
    integer rdone [0:MAXR-1]; reg rflt [0:MAXR-1];
    // expected per (cluster, unit) id FIFOs
    integer eq [0:3][0:4][0:4095]; integer eh [0:3][0:4], et [0:3][0:4];
    integer uq [0:4][0:MAXR-1]; integer uh [0:4], ut [0:4];
    integer fails = 0, nrec = 0, nret = 0, N = 4000, seed = 1, cyc = 0, nmsg = 0;
    function automatic [3:0] ohs(input [1:0] s); ohs = 4'd1 << s; endfunction
    function automatic t_own(input [255:0] d);
        reg [17:0] a; begin a = d[25:8];
            t_own = (d[1:0] == 2'd1) && !(!d[26] && a >= MLO && a < MHI) && !d[26]; end   // SPEC v0.4: word addr >= 2^18 = REPL window, never an owner
    endfunction
    function automatic [3:0] t_route(input [2:0] u, input [2197:0] p);
        reg [255:0] o, a, b, c, d;
        begin
            case (u)
                3'd0, 3'd3: t_route = 4'hF;
                3'd1, 3'd2: begin
                    if (u == 3'd1) begin o = p[1409 +: 256]; a = p[385 +: 256]; b = p[641 +: 256]; c = p[897 +: 256]; d = p[1153 +: 256]; end
                    else begin o = p[897 +: 256]; a = p[129 +: 256]; b = p[385 +: 256]; c = p[641 +: 256]; d = 0; end
                    t_route = t_own(o) ? ohs(o[25:24]) : t_own(a) ? ohs(a[25:24]) : t_own(b) ? ohs(b[25:24]) :
                              t_own(c) ? ohs(c[25:24]) : t_own(d) ? ohs(d[25:24]) : 4'd1;
                end
                default: begin
                    a = p[129 +: 256]; o = p[385 +: 256];
                    if (a[1:0] != 0 && o[1:0] != 0) t_route = t_own(o) ? ohs(o[25:24]) : 4'd1;
                    else begin d = (a[1:0] == 0) ? a : o; t_route = (d[47:45] == 3'd1) ? 4'hF : ohs(d[44:43]); end
                end
            endcase
        end
    endfunction
    function automatic [255:0] rdesc(input integer k);
        reg [255:0] d; integer s;
        begin
            d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            s = $urandom % 8;
            d[1:0] = (s < 4) ? 2'd1 : (s < 6) ? 2'd0 : 2'd2;
            if (d[1:0] == 2'd1) begin
                d[47:8] = 40'd0; d[25:8] = $urandom;
                if ($urandom % 16 == 0) d[25:8] = MLO + ($urandom % 8192);       // mirror window
                if ($urandom % 32 == 0) d[26] = 1'b1;                           // REPL window (SPEC v0.4)
            end else if (d[1:0] == 2'd0) begin
                d[47:8] = {$urandom, $urandom}; d[47:45] = ($urandom % 4 == 0) ? 3'd1 : 3'd0;   // STRIPE4 sometimes
            end
            rdesc = d;
        end
    endfunction
    // ---------------------------------------------------------------- stations + mock units
    wire [938:0] q_sm [0:3]; wire [2197:0] q_su [0:3]; wire [1173:0] q_sfu [0:3]; wire [1471:0] q_att [0:3]; wire [703:0] q_dma [0:3];
    reg [2:0] q_ret [0:3][0:4];
    generate for (g = 0; g < 4; g = g + 1) begin : st
        ot_hgi_b2_rq #(.Q(g), .BW(BW), .MUT(RMUT)) rq (.clk(clk), .rst_n(rst_n), .cb(cbr[RL]), .rb(rbq[g]),
            .sm_rec(q_sm[g]), .sm_ret(q_ret[g][0]), .su_rec(q_su[g]), .su_ret(q_ret[g][1]), .sfu_rec(q_sfu[g]),
            .sfu_ret(q_ret[g][2]), .att_rec(q_att[g]), .att_ret(q_ret[g][3]), .dma_rec(q_dma[g]), .dma_ret(q_ret[g][4]));
    end endgenerate
    integer mlat [0:3][0:4]; integer mid [0:3][0:4]; reg mbusy [0:3][0:4];
    integer q, u;
    task automatic got(input integer qq, input integer uu, input [2197:0] p);
        integer id; reg [2197:0] w;
        begin
            w = p; w[0] = 1'b1;
            if (eh[qq][uu] == et[qq][uu]) begin fails = fails + 1; id = -1;
                if (nmsg < 10) begin nmsg = nmsg + 1; $display("FAIL cluster %0d unit %0d got an unexpected record", qq, uu); end
            end else begin
                id = eq[qq][uu][eh[qq][uu] % 4096]; eh[qq][uu] = eh[qq][uu] + 1;
                if (w != rp[id]) begin fails = fails + 1;
                    if (nmsg < 10) begin : dbg integer z, m; m = -1; for (z = 0; z < nrec; z = z + 1) if (rp[z] == w) m = z;
                        nmsg = nmsg + 1; $display("FAIL cluster %0d unit %0d record %0d payload mismatch (matches record %0d) diff bits %0d t=%0d", qq, uu, id, m, $countones(w ^ rp[id]), cyc);
                        $display("  got hdr %h A %h C %h\n  exp hdr %h A %h C %h", w[128:1], w[129 +: 256], w[641 +: 256], rp[id][128:1], rp[id][129 +: 256], rp[id][641 +: 256]); end
                end
            end
            mid[qq][uu] = id; mbusy[qq][uu] = 1'b1; mlat[qq][uu] = 1 + ($urandom % 24);
        end
    endtask
    always @(posedge clk) if (rst_n) begin
        for (q = 0; q < 4; q = q + 1) for (u = 0; u < 5; u = u + 1) begin
            q_ret[q][u] <= {2'b00, ($urandom % 4 != 0)};
            if (mbusy[q][u]) begin
                if (mlat[q][u] == 0) begin
                    reg f; f = ($urandom % 64 == 0);
                    q_ret[q][u][2:1] <= {f, !f}; mbusy[q][u] = 1'b0;
                    if (mid[q][u] >= 0) begin rdone[mid[q][u]] = rdone[mid[q][u]] + 1; if (f) rflt[mid[q][u]] = 1'b1; end
                end else mlat[q][u] = mlat[q][u] - 1;
            end
        end
    end
    // station record buses are sampled at the negedge (no race with the stations' posedge updates)
    always @(negedge clk) if (rst_n) begin : smp
        integer q;
        for (q = 0; q < 4; q = q + 1) begin
            if (q_sm[q][0])  got(q, 0, q_sm[q]);
            if (q_su[q][0])  got(q, 1, q_su[q]);
            if (q_sfu[q][0]) got(q, 2, q_sfu[q]);
            if (q_att[q][0]) got(q, 3, q_att[q]);
            if (q_dma[q][0]) got(q, 4, q_dma[q]);
        end
    end
    // retire checks (CP side)
    wire [4:0] rt_d = {dma_ret[1], att_ret[1], sfu_ret[1], su_ret[1], sm_ret[1]};
    wire [4:0] rt_f = {dma_ret[2], att_ret[2], sfu_ret[2], su_ret[2], sm_ret[2]};
    always @(posedge clk) if (rst_n) for (u = 0; u < 5; u = u + 1) if (rt_d[u] || rt_f[u]) begin
        integer id;
        nret = nret + 1;
        if (uh[u] == ut[u]) begin fails = fails + 1; if (nmsg < 10) begin nmsg = nmsg + 1; $display("FAIL unit %0d retire with nothing outstanding", u); end end
        else begin
            id = uq[u][uh[u]]; uh[u] = uh[u] + 1;
            if (rdone[id] != $countones(rm[id]) || rt_f[u] != rflt[id]) begin fails = fails + 1;
                if (nmsg < 10) begin nmsg = nmsg + 1; $display("FAIL unit %0d record %0d retired at %0d of %0d cluster completions (fault %0d exp %0d)",
                    u, id, rdone[id], $countones(rm[id]), rt_f[u], rflt[id]); end
            end
        end
    end
    // ---------------------------------------------------------------- record source (cp_die protocol: decision on ret[0], a registered valid pulse)
    initial begin
        reg [2197:0] p; integer uu, k;
        if (!$value$plusargs("N=%d", N)) N = 4000;
        if ($value$plusargs("SEED=%d", seed)) k = $urandom(seed);
        for (q = 0; q < 4; q = q + 1) for (u = 0; u < 5; u = u + 1) begin eh[q][u] = 0; et[q][u] = 0; mbusy[q][u] = 0; mid[q][u] = -1; mlat[q][u] = 0; end
        for (u = 0; u < 5; u = u + 1) begin uh[u] = 0; ut[u] = 0; end
        repeat (4) @(posedge clk); rst_n = 1;
        while (nrec < N) begin
            @(posedge clk); #0.1;
            r_v = 0;
            if (sm_ret[0] && ($urandom % 3 != 0)) begin
                uu = $urandom % 5;
                p = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                case (uu)
                    1: begin p[385 +: 256] = rdesc(0); p[641 +: 256] = rdesc(1); p[897 +: 256] = rdesc(2); p[1153 +: 256] = rdesc(3); p[1409 +: 256] = rdesc(4); end
                    2: begin p[129 +: 256] = rdesc(0); p[385 +: 256] = rdesc(1); p[641 +: 256] = rdesc(2); p[897 +: 256] = rdesc(4); end
                    4: begin p[129 +: 256] = rdesc(0); p[385 +: 256] = rdesc(4); end
                    default: ;
                endcase
                p[0] = 1'b1;
                case (uu) 0: p = W0'(p); 1: ; 2: p = W2'(p); 3: p = W3'(p); default: p = W4'(p); endcase
                rp[nrec] = p; ru[nrec] = uu; rm[nrec] = t_route(uu, p); rdone[nrec] = 0; rflt[nrec] = 0;
                for (q = 0; q < 4; q = q + 1) if (rm[nrec][q]) begin eq[q][uu][et[q][uu] % 4096] = nrec; et[q][uu] = et[q][uu] + 1; end
                uq[uu][ut[uu]] = nrec; ut[uu] = ut[uu] + 1;
                @(posedge clk); #0.1;      // the cp_die register loads one cycle after the decision
                r_p = p; r_v = 5'd1 << uu;
                nrec = nrec + 1;
            end
        end
        @(posedge clk); #0.1; r_v = 0;
        k = 0; while (nret < nrec && k < 200000) begin @(posedge clk); k = k + 1; end
        for (q = 0; q < 4; q = q + 1) for (u = 0; u < 5; u = u + 1) if (eh[q][u] != et[q][u]) begin fails = fails + 1;
            if (nmsg < 20) begin nmsg = nmsg + 1; $display("FAIL cluster %0d unit %0d delivered %0d of %0d", q, u, eh[q][u], et[q][u]); end end
        if (nret != nrec) fails = fails + 1;
        if (fails == 0) $display("B2DISP PASS records=%0d retired=%0d cycles=%0d", nrec, nret, cyc);
        else $display("B2DISP FAIL fails=%0d records=%0d retired=%0d", fails, nrec, nret);
        $finish;
    end
    always @(posedge clk) cyc <= cyc + 1;
endmodule
