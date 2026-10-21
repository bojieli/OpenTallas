`timescale 1ps/1fs
// KV-PC 2026-10-19: lockstep REF ot_qkd_static_emb_cdc (flop Gray FIFOs) vs DUT ot_qkd_static_emb_cdc_kvpc_s (down / up
// FIFO arrays in native banks).  Core clk 834 ps, HBM hclk 1024 ps (+0.3 ps).  Random pulses on both sides at several
// rates (bursts overflow the 8-entry FIFOs: fault paths), two reset events (each domain alone, then both).
// Compared every edge of both clocks: c_v, s_credit, e_v, fault_core, fault_hbm exactly; c_d / c_context whenever c_v,
// e_d whenever e_v (the payload of an EMPTY FIFO head is an undefined async read across domains in the original).
// Unqualified payload differences are counted and printed (information).  +define+KVPC_MUT=N: DUT MUT (1 down bank
// permutation, 2 down read without prefetch: must FAIL).
`ifndef KVPC_MUT
`define KVPC_MUT 0
`endif
module tb_kvpc_cdc;
    reg ck = 0, hck = 0;
    always #417 ck = ~ck;
    initial begin #0.3; forever #512 hck = ~hck; end
    reg rst_n = 0, hrst_n = 0;
    reg s_v, h_credit, h_v;
    reg [286:0] s_d;
    reg [61:0] s_ctx;
    reg [257:0] h_d;
    wire r_cv, d_cv, r_sc, d_sc, r_ev, d_ev, r_fc, d_fc, r_fh, d_fh;
    wire [286:0] r_cd, d_cd;
    wire [61:0] r_cc, d_cc;
    wire [257:0] r_ed, d_ed;
    ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ref (.clk(ck), .rst_n(rst_n), .hclk(hck), .hrst_n(hrst_n), .s_v(s_v), .s_d(s_d),
        .s_context(s_ctx), .c_v(r_cv), .c_d(r_cd), .c_context(r_cc), .h_credit(h_credit), .s_credit(r_sc), .h_v(h_v),
        .h_d(h_d), .e_v(r_ev), .e_d(r_ed), .fault_core(r_fc), .fault_hbm(r_fh));
    ot_qkd_static_emb_cdc_kvpc_s #(.ENABLE(1), .MUT(`KVPC_MUT)) u_dut (.clk(ck), .rst_n(rst_n), .hclk(hck),
        .hrst_n(hrst_n), .s_v(s_v), .s_d(s_d), .s_context(s_ctx), .c_v(d_cv), .c_d(d_cd), .c_context(d_cc),
        .h_credit(h_credit), .s_credit(d_sc), .h_v(h_v), .h_d(h_d), .e_v(d_ev), .e_d(d_ed), .fault_core(d_fc),
        .fault_hbm(d_fh));
    integer bad, chk, ncv, nev, ninfo, seed, edges, t, rate;
    task compare(input [8*3-1:0] ph); begin
        chk = chk + 1;
        if ({r_cv, r_sc, r_ev, r_fc, r_fh} !== {d_cv, d_sc, d_ev, d_fc, d_fh} ||
            (r_cv && {r_cd, r_cc} !== {d_cd, d_cc}) || (r_ev && r_ed !== d_ed)) begin
            bad = bad + 1;
            if (bad < 10) $display("MISMATCH %s t=%0t cv %b/%b cd %h/%h ev %b/%b ed %h/%h sc %b/%b fc %b/%b fh %b/%b", ph,
                $time, r_cv, d_cv, r_cd[31:0], d_cd[31:0], r_ev, d_ev, r_ed[31:0], d_ed[31:0], r_sc, d_sc, r_fc, d_fc,
                r_fh, d_fh);
        end
        if ((!r_cv && {r_cd, r_cc} !== {d_cd, d_cc}) || (!r_ev && r_ed !== d_ed)) ninfo = ninfo + 1;
        if (r_cv) ncv = ncv + 1;
        if (r_ev) nev = nev + 1;
    end endtask
    always @(negedge ck) compare("ck ");
    always @(negedge hck) compare("hck");
    always @(negedge ck) begin
        s_v <= rst_n && (($urandom % 100) < rate);
        s_d <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        s_ctx <= {$urandom, $urandom};
    end
    always @(negedge hck) begin
        h_v <= hrst_n && (($urandom % 100) < rate);
        h_credit <= hrst_n && (($urandom % 100) < rate);
        h_d <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
    end
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("edges=%d", edges)) edges = 20000;
        t = $urandom(seed);
        bad = 0; chk = 0; ncv = 0; nev = 0; ninfo = 0; rate = 20;
        s_v = 0; h_v = 0; h_credit = 0; s_d = 0; s_ctx = 0; h_d = 0;
        repeat (8) @(negedge hck);
        rst_n = 1; hrst_n = 1;
        for (t = 0; t < edges; t = t + 1) begin
            @(negedge hck);
            rate = ((t / 2000) % 3 == 0) ? 20 : ((t / 2000) % 3 == 1) ? 60 : 95;   // 95 %: bursts overrun (faults)
            if (t == edges / 3) begin hrst_n = 0; repeat (5) @(negedge hck); hrst_n = 1; end
            if (t == edges / 2) begin rst_n = 0; repeat (7) @(negedge ck); rst_n = 1; end
            if (t == 2 * edges / 3) begin rst_n = 0; hrst_n = 0; repeat (6) @(negedge hck); rst_n = 1; hrst_n = 1; end
        end
        if (bad == 0 && ncv > 1000 && nev > 1000)
            $display("KVPC_CDC PASS edges=%0d checks=%0d c_v=%0d e_v=%0d errors=0 unqualified_payload_diffs=%0d mut=%0d", edges,
                     chk, ncv, nev, ninfo, `KVPC_MUT);
        else
            $display("KVPC_CDC FAIL edges=%0d checks=%0d errors=%0d c_v=%0d e_v=%0d mut=%0d", edges, chk, bad, ncv, nev,
                     `KVPC_MUT);
        $finish;
    end
endmodule
