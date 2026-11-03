`timescale 1ns/1ps
// DIE-QC-63/RED equivalence bench: as-built qfd_dv_s5_red2_leaf (main, renamed *_old) vs
//   (a) the H1-capable leaf at HARD_PINREG 0 (default users unchanged): every output identical every edge;
//   (b) the plan variant qfd_dv_s5_red2p1_leaf (relay + H1 core + exact rd_v + covering busy):
//       P1 red_we/red_addr/red_data == old delayed L = IN+OUT edges (every edge after warm-up)
//       P2 fault == old fault delayed IN edges
//       P3 rd_v == old rd_v (same edge)
//       P4 old busy -> new busy (su8 idle never earlier)
//       P5 new busy -> old busy within the last L+1 edges (stretch bounded by L)
// plusargs: +cycles=N +seed=S ; defines: DUT_MOD (variant module), LEXP (expected L; default IN+OUT)
module tb;
    parameter integer IN = 2, OUT = 3;
`ifndef DUT_MOD
 `define DUT_MOD qfd_dv_s5_red2p1_leaf
`endif
`ifndef LEXP
 `define LEXP (IN+OUT)
`endif
    localparam integer L = `LEXP;
    reg ck = 0, rst_n = 0;
    reg [7:0] l_ov; reg [255:0] l_out; reg [1:0] l_red0; reg l_redsq0, l_last0; reg [23:0] l_raddr0;
    wire o_we, o_rdv, o_busy, o_fault; wire [23:0] o_addr; wire [31:0] o_data;
    wire h_we, h_rdv, h_busy, h_fault; wire [23:0] h_addr; wire [31:0] h_data;
    wire n_we, n_rdv, n_busy, n_fault; wire [23:0] n_addr; wire [31:0] n_data;
    qfd_dv_s5_red2_leaf_old u_old (.ck(ck), .rst_n(rst_n), .l_ov(l_ov), .l_out(l_out), .l_red0(l_red0), .l_redsq0(l_redsq0),
        .l_last0(l_last0), .l_raddr0(l_raddr0), .red_we(o_we), .red_addr(o_addr), .red_data(o_data), .rd_v(o_rdv), .busy(o_busy), .fault(o_fault));
    qfd_dv_s5_red2_leaf #(.HARD_PINREG(0)) u_h0 (.ck(ck), .rst_n(rst_n), .l_ov(l_ov), .l_out(l_out), .l_red0(l_red0), .l_redsq0(l_redsq0),
        .l_last0(l_last0), .l_raddr0(l_raddr0), .red_we(h_we), .red_addr(h_addr), .red_data(h_data), .rd_v(h_rdv), .busy(h_busy), .fault(h_fault));
    `DUT_MOD #(.IN_STAGES(IN), .OUT_STAGES(OUT)) u_new (.ck(ck), .rst_n(rst_n), .l_ov(l_ov), .l_out(l_out), .l_red0(l_red0), .l_redsq0(l_redsq0),
        .l_last0(l_last0), .l_raddr0(l_raddr0), .red_we(n_we), .red_addr(n_addr), .red_data(n_data), .rd_v(n_rdv), .busy(n_busy), .fault(n_fault));
    // history of old outputs
    localparam integer HD = 16;
    reg [HD-1:0] hwe, hbusy, hfault; reg [55:0] hdat [0:HD-1];
    integer cyc = 0, ncyc = 20000, seed = 1, i, k, e0 = 0, e1 = 0, e2 = 0, e3 = 0, e4 = 0, e5 = 0, e6 = 0, nwe = 0, nbusy = 0, nflt = 0, burst = 0, nfall = 0;
    reg orb; integer mode, gap = 0;
    initial begin
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 20000;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        l_ov = 0; l_out = 0; l_red0 = 0; l_redsq0 = 0; l_last0 = 0; l_raddr0 = 0;
        repeat (6) @(posedge ck);
        #0.1 rst_n = 1;
    end
    always #0.5 ck = ~ck;
    // stimulus: bursts of reduction words (segments of random length ending in last), idle gaps, rare junk words
    integer hold = 24;                   // lanes idle while the reset releases (upstream is in reset too)
    always @(negedge ck) if (rst_n && hold > 0) hold = hold - 1;
    else if (rst_n) begin
        if (gap > 0) begin
            gap = gap - 1;                // idle lanes: no valid word (lets busy fall, exercises su8 idle)
            l_ov <= 0; l_red0 <= 0; l_last0 <= 0;
        end else if (burst == 0) begin
            mode = $urandom(seed) % 8; seed = seed + 1;
            burst = (mode < 5) ? 1 + ($urandom % 40) : 0;
            if (burst == 0) begin
                gap = 1 + ($urandom % 64);
                l_ov <= ($urandom % 64 == 0) ? $urandom : 0; l_red0 <= $urandom % 4; l_last0 <= $urandom % 2;
            end else begin
                l_ov <= 0; l_red0 <= 0; l_last0 <= 0;
            end
        end else begin
            burst = burst - 1;
            l_ov <= ($urandom % 4 == 0) ? 8'hff : $urandom; l_red0 <= 1 + ($urandom % 2) + (($urandom % 32 == 0) ? 1 : 0);
            l_last0 <= (burst == 0) || ($urandom % 9 == 0);
        end
        l_out <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        l_redsq0 <= $urandom % 2; l_raddr0 <= $urandom;
    end
    always @(posedge ck) begin
        #0.2;
        hwe <= {hwe, o_we}; hbusy <= {hbusy, o_busy}; hfault <= {hfault, o_fault};
        for (i = HD-1; i > 0; i = i - 1) hdat[i] <= hdat[i-1];
        hdat[0] <= {o_addr, o_data};
        cyc = cyc + 1;
        if (cyc > 40) begin
            if ({h_we, h_addr, h_data, h_rdv, h_busy, h_fault} !== {o_we, o_addr, o_data, o_rdv, o_busy, o_fault}) begin
                e0 = e0 + 1; if (e0 < 5) $display("H0 MISMATCH cyc %0d", cyc); end
            if (n_we !== hwe[L-1]) begin e1 = e1 + 1; if (e1 < 5) $display("P1 we MISMATCH cyc %0d", cyc); end
            if (n_we && {n_addr, n_data} !== hdat[L-1]) begin e2 = e2 + 1; if (e2 < 5) $display("P1 data MISMATCH cyc %0d", cyc); end
            if (n_fault !== hfault[IN-1]) begin e3 = e3 + 1; if (e3 < 5) $display("P2 fault MISMATCH cyc %0d", cyc); end
            if (n_rdv !== o_rdv) begin e4 = e4 + 1; if (e4 < 5) $display("P3 rd_v MISMATCH cyc %0d", cyc); end
            if (o_busy && !n_busy) begin e5 = e5 + 1; if (e5 < 5) $display("P4 busy NOT COVERED cyc %0d", cyc); end
            orb = o_busy; for (k = 0; k <= L; k = k + 1) orb = orb | hbusy[k];
            if (n_busy && !orb) begin e6 = e6 + 1; if (e6 < 5) $display("P5 busy stretch > L cyc %0d", cyc); end
            nwe = nwe + o_we; nbusy = nbusy + o_busy; nflt = nflt + o_fault; nfall = nfall + (hbusy[0] && !o_busy);
        end
        if (cyc == ncyc) begin
            $display("RESULT cycles %0d L %0d old_writes %0d old_busy_cycles %0d old_fault_cycles %0d busy_falls %0d | H0 %0d P1we %0d P1data %0d P2 %0d P3 %0d P4 %0d P5 %0d",
                     ncyc, L, nwe, nbusy, nflt, nfall, e0, e1, e2, e3, e4, e5, e6);
            if (e0 + e1 + e2 + e3 + e4 + e5 + e6 == 0 && nwe > 100 && nfall > 10) $display("VERDICT PASS"); else $display("VERDICT FAIL");
            $finish;
        end
    end
endmodule
