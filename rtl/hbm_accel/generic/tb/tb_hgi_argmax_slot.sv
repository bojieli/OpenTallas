`timescale 1ns/1ps
// mtp-lead 2026-10-09 (from hgi-adapters tb_hgi_argmax_record): bench of ot_hgi_argmax_slot = ot_hgi_argmax_record on the REAL engine (ot_hgi_argmax18_m GENERIC18 = 1, LP 8)
// and the REAL VM (ot_hgi_vm_unit NC 2: client 0 = the adapter, client 1 = this bench's loader / checker).
// Vectors: tools/hgi_adapters/argmax_bench.py.  RUN: VM loaded, record sent, retire (done) awaited, O = {value, id} read
// back and compared (hbm-sim CF-ARG vm_out / numpy semantics), nan_flag compared.  NEGATIVE: fault, nothing written.
// Prints HGI_ARGMAX PASS / FAIL.
module tb_hgi_argmax_slot;
`ifdef MUT_RANK
    localparam integer MS = 1;
`else
    localparam integer MS = 0;
`endif
    `include "am_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [827:0] casem [0:NCASE-1];
    reg [63:0]  vmm [0:NVM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/am_case.mem"}, casem); $readmemh({dir, "/am_vm.mem"}, vmm);
    end
    integer errors = 0;
    reg rst_n = 0;
    reg [682:0] rec = 0; reg [7:0] rank = 0;
    wire [2:0] ret; wire [337:0] vmq; wire [273:0] vmr0, vmr1; reg [337:0] tq = 0;
    // mtp-lead: the DUT is the R25G MTP-slot unit ot_hgi_argmax_slot (adapter + engine behind the 683 / 3 dispatch bus);
    // the engine and adapter are inside it, die_id = the case's rank, the su_red stream idle
    wire o_v, o_nan, o_f, o_rf; wire [17:0] o_idx; wire [31:0] o_val;
    ot_hgi_argmax_slot #(.MUT(MS)) u (.clk(clk), .rst_n(rst_n), .f_hgi_cmdproc(rec), .t_hgi_cmdproc(ret), .die_id(rank),
        .vmq(vmq), .vmr(vmr0), .in_v(1'b0), .in_last(1'b0), .in_bias_en(1'b0), .in_mask(8'd0), .in_vals(256'd0),
        .in_bias(256'd0), .out_v(o_v), .out_idx(o_idx), .out_nan(o_nan), .fault(o_f), .out_range_fault(o_rf), .out_value(o_val));
    wire nan_flag = u.nan_flag;
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
    integer c, i, kind, f0, nw, t, runs = 0, negs = 0, writes0;
    reg [31:0] q, ev, ei, ob, ois; reg en;
    integer wr_seen = 0;
    always @(posedge clk) if (rst_n && vmq[337] && vmq[336]) wr_seen = wr_seen + 1;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][827:824]; rank = casem[c][823:816]; en = casem[c][815:812]; ev = casem[c][811:780];
            ei = casem[c][779:748]; f0 = casem[c][747:716]; nw = casem[c][715:684];
            rst_n = 0; rec = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
            for (i = 0; i < nw; i = i + 1) vm_req(1'b1, vmm[f0 + i][63:32], vmm[f0 + i][31:0], q);
            wr_seen = 0;
            @(negedge clk); rec = casem[c][682:0];
            @(negedge clk); rec[0] = 1'b0;
            t = 0; while (!(ret[1] || ret[2]) && t < 200000) begin @(negedge clk); t = t + 1; end
            if (c < 3 || c % 10 == 0) $display("case %0d kind %0d: %0d VM words, retire after %0d cycles", c, kind, nw, t);
            if (kind == 0) begin
                if (!ret[1] || ret[2]) begin $display("ERR case %0d: no retire (fault %0d)", c, ret[2]); errors = errors + 1; end
                else begin
                    ob = casem[c][385 + 8 +: 32]; ois = casem[c][385 + 120 +: 16]; if (ois == 0) ois = 1;
                    vm_req(1'b0, ob, 0, q);
                    if (q !== ev) begin $display("ERR case %0d value %h, expected %h", c, q, ev); errors = errors + 1; end
                    vm_req(1'b0, ob + ois, 0, q);
                    if (q !== ei) begin $display("ERR case %0d id %0d, expected %0d", c, q, ei); errors = errors + 1; end
                    if (nan_flag !== en) begin $display("ERR case %0d nan flag %0d", c, nan_flag); errors = errors + 1; end
                end
                runs = runs + 1;
            end else begin
                repeat (20) @(posedge clk);
                if (!ret[2] && t >= 200000 || wr_seen != 0 || ret[0]) begin $display("ERR negative case %0d", c); errors = errors + 1; end
                else negs = negs + 1;
            end
        end
        $display("summary: %0d argmax records run, %0d negatives refused", runs, negs);
        if (errors == 0) $display("HGI_ARGMAX PASS"); else $display("HGI_ARGMAX FAIL errors=%0d", errors);
        $finish;
    end
endmodule
