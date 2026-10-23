`timescale 1ns/1ps
// KV-P3-LEAF 10-23: bench of the plan ID cells (rtl/lib/ot_dp_id.sv).
//   chain A: ot_dp_id_src (V = 3) -> 40 x ot_dp_id_add (K = 1, W = 5): partition j must see (3 + j) mod 32 (wraps);
//   chain B: ot_dp_id_add K = 5, W = 3 on every a in 0..7: (a + 5) mod 8;
//   chain C: ot_dp_id_src (table 4,5,0,1,2,3,6,7, element 0 first) -> 8 x ot_dp_id_rot (N 8, W 3): partition j's o must
//            be PHYS[j];  rot N = 1 passes through.
// MUT 1: the add chain uses K = 2 (must FAIL); MUT 2: the table rotates the wrong way (must FAIL).
module tb_ot_dp_id #(parameter integer MUT = 0);
    localparam integer NA = 40;
    wire [4:0] ida [0:NA];
    ot_dp_id_src #(.W(5), .V(5'd3)) u_src (.y(ida[0]));
    genvar j;
    generate for (j = 0; j < NA; j = j + 1) begin : g_a
        ot_dp_id_add #(.W(5), .K((MUT == 1) ? 2 : 1)) u_add (.a(ida[j]), .y(ida[j+1]));
    end endgenerate
    reg  [2:0] b_a;
    wire [2:0] b_y;
    ot_dp_id_add #(.W(3), .K(5)) u_b (.a(b_a), .y(b_y));
    localparam [23:0] PHYS = {3'd7, 3'd6, 3'd3, 3'd2, 3'd1, 3'd0, 3'd5, 3'd4};   // element 0 (LSB) = 4
    wire [23:0] tab [0:8];
    wire [2:0]  own [0:7];
    ot_dp_id_src #(.W(24), .V(PHYS)) u_tsrc (.y(tab[0]));
    generate for (j = 0; j < 8; j = j + 1) begin : g_c
        if (MUT == 2) begin : g_bad
            wire [23:0] t = {tab[j][20:0], tab[j][23:21]};
            ot_dp_id_rot #(.N(8), .W(3)) u_rot (.a(t), .o(own[j]), .y(tab[j+1]));
        end else begin : g_ok
            ot_dp_id_rot #(.N(8), .W(3)) u_rot (.a(tab[j]), .o(own[j]), .y(tab[j+1]));
        end
    end endgenerate
    wire [2:0] one_o, one_y;
    ot_dp_id_rot #(.N(1), .W(3)) u_one (.a(3'd6), .o(one_o), .y(one_y));
    integer k, errs;
    initial begin
        errs = 0;
        #1;
        for (k = 0; k <= NA; k = k + 1)
            if (ida[k] !== 5'((3 + k) % 32)) begin errs = errs + 1; $display("MISMATCH add j %0d %0d", k, ida[k]); end
        for (k = 0; k < 8; k = k + 1) begin
            b_a = 3'(k); #1;
            if (b_y !== 3'((k + 5) % 8)) begin errs = errs + 1; $display("MISMATCH add3 %0d %0d", k, b_y); end
        end
        for (k = 0; k < 8; k = k + 1)
            if (own[k] !== PHYS[3*k +: 3]) begin errs = errs + 1; $display("MISMATCH rot j %0d %0d", k, own[k]); end
        if (tab[8] !== PHYS) begin errs = errs + 1; $display("MISMATCH rot wrap"); end
        if (one_o !== 3'd6 || one_y !== 3'd6) begin errs = errs + 1; $display("MISMATCH rot N1"); end
        if (errs == 0) $display("PASS tb_ot_dp_id MUT %0d", MUT);
        else $display("FAIL tb_ot_dp_id %0d mismatches MUT %0d", errs, MUT);
        $finish;
    end
endmodule
