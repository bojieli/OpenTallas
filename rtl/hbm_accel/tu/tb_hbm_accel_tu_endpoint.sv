`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_hbm_accel_tu_endpoint: ONE die's switched-tier collective endpoint
// (ot_hbm_accel_tu_endpoint, RTL) at DS-V4.1 TP-96 shape, its far side a
// BEHAVIOURAL Tomahawk-Ultra-tier stub (minimum component, owner rule).
//
// The stub stands for: the die's Ethernet PHY/FEC (Tx and Rx), the cable and
// the switch -- ONE labelled budget +BUDGET (ns) from a flit leaving this
// die's serializer to the same flit reaching the destination die's RX CDC
// (default 377.6 = uarch_model.TU endpoint_phy 100 + switch 250 + cable
// 27.6, VENDOR BUDGET).  It multicasts results, and replays the other ranks
// SYMMETRICALLY: every die runs the same RTL on the same schedule, so peer
// j's flit for us leaves its serializer when our corresponding flit leaves
// ours (partials: our flit to owner s <-> peer 2J - s's flit to us, the
// rotated injection order makes it exact; results / gather segments: our
// result m <-> every other owner's result m).  Egress to this die is paced
// per port at the die's own serializer rate (the RX PHY's line rate) and
// spends this die's receive-buffer credits; credits (both directions) return
// after +CRED ns (labelled reverse-link latency).
// Data: partials from the fixture (part.hex), results / gather words from
// the golden image (expected.hex).  Every delivered word is checked; for an
// all-reduce the die's OWN slice is computed by the RTL tree from real
// operands (bit-exact proof), the rest is placement.
// ---------------------------------------------------------------------------
`ifndef TU_NC
`define TU_NC 8
`endif
`ifndef TU_NOG
`define TU_NOG 8
`endif
`ifndef TU_PFMAX
`define TU_PFMAX 384
`endif
`ifndef TU_BF16
`define TU_BF16 1
`endif
`ifndef TU_INJ
`define TU_INJ 2
`endif
`ifndef TU_DEL
`define TU_DEL 4
`endif
`ifndef TU_NPT
`define TU_NPT 8
`endif
`ifndef TU_DUT
`define TU_DUT ot_hbm_accel_tu_endpoint   // hbm-coll-rtl: +define+TU_DUT=ot_hbm_accel_tu_endpoint_sr
`endif
`ifndef TU_RXAW
`define TU_RXAW 8
`endif
module tb_hbm_accel_tu_endpoint #(
    parameter integer NC = `TU_NC, NOG = `TU_NOG, PFMAX = `TU_PFMAX, BF16 = `TU_BF16,
    parameter integer INJ = `TU_INJ, DEL = `TU_DEL, NPT = `TU_NPT, RXAW = `TU_RXAW,
    parameter integer LANES = 16, HUBW = 35, WSTG = 14, BITS_X100 = 72000, PWB = 545, LAT = 7,
    parameter real    T_CORE = 0.833333, T_PHY = 1.0
);
    localparam integer FW = 32 * LANES, PWT = FW + 33, NR = NOG * NC;
    localparam integer MAXL = NR * PFMAX;
    integer seed, seed0, pf, rank;
    real budget, cred;
    string vecdir;
    reg [FW-1:0] part [0:MAXL-1];      // AR: contributor partials; gather: every rank's segment
    reg [FW-1:0] expw [0:MAXL-1];      // AR: result image (BF16 packed)
    reg go_clk = 0, go = 0;
    real ph0, ph1;
    integer OF, ROF, TOT, OG, J;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("VEC=%s", vecdir)) $fatal(1, "missing VEC");
        if (!$value$plusargs("PF=%d", pf)) $fatal(1, "missing PF");
        if (!$value$plusargs("RANK=%d", rank)) rank = 0;
        if (!$value$plusargs("BUDGET=%f", budget)) budget = 377.6;
        if (!$value$plusargs("CRED=%f", cred)) cred = 113.8;
        if (pf > PFMAX || pf % NC != 0 || (BF16 && (pf / NC) % 2 != 0)) $fatal(1, "bad PF");
        ph0 = (($unsigned($random(seed)) % 1000) / 1000.0);
        ph1 = (($unsigned($random(seed)) % 1000) / 1000.0);
        $readmemh({vecdir, "/part.hex"}, part);
        if (NC > 1) $readmemh({vecdir, "/expected.hex"}, expw);
        OF = pf / NC; ROF = BF16 ? OF / 2 : OF; OG = rank / NC; J = rank % NC;
        TOT = (NC > 1) ? NR * ROF : (NR - 1) * pf;
        $display("TUCFG seed=%0d rank=%0d NC=%0d NOG=%0d PF=%0d INJ=%0d DEL=%0d NPT=%0d RXAW=%0d BUDGET=%0.2f CRED=%0.2f T_CORE=%f T_PHY=%f TOT=%0d",
                 seed0, rank, NC, NOG, pf, INJ, DEL, NPT, RXAW, budget, cred, T_CORE, T_PHY, TOT);
        go_clk = 1;
    end
    reg clk = 0, pclk_r = 0, rst_n = 0, prst_n = 0;
    initial begin wait(go_clk); #(T_CORE * ph0 + 0.001); forever #(T_CORE/2) clk = ~clk; end
    initial begin wait(go_clk); #(T_PHY * ph1 + 0.001);  forever #(T_PHY/2) pclk_r = ~pclk_r; end
`ifdef TU_PCLK_IS_CLK
    wire pclk = clk;      // hbm-coll-rtl: the hfd_coll die view wires pclk = clk (SYNCPHY = 1 endpoints)
`else
    wire pclk = pclk_r;
`endif
    always @(posedge clk)  rst_n  <= ($realtime > 40.0);
    always @(posedge pclk) prst_n <= ($realtime > 40.0);
    initial begin wait(go_clk); #(400.0); @(posedge clk); go <= 1'b1; end

    wire [INJ*16-1:0] ii;
    wire [INJ-1:0] ir;
    reg  [INJ*FW-1:0] idata;
    always @* for (integer i = 0; i < INJ; i = i + 1) idata[FW*i +: FW] = part[rank * pf + integer'(ii[16*i +: 16])];
    wire [NPT-1:0] txv, rxc, fault_v;
    wire [NPT*PWT-1:0] txf;
    reg  [NPT-1:0] crr = 0, rxv = 0;
    reg  [NPT*PWT-1:0] rxf = 0;
    wire [DEL-1:0] dv;
    wire [DEL*PWT-1:0] dfl;
    wire flt;
    wire [31:0] cst;
    `TU_DUT #(.ENABLE(1), .NC(NC), .NOG(NOG), .PFMAX(PFMAX), .LANES(LANES), .BF16(BF16), .NPT(NPT),
        .INJ(INJ), .DEL(DEL), .HUBW(HUBW), .WSTG(WSTG), .BITS_X100(BITS_X100), .PWB(PWB), .RXAW(RXAW),
        .SWCRED(1 << RXAW), .LAT(LAT)
`ifdef TU_SYNCPHY
        , .SYNCPHY(1)
`endif
        )
      dut (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n), .rank(8'(rank)), .pf(16'(pf)), .go(go),
           .inj_idx(ii), .inj_rd(ir), .inj_data(idata), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
           .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt),
           .stat_credit_stall(cst));

    // ---- stub: egress queues per port, credits ------------------------------------------------------------
    real          eq_t [NPT][$];
    reg [PWT-1:0] eq_f [NPT][$];
    real          cr_eg [NPT][$];     // egress credits returning to the switch (from rx_credit)
    real          cr_in [NPT][$];     // ingress credits returning to the die (from departures)
    integer       eg_cred [0:NPT-1];
    integer       eacc [0:NPT-1];
    real t_issue = -1, t_fdep = -1, t_ldep = -1, t_farr = -1, t_larr = -1, t_done = -1, t_fres = -1, t_lres = -1;
    integer ndep = 0, narr = 0, nres = 0;
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 1 << RXAW; eacc[p] = 0; end
    always @(posedge clk) if (go && t_issue < 0) t_issue = $realtime;

    task automatic sched(input integer p, input real t, input [PWT-1:0] f);
        eq_t[p].push_back(t); eq_f[p].push_back(f);
    endtask

    // departures (die PHY clock): record, schedule symmetric arrivals, ingress credit return
    always @(posedge pclk) begin
        for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
            reg [PWT-1:0] f;
            integer kind, dst, src, idx, sl, jp, m;
            real ta;
            f = txf[p*PWT +: PWT];
            kind = integer'(f[PWT-1]); dst = integer'(f[FW+24 +: 8]); src = integer'(f[FW+16 +: 8]);
            idx = integer'(f[FW +: 16]);
            if (t_fdep < 0) t_fdep = $realtime;
            t_ldep = $realtime; ndep = ndep + 1;
            ta = $realtime + budget;
            cr_in[p].push_back($realtime + cred);
            if (kind == 0) begin                           // partial to owner dst: peer 2J - s sends us its slice-J flit
                sl = dst - OG * NC;
                jp = ((2 * J - sl) % NC + NC) % NC;
                sched(p, ta, {1'b0, 8'(rank), 8'(jp), 16'(idx), part[(OG * NC + jp) * pf + J * OF + idx]});
            end else if (NC > 1) begin                     // our result m: every other owner's result m
                m = idx - (OG * NC + J) * ROF;
                if (t_fres < 0) t_fres = $realtime;
                t_lres = $realtime; nres = nres + 1;
                for (integer o = 0; o < NR; o = o + 1) if (o != rank)
                    sched((o + m) % NPT, ta, {1'b1, 8'hFF, 8'(o / NC), 16'(o * ROF + m), expw[o * ROF + m]});
            end else begin                                 // gather segment flit m: every peer's flit m
                m = idx - rank * pf;
                for (integer q = 0; q < NR; q = q + 1) if (q != rank)
                    sched((q + m) % NPT, ta, {1'b1, 8'hFF, 8'(q), 16'(q * pf + m), part[q * pf + m]});
            end
        end
    end
    // egress (die PHY clock): head ready, credit, line-rate pacing
    always @(posedge pclk) begin
        for (integer p = 0; p < NPT; p = p + 1) begin : eg
            integer a;
            while (cr_eg[p].size() > 0 && cr_eg[p][0] <= $realtime) begin void'(cr_eg[p].pop_front()); eg_cred[p] = eg_cred[p] + 1; end
            a = eacc[p] + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            rxv[p] <= 1'b0;
            if (eq_t[p].size() > 0 && eq_t[p][0] <= $realtime && eg_cred[p] > 0 && a >= PWB * 100) begin
                rxv[p] <= 1'b1;
                rxf[p*PWT +: PWT] <= eq_f[p][0];
                void'(eq_t[p].pop_front()); void'(eq_f[p].pop_front());
                eg_cred[p] = eg_cred[p] - 1;
                a = a - PWB * 100;
                if (t_farr < 0) t_farr = $realtime;
                t_larr = $realtime; narr = narr + 1;
            end
            eacc[p] = a;
        end
    end
    // credits (core clock side)
    always @(posedge clk) begin
        for (integer p = 0; p < NPT; p = p + 1) begin
            if (rxc[p]) cr_eg[p].push_back($realtime + cred);
            crr[p] <= 1'b0;
            if (cr_in[p].size() > 0 && cr_in[p][0] <= $realtime) begin void'(cr_in[p].pop_front()); crr[p] <= 1'b1; end
        end
    end

    // ---- checker ------------------------------------------------------------------------------------------
    integer got = 0, mism = 0, own_ok = 0;
    reg seen [0:MAXL-1];
    initial for (integer i = 0; i < MAXL; i = i + 1) seen[i] = 0;
    always @(posedge clk) begin
        for (integer i = 0; i < DEL; i = i + 1) if (dv[i]) begin : chk
            integer gi;
            reg [FW-1:0] want;
            gi = integer'(dfl[i*PWT + FW +: 16]);
            want = (NC > 1) ? expw[gi] : part[gi];
            if (gi >= MAXL || seen[gi] || dfl[i*PWT +: FW] !== want) begin
                mism = mism + 1;
                if (mism < 10) $display("TUMISMATCH gi=%0d", gi);
            end else if (NC > 1 && gi / ROF == rank) own_ok = own_ok + 1;
            if (gi < MAXL) seen[gi] = 1;
            got = got + 1;
            if (got == TOT) t_done = $realtime;
        end
    end
    initial begin
        wait (t_done > 0);
        repeat (20) @(posedge clk);
        $display("TUDONE seed=%0d rank=%0d pf=%0d lat_ns=%0.3f lat_cyc=%0.1f tx_first_ns=%0.3f tx_last_ns=%0.3f rx_first_ns=%0.3f rx_last_ns=%0.3f res_first_ns=%0.3f res_last_ns=%0.3f deliver_tail_ns=%0.3f ndep=%0d narr=%0d nres=%0d got=%0d own_exact=%0d mismatches=%0d faults=%0d credit_stall=%0d",
                 seed0, rank, pf, t_done - t_issue, (t_done - t_issue) / T_CORE, t_fdep - t_issue, t_ldep - t_issue,
                 t_farr - t_issue, t_larr - t_issue, t_fres - t_issue, t_lres - t_issue, t_done - t_larr,
                 ndep, narr, nres, got, own_ok, mism, flt, cst);
        $finish;
    end
    initial begin #(400000.0); $display("TUTIMEOUT got=%0d of %0d ndep=%0d narr=%0d", got, TOT, ndep, narr); $finish; end
endmodule
