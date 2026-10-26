// TYPE-DEDUP: lockstep miter of the KV hg row config chain kvs_hroot_<Q>.o_cN, as bound in
// physical/die_plan/qwen_kvsys/bind/bound_r8/rtl/kv3_hg_v1_part_r{1..5}.sv (tapered: row k receives 5(k+1) bits,
// consumes the top 5, forwards the low 5k), against the proposed uniform ROTATING chain (every row receives 30 bits,
// consumes [29:25], forwards {q[24:0], q[29:25]}: no constants, no tie-offs, one netlist for r1/r3/r5).
// r4 keeps its own R8 pad (pd2 on its cfg slice) in both chains; hg_EN_0 consumes 5 bits (top slice of r1's out in
// the rotating chain).  Every row's cfg and the epoch bits are compared every cycle for NCYC random cycles,
// with resets asserted at random.  Boundary cells: the bound tree's ot_dp_st / ot_dp_dly (bind_cells.sv).
`timescale 1ns/1ps
`default_nettype none
module row_taper #(parameter integer K = 1, parameter integer PAD = 0) (
    input wire clk, input wire rst_n, input wire [5*(K+1):0] i, output wire [5*K:0] o, output wire [4:0] cfg);
    wire [5*(K+1)-1:0] q; wire eq;
    ot_dp_st #(.W(5*(K+1))) u_bin (.clk(clk), .rst_n(rst_n), .d(i[5*(K+1)-1:0]), .ea(i[5*(K+1)]), .q(q), .eq(eq));
    ot_dp_st #(.W(5*K)) u_bout (.clk(clk), .rst_n(rst_n), .d(q[5*K-1:0]), .ea(rst_n), .q(o[5*K-1:0]), .eq(o[5*K]));
    generate if (PAD > 0) begin : g_pad
        ot_dp_dly #(.W(5), .D(PAD)) u_pd (.clk(clk), .d(q[5*K+4:5*K]), .q(cfg));
    end else begin : g_nopad
        assign cfg = q[5*K+4:5*K];
    end endgenerate
endmodule
module row_rot #(parameter integer PAD = 0) (
    input wire clk, input wire rst_n, input wire [30:0] i, output wire [30:0] o, output wire [4:0] cfg);
    wire [29:0] q; wire eq;
    ot_dp_st #(.W(30)) u_bin (.clk(clk), .rst_n(rst_n), .d(i[29:0]), .ea(i[30]), .q(q), .eq(eq));
    ot_dp_st #(.W(30)) u_bout (.clk(clk), .rst_n(rst_n), .d({q[24:0], q[29:25]}), .ea(rst_n), .q(o[29:0]), .eq(o[30]));
    generate if (PAD > 0) begin : g_pad
        ot_dp_dly #(.W(5), .D(PAD)) u_pd (.clk(clk), .d(q[29:25]), .q(cfg));
    end else begin : g_nopad
        assign cfg = q[29:25];
    end endgenerate
endmodule
module en0 (input wire clk, input wire rst_n, input wire [5:0] i, output wire [4:0] cfg, output wire eq);
    ot_dp_st #(.W(5)) u_bin (.clk(clk), .rst_n(rst_n), .d(i[4:0]), .ea(i[5]), .q(cfg), .eq(eq));
endmodule
module tb;
    reg clk = 0, rst_n = 0;
    reg [30:0] src;                        // hg_EN_6 -> hg_EN_5: 30 data + epoch (as bound)
    always #1 clk = ~clk;
    // tapered (as bound): r5 .. r1, r4 with the pd2 pad
    wire [25:0] t5; wire [20:0] t4; wire [15:0] t3; wire [10:0] t2; wire [5:0] t1;
    wire [4:0] tc5, tc4, tc3, tc2, tc1, tc0; wire te0;
    row_taper #(.K(5))         T5 (clk, rst_n, src, t5, tc5);
    row_taper #(.K(4), .PAD(2)) T4 (clk, rst_n, t5, t4, tc4);
    row_taper #(.K(3))         T3 (clk, rst_n, t4, t3, tc3);
    row_taper #(.K(2))         T2 (clk, rst_n, t3, t2, tc2);
    row_taper #(.K(1))         T1 (clk, rst_n, t2, t1, tc1);
    en0                        T0 (clk, rst_n, t1, tc0, te0);
    // rotating (proposed): one row module; r4 keeps its pad
    wire [30:0] u5, u4, u3, u2, u1; wire [4:0] uc5, uc4, uc3, uc2, uc1, uc0; wire ue0;
    row_rot         U5 (clk, rst_n, src, u5, uc5);
    row_rot #(.PAD(2)) U4 (clk, rst_n, u5, u4, uc4);
    row_rot         U3 (clk, rst_n, u4, u3, uc3);
    row_rot         U2 (clk, rst_n, u3, u2, uc2);
    row_rot         U1 (clk, rst_n, u2, u1, uc1);
    en0             U0 (clk, rst_n, {u1[30], u1[29:25]}, uc0, ue0);
    integer cyc = 0, errs = 0, checked = 0;
    integer NCYC;
    initial begin
        if (!$value$plusargs("NCYC=%d", NCYC)) NCYC = 200000;
        src = 0;
        repeat (3) @(negedge clk);
        rst_n = 1;
        while (cyc < NCYC) begin
            @(negedge clk);
            src = {$random, $random};
            if (($random & 1023) == 0) rst_n = 0; else rst_n = 1;
            cyc = cyc + 1;
        end
        $display("MITER kv_hg_cn %s: %0d cycles, %0d compared, %0d mismatches", errs ? "FAIL" : "PASS", cyc, checked, errs);
        $finish;
    end
    reg warm = 0;
    always @(posedge clk) if (cyc > 12) warm <= 1;
    always @(negedge clk) if (warm) begin
        checked = checked + 1;
        if ({tc5, tc4, tc3, tc2, tc1, tc0, te0} !== {uc5, uc4, uc3, uc2, uc1, uc0, ue0} ||
            {t5[25], t4[20], t3[15], t2[10], t1[5]} !== {u5[30], u4[30], u3[30], u2[30], u1[30]}) begin
            errs = errs + 1;
            if (errs < 5) $display("mismatch cyc %0d: taper %h rot %h", cyc, {tc5, tc4, tc3, tc2, tc1, tc0, te0},
                                   {uc5, uc4, uc3, uc2, uc1, uc0, ue0});
        end
    end
endmodule
