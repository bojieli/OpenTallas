`timescale 1ns/1ps
// HEAD-RTL 2026-10-26: ot_s81hd_mesh_ep_core bench.  Two endpoints X / Y (two peer ranks), SerDes pairs cross-connected
// (X.coll_oa -> Y.coll_ia, X.coll_ob -> Y.coll_ib and back; ot_pdie_serdes st = {live 1, fault 0}).  Each side has the
// hd_ctl-side models: ot_s81hd_best64_tx (own BEST -> m_tx_i) and ot_s81hd_mesh64_rx (m_rx_o -> copy A / B frames).
// Phase 1: both sides send canonical BEST frames (random 81-b records + header) at random gaps >= 6 cycles, with CRC
//   corruption windows on lane b of both directions (lane replay).  Check: every record arrives at the peer's ctl
//   ONCE as copy A and ONCE as copy B, in order, bit-exact (97 b), and no fault (endpoint vector or word) anywhere.
// Phase 2 (directed fault): a lone out-of-order beat is forced onto X.m_tx_i; Y then sends one more record.  Check: the
//   word X delivers carries ep_fault[8] (m_tx decode) at ctl X, and ctl Y stays clean.
// Mutants (MUT 1..4 in ot_s81hd_mesh_ep_core, applied to both endpoints) must FAIL.
module tb_s81hd_mesh_ep;
    parameter integer MUT = 0, NREC = 400, P2 = 9000, NCYC = 11000;
    reg ck = 0, rst_n = 0; always #0.5 ck = ~ck;
    reg [31:0] rng = 32'h1f2e3d4c;
    reg tv [0:1]; reg [552:0] tf [0:1];
    wire [63:0] mtx [0:1], mrx [0:1], mtx_drv [0:1];
    wire [511:0] oa [0:1], ob [0:1];
    reg  [511:0] imp [0:1];
    reg force_bad = 0;
    wire fa [0:1], vb_ [0:1], va_ [0:1], rf [0:1];
    wire [552:0] rfr [0:1]; wire [11:0] epf [0:1];
    genvar s;
    generate for (s = 0; s < 2; s = s + 1) begin : g_side
        ot_s81hd_best64_tx u_tx (.ck(ck), .rn(rst_n), .v(tv[s]), .frame(tf[s]), .lane(mtx[s]), .fault(fa[s]));
        assign mtx_drv[s] = (s == 0 && force_bad) ? {1'b1, 1'b1, 62'h155} : mtx[s];
        ot_s81hd_mesh64_rx u_rx (.ck(ck), .rn(rst_n), .lane(mrx[s]), .va(va_[s]), .vb(vb_[s]), .frame(rfr[s]),
            .ep_fault(epf[s]), .fault(rf[s]));
    end endgenerate
    ot_s81hd_mesh_ep_core #(.MUT(MUT)) u_x (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, oa[1]}), .coll_oa(oa[0]),
        .coll_ib({2'b10, ob[1] ^ imp[1]}), .coll_ob(ob[0]), .m_tx_i(mtx_drv[0]), .m_rx_o(mrx[0]));
    ot_s81hd_mesh_ep_core #(.MUT(MUT)) u_y (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, oa[0]}), .coll_oa(oa[1]),
        .coll_ib({2'b10, ob[0] ^ imp[0]}), .coll_ob(ob[1]), .m_tx_i(mtx_drv[1]), .m_rx_o(mrx[1]));
    function automatic [96:0] body(input integer side, input integer k);
        reg [31:0] h; reg [80:0] r; integer b; begin
            h = 32'h9e3779b9 * (k + 7) ^ (side * 32'h85ebca6b);
            for (b = 0; b < 81; b = b + 1) begin r[b] = h[b % 32] ^ h[(b / 32 + k) % 32]; if (b % 32 == 31) h = h ^ (h << 13) ^ (h >> 7); end
            r[0] = 1'b1;                                          // record valid
            body = {r, 8'd0, 2'(side), 2'(k), 4'd1};              // header: grp, rank, type BEST
        end endfunction
    integer c = 0, err = 0, i, sk [0:1], ra [0:1], rb [0:1], gap [0:1], f1 = 0, lmax = 0, lmaxb = 0;
    integer ts [0:1][0:1023];
    initial for (i = 0; i < 2; i = i + 1) begin sk[i] = 0; ra[i] = 0; rb[i] = 0; gap[i] = 0; tv[i] = 0; tf[i] = 0; imp[i] = 0; end
    always @(negedge ck) begin
        c = c + 1;
        rst_n = (c >= 8);
        force_bad = (c == P2 + 10);
        for (i = 0; i < 2; i = i + 1) if (rst_n) begin
            // records on ctl i came from side 1-i
            if (va_[i]) begin
                if (rfr[i][96:0] !== body(1 - i, ra[i])) begin err = err + 1; if (err < 8) $display("MESH_DATA_ERR c=%0d side=%0d copyA rec=%0d", c, i, ra[i]); end
                if (ra[i] >= sk[1 - i]) begin err = err + 1; if (err < 8) $display("MESH_DUP_ERR c=%0d side=%0d copyA", c, i); end
                if (c - ts[1 - i][ra[i] % 1024] > lmax) lmax = c - ts[1 - i][ra[i] % 1024];
                ra[i] = ra[i] + 1;
            end
            if (vb_[i]) begin
                if (rfr[i][96:0] !== body(1 - i, rb[i])) begin err = err + 1; if (err < 8) $display("MESH_DATA_ERR c=%0d side=%0d copyB rec=%0d", c, i, rb[i]); end
                if (rb[i] >= sk[1 - i]) begin err = err + 1; if (err < 8) $display("MESH_DUP_ERR c=%0d side=%0d copyB", c, i); end
                if (c - ts[1 - i][rb[i] % 1024] > lmaxb) lmaxb = c - ts[1 - i][rb[i] % 1024];
                rb[i] = rb[i] + 1;
            end
            if (tv[i]) begin ts[i][sk[i] % 1024] = c - 1; sk[i] = sk[i] + 1; end
        end
        if (c < P2 && (epf[0] != 0 || epf[1] != 0 || rf[0] || rf[1] || fa[0] || fa[1])) f1 = 1;
        rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
        imp[0] = 0; imp[1] = 0;
        if (c >= 3000 && c < 3004) imp[0] = {rng, rng[15:0]} << 96;
        if (c >= 5000 && c < 5010) imp[1] = {rng[7:0], rng} << 300;
        for (i = 0; i < 2; i = i + 1) begin
            tv[i] = rst_n && c > 60 && c < P2 - 600 && sk[i] < NREC && gap[i] >= 6 && rng[i * 3 + 1];
            if (c == P2 + 200 && i == 1) tv[i] = 1'b1;                      // phase 2: one more record Y -> X
            gap[i] = tv[i] ? 0 : gap[i] + 1;
            tf[i] = {1'b1, 455'd0, body(i, sk[i])};
        end
        if (c == NCYC) begin
            $display("MESH_STATS sent=%0d/%0d copyA=%0d/%0d copyB=%0d/%0d max_latency=%0d/%0d errors=%0d phase1_fault=%0d epf=%h/%h rf=%b/%b",
                sk[0], sk[1], ra[1], ra[0], rb[1], rb[0], lmax, lmaxb, err, f1, epf[0], epf[1], rf[0], rf[1]);
            if (err != 0 || ra[0] != sk[1] || rb[0] != sk[1] || ra[1] != sk[0] || rb[1] != sk[0] || sk[0] < NREC)
                $display("MESH_EP FAIL data: errors %0d", err);
            else if (f1 != 0) $display("MESH_EP FAIL fault on the static schedule");
            else if (epf[0][8] !== 1'b1) $display("MESH_EP FAIL m_tx decode fault not delivered in-band (epf X %h)", epf[0]);
            else if (epf[1] !== 12'd0 || rf[1]) $display("MESH_EP FAIL spurious fault on Y (epf %h)", epf[1]);
            else $display("MESH_EP PASS records %0d/%0d x 2 copies exact, in-band fault delivered", ra[1], ra[0]);
            $finish;
        end
    end
endmodule
