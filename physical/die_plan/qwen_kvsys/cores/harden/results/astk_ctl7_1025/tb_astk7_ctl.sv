// PATH-KV-ASTK7 10-25 ctl lockstep: ASTK7 qkd_astk_ctl_s == ASTK6 (old, renamed _o), 0 cycles: every output, the fault
// flag f, the slot registers and the 17 zk_r slices, every edge; z_done events counted (must be exercised).
`timescale 1ns/1ps
module tb;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [31:0] cal; reg [1:0] st; reg [539:0] aq; reg [34:0] am; reg [266:0] xi; reg [137:0] czi; reg fz;
    wire [20:0] lt_n, lt_o; wire [42:0] ap_n, ap_o; wire af_n, af_o; wire [571:0] qo_n, qo_o, qf_n, qf_o; wire [59:0] tf_n, tf_o;
    qkd_astk_ctl_s   #(.Z_STRIDE(4), .PORT_REGS(1), .AM_G_PIN(0), .G_CONST(1'b0)) c_n (.cal(cal), .ck(ck), .rst_n(rst_n), .st(st), .aq(aq),
        .lt(lt_n), .am(am), .ap(ap_n), .af(af_n), .qo(qo_n), .tc_faces(tf_n), .qo_face(qf_n), .xi(xi), .zi(czi), .fz(fz));
    qkd_astk_ctl_s_o #(.Z_STRIDE(4), .PORT_REGS(1), .AM_G_PIN(0), .G_CONST(1'b0)) c_o (.cal(cal), .ck(ck), .rst_n(rst_n), .st(st), .aq(aq),
        .lt(lt_o), .am(am), .ap(ap_o), .af(af_o), .qo(qo_o), .tc_faces(tf_o), .qo_face(qf_o), .xi(xi), .zi(czi), .fz(fz));
    wire [4*17-1:0] zk_n, zk_o;
    genvar g;
    generate for (g = 0; g < 17; g = g + 1) begin : g_c
        assign zk_n[4*g +: 4] = c_n.g_zk[g].zk_r;
        assign zk_o[4*g +: 4] = c_o.g_zk[g].zk_r;
    end endgenerate
    integer cyc = 0, mc = 0, mk = 0, mf = 0, mr = 0, nst = 0, nemit = 0, ndone = 0, nf = 0, i;
    reg [15:0] lm, zs;
    always @(negedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1;
        if (cyc == 40000) rst_n <= 0;
        if (cyc == 40004) rst_n <= 1;
        if (cyc == 90000) rst_n <= 0;
        if (cyc == 90002) rst_n <= 1;
        lm = 16'd1 + ($unsigned($random) % 40); zs = lm + 16'd4 + ($unsigned($random) % 60);
        // occasional illegal schedules (fault path)
        if (($unsigned($random) % 41) == 0) zs = $random;
        cal <= (($random % 5) == 0) ? {zs, lm} : cal;
        st <= $random;
        for (i = 0; i < 540; i = i + 32) aq[i +: 32] <= $random;
        aq[0] <= ($unsigned($random) % 200) == 0;
        // short stacks too, so nblk * Z_STRIDE lands inside the window often
        if (($unsigned($random) % 3) == 0) aq[14:1] <= $unsigned($random) % 700;
        for (i = 0; i < 267; i = i + 32) xi[i +: 32] <= $random;
        for (i = 0; i < 138; i = i + 32) czi[i +: 32] <= $random;
        am <= {$random, $random}; fz <= ($random % 50) == 0;
    end
    always @(posedge ck) if (cyc > 8) begin
        if (lt_n !== lt_o || ap_n !== ap_o || af_n !== af_o || qo_n !== qo_o || qf_n !== qf_o || tf_n !== tf_o) begin
            mc = mc + 1; if (mc < 5) $display("CTL MISMATCH cyc %0d", cyc); end
        if (zk_n !== zk_o) mk = mk + 1;
        if (c_n.f !== c_o.f) begin mf = mf + 1; if (mf < 5) $display("F MISMATCH cyc %0d", cyc); end
        if (c_n.z_done_r !== c_o.z_done_slot || c_n.l_slot_r !== c_o.l_slot || c_n.z_slot_r !== c_o.z_slot) begin
            mr = mr + 1; if (mr < 5) $display("SLOT MISMATCH cyc %0d", cyc); end
        if (c_n.start) nst = nst + 1;
        if (c_n.z_emit) nemit = nemit + 1;
        if (c_o.z_done_slot) ndone = ndone + 1;
        if (c_o.f) nf = nf + 1;
        if (cyc == 120000) begin
            $display("ASTK7 CTL checks %0d ctl_mismatch %0d zk_mismatch %0d f_mismatch %0d slot_mismatch %0d (starts %0d z_emit %0d z_done %0d f_cycles %0d) %s",
                     cyc - 9, mc, mk, mf, mr, nst, nemit, ndone, nf, (mc == 0 && mk == 0 && mf == 0 && mr == 0 && ndone > 50 && nf > 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
