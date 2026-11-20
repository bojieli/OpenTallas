`timescale 1ns/1ps
// tb_s81hd_pick_split (FABLE-FIX-HEAD-MESH 11-20): ot_s81hd_bundle_native PICK_SPLIT differential bench.
// Four bundles on the same stimulus at the hd_tile parameter point (CV 1, A_INPUT_STAGES 1, ROW_IN_REG 1, FLT_XHOP 1,
// BST 3, MERGE_HOP = MH): PICK_SPLIT 0 (reference), 1, 2, 3.  The CV element macros are behavioural stubs (below):
// after each go an A element drops done, waits a pseudo-random 4..43 cycles and raises done with a pseudo-random
// {key, row, bits}; keys come from a 3-bit range so equal keys (row tie-break) are frequent.  The stubs are seeded from
// INSTANCE, so every bundle sees identical element outputs.
// Check, every cycle after warm-up: split bundle k's res_v and {res_row, res_bits} equal the reference's EXPECT_LAG(k)
// cycles earlier (EXPECT_LAG = popcount(PICK_SPLIT) + LAG_ERR; LAG_ERR != 0 is the mutant the test must catch).
// PASS line: "PICK_SPLIT_PASS results=<n>"; any mismatch prints PICK_SPLIT_FAIL and $fatal.
module tb_s81hd_pick_split;
    parameter integer MH = 1;
    parameter integer LAG_ERR = 0;
    parameter integer NCYC = 20000;
    reg clk = 0, rst_n = 0, go = 0;
    always #0.5 clk = ~clk;
    wire        rv [0:3];
    wire [16:0] rr [0:3];
    wire [31:0] rb [0:3];
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_dut
        wire        fault;
        wire [3:0]  hv;
        wire [127:0] hd;
        wire [67:0] hr;
        wire [19:0] nc;
        ot_s81hd_bundle_native #(.CV(1), .IOREG(1), .SAFE(1), .CUT(9'h1ff), .SPLIT9(1), .A_INPUT_STAGES(1), .MERGE_HOP(MH),
                                 .ROW_IN_REG(1), .FLT_XHOP(1), .BST(3), .PICK_SPLIT(k[1:0])) u_b (
            .hci0_ck0_i(1'b0), .hci0_ck1_i(1'b0), .hci0_mesh_i(1'b0), .hci0_rst_i(1'b0),
            .hci0_ck0_o(nc[0]), .hci0_ck1_o(nc[1]), .hci0_mesh_o(nc[2]), .hci0_rst_o(nc[3]),
            .hci1_ck0_i(1'b0), .hci1_ck1_i(1'b0), .hci1_mesh_i(1'b0), .hci1_rst_i(1'b0),
            .hci1_ck0_o(nc[4]), .hci1_ck1_o(nc[5]), .hci1_mesh_o(nc[6]), .hci1_rst_o(nc[7]),
            .hci2_ck0_i(1'b0), .hci2_ck1_i(1'b0), .hci2_mesh_i(1'b0), .hci2_rst_i(1'b0),
            .hci2_ck0_o(nc[8]), .hci2_ck1_o(nc[9]), .hci2_mesh_o(nc[10]), .hci2_rst_o(nc[11]),
            .hci3_ck0_i(1'b0), .hci3_ck1_i(1'b0), .hci3_mesh_i(1'b0), .hci3_rst_i(1'b0),
            .hci3_ck0_o(nc[12]), .hci3_ck1_o(nc[13]), .hci3_mesh_o(nc[14]), .hci3_rst_o(nc[15]),
            .hci4_ck0_i(1'b0), .hci4_ck1_i(1'b0), .hci4_mesh_i(1'b0), .hci4_rst_i(1'b0),
            .hci4_ck0_o(nc[16]), .hci4_ck1_o(nc[17]), .hci4_mesh_o(nc[18]), .hci4_rst_o(nc[19]),
            .clk(clk), .rst_n(rst_n), .go(go), .row0(17'd256), .xa(256'd0), .xb(256'd0),
            .res_v(rv[k]), .res_row(rr[k]), .res_bits(rb[k]), .fault(fault), .head_v(hv), .head_d(hd), .head_row(hr));
    end endgenerate
    // reference history
    localparam integer H = 8;
    reg        hv_ [0:H-1];
    reg [48:0] hd_ [0:H-1];
    integer cyc = 0, results = 0, errors = 0, i, gap = 0;
    function integer lag(input integer kk);
        lag = kk[0] + kk[1] + LAG_ERR;
    endfunction
    always @(posedge clk) begin
        for (i = H - 1; i > 0; i = i - 1) begin hv_[i] <= hv_[i-1]; hd_[i] <= hd_[i-1]; end
        hv_[0] <= rv[0]; hd_[0] <= {rr[0], rb[0]};
    end
    integer kc;
    always @(negedge clk) if (rst_n && cyc > 200) begin
        if (rv[0] && !hv_[0]) results = results + 1;
        for (kc = 1; kc < 4; kc = kc + 1) begin
            if (rv[kc] !== (lag(kc) == 0 ? rv[0] : hv_[lag(kc) - 1])) begin
                errors = errors + 1;
                if (errors < 6) $display("PICK_SPLIT_FAIL cyc %0d split %0d res_v %b expected %b", cyc, kc, rv[kc],
                                         lag(kc) == 0 ? rv[0] : hv_[lag(kc) - 1]);
            end
            if (rv[kc] === 1'b1 && {rr[kc], rb[kc]} !== (lag(kc) == 0 ? {rr[0], rb[0]} : hd_[lag(kc) - 1])) begin
                errors = errors + 1;
                if (errors < 6) $display("PICK_SPLIT_FAIL cyc %0d split %0d data %h expected %h", cyc, kc, {rr[kc], rb[kc]},
                                         lag(kc) == 0 ? {rr[0], rb[0]} : hd_[lag(kc) - 1]);
            end
        end
    end
    // go every 60..123 cycles (fixed sequence)
    reg [31:0] gs = 32'h1234_5678;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 20) rst_n <= 1;
        gs <= gs ^ (gs << 13) ^ (gs >> 17) ^ (gs << 5);
        go <= 1'b0;
        if (rst_n && cyc > 40) begin
            if (gap == 0) begin go <= 1'b1; gap <= 60 + gs[5:0]; end else gap <= gap - 1;
        end
        if (cyc == NCYC) begin
            if (errors == 0 && results > 50) $display("PICK_SPLIT_PASS results=%0d MH=%0d", results, MH);
            else begin
                $display("PICK_SPLIT_FAIL errors=%0d results=%0d MH=%0d", errors, results, MH);
                $fatal(1, "pick split mismatch");
            end
            $finish;
        end
    end
endmodule

// behavioural CV element stubs (simulation only, this bench)
module ot_s81hd_elemA_cv #(parameter INSTANCE = "") (
    input wire ft_ck0_i, input wire ft_ck1_i, input wire ft_mesh_i, input wire ft_rst_i,
    output wire ft_ck0_o, output wire ft_ck1_o, output wire ft_mesh_o, output wire ft_rst_o,
    input ft_mstrap_i, input rst_n, input go, input [16:0] row0, input [255:0] x, input b_v, input [31:0] b_d,
    output o_v, output [31:0] o_d, output l_v, output [31:0] l_d, output reg done, output reg [16:0] best_row,
    output reg [31:0] best_bits, output reg [31:0] best_key, output fault);
    assign {ft_ck0_o, ft_ck1_o, ft_mesh_o, ft_rst_o} = {ft_ck0_i, ft_ck1_i, ft_mesh_i, ft_rst_i};
    assign {o_v, o_d, l_v, l_d, fault} = 0;
    reg [31:0] s;
    initial begin
        string nm;
        nm = INSTANCE;
        s = 32'h9e37_79b9;
        for (int ci = 0; ci < nm.len(); ci++) s = s * 32'd31 + {24'd0, nm[ci]};
    end
    reg [5:0]  w;
    always @(posedge ft_mstrap_i or negedge rst_n)
        if (!rst_n) begin done <= 1'b0; w <= 6'd0; best_row <= 17'd0; best_bits <= 32'd0; best_key <= 32'd0; end
        else begin
            s <= s ^ (s << 13) ^ (s >> 17) ^ (s << 5);
            if (go) begin done <= 1'b0; w <= 6'd4 + s[5:0] % 40; end
            else if (w != 0) begin
                w <= w - 6'd1;
                if (w == 6'd1) begin
                    done <= 1'b1;
                    best_key <= {29'd0, s[10:8]};
                    best_row <= row0 + {12'd0, s[15:11]};
                    best_bits <= s ^ {s[15:0], s[31:16]};
                end
            end
        end
endmodule

module ot_s81hd_elemB_cv #(parameter INSTANCE = "") (
    input wire ft_ck0_i, input wire ft_ck1_i, input wire ft_mesh_i, input wire ft_rst_i,
    output wire ft_ck0_o, output wire ft_ck1_o, output wire ft_mesh_o, output wire ft_rst_o,
    input ft_mstrap_i, input rst_n, input go, input [255:0] x,
    output o_v, output [31:0] o_d, output fault);
    assign {ft_ck0_o, ft_ck1_o, ft_mesh_o, ft_rst_o} = {ft_ck0_i, ft_ck1_i, ft_mesh_i, ft_rst_i};
    assign {o_v, o_d, fault} = 0;
endmodule
