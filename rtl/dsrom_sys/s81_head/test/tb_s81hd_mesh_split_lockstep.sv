`timescale 1ns/1ps
// DH58-RFRTL 2026-11-03: lockstep of the hd_mesh split (ot_s81hd_mesh_split_ref = mesh_a + mesh_b) against the unsplit
// ot_s81hd_mesh_ep_core.  Two worlds with the same stimulus (tb_s81hd_mesh_ep traffic: two peer endpoints X / Y,
// SerDes pairs cross-connected, impaired beats on lane b both ways, a directed out-of-order m_tx beat on X):
//   R: X = unsplit core fed m_tx_i delayed 2 edges, Y = unsplit
//   S: X = split (a + b) fed m_tx_i undelayed,       Y = unsplit
// Checked every edge: S.X.coll_oa/coll_ob == R.X.coll_oa/coll_ob, S.Y.* == R.Y.*, S.X.m_rx_o(t) == R.X.m_rx_o(t-1)
// (declared +2/+2 seam latency, less the +1 RX stage the core gained in DIE-HEAD-65; split not in the plan), and the traffic is not vacuous (both copies of >= NREC records reach S.X's ctl).
// Phase 3 (fault paths, so that every seam bit toggles): at P2+600 Y sends one record whose frame bit 552 is forced
// low in both Y's (a non-canonical record on both X lanes: ncan fault, the can_b seam term); [P2+1000, P2+1040) the
// SerDes fault bit of X lane b and [P2+1200, P2+1240) of X lane a are raised in both worlds (lane flt seam bits); a
// directed out-of-order m_tx beat at FBAD = P2+231 so that the own_f (m_tx decode fault) rise lands 2 edges before the
// first word issued after P2+200 (the only window where a missing own_f balance stage, SPLIT_MUT 3, is visible); a
// last Y record at P2+1400 carries X's sticky fault vector, which must show all four (non-vacuous fault phase).
module tb_s81hd_mesh_split_lockstep;
    parameter integer MUT = 0, SPLIT_MUT = 0, BQ = 7, NREC = 400, P2 = 9000, NCYC = 11000, FBAD = P2 + 231;
    reg ck = 0, rst_n = 0; always #0.5 ck = ~ck;
    reg [31:0] rng = 32'h1f2e3d4c;
    reg tv [0:1]; reg [552:0] tf [0:1];
    wire [63:0] mtx [0:1], mtx_drv [0:1];
    reg  [63:0] mtx_d1, mtx_d2;
    reg  [511:0] imp [0:1];
    reg force_bad = 0, fb_a = 0, fb_b = 0;
    wire fa [0:1];
    genvar s;
    generate for (s = 0; s < 2; s = s + 1) begin : g_side
        ot_s81hd_best64_tx u_tx (.ck(ck), .rn(rst_n), .v(tv[s]), .frame(tf[s]), .lane(mtx[s]), .fault(fa[s]));
        assign mtx_drv[s] = (s == 0 && force_bad) ? {1'b1, 1'b1, 62'h155} : mtx[s];
    end endgenerate
    always @(posedge ck) begin mtx_d1 <= mtx_drv[0]; mtx_d2 <= mtx_d1; end
    initial begin mtx_d1 = 0; mtx_d2 = 0; end
    // world R
    wire [511:0] roa [0:1], rob [0:1]; wire [63:0] rmrx [0:1];
    ot_s81hd_mesh_ep_core #(.BQ(BQ), .MUT(MUT)) r_x (.ck(ck), .rst_n(rst_n), .coll_ia({1'b1, fb_a, roa[1]}), .coll_oa(roa[0]),
        .coll_ib({1'b1, fb_b, rob[1] ^ imp[1]}), .coll_ob(rob[0]), .m_tx_i(mtx_d2), .m_rx_o(rmrx[0]));
    ot_s81hd_mesh_ep_core #(.BQ(BQ), .MUT(MUT)) r_y (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, roa[0]}), .coll_oa(roa[1]),
        .coll_ib({2'b10, rob[0] ^ imp[0]}), .coll_ob(rob[1]), .m_tx_i(mtx_drv[1]), .m_rx_o(rmrx[1]));
    // world S
    wire [511:0] soa [0:1], sob [0:1]; wire [63:0] smrx [0:1];
    ot_s81hd_mesh_split_ref #(.BQ(BQ), .MUT(MUT), .SPLIT_MUT(SPLIT_MUT)) s_x (.ck(ck), .rst_n(rst_n),
        .coll_ia({1'b1, fb_a, soa[1]}), .coll_oa(soa[0]), .coll_ib({1'b1, fb_b, sob[1] ^ imp[1]}), .coll_ob(sob[0]),
        .m_tx_i(mtx_drv[0]), .m_rx_o(smrx[0]));
    ot_s81hd_mesh_ep_core #(.BQ(BQ), .MUT(MUT)) s_y (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, soa[0]}), .coll_oa(soa[1]),
        .coll_ib({2'b10, sob[0] ^ imp[0]}), .coll_ob(sob[1]), .m_tx_i(mtx_drv[1]), .m_rx_o(smrx[1]));
    // S.X ctl-side decoder (non-vacuity)
    wire va, vb, rfv; wire [552:0] rfr; wire [11:0] epf;
    ot_s81hd_mesh64_rx u_rx (.ck(ck), .rn(rst_n), .lane(smrx[0]), .va(va), .vb(vb), .frame(rfr), .ep_fault(epf), .fault(rfv));
    function automatic [96:0] body(input integer side, input integer k);
        reg [31:0] h; reg [80:0] r; integer b; begin
            h = 32'h9e3779b9 * (k + 7) ^ (side * 32'h85ebca6b);
            for (b = 0; b < 81; b = b + 1) begin r[b] = h[b % 32] ^ h[(b / 32 + k) % 32]; if (b % 32 == 31) h = h ^ (h << 13) ^ (h >> 7); end
            r[0] = 1'b1;
            body = {r, 8'd0, 2'(side), 2'(k), 4'd1};
        end endfunction
    integer c = 0, i, sk [0:1], gap [0:1], ea = 0, eb = 0, ey = 0, em = 0, na = 0, nb = 0, nw = 0, first = -1;
    reg [63:0] rm1, rm2;
    initial for (i = 0; i < 2; i = i + 1) begin sk[i] = 0; gap[i] = 0; tv[i] = 0; tf[i] = 0; imp[i] = 0; end
    initial begin rm1 = 0; rm2 = 0; end
    always @(negedge ck) begin
        c = c + 1;
        rst_n = (c >= 8);
        force_bad = (c == FBAD);
        fb_b = (c >= P2 + 1000 && c < P2 + 1040); fb_a = (c >= P2 + 1200 && c < P2 + 1240);
        if (c == P2 + 590) begin force r_y.own_frame[552] = 1'b0; force s_y.own_frame[552] = 1'b0; end
        if (c == P2 + 700) begin release r_y.own_frame[552]; release s_y.own_frame[552]; end
        if (soa[0] !== roa[0]) begin ea = ea + 1; if (first < 0) first = c; end
        if (sob[0] !== rob[0]) begin eb = eb + 1; if (first < 0) first = c; end
        if (soa[1] !== roa[1] || sob[1] !== rob[1] || smrx[1] !== rmrx[1]) begin ey = ey + 1; if (first < 0) first = c; end
        if (c > 2 && smrx[0] !== rm1) begin em = em + 1; if (first < 0) first = c; end
        if (smrx[0] != 0) nw = nw + 1;
        rm2 = rm1; rm1 = rmrx[0];
        if (rst_n) begin if (va) na = na + 1; if (vb) nb = nb + 1; end
        rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
        imp[0] = 0; imp[1] = 0;
        if (c >= 1000 && c < 1200 && c % 16 == 0) imp[0] = {rng, rng[15:0]} << 96;
        if (c >= 2000 && c < 2200 && c % 16 == 8) imp[1] = {rng[7:0], rng} << 300;
        for (i = 0; i < 2; i = i + 1) begin
            tv[i] = rst_n && c > 60 && c < P2 - 600 && sk[i] < NREC && gap[i] >= 6 && rng[i * 3 + 1];
            if ((c == P2 + 200 || c == P2 + 600 || c == P2 + 1400) && i == 1) tv[i] = 1'b1;   // P2+1400: carries the phase-3 fault vector
            gap[i] = tv[i] ? 0 : gap[i] + 1;
            tf[i] = {1'b1, 455'd0, body(i, sk[i])};
            if (tv[i]) sk[i] = sk[i] + 1;
        end
`ifdef MESH_TRACE
        if (c > P2 && c < P2 + 400 && (s_x.u_a.own_f0 || s_x.u_a.iss_q)) $display("TRACE c=%0d own_f0=%b iss_q=%b", c, s_x.u_a.own_f0, s_x.u_a.iss_q);
`endif
        if (c == NCYC) begin
            $display("MESH_SPLIT_STATS cycles=%0d mismatches coll_oa=%0d coll_ob=%0d peer=%0d m_rx_o(+2)=%0d first=%0d copyA=%0d copyB=%0d words=%0d sent=%0d/%0d epf=%h",
                c, ea, eb, ey, em, first, na, nb, nw, sk[0], sk[1], epf);
            if (ea + eb + ey + em != 0) $display("MESH_SPLIT FAIL lockstep mismatch (first at edge %0d)", first);
            else if (na < NREC || nb < NREC) $display("MESH_SPLIT FAIL vacuous traffic copyA %0d copyB %0d < %0d", na, nb, NREC);
            else if (epf[3:0] == 0 || epf[7:4] == 0 || !epf[8] || !epf[9]) $display("MESH_SPLIT FAIL vacuous fault phase: S.X ep_fault %h (want lane a / lane b / m_tx / ncan bits)", epf);
            else $display("MESH_SPLIT PASS split == unsplit (m_tx_i +2, m_rx_o +2) for %0d edges, %0d/%0d records x 2 copies", c, na, nb);
            $finish;
        end
    end
endmodule
