`timescale 1ps/1ps
// tb_ot_s81_vm_x34_sw2_diff (S-VM-X34 2026-10-16): cycle differential of the VM parent's u_xsw transfer, the former
// ot_s81_vm_x34 #(.W(1026)) (REF) vs ot_s81_vm_x34_sw2 (two W514 halves, DUT).  One epoch source: serial 1112 ps, stream
// 834 ps (3 x 1112 = 4 x 834).  Random s_v and random 1026-b s_d on every serial cycle; o_v, o_d and fault of the two are
// compared after EVERY stream edge from the first edge after reset release (incl. warm-up; o_d compared bit-for-bit
// always, not only when valid).  +mode 0: resets on the epoch contract (no fault allowed); +mode 1: stream reset one
// stream cycle late; +mode 2: serial reset one serial cycle late (both must raise the same fault on the same edge).
// Mutants +define+OT_VM_X34SPLIT_MUT_SWAP / _MUT_DROP must FAIL.
module tb_ot_s81_vm_x34_sw2_diff;
    reg s_ck = 0, t_ck = 0, s_rn = 0, t_rn = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    reg s_v = 0; reg [1025:0] s_d = 0;
    wire r_v, d_v, r_f, d_f; wire [1025:0] r_d, d_d;
    ot_s81_vm_x34 #(.W(1026)) u_ref (.s_ck(s_ck), .s_rst_n(s_rn), .s_v(s_v), .s_d(s_d), .t_ck(t_ck), .t_rst_n(t_rn),
        .o_v(r_v), .o_d(r_d), .fault(r_f));
    ot_s81_vm_x34_sw2 u_dut (.s_ck(s_ck), .s_rst_n(s_rn), .s_v(s_v), .s_d(s_d), .t_ck(t_ck), .t_rst_n(t_rn),
        .o_v(d_v), .o_d(d_d), .fault(d_f));
    integer mode = 0, seed = 1, seed0 = 1, nep = 3000, bad = 0, edges = 0, valid = 0, faults = 0, i;
    always @(posedge s_ck) begin
        #10 s_v = $random(seed);
        for (i = 0; i < 1026; i = i + 32) s_d[i +: 32] = $random(seed);
    end
    always @(posedge t_ck) if (t_rn) begin
        #20;
        edges = edges + 1;
        if (r_v) valid = valid + 1;
        if (r_f) faults = faults + 1;
        if (r_v !== d_v || r_d !== d_d || r_f !== d_f || u_dut.hv[1] !== u_dut.hv[0]) begin
            bad = bad + 1;
            if (bad < 5) $display("MISMATCH edge %0d v %b/%b f %b/%b d_eq %b", edges, r_v, d_v, r_f, d_f, r_d === d_d);
        end
    end
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        seed0 = seed;
        if (!$value$plusargs("nep=%d", nep)) nep = 3000;
        #(3336 * 4 - 100);
        s_rn = (mode == 2) ? 0 : 1; t_rn = (mode == 1) ? 0 : 1;
        if (mode == 1) begin #(834); t_rn = 1; end
        if (mode == 2) begin #(1112); s_rn = 1; end
        #(3336 * nep);
        if (mode == 0 && (r_f || faults)) begin bad = bad + 1; $display("UNEXPECTED FAULT"); end
        if (mode != 0 && !r_f) begin bad = bad + 1; $display("EXPECTED FAULT MISSING"); end
        $display("TB_X34SW2 RESULT mode %0d seed %0d edges %0d valid %0d fault_edges %0d bad %0d", mode, seed0, edges, valid, faults, bad);
        $display("TB_X34SW2 %s mode %0d", (bad == 0 && edges > 1000 && valid > 500) ? "PASS" : "FAIL", mode);
        $finish;
    end
endmodule
