`timescale 1ns/1ps
// TL-LEAF42SETUP 11-14: lockstep ot_s81sl_vp #(`PA) vs #(`PB), e.g. iverilog -g2012 -s tb_vp_wrp_eq -DPA=.WRP(0) -DPB=.WRP(1); random sw / cw / xw / hq writes + random commands, every output compared each cycle (+seed= +ncyc= +pw= +px= +pc=)
module tb_vp_wrp_eq;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg c_v; reg [159:0] c_d; reg sw_v; reg [9:0] sw_a; reg [7:0] sw_m; reg [255:0] sw_d; reg [1:0] cw_v; reg [23:0] cw_a; reg [63:0] cw_d;
    reg x_rv; reg [9:0] x_ra; reg x_wv; reg [9:0] x_wa; reg [7:0] x_wm; reg [255:0] x_wd; reg hq_v; reg [255:0] hq_d;
`define OUTS(p) wire p``lo_v, p``s_v, p``x_qv, p``hw_v, p``hw_hf, p``hr_v, p``hr_hf, p``n_go, p``m_v, p``m_q, p``m_b, p``wl_v, p``fault; \
    wire [255:0] p``lo_d, p``x_qd, p``hw_d, p``wl_d; wire [159:0] p``s_d; wire [2:0] p``hw_j, p``hr_j, p``wl_i; wire [127:0] p``n_pre; wire [7:0] p``m_i;
    `OUTS(a_) `OUTS(b_)
`define INST(M,P,p) M #(P) u_``p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), \
      .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .lo_v(p``lo_v), .lo_d(p``lo_d), .s_v(p``s_v), .s_d(p``s_d), .x_rv(x_rv), .x_ra(x_ra), \
      .x_qv(p``x_qv), .x_qd(p``x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd), .hw_v(p``hw_v), .hw_j(p``hw_j), .hw_hf(p``hw_hf), \
      .hw_d(p``hw_d), .hr_v(p``hr_v), .hr_j(p``hr_j), .hr_hf(p``hr_hf), .hq_v(hq_v), .hq_d(hq_d), .n_go(p``n_go), .n_pre(p``n_pre), \
      .m_v(p``m_v), .m_q(p``m_q), .m_b(p``m_b), .m_i(p``m_i), .wl_v(p``wl_v), .wl_i(p``wl_i), .wl_d(p``wl_d), .fault(p``fault));
    `INST(ot_s81sl_vp, `PA, a_)
    `INST(ot_s81sl_vp, `PB, b_)
    wire [2048:0] va = {a_lo_v,a_s_v,a_x_qv,a_hw_v,a_hw_hf,a_hr_v,a_hr_hf,a_n_go,a_m_v,a_m_q,a_m_b,a_wl_v,a_fault,a_lo_d,a_x_qd,a_hw_d,a_wl_d,a_s_d,a_hw_j,a_hr_j,a_wl_i,a_n_pre,a_m_i};
    wire [2048:0] vb = {b_lo_v,b_s_v,b_x_qv,b_hw_v,b_hw_hf,b_hr_v,b_hr_hf,b_n_go,b_m_v,b_m_q,b_m_b,b_wl_v,b_fault,b_lo_d,b_x_qd,b_hw_d,b_wl_d,b_s_d,b_hw_j,b_hr_j,b_wl_i,b_n_pre,b_m_i};
    integer seed, ncyc, cyc, err, nlo, nfault, pw, px, pc, nsw, ncw, nxw, nhs;
    reg [3:0] ops [0:6];
    task rnd_cmd; reg [3:0] op; begin
        op = $urandom_range(1,7); if (op == 5) op = 4;
        c_d = {$urandom,$urandom,$urandom,$urandom,$urandom}; c_d[3:0] = op; c_d[13:4] = {$urandom_range(0,255),1'b0} + ($urandom_range(0,3)==0); c_d[23:14] = $urandom_range(0,255); c_d[31:24] = $urandom_range(1,8);
    end endtask
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1; if (!$value$plusargs("ncyc=%d", ncyc)) ncyc = 100000;
        if (!$value$plusargs("pw=%d", pw)) pw = 30; if (!$value$plusargs("px=%d", px)) px = 30; if (!$value$plusargs("pc=%d", pc)) pc = 20;
        $urandom(seed); err = 0; nlo = 0; nsw = 0; ncw = 0; nxw = 0; nhs = 0;
        c_v = 0; c_d = 0; sw_v = 0; sw_a = 0; sw_m = 0; sw_d = 0; cw_v = 0; cw_a = 0; cw_d = 0; x_rv = 0; x_ra = 0; x_wv = 0; x_wa = 0; x_wm = 0; x_wd = 0; hq_v = 0; hq_d = 0;
        repeat (6) @(posedge clk); #0.5 rst_n = 1;
        for (cyc = 0; cyc < ncyc; cyc = cyc + 1) begin
            @(negedge clk);
            if (va !== vb) begin err = err + 1; if (err < 6) $display("MISMATCH cyc %0d (diff bits %0d)", cyc, $countones(va ^ vb)); end
            if (a_lo_v) nlo = nlo + 1;
            if ($urandom_range(0,99) < pc) begin c_v = 1; rnd_cmd(); end else c_v = 0;
            sw_v = ($urandom_range(0,99) < pw); sw_a = $urandom_range(0,63); sw_m = ($urandom_range(0,3) == 0) ? $urandom : 8'hFF; sw_d = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
            cw_v = {($urandom_range(0,99) < pw/3), ($urandom_range(0,99) < pw/3)}; cw_a = {$urandom,$urandom}; cw_a[2] = $urandom; cw_a[14] = $urandom; cw_a[11:3] = $urandom_range(0,31); cw_a[23:15] = $urandom_range(0,31); cw_d = {$urandom,$urandom};
            x_wv = ($urandom_range(0,99) < px); x_wa = $urandom_range(0,63); x_wm = ($urandom_range(0,3) == 0) ? $urandom : 8'hFF; x_wd = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
            x_rv = ($urandom_range(0,99) < 20); x_ra = $urandom_range(0,63);
            hq_v = ($urandom_range(0,99) < 60); hq_d = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
            if (a_fault) nfault = nfault + 1;
            if (u_a_.wv !== 2'b00) nsw = nsw + 1;
            if (u_a_.wcol) ncw = ncw + 1;
            if (u_a_.hs_v) nhs = nhs + 1;
        end
        $display("WR_EQ %s cycles %0d mismatches %0d lo_v %0d fault_cycles %0d wv_nonzero %0d wcol %0d hs %0d", err == 0 ? "PASS" : "FAIL", ncyc, err, nlo, nfault, nsw, ncw, nhs);
        $finish;
    end
endmodule
