`timescale 1ns/1ps
// QW-SLICE7-LEAVES sc2 lockstep bench: DUT `DUTMOD vs REF `REFMOD (original qfd_dv_s5_sc, MU_NU 4) on random legal
// scheduled traffic: non-root phases (pass words both ways, own PSUM / AMI+AMV / RB, RB taps on every VM window, TOK
// latch) and root phases (nb PSUMs from dn / up / own -> total or fused rsqrt -> RB broadcast + w1; four per-user argmax
// merges with simultaneous dn / up / own candidates and value ties -> TOK).  Each output stream (dn_o, up_o words, w1
// writes, tok events) must match in order and value; every event's edge offset must be the priced one for its kind:
// `OFF0 (face regs), `OFF0+`AMO (root argmax merge; default 1), `OFF0+`DT (root total), `OFF0+`DR (fused rsqrt).  fault 0 on both.
`ifndef AMO
`define AMO 1
`endif
module tb_sc2;
    reg ck = 0; always #5 ck = ~ck;
    reg rst_n = 0;
    reg [100:0] sc_cfg = 0; reg [47:0] dn_i = 0, up_i = 0; reg red_we = 0; reg [23:0] red_addr = 0; reg [31:0] red_data = 0;
    reg [7:0] vm_we = 0; reg [1:0] vm_win0 = 0; reg [31:0] vm_wdata0 = 0; reg am_v = 0; reg [23:0] am_idx = 0;
    reg [31:0] am_val = 0; reg [1:0] am_u = 0;
    wire [47:0] d_dn, r_dn, d_up, r_up; wire d_we, r_we, d_tv, r_tv, d_to, r_to, d_b, r_b, d_f, r_f;
    wire [23:0] d_wa, r_wa, d_ti, r_ti; wire [31:0] d_wd, r_wd, d_tval, r_tval; wire [1:0] d_tu, r_tu;
    `DUTMOD dut (.ck(ck), .rst_n(rst_n), .sc_cfg(sc_cfg), .dn_i(dn_i), .dn_o(d_dn), .up_i(up_i), .up_o(d_up), .red_we(red_we),
        .red_addr(red_addr), .red_data(red_data), .vm_we(vm_we), .vm_win0(vm_win0), .vm_wdata0(vm_wdata0), .am_v(am_v),
        .am_idx(am_idx), .am_val(am_val), .am_u(am_u), .w1_we(d_we), .w1_addr(d_wa), .w1_data(d_wd), .tok_v(d_tv),
        .tok_idx(d_ti), .tok_own(d_to), .tok_val(d_tval), .tok_user(d_tu), .busy(d_b), .fault(d_f));
    `REFMOD refm (.ck(ck), .rst_n(rst_n), .sc_cfg(sc_cfg), .dn_i(dn_i), .dn_o(r_dn), .up_i(up_i), .up_o(r_up), .red_we(red_we),
        .red_addr(red_addr), .red_data(red_data), .vm_we(vm_we), .vm_win0(vm_win0), .vm_wdata0(vm_wdata0), .am_v(am_v),
        .am_idx(am_idx), .am_val(am_val), .am_u(am_u), .w1_we(r_we), .w1_addr(r_wa), .w1_data(r_wd), .tok_v(r_tv),
        .tok_idx(r_ti), .tok_own(r_to), .tok_val(r_tval), .tok_user(r_tu), .busy(r_b), .fault(r_f));
    integer cyc = 0, errors = 0;
    // streams: 0 dn_o, 1 up_o, 2 w1, 3 tok
    integer rt0[$], dt0[$], rt1[$], dt1[$], rt2[$], dt2[$], rt3[$], dt3[$];
    reg [63:0] rv0[$], dv0[$], rv1[$], dv1[$], rv2[$], dv2[$], rv3[$], dv3[$];
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (rst_n && cyc > 3) begin
        if (r_dn[47]) begin rt0.push_back(cyc); rv0.push_back({16'd0, r_dn}); end
        if (d_dn[47]) begin dt0.push_back(cyc); dv0.push_back({16'd0, d_dn}); end
        if (r_up[47]) begin rt1.push_back(cyc); rv1.push_back({16'd0, r_up}); end
        if (d_up[47]) begin dt1.push_back(cyc); dv1.push_back({16'd0, d_up}); end
        if (r_we) begin rt2.push_back(cyc); rv2.push_back({8'd0, r_wa, r_wd}); end
        if (d_we) begin dt2.push_back(cyc); dv2.push_back({8'd0, d_wa, d_wd}); end
        if (r_tv) begin rt3.push_back(cyc); rv3.push_back({5'd0, r_to, r_tu, r_ti, r_to ? r_tval : 32'd0}); end
        if (d_tv) begin dt3.push_back(cyc); dv3.push_back({5'd0, d_to, d_tu, d_ti, d_to ? d_tval : 32'd0}); end
        end
        if (rst_n && cyc > 3 && (d_f !== 1'b0 || r_f !== 1'b0)) begin
            errors = errors + 1; if (errors < 5) $display("MISMATCH fault cyc=%0d d=%b r=%b", cyc, d_f, r_f); end
    end
    integer ok_off[0:3][0:3];
    task automatic cmp(input integer st, ref integer rt[$], ref integer dt[$], ref reg [63:0] rv[$], ref reg [63:0] dv[$]);
        integer j, o, good, k;
        if (rt.size() != dt.size()) begin errors = errors + 1; $display("MISMATCH stream %0d count ref=%0d dut=%0d", st, rt.size(), dt.size()); end
        for (j = 0; j < rt.size() && j < dt.size(); j = j + 1) begin
            o = dt[j] - rt[j]; good = 0;
            for (k = 0; k < 4; k = k + 1) if (ok_off[st][k] == o) good = 1;
            if (rv[j] !== dv[j] || !good) begin
                errors = errors + 1;
                if (errors < 12) $display("MISMATCH stream %0d ev %0d ref t=%0d %h dut t=%0d %h off=%0d", st, j, rt[j], rv[j], dt[j], dv[j], o);
            end
        end
    endtask
    function automatic [31:0] rnd_f(input integer pos);
        rnd_f = {pos ? 1'b0 : 1'($urandom % 2), 8'(115 + $urandom % 20), 23'($urandom)};
    endfunction
    integer s, rounds, r, i, n, a, u, c, nb, amnb, fuse, kind, src, act, gapc;
    integer used[0:31];
    integer nwords = 0, nps = 0, ntok = 0, nrr = 0, ntot = 0;
    task automatic idle(); sc_cfg = 0; dn_i = 0; up_i = 0; red_we = 0; vm_we = 0; am_v = 0; endtask
    task automatic step(); @(negedge ck); idle(); endtask
    initial begin
        if (!$value$plusargs("seed=%d", s)) s = 1;
        void'($urandom(s));
        if (!$value$plusargs("rounds=%d", rounds)) rounds = 40;
        ok_off[0][0] = `OFF0; ok_off[0][1] = `OFF0 + `AMO; ok_off[0][2] = `OFF0 + `DR; ok_off[0][3] = `OFF0;
        for (i = 0; i < 4; i = i + 1) ok_off[1][i] = ok_off[0][i];
        ok_off[2][0] = `OFF0; ok_off[2][1] = `OFF0 + `DT; ok_off[2][2] = `OFF0 + `DR; ok_off[2][3] = `OFF0;
        ok_off[3][0] = `OFF0; ok_off[3][1] = `OFF0 + `AMO; ok_off[3][2] = `OFF0; ok_off[3][3] = `OFF0;
        repeat (6) @(negedge ck); rst_n = 1;
        repeat (12) @(negedge ck);
        for (r = 0; r < rounds; r = r + 1) begin
            // ---------------- non-root phase
            idle(); sc_cfg = {1'b1, 1'b0, 1'($urandom % 2), 6'd0, 24'($urandom), 1'b0, 24'($urandom), 32'd0, 5'd0, 6'd0};
            step(); repeat (3) step();
            for (i = 0; i < 120; i = i + 1) begin
                act = $urandom % 8;
                case (act)
                    0, 1: begin kind = 1 + $urandom % 5; dn_i = {1'b1, 3'(kind), 12'($urandom), 32'($urandom)}; nwords = nwords + 1; end
                    2, 3: begin kind = 1 + $urandom % 5; up_i = {1'b1, 3'(kind), 12'($urandom), 32'($urandom)}; nwords = nwords + 1; end
                    4: begin red_we = 1; red_addr = {2'($urandom), 22'($urandom % 32)}; red_data = $urandom; end
                    5: begin am_v = 1; am_idx = $urandom; am_val = $urandom; am_u = $urandom; step(); end
                    6: begin vm_we = 8'($urandom) | 8'd1; vm_win0 = $urandom; vm_wdata0 = $urandom; end
                    default: ;
                endcase
                step();
            end
            repeat (40) step();
            // ---------------- root phase: PSUM reduction
            nb = 1 + $urandom % 32; fuse = $urandom % 2; amnb = 1 + $urandom % 6;
            sc_cfg = {1'b1, 1'b1, 1'($urandom % 2), 6'(nb), 24'($urandom), 1'(fuse), 24'($urandom), 32'h3727c5ac,
                      5'($urandom % 8), 6'(amnb)};
            step(); repeat (3) step();
            for (i = 0; i < 32; i = i + 1) used[i] = 0;
            for (i = 0; i < nb; i = i + 1) begin
                src = $urandom % 3;
                case (src)
                    0: dn_i = {1'b1, 3'd1, 7'd0, 5'(i), rnd_f(1)};
                    1: up_i = {1'b1, 3'd1, 7'd0, 5'(i), rnd_f(1)};
                    default: begin red_we = 1; red_addr = {2'b11, 17'd0, 5'(i)}; red_data = rnd_f(1); end
                endcase
                nps = nps + 1;
                step();
                if ($urandom % 3 == 0) step();
            end
            if (fuse) nrr = nrr + 1; else ntot = ntot + 1;
            repeat (160) step();
            // ---------------- root phase: four users' argmax merges (amnb candidates each)
            for (u = 0; u < 4; u = u + 1) begin
                c = 0;
                while (c < amnb) begin
                    a = 1 + $urandom % 3; if (a > amnb - c) a = amnb - c;
                    // index beats on dn / up
                    if (a >= 1) dn_i = {1'b1, 3'd3, 10'd0, 2'(u), 8'd0, 24'($urandom)};
                    if (a >= 2) up_i = {1'b1, 3'd3, 10'd0, 2'(u), 8'd0, 24'($urandom)};
                    step();
                    gapc = ($urandom % 4 == 0) ? 32'h40400000 : rnd_f(0);
                    if (a >= 1) dn_i = {1'b1, 3'd4, 10'd0, 2'(u), ($urandom % 2) ? gapc : rnd_f(0)};
                    if (a >= 2) up_i = {1'b1, 3'd4, 10'd0, 2'(u), ($urandom % 2) ? gapc : rnd_f(0)};
                    if (a >= 3) begin am_v = 1; am_idx = $urandom; am_val = gapc; am_u = u; end
                    step();
                    c = c + a; ntok = ntok + (c >= amnb);
                    repeat ($urandom % 3) step();
                end
                repeat (6) step();
            end
            repeat (60) step();
        end
        repeat (200) step();
        cmp(0, rt0, dt0, rv0, dv0); cmp(1, rt1, dt1, rv1, dv1); cmp(2, rt2, dt2, rv2, dv2); cmp(3, rt3, dt3, rv3, dv3);
        if (rt0.size() + rt1.size() < 100 || rt3.size() < 4 * rounds || rt2.size() < 20) begin
            errors = errors + 1; $display("MISMATCH too few events dn=%0d up=%0d w1=%0d tok=%0d", rt0.size(), rt1.size(), rt2.size(), rt3.size()); end
        if (errors) begin $display("SC2_EQ FAIL errors=%0d", errors); $fatal(1, "SC2_EQ FAIL"); end
        $display("SC2_EQ PASS dn=%0d up=%0d w1=%0d tok=%0d (merges %0d, psum %0d, rsqrt %0d, total %0d) OFF0=%0d DT=%0d DR=%0d",
            rt0.size(), rt1.size(), rt2.size(), rt3.size(), ntok, nps, nrr, ntot, `OFF0, `DT, `DR);
        $finish;
    end
endmodule
