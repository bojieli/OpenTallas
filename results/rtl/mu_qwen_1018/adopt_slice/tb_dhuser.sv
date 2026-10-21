`timescale 1ns/1ps
// MU-ADOPT-SLICE (R3 without touching the closed qfd_sys_face): bench of qfd_sys_face_mu_dhuser.  Verilator 5.050
// --binary --timing.  A compiled 4-user period (NS h_starts; user, stage and RESULT flag per entry from an LFSR of
// SEED: runs of one user, as the static calendar interleaves whole stages) is played as seq_dh for P periods: h_start
// pulses at random gaps (0 = back to back), the stage of the entry on the h_start edge, random tok / pos / kwd and a
// random (held-face-like) stage field between h_starts.
//   n4 (NU 4): dh_user == the entry's user ON the h_start edge, held between; res_user == user of the latest RESULT
//              entry (one edge after it); mu_fault stays 0.
//   n1 (NU 1): dh_user = res_user = 0 and mu_fault = 0 on every edge (default identity: today).
// +slip: one h_start of period 3 is dropped (a calendar slip): mu_fault MUST rise within the next NS h_starts
//        (TB_DHUSER PASS = detected); the user checks are off after the slip.
module tb_dhuser;
    parameter integer MUT = 0;
    parameter integer NS = 37;
    parameter integer SEED = 7;
    function automatic [31:0] lf(input [31:0] x); lf = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; endfunction
    function automatic [64*2-1:0] gen_u(input integer s);
        reg [31:0] x; integer k; reg [1:0] u;
        begin x = 32'h9E3779B9 ^ s; u = 0; gen_u = 0;
            for (k = 0; k < NS; k = k + 1) begin x = lf(lf(lf(x))); if (x[2:0] < 3) u = x[4:3]; gen_u[2*k +: 2] = u; end
        end
    endfunction
    function automatic [64*6-1:0] gen_s(input integer s);
        reg [31:0] x; integer k;
        begin x = 32'h7F4A7C15 ^ s; gen_s = 0;
            for (k = 0; k < NS; k = k + 1) begin x = lf(lf(lf(lf(x)))); gen_s[6*k +: 6] = 6'(x[5:0] % 38); end
        end
    endfunction
    function automatic [63:0] gen_r(input integer s);
        reg [31:0] x; integer k;
        begin x = 32'h2545F491 ^ s; gen_r = 0;
            for (k = 0; k < NS; k = k + 1) begin x = lf(lf(x)); gen_r[k] = (x[3:0] == 0); end
        end
    endfunction
    localparam [64*2-1:0] US = gen_u(SEED);
    localparam [64*6-1:0] SS = gen_s(SEED);
    localparam [63:0]     RS = gen_r(SEED);
    reg ck = 1'b0;
    always #1 ck = ~ck;
    reg rst_n = 1'b0;
    reg [43:0] dh = 44'd0;
    wire [1:0] u4, r4, u1, r1; wire f4, f1;
    qfd_sys_face_mu_dhuser #(.NU(4), .NS(NS), .USER_SEQ(US), .STG_SEQ(SS), .RES_SEQ(RS), .MUT(MUT)) n4 (
        .ck(ck), .rst_n(rst_n), .dh_run(dh), .dh_user(u4), .res_user(r4), .mu_fault(f4));
    qfd_sys_face_mu_dhuser #(.NU(1)) n1 (.ck(ck), .rst_n(rst_n), .dh_run(dh), .dh_user(u1), .res_user(r1), .mu_fault(f1));
    integer P = 50, p, k, g, err = 0, nhs = 0, nb2b = 0, nres = 0, slip = 0, slip_at = -1, det = -1, hs_after = 0;
    reg [1:0] mu, mr, mr_next; reg res_pend;
    integer ucount [0:3];
    task automatic chk;
        begin
            #0.5;
            if (u1 !== 2'd0 || r1 !== 2'd0 || f1 !== 1'b0) begin
                err = err + 1; if (err <= 5) $display("NU1 not constant: user %0d res %0d fault %b", u1, r1, f1); end
            if (slip_at < 0) begin
                if (u4 !== mu || r4 !== mr || f4 !== 1'b0) begin
                    err = err + 1;
                    if (err <= 5) $display("NU4 period %0d entry %0d hs %b: user %0d want %0d, res %0d want %0d, fault %b",
                                           p, k, dh[42], u4, mu, r4, mr, f4);
                end
            end else if (f4 === 1'b1 && det < 0) det = hs_after;
        end
    endtask
    initial begin
        if ($test$plusargs("slip")) slip = 1;
        for (k = 0; k < 4; k = k + 1) ucount[k] = 0;
        for (k = 0; k < NS; k = k + 1) ucount[US[2*k +: 2]] = ucount[US[2*k +: 2]] + 1;
        $display("table NS %0d users 0..3 entries %0d %0d %0d %0d, RESULT entries %0d", NS, ucount[0], ucount[1],
                 ucount[2], ucount[3], $countones(RS));
        mu = 0; mr = 0; res_pend = 0; mr_next = 0;
        repeat (3) @(negedge ck); rst_n = 1;
        for (p = 0; p < P; p = p + 1) begin
            for (k = 0; k < NS; k = k + 1) begin
                g = (($urandom % 4) == 0) ? 0 : $urandom % 20;
                repeat (g) begin
                    @(negedge ck);
                    dh = {1'($urandom), 1'b0, 6'($urandom), 18'($urandom), 18'($urandom)};
                    if (res_pend) begin mr = mr_next; res_pend = 0; end
                    chk;
                end
                if (g == 0) nb2b = nb2b + 1;
                @(negedge ck);
                if (res_pend) begin mr = mr_next; res_pend = 0; end
                if (slip && p == 3 && k == 5 && slip_at < 0) begin
                    slip_at = nhs; dh = {1'($urandom), 1'b0, 6'($urandom), 18'($urandom), 18'($urandom)};
                end else begin
                    dh = {1'($urandom), 1'b1, SS[6*k +: 6], 18'($urandom), 18'($urandom)};
                    nhs = nhs + 1; if (slip_at >= 0) hs_after = hs_after + 1;
                    mu = US[2*k +: 2];
                    if (RS[k]) begin res_pend = 1; mr_next = US[2*k +: 2]; nres = nres + 1; end
                end
                chk;
            end
        end
        @(negedge ck); dh = 44'd0; chk;
        $display("%0d periods, %0d h_starts (%0d back to back), %0d RESULT entries, slip %0d", P, nhs, nb2b, nres, slip);
        if (slip) begin
            if (det >= 0 && det <= NS) $display("TB_DHUSER PASS slip detected %0d h_starts after the slip (NU1 err %0d)", det, err);
            else $display("TB_DHUSER FAIL slip not detected (det %0d)", det);
        end else if (err == 0) $display("TB_DHUSER PASS MUT=%0d", MUT);
        else $display("TB_DHUSER FAIL MUT=%0d %0d mismatches", MUT, err);
        $finish;
    end
endmodule
