`timescale 1ns/1ps
// CFGREP lockstep (drive-2125 2026-10-08, REVIEW_20261008 DQ1): hfd_loader with the registered cfg-valid copies (RG 8)
// against the unchanged wrapper + SKID half loader (renamed *_ref0 by run_cfgrep.sh), same random die inputs every cycle
// (h[511:256], h[513]; h[499] feeds the cfg chain), compared on every die output (h[255:0], h[512], t_cmdproc) each cycle.
// Prints CFGREP_LOCKSTEP checks / mismatches / slice pushes (rsp0, rsp1, m_r) so a vacuous run is visible.
module tb_cfgrep_lockstep;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst;
    reg [513:0] drv;
    wire [513:0] h_d, h_r; wire [340:0] t_d, t_r;
    hfd_loader dut (.ck(ck), .h(h_d), .rst(rst), .t_cmdproc(t_d));
    hfd_loader_ref0 rf (.ck(ck), .h(h_r), .rst(rst), .t_cmdproc(t_r));
    assign h_d[511:256] = drv[511:256]; assign h_d[513] = drv[513];
    assign h_r[511:256] = drv[511:256]; assign h_r[513] = drv[513];
    integer err = 0, nchk = 0, cyc, p0 = 0, p1 = 0, pm = 0;
    integer seed = `SEED;
    task automatic rnd; integer i; begin
        for (i = 0; i < 17; i = i + 1) drv[i*32 +: 32] = $urandom(seed + i);
        drv[513:512] = $urandom(seed + 17); seed = seed + 18;
        // valid-heavy cfg stream: h[499] high 3 of 4 cycles so the slices fill and back-pressure
        drv[499] = ($urandom(seed) % 4) != 0; seed = seed + 1;
    end endtask
    always @(posedge ck) if (!rst) begin
        p0 <= p0 + dut.u_ld.u_sk_rsp[0].g_rep.u.push; p1 <= p1 + dut.u_ld.u_sk_rsp[1].g_rep.u.push;
        pm <= pm + dut.u_ld.u_sk_m_r[0].g_rep.u.push;
    end
    initial begin
        rst = 1; drv = 0; rnd;
        repeat (8) @(posedge ck);
        #0.05 rst = 0;
        for (cyc = 0; cyc < `NCYC; cyc = cyc + 1) begin
            @(negedge ck);
            nchk = nchk + 1;
            if (h_d[255:0] !== h_r[255:0] || h_d[512] !== h_r[512] || t_d !== t_r) begin
                err = err + 1; if (err < 6) $display("MISMATCH cyc %0d h %h/%h t %h/%h", cyc, h_d[255:0], h_r[255:0], t_d, t_r);
            end
            rnd;
        end
        $display("CFGREP_LOCKSTEP seed %0d checks=%0d mismatches=%0d push_rsp0=%0d push_rsp1=%0d push_mr=%0d", `SEED, nchk, err, p0, p1, pm);
        if (err != 0 || nchk == 0 || p0 == 0 || p1 == 0 || pm == 0) $fatal(1, "FAIL");
        $finish;
    end
endmodule
