`timescale 1ns/1ps
// tb_dsfd_svc_hs (s81-die-rtl-bind 2026-10-14): exact bench of the svc HBM-status face against a cycle model.
// Random jd_i / flt_i every cycle; hs scenarios: (A) live rises, no fault -> outputs = inputs one cycle later;
// (B) fault pulse -> sticky fault on jd_o[1] / flt_o; (C) reset, live rises then drops -> sticky fault; (D) reset with live
// never high, drop irrelevant -> no fault.  MUT 8 (hf not folded) must FAIL.
module tb_dsfd_svc_hs;
    parameter integer MUT = 0;
    reg ck = 0, rst = 0; always #1 ck = ~ck;
    reg [1:0] hs = 0, jd_i = 0; reg flt_i = 0;
    wire [1:0] jd_o; wire flt_o;
    dsfd_svc_hs #(.MUT(MUT)) dut (.ck(ck), .rst(rst), .hs(hs), .jd_i(jd_i), .flt_i(flt_i), .jd_o(jd_o), .flt_o(flt_o));
    // model
    reg [1:0] m_rs; reg [1:0] m0, m1; reg m_up, m_hf; reg [1:0] m_jd; reg m_flt;
    integer errs = 0, checks = 0, faults_seen = 0, cyc;
    always @(posedge ck or negedge rst)
        if (!rst) m_rs <= 0; else m_rs <= {m_rs[0], 1'b1};
    always @(posedge ck or negedge m_rs[1])
        if (!m_rs[1]) begin m0 <= 0; m1 <= 0; m_up <= 0; m_hf <= 0; m_jd <= 0; m_flt <= 0; end
        else begin
            m0 <= hs; m1 <= m0; if (m1[0]) m_up <= 1; if (m1[1] || (m_up && !m1[0])) m_hf <= 1;
            m_jd <= {jd_i[1] | m_hf, jd_i[0]}; m_flt <= flt_i | m_hf;
        end
    always @(negedge ck) if (rst) begin
        checks = checks + 1;
        if (jd_o !== m_jd || flt_o !== m_flt) errs = errs + 1;
        if (m_flt && !flt_i) faults_seen = faults_seen + 1;
    end
    task run(input integer n, input [1:0] h); integer i; begin
        for (i = 0; i < n; i = i + 1) begin @(posedge ck); #0.1 hs = h; jd_i = $random; flt_i = ($random % 7) == 0; end
    end endtask
    initial begin
        // A
        #5 rst = 1; run(10, 2'b00); run(200, 2'b01);
        // B
        run(1, 2'b11); run(100, 2'b01);
        // C
        rst = 0; #4 rst = 1; run(20, 2'b00); run(50, 2'b01); run(50, 2'b00);
        // D
        rst = 0; #4 rst = 1; run(100, 2'b00);
        if (faults_seen == 0) errs = errs + 1;          // the scenarios must exercise the fold
        $display("TB_DSFD_SVC_HS checks=%0d errors=%0d faults_folded=%0d %s", checks, errs, faults_seen, errs == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
