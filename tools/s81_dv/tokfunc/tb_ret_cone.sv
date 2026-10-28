`timescale 1ns/1ps
// TOK-ALL-17 (10-27): standalone check of the die_b178 return-lane cone of slice u_s_0S (die_ret_cone.py):
// six frame ret lanes -> hop-0 ICG -> real dsfd_dvrlyh half-cycle stations -> land-plan last-hop flight ->
// real dsfd_dvland_70 with the die K strap, reset by the real die reset wavefront from rst_n.  Uniform root clocks.
// Each lane gets a burst of tagged words (back-to-back and gapped) at the frame-side ret pins; the bench checks the
// landed sequence is the injected one, in order, at ONE constant latency per lane, no landing fault.
module tb_ret_cone;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst_n = 0;
    integer cyc = 0;
    localparam N = 6;
    reg  [69:0] r [0:N-1];
    wire [69:0] l [0:N-1];
    wire lf;
    ret_cone u (.ck(ck), .rst_n(rst_n),
        .ret_0L01(r[0]), .lnd_0L01(l[0]), .ret_0L02(r[1]), .lnd_0L02(l[1]), .ret_0L03(r[2]), .lnd_0L03(l[2]),
        .ret_0R01(r[3]), .lnd_0R01(l[3]), .ret_0R02(r[4]), .lnd_0R02(l[4]), .ret_0R03(r[5]), .lnd_0R03(l[5]), .land_fault(lf));
    integer j, sent [0:N-1], got [0:N-1], lat [0:N-1], bad = 0, t0 [0:N-1][0:63];
    initial for (j = 0; j < N; j = j + 1) begin r[j] = 70'd1; sent[j] = 0; got[j] = 0; lat[j] = -1; end
    // pattern: 14 words per lane like the GB frame (732..772 shape): runs of 1,2,4 back-to-back with gaps
    function automatic bit inj(input integer c, input integer ln);
        integer d; d = c - (700 + 3*ln);
        inj = (d >= 0 && d < 60) && (d % 5 != 4) && (d % 13 != 7);
    endfunction
    always @(negedge ck) begin
        if (cyc == 15) rst_n = 1;
        for (j = 0; j < N; j = j + 1) begin
            r[j] = 70'd1;
            if (inj(cyc, j) && sent[j] < 64) begin
                r[j] = {2'b00, 16'(j), 16'(sent[j]), 34'(cyc), 1'b1, 1'b1};
                t0[j][sent[j]] = cyc; sent[j] = sent[j] + 1;
            end
        end
    end
    wire [N-1:0] lfv = {u.lf_ld_r_f_0R03, u.lf_ld_r_f_0R02, u.lf_ld_r_f_0R01, u.lf_ld_r_f_0L03, u.lf_ld_r_f_0L02, u.lf_ld_r_f_0L01};
    wire [N-1:0] lrs = {u.ld_r_f_0R03.rs, u.ld_r_f_0R02.rs, u.ld_r_f_0R01.rs, u.ld_r_f_0L03.rs, u.ld_r_f_0L02.rs, u.ld_r_f_0L01.rs};
    wire [N-1:0] lwm = {u.ld_r_f_0R03.u.warm, u.ld_r_f_0R02.u.warm, u.ld_r_f_0R01.u.warm, u.ld_r_f_0L03.u.warm, u.ld_r_f_0L02.u.warm, u.ld_r_f_0L01.u.warm};
    wire [N-1:0] lck = {u.ld_r_f_0R03.ck_f, u.ld_r_f_0R02.ck_f, u.ld_r_f_0R01.ck_f, u.ld_r_f_0L03.ck_f, u.ld_r_f_0L02.ck_f, u.ld_r_f_0L01.ck_f};
    integer ff [0:N-1], fr [0:N-1], fw [0:N-1], fc [0:N-1];
    initial for (j = 0; j < N; j = j + 1) begin ff[j] = -1; fr[j] = -1; fw[j] = -1; fc[j] = -1; end
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_ck
        always @(posedge lck[g]) if ($time > 2 && fc[g] < 0) fc[g] = cyc;
    end endgenerate
    always @(posedge ck) begin
        cyc <= cyc + 1;
        for (j = 0; j < N; j = j + 1) begin
            if (lfv[j] && ff[j] < 0) ff[j] = cyc;
            if (lrs[j] && fr[j] < 0) fr[j] = cyc;
            if (lwm[j] && fw[j] < 0) fw[j] = cyc;
        end
        for (j = 0; j < N; j = j + 1) if (rst_n && l[j][1]) begin
            if (l[j][67:52] != 16'(j) || l[j][51:36] != 16'(got[j])) begin bad = bad + 1;
                $display("RC_BAD lane %0d cyc %0d word %h exp idx %0d", j, cyc, l[j], got[j]); end
            else begin
                if (lat[j] < 0) lat[j] = cyc - t0[j][got[j]];
                else if (cyc - t0[j][got[j]] != lat[j]) begin bad = bad + 1;
                    $display("RC_BAD lane %0d latency %0d != %0d", j, cyc - t0[j][got[j]], lat[j]); end
            end
            got[j] = got[j] + 1;
        end
        if (cyc == 1200) begin
            for (j = 0; j < N; j = j + 1) begin
                $display("RC lane %0d sent %0d got %0d latency %0d rs_release %0d first_ck_f %0d warm %0d first_fault %0d", j, sent[j], got[j], lat[j], fr[j], fc[j], fw[j], ff[j]);
                if (got[j] != sent[j]) bad = bad + 1;
            end
            $display("RC_END bad=%0d land_fault=%b %s", bad, lf, (bad == 0 && !lf) ? "PASS" : "FAIL");
            $finish;
        end
    end
`ifdef RC_TRACE
    wire trace = 1'b1;
    always @(u.fwd_r_f_0L01.ENA or u.nr_f_0L01_fck[0] or u.nr_f_0L01_fck[39] or u.flck_0L01 or u.ld_r_f_0L01.rs)
        if ($time > 80 && $time < 106 && trace)
            $display("T %0t ena=%b g=%b f39=%b fl=%b rs=%b wc=%0d rc=%0d warm=%b fault=%b epo=%0d,%0d,%0d,%0d", $time,
              u.fwd_r_f_0L01.ENA, u.nr_f_0L01_fck[0], u.nr_f_0L01_fck[39], u.flck_0L01,
              u.ld_r_f_0L01.rs, u.ld_r_f_0L01.u.wc, u.ld_r_f_0L01.u.rc, u.ld_r_f_0L01.u.warm,
              u.ld_r_f_0L01.u.fault, u.ld_r_f_0L01.u.epo[0], u.ld_r_f_0L01.u.epo[1], u.ld_r_f_0L01.u.epo[2], u.ld_r_f_0L01.u.epo[3]);
`endif
endmodule
