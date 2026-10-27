`timescale 1ns/1ps
// HEAD-CORE-R17 2026-10-27 (COORD ruling 5 on HEAD-CORE-R15 / RULING HEAD-RTL-4): copy-B burst-FIFO depth at the
// PRODUCTION static schedule under the WORST replay stall the production link protocol allows without declaring a fault.
// Two ot_s81hd_mesh_ep_core endpoints X / Y cross-connected as tb_s81hd_mesh_ep.  Records: both sides send one canonical
// BEST record every T = 8,357 cycles (the minimum static position period, rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv).
// Impairment (lane b only, cycles [W0, W0 + W)): every X -> Y lane-b beat has its data payload corrupted (gpay bits
//   [143:56], CRC-protected flit bits / slot framing) AND every Y -> X lane-b beat has its reverse frame (bits [55:3],
//   own CRC: Y's ACK / NAK for X's sender) corrupted.  X's lane-b sender therefore gets neither ACK nor NAK and rewinds
//   on its ACK timeout only (ATOB = 1,481 cycles at CH_BOARD 700, the longest the lane has), once per timeout; the
//   link declares a fault (retry_exh) at the 9th rewind without progress (MAX_RETRY 8).  The window W (plusarg +W=)
//   is swept by results/s81_head_r17/copyb/run.sh: the largest W without a link fault is the worst stall.
// +BOTH: lane a (copy A) gets the same blackout, so both copies replay identically and their bursts land on the same
//   edges; copy A has priority on the word port, so copy B must hold its whole burst (the worst case for the FIFO).
// Checks: every record arrives at the peer ctl ONCE as copy A and ONCE as copy B, in order, bit-exact (97 b); no
//   endpoint fault (ep_fault vector, word fault) unless +EXPECT_LINKFAULT (W beyond the protocol limit).
// Prints the copy-B extra latency S (max lateness - nominal) and the peak FIFO occupancy (records held + landing).
module tb_s81hd_mesh_ep_burst;
    parameter integer BQ = 2, MUT = 0, T = 8357, NREC = 5, T0 = 2000;
    reg ck = 0, rst_n = 0; always #0.5 ck = ~ck;
    integer W = 0, W0;
    reg tv [0:1]; reg [552:0] tf [0:1];
    wire [63:0] mtx [0:1], mrx [0:1];
    wire [511:0] oa [0:1], ob [0:1];
    reg  [511:0] imp [0:1];
    integer both = 0;                                     // +BOTH: lane a gets the SAME blackout (common-mode)
    wire fa [0:1], vb_ [0:1], va_ [0:1], rf [0:1];
    wire [552:0] rfr [0:1]; wire [11:0] epf [0:1];
    genvar s;
    generate for (s = 0; s < 2; s = s + 1) begin : g_side
        ot_s81hd_best64_tx u_tx (.ck(ck), .rn(rst_n), .v(tv[s]), .frame(tf[s]), .lane(mtx[s]), .fault(fa[s]));
        ot_s81hd_mesh64_rx u_rx (.ck(ck), .rn(rst_n), .lane(mrx[s]), .va(va_[s]), .vb(vb_[s]), .frame(rfr[s]),
            .ep_fault(epf[s]), .fault(rf[s]));
    end endgenerate
    ot_s81hd_mesh_ep_core #(.BQ(BQ), .MUT(MUT)) u_x (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, oa[1] ^ (both ? imp[1] : 512'd0)}), .coll_oa(oa[0]),
        .coll_ib({2'b10, ob[1] ^ imp[1]}), .coll_ob(ob[0]), .m_tx_i(mtx[0]), .m_rx_o(mrx[0]));
    ot_s81hd_mesh_ep_core #(.BQ(BQ), .MUT(MUT)) u_y (.ck(ck), .rst_n(rst_n), .coll_ia({2'b10, oa[0] ^ (both ? imp[0] : 512'd0)}), .coll_oa(oa[1]),
        .coll_ib({2'b10, ob[0] ^ imp[0]}), .coll_ob(ob[1]), .m_tx_i(mtx[1]), .m_rx_o(mrx[1]));
    wire [31:0] to_xb = u_x.u_lb.u_ln.u.u_ep.st_timeouts, rp_xb = u_x.u_lb.u_ln.u.u_ep.st_replays;
    wire [31:0] ce_yb = u_y.u_lb.u_ln.u.u_ep.st_crc_err;
    wire        lf_xb = u_x.u_lb.u_ln.u.u_ep.fault;
    function automatic [96:0] body(input integer side, input integer k);
        reg [31:0] h; reg [80:0] r; integer b; begin
            h = 32'h9e3779b9 * (k + 7) ^ (side * 32'h85ebca6b);
            for (b = 0; b < 81; b = b + 1) begin r[b] = h[b % 32] ^ h[(b / 32 + k) % 32]; if (b % 32 == 31) h = h ^ (h << 13) ^ (h >> 7); end
            r[0] = 1'b1;
            body = {r, 8'd0, 2'(side), 2'(k), 4'd1};
        end endfunction
    integer c = 0, err = 0, i, sk [0:1], ra [0:1], rb [0:1], f1 = 0, lmin_b = 1 << 30, lmax_b = 0, lmax_a = 0;
    integer ts [0:1][0:63];
    integer pk_a = 0, pk_b = 0, ncyc, expect_lf = 0;
    reg [31:0] rng = 32'h1f2e3d4c;
    always @(posedge ck) begin
        if (u_x.na + u_x.la > pk_a) pk_a = u_x.na + u_x.la; if (u_y.na + u_y.la > pk_a) pk_a = u_y.na + u_y.la;
        if (u_x.nb + u_x.lb > pk_b) pk_b = u_x.nb + u_x.lb; if (u_y.nb + u_y.lb > pk_b) pk_b = u_y.nb + u_y.lb;
    end
    initial begin
        if (!$value$plusargs("W=%d", W)) W = 0;
        if ($test$plusargs("EXPECT_LINKFAULT")) expect_lf = 1;
        if ($test$plusargs("BOTH")) both = 1;
        W0 = T0 + 2 * T - 50;                                   // window opens just before X's record 2 is sent
        ncyc = T0 + NREC * T + 20000;
        for (i = 0; i < 2; i = i + 1) begin sk[i] = 0; ra[i] = 0; rb[i] = 0; tv[i] = 0; tf[i] = 0; imp[i] = 0; end
    end
    always @(negedge ck) begin
        c = c + 1;
        rst_n = (c >= 8);
        for (i = 0; i < 2; i = i + 1) if (rst_n) begin
            if (va_[i]) begin
                if (rfr[i][96:0] !== body(1 - i, ra[i]) || ra[i] >= sk[1 - i]) begin err = err + 1; if (err < 8) $display("MESH_DATA_ERR c=%0d side=%0d copyA rec=%0d", c, i, ra[i]); end
                if (c - ts[1 - i][ra[i] % 64] > lmax_a) lmax_a = c - ts[1 - i][ra[i] % 64];
                ra[i] = ra[i] + 1;
            end
            if (vb_[i]) begin
                if (rfr[i][96:0] !== body(1 - i, rb[i]) || rb[i] >= sk[1 - i]) begin err = err + 1; if (err < 8) $display("MESH_DATA_ERR c=%0d side=%0d copyB rec=%0d", c, i, rb[i]); end
                if (c - ts[1 - i][rb[i] % 64] > lmax_b) lmax_b = c - ts[1 - i][rb[i] % 64];
                if (c - ts[1 - i][rb[i] % 64] < lmin_b) lmin_b = c - ts[1 - i][rb[i] % 64];
                rb[i] = rb[i] + 1;
            end
            if (tv[i]) begin ts[i][sk[i] % 64] = c - 1; sk[i] = sk[i] + 1; end
        end
        if (epf[0] != 0 || epf[1] != 0 || rf[0] || rf[1] || fa[0] || fa[1]) f1 = 1;
        rng = rng ^ (rng << 13); rng = rng ^ (rng >> 17); rng = rng ^ (rng << 5);
        imp[0] = 0; imp[1] = 0;
        if (c >= W0 && c < W0 + W) begin
            imp[0] = {rng[23:0], rng, rng} << 56;               // X -> Y lane b: data payload bits [143:56]
            imp[1] = {rng[20:0], rng} << 3;      // Y -> X lane b: reverse frame bits [55:3]
            imp[0][56] = 1'b1; imp[1][3] = 1'b1;                 // never an all-zero mask
        end
        for (i = 0; i < 2; i = i + 1) begin
            tv[i] = rst_n && c >= T0 && (c - T0) % T == 0 && sk[i] < NREC;   // static schedule: one record per T
            tf[i] = {1'b1, 455'd0, body(i, sk[i])};
        end
        if (c == ncyc) begin
            $display("MESH_BURST both=%0d W=%0d W0=%0d T=%0d BQ=%0d sent=%0d/%0d copyA=%0d/%0d copyB=%0d/%0d errors=%0d fault=%0d epf=%h/%h link_fault_xb=%0d",
                both, W, W0, T, BQ, sk[0], sk[1], ra[1], ra[0], rb[1], rb[0], err, f1, epf[0], epf[1], lf_xb);
            $display("MESH_BURST_STALL timeouts_xb=%0d replays_xb=%0d crc_err_yb=%0d copyB_latency min=%0d max=%0d S=%0d copyA_max=%0d",
                to_xb, rp_xb, ce_yb, lmin_b, lmax_b, lmax_b - lmin_b, lmax_a);
            $display("MESH_FIFO BQ=%0d peak_occupancy copyA=%0d copyB=%0d", BQ, pk_a, pk_b);
            if (expect_lf) begin
                if (lf_xb) $display("MESH_EP LINKFAULT (expected: W beyond the protocol retry limit)");
                else $display("MESH_EP FAIL expected a link fault");
            end
            else if (err != 0 || ra[0] != sk[1] || rb[0] != sk[1] || ra[1] != sk[0] || rb[1] != sk[0] || sk[0] < NREC)
                $display("MESH_EP FAIL data: errors %0d", err);
            else if (f1 != 0) $display("MESH_EP FAIL fault (epf %h/%h)", epf[0], epf[1]);
            else $display("MESH_EP PASS records %0d/%0d x 2 copies exact, no fault", ra[1], ra[0]);
            $finish;
        end
    end
endmodule
