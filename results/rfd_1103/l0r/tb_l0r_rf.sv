`timescale 1ns/1ps
// DIE-S81-51/RF-D 11-03 (S81-064 RE-FORM): lockstep bench dsdv_gunit_l0r RF 0 (old form) vs RF 1 (registered one-hot
// write slots + go delayed one edge).  Expected: every output of RF 1 equals RF 0 one edge later, on every edge after
// reset (r_d included, whether or not r_v).  Stimulus mode 0 = L0's contract (32 distinct (g, h) slots a window, one or
// two writes an edge, the go on the last write's edge, buffer toggles, completions >= 20 edges apart); mode 1 = random
// (any write / go pattern, slot collisions a == b, gos while streaming).  +define+OT_RFD_MUT_L0R must FAIL.
// Form 2 (11-03): -GRA / -GRB pick the two forms (delay = [RB>=1]-[RA>=1]; RF 2 = RF 1 + negedge in-face, 0 cycles);
// RA 1 / RB 2 with +define+OT_RFD_MUT_L0R2 (posedge in-face) must FAIL.
module tb_l0r_rf #(parameter integer RA = 0, parameter integer RB = 1);
    localparam integer DL = (RB >= 1) - (RA >= 1);
    reg clk = 0; always #0.4165 clk = ~clk;
    reg rst_n = 0;
    reg wr_av = 0, wr_bv = 0, wr_b = 0, go_a = 0, go_b = 0; reg [4:0] wr_agh = 0, wr_bgh = 0, go_acc = 0;
    reg [191:0] wr_ad = 0, wr_bd = 0;
    wire v0, v1, f0, f1; wire [3:0] i0, i1; wire [4:0] c0, c1; wire [319:0] d0, d1;
    dsdv_gunit_l0r #(.RF(RA)) u0 (.clk(clk), .rst_n(rst_n), .wr_av(wr_av), .wr_agh(wr_agh), .wr_ad(wr_ad), .wr_bv(wr_bv),
        .wr_bgh(wr_bgh), .wr_bd(wr_bd), .wr_b(wr_b), .go_a(go_a), .go_acc(go_acc), .go_b(go_b), .r_v(v0), .r_i(i0), .r_acc(c0), .r_d(d0), .r_f(f0));
    dsdv_gunit_l0r #(.RF(RB)) u1 (.clk(clk), .rst_n(rst_n), .wr_av(wr_av), .wr_agh(wr_agh), .wr_ad(wr_ad), .wr_bv(wr_bv),
        .wr_bgh(wr_bgh), .wr_bd(wr_bd), .wr_b(wr_b), .go_a(go_a), .go_acc(go_acc), .go_b(go_b), .r_v(v1), .r_i(i1), .r_acc(c1), .r_d(d1), .r_f(f1));
    integer cyc = 0, err = 0, ncmp = 0, nv = 0, ngo = 0, mode = 0, seed = 1, ncyc = 200000;
    reg [330:0] p0;                                    // RF 0 outputs one edge ago
    reg [31:0] perm [0:31]; integer wn = 0, gap = 0, idle = 0, k, t, x;
    reg wbuf = 0; reg synced = 0;
    function automatic [191:0] rd192(input integer z); rd192 = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom}; endfunction
    task automatic newperm; begin
        for (k = 0; k < 32; k = k + 1) perm[k] = k;
        for (k = 31; k > 0; k = k - 1) begin t = $urandom % (k + 1); x = perm[k]; perm[k] = perm[t]; perm[t] = x; end
    end endtask
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 200000;
        void'($urandom(seed)); newperm;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 10) rst_n <= 1'b1;
        if (cyc == ncyc / 2) rst_n <= 1'b0;
        if (cyc == ncyc / 2 + 64) begin rst_n <= 1'b1; wn = 0; gap = 0; idle = 0; newperm; end
        go_a <= 1'b0; wr_av <= 1'b0; wr_bv <= 1'b0;
        wr_ad <= rd192(0); wr_bd <= rd192(0); wr_agh <= $urandom; wr_bgh <= $urandom; go_acc <= $urandom; go_b <= $urandom;
        if (mode == 1) begin
            wr_av <= ($urandom % 3) == 0; wr_bv <= ($urandom % 3) == 0; wr_b <= $urandom; go_a <= ($urandom % 9) == 0;
            if ($urandom % 4 == 0) wr_bgh <= wr_agh;
        end else if (rst_n && cyc > 40) begin
            gap = gap + 1;
            if (idle > 0) idle = idle - 1;
            else if (wn < 32) begin
                wr_b <= wbuf;
                wr_av <= 1'b1; wr_agh <= perm[wn]; wn = wn + 1;
                if (wn < 32 && ($urandom % 2)) begin wr_bv <= 1'b1; wr_bgh <= perm[wn]; wn = wn + 1; end
                if (wn == 32) begin
                    if (gap < 20) begin wn = wn - 1; wr_av <= 1'b0; wr_bv <= 1'b0; if (perm[wn - 1] != 0) ; end   // wait for spacing
                    else begin go_a <= 1'b1; go_b <= wbuf; ngo = ngo + 1; gap = 0; end
                end
                if ($urandom % 5 == 0) idle = $urandom % 3;
            end else begin wn = 0; wbuf = !wbuf; newperm; end
        end
        if (cyc > 20 && !(cyc >= ncyc / 2 && cyc <= ncyc / 2 + 2)) begin
            ncmp = ncmp + 1; if (v0) nv = nv + 1;
            // r_d before the first stream is junk of the free-running read select (r_v = 0; the select is not reset):
            // compared from the first stream on (then on EVERY edge, valid or not)
            if (DL == 0 ? ({v1, i1, c1, f1} !== {v0, i0, c0, f0} || (synced && d1 !== d0))
                        : ({v1, i1, c1, f1} !== {p0[330:321], p0[0]} || (synced && d1 !== p0[320:1]))) begin err = err + 1; if (err < 6) $display("MISMATCH cyc %0d v %b/%b f %b/%b", cyc, v1, p0[330], f1, p0[0]); end
        end
        p0 <= {v0, i0, c0, d0, f0}; if (p0[330]) synced <= 1'b1;
        if (cyc == ncyc) begin
            $display("L0R_RF %s ra=%0d rb=%0d mode=%0d cycles=%0d compared=%0d stream_edges=%0d gos=%0d errors=%0d", err == 0 ? "PASS" : "FAIL", RA, RB, mode, cyc, ncmp, nv, ngo, err);
            $finish;
        end
    end
endmodule
