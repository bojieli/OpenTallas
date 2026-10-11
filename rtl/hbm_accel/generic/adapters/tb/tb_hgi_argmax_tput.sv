`timescale 1ns/1ps
// hgi-1010/tput1-argmax (2026-10-10): PRODUCTION-SHAPE throughput bench of ARGMAX.LOCAL: ot_hgi_argmax_record (LPS 8 =
// the closed build | 16 = opt-in wide) + the REAL engine ot_hgi_argmax18_m (GENERIC18 1, LP = LPS) + the REAL VM
// (ot_hgi_vm_unit NC 2: client 0 = the adapter's O writes, client 1 = this bench's checker).
// Vectors: tools/hgi_unitrate/argmax_tput_vec.py (the real Qwen3-8B / DeepSeek-V4.1 ARGMAX.LOCAL dispatches, A = STREAM).
// Per record: dispatch (rec valid) -> the producer sends the logit row as LPS-lane STREAM beats while am_rdy, one beat
// every GAP cycles (GAP 1 = the stream bus at full rate: the unit's own throughput) -> retire (done) -> O {value, id}
// read back from VM and compared with the golden (numpy argmax), nan_flag compared.
// Prints per record "REC k disp D first F last L ret R" (cycles from the dispatch) and HGI_ARGMAX_TPUT PASS / FAIL.
module tb_hgi_argmax_tput;
`ifndef LPS
 `define LPS 8
`endif
`ifndef MUT
 `define MUT 0
`endif
    localparam integer LPS = `LPS, MUTV = `MUT, SWB = 3 + 65 * LPS;
    `include "at_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [823:0] casem [0:NCASE-1];
    reg [31:0]  strm [0:NSTR-1];
    reg [8*256-1:0] dir;
    integer gap = 1;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("GAP=%d", gap)) gap = 1;
        $readmemh({dir, "/at_case.mem"}, casem); $readmemh({dir, "/at_str.mem"}, strm);
    end
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer errors = 0;
    reg rst_n = 0;
    reg [682:0] rec = 0; reg [7:0] rank = 0; reg [SWB-1:0] ams = 0;
    wire [2:0] ret; wire nan_flag, am_rdy; wire [337:0] vmq; wire [273:0] vmr0, vmr1; reg [337:0] tq = 0;
    wire e_in_v, e_in_last, e_bias_en, e_out_v, e_out_nan, e_fault, e_rf; wire [LPS-1:0] e_mask; wire [LPS*32-1:0] e_vals, e_bias;
    wire [6:0] e_rank; wire [17:0] e_imm, e_idx; wire [31:0] e_val;
    ot_hgi_argmax_record #(.LPS(LPS), .MUT(MUTV)) u (.clk(clk), .rst_n(rst_n), .cfg_rank(rank), .rec(rec), .ret(ret),
        .nan_flag(nan_flag), .vmq(vmq), .vmr(vmr0), .am_stream(ams), .am_rdy(am_rdy), .e_in_v(e_in_v), .e_in_last(e_in_last),
        .e_bias_en(e_bias_en), .e_mask(e_mask), .e_vals(e_vals), .e_bias(e_bias), .e_rank(e_rank), .e_imm(e_imm),
        .e_out_v(e_out_v), .e_out_idx(e_idx), .e_out_nan(e_out_nan), .e_fault(e_fault), .e_range_fault(e_rf),
        .e_out_value(e_val));
    ot_hgi_argmax18_m #(.LP(LPS), .GENERIC18(1)) u_e (.clk(clk), .rst_n(rst_n), .in_v(e_in_v), .in_last(e_in_last),
        .in_bias_en(e_bias_en), .in_mask(e_mask), .in_vals(e_vals), .in_bias(e_bias), .cfg_rank(e_rank), .cfg_imm_a(e_imm),
        .out_v(e_out_v), .out_idx(e_idx), .out_nan(e_out_nan), .fault(e_fault), .out_range_fault(e_rf), .out_value(e_val));
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, vmq}), .cr({vmr1, vmr0}), .status());
    integer tw;
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] q);
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!vmr1[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 1000) begin $display("ERR VM request timeout (word %0d)", word); $finish; end
            q = vmr1[32 * word[2:0] +: 32];
        end
    endtask
    integer c, i, j, n, f0, t, nb, b, g, t0, tf, tl, tr;
    reg [31:0] q, ev, ei, ob, ois; reg en;
    reg [683:0] rb;
    integer sum_ret = 0, max_tail = 0;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            rank = casem[c][823:816]; en = casem[c][815:812]; ev = casem[c][811:780]; ei = casem[c][779:748];
            f0 = casem[c][747:716]; n = casem[c][715:684]; rb = casem[c][683:0];
            rst_n = 0; rec = 0; ams = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
            // clear the O words (a stale value must not pass)
            ob = rb[385 + 8 +: 32]; ois = rb[385 + 120 +: 16]; if (ois == 0) ois = 1;
            vm_req(1'b1, ob, 32'hDEAD_BEEF, q); vm_req(1'b1, ob + ois, 32'hDEAD_BEEF, q);
            @(negedge clk); rec = rb[682:0]; t0 = cyc;
            @(negedge clk); rec[0] = 1'b0;
            nb = (n + LPS - 1) / LPS; b = 0; g = 0; tf = -1; tl = -1; t = 0;
            while (!(ret[1] || ret[2]) && t < 400000) begin
                ams[0] = 1'b0; ams[1] = 1'b0;
                if (b < nb && am_rdy && g == 0) begin
                    ams = 0; ams[0] = 1'b1; ams[1] = (b == nb - 1);
                    for (j = 0; j < LPS; j = j + 1)
                        if (b * LPS + j < n) begin ams[2 + j] = 1'b1; ams[2 + LPS + 32 * j +: 32] = strm[f0 + b * LPS + j]; end
                    if (b == 0) tf = cyc - t0;
                    if (b == nb - 1) tl = cyc - t0;
                    b = b + 1; g = gap - 1;
                end else if (g > 0) g = g - 1;
                @(negedge clk); t = t + 1;
            end
            ams = 0;
            tr = cyc - t0;
            if (!ret[1] || ret[2]) begin $display("ERR case %0d: no retire (fault %0d)", c, ret[2]); errors = errors + 1; end
            else begin
                vm_req(1'b0, ob, 0, q);
                if (q !== ev) begin $display("ERR case %0d value %h, expected %h", c, q, ev); errors = errors + 1; end
                vm_req(1'b0, ob + ois, 0, q);
                if (q !== ei) begin $display("ERR case %0d id %0d, expected %0d", c, q, ei); errors = errors + 1; end
                if (nan_flag !== en) begin $display("ERR case %0d nan flag %0d expected %0d", c, nan_flag, en); errors = errors + 1; end
            end
            $display("REC %0d n %0d rank %0d disp 0 first %0d last %0d ret %0d tail %0d", c, n, rank, tf, tl, tr, tr - tl);
            sum_ret = sum_ret + tr; if (tr - tl > max_tail) max_tail = tr - tl;
        end
        $display("summary: %0d records LPS %0d GAP %0d MUT %0d: dispatch->retire total %0d, max last-beat->retire %0d",
                 NCASE, LPS, gap, MUTV, sum_ret, max_tail);
        if (errors == 0) $display("HGI_ARGMAX_TPUT PASS"); else $display("HGI_ARGMAX_TPUT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
