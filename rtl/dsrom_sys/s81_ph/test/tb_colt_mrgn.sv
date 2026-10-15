`timescale 1ns/1ps
// tb_colt_mrgn (s81-die-rtl-bind 2026-10-14, F5): (A) NQ 4: dsfd_colt_mrgn in LOCKSTEP with the CLOSED dsfd_colt_mrg on
// the same lane traffic (vd and t_cr equal every cycle); (B) NQ 1 (the 1-stack collector): the output word stream =
// the lane's frames in order, one DONE word per job (its tag, its DONE code) after the frames sent before it.
// Lane traffic: jobs of random result frames (type 3, len 0..6) then a DONE head (type 4, len 0, tag = job), under the
// merger's credits (DM landing slots, one credit back per pop).  MUT 1 (no DONE) must FAIL.
module tb_colt_mrgn;
    parameter integer NQ = 4, MUT = 0, NJOB = 60, DM = 8, SEED = 3;
    reg ck = 0, rst = 0; always #1 ck = ~ck;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg [63:0] rs = 64'h2545F4914F6CDD1D ^ SEED;
    function [31:0] rnd(input integer d); begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end endfunction
    reg [NQ*513-1:0] f_w = 0; reg [NQ*4-1:0] f_f = 0;
    wire [NQ-1:0] t_cr; wire [513:0] vd; wire vf;
    dsfd_colt_mrgn #(.NQ(NQ), .DM(DM), .PACE(2), .MUT(MUT)) dut (.ck(ck), .rst(rst), .f_w(f_w), .f_f(f_f), .t_cr(t_cr), .vd(vd), .vf(vf));
    wire [3:0] r_cr; wire [513:0] r_vd; wire r_vf;
    generate if (NQ == 4) begin : g_ref
        dsfd_colt_mrg #(.DM(DM), .PACE(2)) u_ref (.ck(ck), .rst(rst), .f_w(f_w), .f_f(f_f), .t_cr(r_cr), .vd(r_vd), .vf(r_vf));
    end endgenerate
    // per-lane word queues
    reg [511:0] lw [0:NQ-1][0:8191]; integer lwn [0:NQ-1], lwr [0:NQ-1], cred [0:NQ-1];
    reg [511:0] exp_ [0:65535]; integer ne = 0, nr = 0, errs = 0, lock_err = 0, dones = 0;
    integer j, q, f, nf, len, w;
    reg [511:0] h;
    initial begin
        for (q = 0; q < NQ; q = q + 1) begin lwn[q] = 0; lwr[q] = 0; cred[q] = DM; end
        for (j = 0; j < NJOB; j = j + 1) begin
            for (q = 0; q < NQ; q = q + 1) begin
                nf = rnd(0) % 4;
                for (f = 0; f < nf; f = f + 1) begin
                    len = rnd(0) % 7;
                    h = {4'd3, 8'(j), 8'(q), 12'(len), 448'd0, rnd(0)};
                    lw[q][lwn[q]] = h; lwn[q] = lwn[q] + 1; if (NQ == 1) begin exp_[ne] = h; ne = ne + 1; end
                    for (w = 0; w < len; w = w + 1) begin
                        h = {4'd2, 60'(rnd(0)), 448'd0} | {64'd0, 416'd0, rnd(0)}; lw[q][lwn[q]] = h; lwn[q] = lwn[q] + 1;
                        if (NQ == 1) begin exp_[ne] = h; ne = ne + 1; end
                    end
                end
                h = {4'd4, 8'(j), 8'd0, 12'd0, 469'd0, 11'(rnd(0) % 2048)};
                lw[q][lwn[q]] = h; lwn[q] = lwn[q] + 1;
                if (NQ == 1) begin exp_[ne] = {4'd4, 8'(j), 484'd0, 5'd0, h[10:0]}; ne = ne + 1; end
            end
        end
        #9 rst = 1;
    end
    always @(posedge ck) begin
        for (q = 0; q < NQ; q = q + 1) begin
            cred[q] = cred[q] + t_cr[q];
            f_w[513 * q] <= 1'b0;
            if (rst && cyc > 12 && lwr[q] < lwn[q] && cred[q] > 0 && (rnd(0) % 3) != 0) begin
                f_w[513 * q +: 513] <= {lw[q][lwr[q]], 1'b1}; lwr[q] = lwr[q] + 1; cred[q] = cred[q] - 1;
            end
        end
        if (NQ == 4 && (vd !== r_vd || t_cr !== r_cr)) lock_err = lock_err + 1;
        if (vd[1]) begin
            if (vd[513:510] == 4'd4) dones = dones + 1;   // DONE words (data words are type 2, headers type 3)
            if (NQ == 1) begin
                if (nr >= ne || vd[513:2] !== exp_[nr]) begin errs = errs + 1; if (errs < 5) $display("ERR word %0d got %h exp %h", nr, vd[513:450], exp_[nr][511:448]); end
                nr = nr + 1;
            end
        end
    end
    initial begin
        wait (cyc > 200 * NJOB);
        if (NQ == 1 && nr != ne) errs = errs + 1;
        if (dones != NJOB) errs = errs + 1;
        $display("TB_COLT_MRGN NQ=%0d MUT=%0d jobs=%0d dones=%0d words=%0d/%0d lockstep_mismatch=%0d errors=%0d %s", NQ, MUT, NJOB,
                 dones, nr, ne, lock_err, errs, (errs == 0 && lock_err == 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
