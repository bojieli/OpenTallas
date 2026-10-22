`timescale 1ns/1ps
// S81-XG4XS (10-20): cycle equivalence of ot_s81sl_xs4 (native-bounded x streamer leaf) against CURRENT MAIN
// ot_s81sl_xs (renamed copy ot_s81sl_xs_refm) fed through a one-edge testbench relay on EVERY input (rst_n included):
// the successor is main's x streamer with one capture edge in front, so its outputs xw_v / xw_d / fault must equal
// the reference's on every edge.
//   +stim=<file>   events "it kind a b c d hex" (kind 0: issuer word is_d = hex; kind 1: gather beat a = source,
//                  b = family, c = beat, d = x vector id); data of a beat = hash(d, b, c, word) (identical for both)
//   +cycles=<n> +seed=<n>
//   +legal=1       production program: the reference must not fault; every output compared every edge
//   +expfault=1    the program must fault (late-beat offset): outputs compared up to the fault edge + 4, fault always
//   +inj=<k> +injt=<it>  inject one event class at program iteration it (1 duplicate beat, 2 q beat 100, 3 BF beat 85,
//                  4 reserved is_d bit, 5 offset load in flight, 6 random is_d word, 7 random gather burst 16 edges)
//   +rstat=<cyc>   in-flight reset: rst_n low 8 edges at <cyc>, the program restarts at <cyc> + 24 (iteration 0);
//                  compare suspended for 30 edges; the restarted program must match (and not fault if +legal)
// Prints XS4_EQUIV PASS|FAIL.
module tb_s81sl_xs4_equiv (input wire clk);
    integer cyc = 0, ncyc = 3000, seed = 1, legal = 0, expfault = 0, inj = 0, injt = 0, rstat = 0;
    integer nev = 0, ep = 0, pbase = 0;
    integer mism_pre = 0, mism_post = 0, mism_f = 0, first_bad = -1, a_fault_at = -1, nvalid = 0, nbf = 0, nq = 0;
    integer last_src = 0, last_fam = 0, last_bt = 0, last_gid = 0, burst = 0;
    reg [1023:0] stim_name;
    integer ev_it [0:8191]; integer ev_k [0:8191]; integer ev_a [0:8191]; integer ev_b [0:8191];
    integer ev_c [0:8191]; integer ev_d [0:8191]; reg [159:0] ev_h [0:8191];
    reg rst_n = 1'b0;
    reg [2:0] g_v = 0, g_fam = 0; reg [20:0] g_idx = 0; reg [3071:0] g_d = 0; reg is_v = 0; reg [159:0] is_d = 0;
    reg r_rst_n = 1'b0;
    reg [2:0] r_gv = 0, r_gf = 0; reg [20:0] r_gi = 0; reg [3071:0] r_gd = 0; reg r_isv = 0; reg [159:0] r_isd = 0;
    always @(posedge clk) begin
        r_rst_n <= rst_n; r_gv <= g_v; r_gf <= g_fam; r_gi <= g_idx; r_gd <= g_d; r_isv <= is_v; r_isd <= is_d;
    end
    wire a_xwv, a_f, b_xwv, b_f; wire [1100:0] a_xw, b_xw;
    ot_s81sl_xs_refm u_a (.clk(clk), .rst_n(r_rst_n), .g_v(r_gv), .g_fam(r_gf), .g_idx(r_gi), .g_d(r_gd),
        .is_v(r_isv), .is_d(r_isd), .xw_v(a_xwv), .xw_d(a_xw), .fault(a_f));
    ot_s81sl_xs4 u_b (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d),
        .is_v(is_v), .is_d(is_d), .xw_v(b_xwv), .xw_d(b_xw), .fault(b_f));

    function automatic [31:0] hmix(input integer a, input integer b, input integer c, input integer d);
        reg [31:0] x;
        begin
            x = a * 32'h9E3779B1 ^ b * 32'h85EBCA77 ^ c * 32'hC2B2AE3D ^ d * 32'h27D4EB2F ^ seed;
            x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
            hmix = x;
        end
    endfunction
    integer fd, rc, t_it, t_k, t_a, t_b, t_c, t_d; reg [159:0] t_h;
    initial begin
        void'($value$plusargs("cycles=%d", ncyc)); void'($value$plusargs("seed=%d", seed));
        void'($value$plusargs("legal=%d", legal)); void'($value$plusargs("expfault=%d", expfault));
        void'($value$plusargs("inj=%d", inj)); void'($value$plusargs("injt=%d", injt));
        void'($value$plusargs("rstat=%d", rstat));
        if (!$value$plusargs("stim=%s", stim_name)) begin $display("XS4_EQUIV FAIL no +stim"); $finish; end
        void'($urandom(seed));
        fd = $fopen(stim_name, "r");
        if (fd == 0) begin $display("XS4_EQUIV FAIL cannot open stim"); $finish; end
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%d %d %d %d %d %d %h\n", t_it, t_k, t_a, t_b, t_c, t_d, t_h);
            if (rc == 7) begin
                ev_it[nev] = t_it; ev_k[nev] = t_k; ev_a[nev] = t_a; ev_b[nev] = t_b; ev_c[nev] = t_c; ev_d[nev] = t_d;
                ev_h[nev] = t_h; nev = nev + 1;
            end
        end
        $fclose(fd);
    end
    integer pc, w, s;
    reg [2:0] n_gv, n_gf; reg [20:0] n_gi; reg [3071:0] n_gd; reg n_isv; reg [159:0] n_isd;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        // reset: initial 15 edges low; in-flight reset 8 edges, program restart
        if (cyc == 14) rst_n <= 1'b1;
        if (rstat > 0 && cyc == rstat) begin rst_n <= 1'b0; ep = nev; end
        if (rstat > 0 && cyc == rstat + 8) begin rst_n <= 1'b1; pbase = rstat + 24; ep = 0; end
        // inputs applied now are sampled on the next edge = program iteration pc
        pc = cyc + 1 - pbase;
        n_gv = 0; n_gf = 0; n_gi = 0; n_gd = 0; n_isv = 0; n_isd = 0;
        while (ep < nev && ev_it[ep] < pc) ep = ep + 1;
        while (ep < nev && ev_it[ep] == pc) begin
            if (ev_k[ep] == 0) begin n_isv = 1'b1; n_isd = ev_h[ep]; end
            else begin
                s = ev_a[ep];
                n_gv[s] = 1'b1; n_gf[s] = ev_b[ep][0]; n_gi[7*s +: 7] = ev_c[ep][6:0];
                for (w = 0; w < 32; w = w + 1) n_gd[1024*s + 32*w +: 32] = hmix(ev_d[ep], ev_b[ep], ev_c[ep], w);
                last_src = s; last_fam = ev_b[ep]; last_bt = ev_c[ep]; last_gid = ev_d[ep];
            end
            ep = ep + 1;
        end
        if (inj > 0 && pc == injt && (rstat == 0 || pbase == 0)) begin
            case (inj)
                1: begin s = (last_src + 1) % 3; n_gv[s] = 1'b1; n_gf[s] = last_fam[0]; n_gi[7*s +: 7] = last_bt[6:0];
                       for (w = 0; w < 32; w = w + 1) n_gd[1024*s + 32*w +: 32] = hmix(last_gid, last_fam, last_bt, w + 1); end
                2: begin n_gv[0] = 1'b1; n_gf[0] = 1'b0; n_gi[6:0] = 7'd100; end
                3: begin n_gv[1] = 1'b1; n_gf[1] = 1'b1; n_gi[13:7] = 7'd85; end
                4: begin n_isv = 1'b1; n_isd[140] = 1'b1; end
                5: begin n_isv = 1'b1; n_isd[123] = 1'b1; n_isd[131:124] = 8'd20; end
                6: begin n_isv = 1'b1; for (w = 0; w < 5; w = w + 1) n_isd[32*w +: 32] = $urandom; n_isd[159:132] = 0; end
                7: burst = 16;
                default: ;
            endcase
        end
        if (burst > 0) begin
            burst = burst - 1;
            for (s = 0; s < 3; s = s + 1) if ($urandom % 2) begin
                n_gv[s] = 1'b1; n_gf[s] = $urandom % 2; n_gi[7*s +: 7] = 7'($urandom % 96);
                for (w = 0; w < 32; w = w + 1) n_gd[1024*s + 32*w +: 32] = $urandom;
            end
        end
        g_v <= n_gv; g_fam <= n_gf; g_idx <= n_gi; g_d <= n_gd; is_v <= n_isv; is_d <= n_isd;
        // compare every edge (outputs of this edge are the values before the update)
        if (cyc > 2 && !(rstat > 0 && cyc >= rstat && cyc < rstat + 30)) begin
            if (a_f !== b_f) begin mism_f = mism_f + 1; if (mism_f <= 3) $display("MISMATCH fault cyc=%0d ref=%0d dut=%0d", cyc, a_f, b_f); end
            if (a_xw !== b_xw || a_xwv !== b_xwv) begin
                if (a_fault_at < 0 || cyc <= a_fault_at + 4) begin
                    mism_pre = mism_pre + 1;
                    if (first_bad < 0) first_bad = cyc;
                    if (mism_pre <= 4) begin
                        $write("MISMATCH xw cyc=%0d bits:", cyc);
                        s = 0;
                        for (w = 0; w < 1101 && s < 10; w = w + 1)
                            if (a_xw[w] !== b_xw[w]) begin $write(" b%0d=%0d/%0d", w, a_xw[w], b_xw[w]); s = s + 1; end
                        $display("");
                    end
                end else mism_post = mism_post + 1;
            end
            if (a_f && a_fault_at < 0) a_fault_at = cyc;
            if (a_xwv) begin
                nvalid = nvalid + 1;
                if (a_xw[1100:565] != 0) nbf = nbf + 1;
                else if (a_xw[256:1] != 0) nq = nq + 1;
            end
        end
        if (rstat > 0 && cyc == rstat + 8) a_fault_at = -1;   // the restarted run is judged on its own
        if (cyc == ncyc) begin
            $display("XS4_EQUIV cycles=%0d events=%0d legal=%0d expfault=%0d inj=%0d injt=%0d rstat=%0d valid=%0d bf=%0d qnz=%0d ref_fault_at=%0d mismatches=%0d fault_mismatches=%0d post_fault_mismatches=%0d first_bad=%0d",
                     ncyc, nev, legal, expfault, inj, injt, rstat, nvalid, nbf, nq, a_fault_at, mism_pre, mism_f, mism_post, first_bad);
            if (mism_pre == 0 && mism_f == 0 && (!legal || (a_fault_at < 0 && nvalid > 0 && nbf > 0 && nq > 0)) &&
                (!expfault || a_fault_at >= 0))
                $display("XS4_EQUIV PASS");
            else $display("XS4_EQUIV FAIL");
            $finish;
        end
    end
endmodule
