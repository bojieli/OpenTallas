`timescale 1ns/1ps
// hgi-adapters (2026-10-09): STREAM path bench: STREAM 0 beats (the SM's logits, shuffled arrival order) -> the D1 SU
// unit (head_scale SU.VOP: A STREAM, B VM scales staged from the REAL HGI VM, O STREAM) -> the 523-b stream -> ARGMAX
// (ot_hgi_argmax_record + the REAL ot_hgi_argmax18_m) -> {value, id} in VM.  Records exactly as the hbm-sim Qwen token
// program issues them (n 300 / 1,001 / 37,984).  Prints HGI_SU_STREAM PASS / FAIL.
module tb_hgi_su_stream;
    `include "ss_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [3139:0] casem [0:NCASE-1]; reg [63:0] strm [0:NSTR-1]; reg [63:0] vmm [0:NVM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/ss_case.mem"}, casem); $readmemh({dir, "/ss_stream.mem"}, strm); $readmemh({dir, "/ss_vm.mem"}, vmm);
    end
    integer errors = 0, cyc = 0, seed = 9; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [2196:0] sur; reg su_v = 0; reg [682:0] amr = 0; reg [7:0] rank = 0;
    reg s0_v = 0; reg [19:0] s0_idx = 0; reg [31:0] s0_data = 0;
    wire su_rdy, su_done, su_fault, su_halt; wire [522:0] ams; wire am_rdy; wire [2:0] am_ret; wire nan_flag;
    wire [337:0] sq, aq; wire [273:0] sr, ar, tr; reg [337:0] tq = 0;
    ot_hgi_su_unit #(.N(32), .M(8), .LV(7)) u_su (.clk(clk), .rst_n(rst_n), .rec_v(su_v), .rec_rdy(su_rdy),
        .rec_hdr(sur[127:0]), .rec_sut(sur[383:128]), .rec_a(sur[639:384]), .rec_b(sur[895:640]), .rec_c(sur[1151:896]),
        .rec_d(sur[1407:1152]), .rec_o(sur[1663:1408]), .rec_r(sur[1919:1664]), .rec_i(sur[2175:1920]),
        .rec_n_a(sur[2196:2176]), .rec_done(su_done), .rec_fault(su_fault), .halted(su_halt), .vmq(sq), .vmr(sr),
        .s0_v(s0_v), .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(ams), .am_rdy(am_rdy));
    wire e_in_v, e_in_last, e_bias_en, e_out_v, e_out_nan, e_fault, e_rf; wire [7:0] e_mask; wire [255:0] e_vals, e_bias;
    wire [6:0] e_rank; wire [17:0] e_imm, e_idx; wire [31:0] e_val;
    ot_hgi_argmax_record u_am (.clk(clk), .rst_n(rst_n), .cfg_rank(rank), .rec(amr), .ret(am_ret), .nan_flag(nan_flag),
        .vmq(aq), .vmr(ar), .am_stream(ams), .am_rdy(am_rdy), .e_in_v(e_in_v), .e_in_last(e_in_last),
        .e_bias_en(e_bias_en), .e_mask(e_mask), .e_vals(e_vals), .e_bias(e_bias), .e_rank(e_rank), .e_imm(e_imm),
        .e_out_v(e_out_v), .e_out_idx(e_idx), .e_out_nan(e_out_nan), .e_fault(e_fault), .e_range_fault(e_rf),
        .e_out_value(e_val));
    ot_hgi_argmax18_m #(.LP(8), .GENERIC18(1)) u_e (.clk(clk), .rst_n(rst_n), .in_v(e_in_v), .in_last(e_in_last),
        .in_bias_en(e_bias_en), .in_mask(e_mask), .in_vals(e_vals), .in_bias(e_bias), .cfg_rank(e_rank), .cfg_imm_a(e_imm),
        .out_v(e_out_v), .out_idx(e_idx), .out_nan(e_out_nan), .fault(e_fault), .out_range_fault(e_rf), .out_value(e_val));
    ot_hgi_vm_unit #(.NC(3)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, aq, sq}), .cr({tr, ar, sr}), .status());
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    integer amd, sud, suf;
    always @(posedge clk) begin if (rst_n && am_ret[1]) amd = amd + 1; if (rst_n && (am_ret[2] || su_fault)) suf = suf + 1;
                                if (rst_n && su_done) sud = sud + 1; end
    integer c, j, t, n, s0, v0, nv, t0; reg [31:0] qd, ev, ei, ob;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            n = casem[c][3139:3108]; rank = casem[c][3107:3076]; ev = casem[c][3043:3012]; ei = casem[c][3011:2980];
            s0 = casem[c][2979:2948]; v0 = casem[c][2947:2916]; nv = casem[c][2915:2884];
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nv; j = j + 1) vm_req(1'b1, vmm[v0 + j][63:32], vmm[v0 + j][31:0], qd);
            amd = 0; sud = 0; suf = 0; t0 = cyc;
            // the SU record and the ARGMAX record are both dispatched (program order), then the SM stream arrives
            @(negedge clk); sur = casem[c][2196 + 684:684]; su_v = 1;
            while (!su_rdy) @(negedge clk);
            @(posedge clk); #0.1 su_v = 0;
            @(negedge clk); amr = casem[c][682:0];
            @(negedge clk); amr[0] = 1'b0;
            for (j = 0; j < n; j = j + 1) begin
                @(negedge clk); s0_v = 1; s0_idx = strm[s0 + j][51:32]; s0_data = strm[s0 + j][31:0];
                if (($random(seed) & 3) == 0) begin @(negedge clk); s0_v = 0; end
            end
            @(negedge clk); s0_v = 0;
            t = 0; while (amd == 0 && suf == 0 && t < 2000000) begin @(posedge clk); t = t + 1; end
            if (amd != 1 || suf != 0 || sud != 1) begin $display("ERR case %0d: argmax done %0d su done %0d faults %0d", c, amd, sud, suf); errors = errors + 1; end
            ob = amr[385 + 8 +: 32];
            vm_req(1'b0, ob, 0, qd);
            if (qd !== ev) begin $display("ERR case %0d value %h expected %h", c, qd, ev); errors = errors + 1; end
            vm_req(1'b0, ob + 1, 0, qd);
            if (qd !== ei) begin $display("ERR case %0d id %0d expected %0d", c, qd, ei); errors = errors + 1; end
            $display("case %0d: n %0d, stream -> scale -> argmax in %0d cycles", c, n, cyc - t0); $fflush;
        end
        if (errors == 0) $display("HGI_SU_STREAM PASS"); else $display("HGI_SU_STREAM FAIL errors=%0d", errors);
        $finish;
    end
endmodule
