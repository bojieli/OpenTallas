// PATH-KV-ASTK4 10-25 leaf lockstep: (1) zn_0: new qkd_astk_zn_head_p == old one fed tc/zi delayed by one edge
// (exact +1 cycle: zo/fo and every old register zq/tq equal); (2) ctl: new qkd_astk_ctl_s == old (0 cycles), all
// outputs + the 17 zk_r slices every edge.
module tb;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    // ---------------- zn_0 ----------------
    reg  [14:0]  tc;  reg [137:0] zi;
    reg  [14:0]  tc_d; reg [137:0] zi_d; reg rn_d;
    always @(posedge ck) rn_d <= rst_n;
    always @(posedge ck) begin tc_d[14:1] <= tc[14:1]; zi_d[137:1] <= zi[137:1]; end
    always @(posedge ck or negedge rn_d) if (!rn_d) begin tc_d[0] <= 0; zi_d[0] <= 0; end else begin tc_d[0] <= tc[0]; zi_d[0] <= zi[0]; end
    wire [137:0] zo_n, zo_o; wire fo_n, fo_o;
    qkd_astk_zn_head_p   u_n (.ck(ck), .rst_n(rst_n), .tc(tc),   .zi(zi),   .zo(zo_n), .fo(fo_n));
    qkd_astk_zn_head_p_o u_o (.ck(ck), .rst_n(rst_n), .tc(tc_d), .zi(zi_d), .zo(zo_o), .fo(fo_o));
    // ---------------- ctl ----------------
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
    integer cyc = 0, mz = 0, mc = 0, mk = 0, nv = 0, nemit = 0, nst = 0, i;
    reg [15:0] lm, zs;
    always @(negedge ck) begin
        cyc <= cyc + 1;
        if (cyc == 6) rst_n <= 1;
        if (cyc == 40000) rst_n <= 0;          // mid-run reset
        if (cyc == 40004) rst_n <= 1;
        // zn_0 stimulus
        for (i = 0; i < 138; i = i + 32) zi[i +: 32] <= $random;
        zi[0] <= ($random % 3) != 0;
        tc[14:1] <= (($random % 97) == 0) ? $random : tc[14:1];
        tc[0] <= ($random % 211) == 0;
        // ctl stimulus: start rare, schedule ages small so the Z window opens
        lm = 16'd1 + ($unsigned($random) % 40); zs = lm + 16'd4 + ($unsigned($random) % 60);
        cal <= (($random % 5) == 0) ? {zs, lm} : cal;
        st <= $random;
        for (i = 0; i < 540; i = i + 32) aq[i +: 32] <= $random;
        aq[0] <= ($unsigned($random) % 300) == 0;
        for (i = 0; i < 267; i = i + 32) xi[i +: 32] <= $random;
        for (i = 0; i < 138; i = i + 32) czi[i +: 32] <= $random;
        am <= {$random, $random}; fz <= ($random % 50) == 0;
    end
    always @(posedge ck) if (cyc > 8) begin
        if (zo_n !== zo_o || fo_n !== fo_o || u_n.zq !== u_o.zq || u_n.tq !== u_o.tq) begin
            mz = mz + 1; if (mz < 5) $display("ZN0 MISMATCH cyc %0d", cyc); end
        if (u_n.zq[0]) nv = nv + 1;
        if (lt_n !== lt_o || ap_n !== ap_o || af_n !== af_o || qo_n !== qo_o || qf_n !== qf_o || tf_n !== tf_o) begin
            mc = mc + 1; if (mc < 5) $display("CTL MISMATCH cyc %0d", cyc); end
        if (zk_n !== zk_o) begin mk = mk + 1; if (mk < 5) $display("ZK MISMATCH cyc %0d", cyc); end
        if (c_n.z_emit) nemit = nemit + 1;
        if (c_n.start) nst = nst + 1;
        if (cyc == 80000) begin
            $display("ASTK4 LEAF zn0_mismatch %0d (valid %0d) ctl_mismatch %0d zk_mismatch %0d (starts %0d z_emit %0d) %s", mz, nv, mc, mk, nst, nemit,
                     (mz == 0 && mc == 0 && mk == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
