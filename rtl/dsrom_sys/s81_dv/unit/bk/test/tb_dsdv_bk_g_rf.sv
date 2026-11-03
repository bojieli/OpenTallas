`timescale 1ns/1ps
// DIE-S81-51/RF-D 11-03 (S81-062 RE-FORM): lockstep bench dsdv_bk_g RF 0 (old form) vs RF 1 (vstop FPIPE + negedge
// in/out faces).  Same stimulus (driven after each posedge, like a posedge sender); outputs sampled by rising-edge
// receivers (tb always @(posedge) = pre-edge values).  Expected: vo_s / vo_n (RF 1) = vo_* (RF 0) one edge later;
// ln0..ln3 equal on every edge; fault (sticky) RF 1 between RF 0 now and RF 0 one edge earlier.  Stimulus: random rung
// beats (idle / singles of every kind / XQ-XB 4-fragment streams / addressed drain CTLs for uid 5B and foreign uids) on
// vi_s / vi_n, random vd words.  +define+OT_RFD_MUT_BKG (vstop mutant) must FAIL.  Verdict line "BKG_RF PASS|FAIL".
module tb_dsdv_bk_g_rf;
    localparam integer V = 276;
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst_n = 0;
    reg [V-1:0] vi_s = 0, vi_n = 0; reg [366:0] vd = 0;
    wire [V-1:0] vo_s0, vo_n0, vo_s1, vo_n1; wire [514:0] a0, a1, a2, a3, b0, b1, b2, b3; wire f0, f1;
    dsdv_bk_g #(.RF(0)) u0 (.clk(clk), .rst_n(rst_n), .tap_k(6'h05), .sink_k(6'h04), .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0),
        .vi_s(vi_s), .vo_s(vo_s0), .vi_n(vi_n), .vo_n(vo_n0), .ln0(a0), .ln1(a1), .ln2(a2), .ln3(a3), .vd(vd), .fault(f0));
    dsdv_bk_g #(.RF(1)) u1 (.clk(clk), .rst_n(rst_n), .tap_k(6'h05), .sink_k(6'h04), .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0),
        .vi_s(vi_s), .vo_s(vo_s1), .vi_n(vi_n), .vo_n(vo_n1), .ln0(b0), .ln1(b1), .ln2(b2), .ln3(b3), .vd(vd), .fault(f1));
    integer cyc = 0, err = 0, nfwd = 0, nln = 0, ncmp = 0, seed = 1, ncyc = 200000;
    reg [V-1:0] ps0, pn0; reg pf0; integer frs = 0, frn = 0;
    function automatic [V-1:0] rbeat(input integer fr);
        reg [V-1:0] b; integer r, k;
        begin
            b = 0; for (k = 0; k < V; k = k + 32) b[k +: 32] = $urandom;
            if (fr > 0) rbeat = b;                                   // continuation fragment: raw payload
            else begin
                r = $urandom % 16;
                if (r < 5) rbeat = 0;                                // idle
                else begin
                    b[0] = 1'b1; b[3:1] = $urandom % 8;
                    if (r < 8) begin b[3:1] = 3'd0; b[31:29] = 3'd1; b[28:21] = ($urandom % 3 == 0) ? 8'h5B : $urandom; end
                    else if (r < 12) begin b[3:1] = 3'd4; if ($urandom % 2) begin b[7] = 1'b1; b[6] = 1'b0; end end   // ingress kind ik (half singles)
                    rbeat = b;
                end
            end
        end
    endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 200000;
        void'($urandom(seed));
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 20) rst_n <= 1'b1;
        if (cyc == ncyc / 2) rst_n <= 1'b0;                          // mid-run reset (held 64 edges)
        if (cyc == ncyc / 2 + 64) rst_n <= 1'b1;
        // stimulus (posedge sender)
        begin : stim
            reg [V-1:0] b;
            b = rbeat(frs); vi_s <= b;
            frs = (frs > 0) ? frs - 1 : (b[0] && (b[3:1] == 3'd1 || b[3:1] == 3'd2)) ? 3 : 0;
            b = rbeat(frn); vi_n <= b;
            frn = (frn > 0) ? frn - 1 : (b[0] && (b[3:1] == 3'd1 || b[3:1] == 3'd2)) ? 3 : 0;
            vd <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        end
        // checks (pre-edge values)
        if (cyc > 30 && !(cyc >= ncyc / 2 && cyc <= ncyc / 2 + 2)) begin   // RF 1 samples rst_n at the negedge: assertion lands half an edge later (held 64)
            ncmp = ncmp + 1;
            if (vo_s1 !== ps0 || vo_n1 !== pn0) begin err = err + 1; if (err < 6) $display("MISMATCH vo cyc %0d", cyc); end
            if ({b0, b1, b2, b3} !== {a0, a1, a2, a3}) begin err = err + 1; if (err < 6) $display("MISMATCH ln cyc %0d", cyc); end
            if (!(f1 === f0 || f1 === pf0)) begin err = err + 1; if (err < 6) $display("MISMATCH fault cyc %0d f0 %b pf0 %b f1 %b", cyc, f0, pf0, f1); end
            if (|vo_s0 || |vo_n0) nfwd = nfwd + 1;
            if (a0[0] || a1[0] || a2[0] || a3[0]) nln = nln + 1;
        end
        ps0 <= vo_s0; pn0 <= vo_n0; pf0 <= f0;
        if (cyc == ncyc) begin
            $display("BKG_RF %s cycles=%0d compared=%0d fwd_beats=%0d lane_words=%0d errors=%0d", err == 0 ? "PASS" : "FAIL", cyc, ncmp, nfwd, nln, err);
            $finish;
        end
    end
endmodule
