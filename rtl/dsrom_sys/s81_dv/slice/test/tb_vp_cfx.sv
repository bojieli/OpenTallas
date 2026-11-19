`timescale 1ns/1ps
// TYPE-SAFE-5 11-10 (from DIE-S81-85 11-09 tb_vp_sr): CFR bench, SHIFT 0 = same cycle. Lock-step equivalence bench for ot_s81sl_vp SR (OT_S81SL_VP_SRAMREG).
// ref = vp SR 0 (renamed _r), new = vp SR 1 (renamed _n), identical random inputs every cycle (legal and illegal
// schedules alike).  Contract: new outputs at cycle t + SHIFT == ref outputs at t, except hr_* (vn read request) at t.
module tb;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg c_v, sw_v, x_rv, x_wv, hq_v; reg [159:0] c_d; reg [9:0] sw_a, x_ra, x_wa; reg [7:0] sw_m, x_wm;
    reg [255:0] sw_d, x_wd, hq_d; reg [1:0] cw_v; reg [23:0] cw_a; reg [63:0] cw_d;
`define VP_PORTS(sfx) \
    wire lo_v``sfx, s_v``sfx, x_qv``sfx, hw_v``sfx, hw_hf``sfx, hr_v``sfx, hr_hf``sfx, n_go``sfx, m_v``sfx, m_q``sfx, m_b``sfx, wl_v``sfx, fault``sfx; \
    wire [255:0] lo_d``sfx, x_qd``sfx, hw_d``sfx, wl_d``sfx; wire [159:0] s_d``sfx; wire [2:0] hw_j``sfx, hr_j``sfx, wl_i``sfx; \
    wire [127:0] n_pre``sfx; wire [7:0] m_i``sfx;
    `VP_PORTS(_a)
    `VP_PORTS(_b)
`define VP_CONN(sfx) .clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d), \
    .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d), .lo_v(lo_v``sfx), .lo_d(lo_d``sfx), .s_v(s_v``sfx), .s_d(s_d``sfx), .x_rv(x_rv), .x_ra(x_ra), \
    .x_qv(x_qv``sfx), .x_qd(x_qd``sfx), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd), .hw_v(hw_v``sfx), .hw_j(hw_j``sfx), \
    .hw_hf(hw_hf``sfx), .hw_d(hw_d``sfx), .hr_v(hr_v``sfx), .hr_j(hr_j``sfx), .hr_hf(hr_hf``sfx), .hq_v(hq_v), .hq_d(hq_d), \
    .n_go(n_go``sfx), .n_pre(n_pre``sfx), .m_v(m_v``sfx), .m_q(m_q``sfx), .m_b(m_b``sfx), .m_i(m_i``sfx), .wl_v(wl_v``sfx), \
    .wl_i(wl_i``sfx), .wl_d(wl_d``sfx), .fault(fault``sfx)
    ot_s81sl_vp_r #(.HQX(`HQXV), .CS_HI_D(`CSD), .CS_HO_D(`CSD)) u_a (`VP_CONN(_a));
    ot_s81sl_vp_n #(.HQX(`HQXV), .CS_HI_D(`CSD), .CS_HO_D(`CSD), .CFX(`CFXV)) u_b (`VP_CONN(_b));
`define OUTS(sfx) {lo_v``sfx, lo_d``sfx, s_v``sfx, s_d``sfx, x_qv``sfx, x_qd``sfx, hw_v``sfx, hw_j``sfx, hw_hf``sfx, hw_d``sfx, \
    n_go``sfx, n_pre``sfx, m_v``sfx, m_q``sfx, m_b``sfx, m_i``sfx, wl_v``sfx, wl_i``sfx, wl_d``sfx, fault``sfx}
    localparam integer OW = 1+256+1+160+1+256+1+3+1+256+1+128+1+1+1+8+1+3+256+1;
    wire [OW-1:0] oa = `OUTS(_a), ob = `OUTS(_b);
    wire [6:0] ha = {hr_v_a, hr_j_a, hr_hf_a}, hb = {hr_v_b, hr_j_b, hr_hf_b};
`define NOHW(sfx) {lo_v``sfx, lo_d``sfx, s_v``sfx, s_d``sfx, x_qv``sfx, x_qd``sfx, n_go``sfx, n_pre``sfx, m_v``sfx, m_q``sfx, m_b``sfx, m_i``sfx, wl_v``sfx, wl_i``sfx, wl_d``sfx}
    localparam integer NW = 1+256+1+160+1+256+1+128+1+1+1+8+1+3+256, HW = 1+3+1+256;
    wire [NW-1:0] na = `NOHW(_a), nb = `NOHW(_b);
    wire [HW-1:0] hwa = {hw_v_a, hw_j_a, hw_hf_a, hw_d_a}, hwb = {hw_v_b, hw_j_b, hw_hf_b, hw_d_b};
    reg awb = 0, awb_q = 0; reg [HW-1:0] hwa_q; integer nwb = 0;
    reg [OW-1:0] oa_q [0:3];
    wire [OW-1:0] oref = (`SHIFT == 0) ? oa : oa_q[(`SHIFT == 0) ? 0 : `SHIFT - 1];
    integer cyc = 0, errs = 0, checks = 0, nv = 0, nfault = -1, nlo = 0, nhw = 0, nng = 0, nxq = 0, nwl = 0, nsv = 0, seed;
    // op mix: mostly legal one-op-at-a-time streams with gaps, sometimes overlapping (fault paths)
    function automatic [159:0] rcmd(input integer r);
        reg [3:0] o; begin
            case (r % 9) 0: o = 4'd1; 1: o = 4'd2; 2: o = 4'd3; 3: o = 4'd4; 4: o = 4'd5; 5: o = 4'd6; 6: o = 4'd7;
                default: o = 4'd8 + ($urandom % 8); endcase
            `ifdef NOPOST
            if (o == 4'd2) o = 4'd3;
`endif
            rcmd = {{4{$urandom}}, $urandom} ; rcmd[3:0] = o;
            rcmd[31:24] = 8'd1 + ($urandom % 6);
        end
    endfunction
    integer gap = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 8) rst_n <= 1'b1;
        // inputs
        c_v <= 1'b0; c_d <= {5{$urandom}};
        if (cyc > 20) begin
            if (gap > 0) gap <= gap - 1;
            else if (($urandom % 4) == 0) begin c_v <= 1'b1; c_d <= rcmd($urandom); gap <= (`DENSE) ? 0 : `GAPMIN + ($urandom % 8); end
        end
        sw_v <= ($urandom % 7) == 0; sw_a <= $urandom; sw_m <= $urandom; sw_d <= {8{$urandom}};
        cw_v <= (($urandom % 5) == 0) ? $urandom : 2'b00; cw_a <= $urandom; cw_d <= {$urandom, $urandom};
        x_rv <= ($urandom % 9) == 0; x_ra <= $urandom; x_wv <= ($urandom % 11) == 0; x_wa <= $urandom; x_wm <= $urandom;
        x_wd <= {8{$urandom}}; hq_v <= ($urandom % 3) != 0; hq_d <= {8{$urandom}};
        // compare
        oa_q[0] <= oa; for (int j = 1; j < 4; j++) oa_q[j] <= oa_q[j - 1];
        // CFX contract: hc_post write-back (hw_* while the ref's wvl drove it) one clk later, every other output the same cycle
        awb <= u_a.wvl; awb_q <= awb; hwa_q <= hwa; if (awb) nwb <= nwb + 1;
        if (cyc > 40) begin
            checks <= checks + 1;
            if (nb !== na) begin errs <= errs + 1; if (errs < 8) $display("MISMATCH cyc %0d same-cycle outputs: diff bits %0d", cyc, $countones(nb ^ na)); end
            if (awb_q && hwb !== {1'b1, hwa_q[HW-2:0]}) begin errs <= errs + 1; if (errs < 8) $display("MISMATCH cyc %0d write-back + 1: diff bits %0d v %b", cyc, $countones(hwb ^ hwa_q), hw_v_b); end
            if (!awb && !awb_q && hwb !== hwa) begin errs <= errs + 1; if (errs < 8) $display("MISMATCH cyc %0d hw (no write-back): diff bits %0d", cyc, $countones(hwb ^ hwa)); end
`ifndef DENSE_CTL
            if (fault_b !== fault_a) begin errs <= errs + 1; if (errs < 8) $display("MISMATCH cyc %0d fault %b/%b", cyc, fault_b, fault_a); end
`endif
            if (hb !== ha) begin errs <= errs + 1; if (errs < 8) $display("MISMATCH cyc %0d hr", cyc); end
            if (lo_v_a) nlo <= nlo + 1; if (hw_v_a) nhw <= nhw + 1; if (n_go_a) nng <= nng + 1; if (x_qv_a) nxq <= nxq + 1;
            if (wl_v_a) nwl <= nwl + 1; if (s_v_a) nsv <= nsv + 1;
            if (fault_a && nfault < 0) nfault <= cyc;
        end
        if (cyc == `NCYC) begin
            $display("VP_CFX_RESULT %s checks %0d errors %0d write-backs %0d | events lo %0d hw %0d n_go %0d x_q %0d wl %0d s %0d | first ref fault cyc %0d",
                (errs == 0) ? "PASS" : "FAIL", checks, errs, nwb, nlo, nhw, nng, nxq, nwl, nsv, nfault);
            $finish;
        end
    end
endmodule
