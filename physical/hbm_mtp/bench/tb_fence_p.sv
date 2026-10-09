`timescale 1ns/1ps
// mtp-hbm 2026-10-08: transaction-level exactness of ot_gpu_rf_visibility_fence_p against the original
// ot_gpu_rf_visibility_fence (ENABLE 1).  Two independent reactive environments (random valid / ready / ACK delays,
// same operation script: epochs, vector counts, capture data, an illegal op and a wrong-epoch producer_done near the
// end) drive the two DUTs; the host-write stream (dst, data hash), the ACK-visible stream (addr, epoch), the fence
// stream (epoch) and the final fault must be identical.  +MUT=1 (fence_p MUT 1) must FAIL.
module fence_env #(parameter integer PV = 0, parameter integer MUT = 0, parameter integer SEED = 1, parameter integer NOP = 40) (
    input wire clk, input wire rst_n, output reg fin);
    reg op_valid = 0; reg [7:0] op_epoch = 0; reg [9:0] op_vectors = 0;
    reg cap_valid = 0; reg [7:0] cap_epoch = 0; reg [8:0] cap_addr = 0; reg cap_last = 0; reg [4095:0] cap_data = 0;
    reg producer_done_valid = 0; reg [7:0] producer_done_epoch = 0;
    reg host_wr_ready = 0, host_ack_valid = 0, ack_retire_enable = 1, fence_ready = 0;
    wire op_ready, cap_ready, host_wr_valid, host_ack_ready, vav, wv, fence_valid, pw, fault;
    wire [8:0] host_dst, vaa; wire [4095:0] host_wdata; wire [7:0] vae, fence_epoch;
    generate if (PV == 0) begin : g_o
        ot_gpu_rf_visibility_fence #(.ENABLE(1)) dut (.clk(clk), .rst_n(rst_n), .op_valid(op_valid), .op_ready(op_ready),
            .op_epoch(op_epoch), .op_vectors(op_vectors), .cap_valid(cap_valid), .cap_ready(cap_ready), .cap_epoch(cap_epoch),
            .cap_addr(cap_addr), .cap_last(cap_last), .cap_data(cap_data), .producer_done_valid(producer_done_valid),
            .producer_done_epoch(producer_done_epoch), .host_wr_valid(host_wr_valid), .host_wr_ready(host_wr_ready),
            .host_dst(host_dst), .host_wdata(host_wdata), .host_ack_valid(host_ack_valid), .host_ack_ready(host_ack_ready),
            .ack_retire_enable(ack_retire_enable), .vector_ACK_visible(vav), .vector_ACK_addr(vaa), .vector_ACK_epoch(vae),
            .writes_visible(wv), .fence_valid(fence_valid), .fence_ready(fence_ready), .fence_epoch(fence_epoch),
            .pending_write(pw), .fault(fault));
    end else begin : g_p
        ot_gpu_rf_visibility_fence_p #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .op_valid(op_valid), .op_ready(op_ready),
            .op_epoch(op_epoch), .op_vectors(op_vectors), .cap_valid(cap_valid), .cap_ready(cap_ready), .cap_epoch(cap_epoch),
            .cap_addr(cap_addr), .cap_last(cap_last), .cap_data(cap_data), .producer_done_valid(producer_done_valid),
            .producer_done_epoch(producer_done_epoch), .host_wr_valid(host_wr_valid), .host_wr_ready(host_wr_ready),
            .host_dst(host_dst), .host_wdata(host_wdata), .host_ack_valid(host_ack_valid), .host_ack_ready(host_ack_ready),
            .ack_retire_enable(ack_retire_enable), .vector_ACK_visible(vav), .vector_ACK_addr(vaa), .vector_ACK_epoch(vae),
            .writes_visible(wv), .fence_valid(fence_valid), .fence_ready(fence_ready), .fence_epoch(fence_epoch),
            .pending_write(pw), .fault(fault));
    end endgenerate
    // ---- event logs ----
    reg [63:0] wlog [0:65535]; reg [16:0] alog [0:65535]; reg [7:0] flog [0:4095];
    integer nw = 0, na = 0, nf = 0, k;
    reg [63:0] h;
    reg wr_seen = 0;
    always @(posedge clk) if (rst_n) begin
        if (host_wr_valid && host_wr_ready) begin
            h = {55'd0, host_dst};
            for (k = 0; k < 64; k = k + 1) h = (h ^ host_wdata[k*64 +: 64]) * 64'h100000001B3;
            wlog[nw] = h; nw = nw + 1; wr_seen = 1;
        end
        if (vav) begin alog[na] = {vaa, vae}; na = na + 1; end
        if (fence_valid && fence_ready) begin flog[nf] = fence_epoch; nf = nf + 1; end
    end
    // ---- reactive host: write accepted after a random delay, ACK after a random delay ----
    integer rs = SEED, ack_due = -1, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    always @(negedge clk) if (rst_n) begin
        host_wr_ready = ($urandom(rs) % 3) != 0; rs = rs + 1;
        fence_ready = ($urandom(rs) % 4) != 0; rs = rs + 1;
        if (wr_seen && ack_due < 0) begin ack_due = cyc + 1 + ($urandom(rs) % 6); wr_seen = 0; end
        rs = rs + 1;
        if (host_ack_valid && host_ack_ready) begin host_ack_valid = 0; ack_due = -1; end
        else if (ack_due >= 0 && cyc >= ack_due) host_ack_valid = 1;
    end
    // ---- producer script (same content for both environments; timing reacts to the DUT) ----
    integer o, v, nv, ep, guard, exp_w = 0;
    initial begin
        fin = 0;
        @(posedge rst_n); repeat (8) @(negedge clk);
        for (o = 0; o < NOP; o = o + 1) begin
            ep = (o * 37 + 5) & 255; nv = 1 + ((o * 13) % 9);
            if (o == NOP - 2) nv = 0;                                   // illegal op: a fault (sticky)
            @(negedge clk); op_valid = 1; op_epoch = ep; op_vectors = nv;
            guard = 0;
            @(posedge clk); while (!op_ready && guard < 50) begin @(posedge clk); guard = guard + 1; end
            #0.1 op_valid = 0;
            if (guard >= 50) begin repeat (20) @(negedge clk); o = NOP; end
            else begin
                for (v = 0; v < nv; v = v + 1) begin
                    repeat ($urandom(rs) % 3) @(negedge clk); rs = rs + 1;
                    cap_valid = 1; cap_epoch = ep; cap_addr = v; cap_last = (v == nv - 1);
                    for (k = 0; k < 128; k = k + 1) cap_data[k*32 +: 32] = (o * 1000003 + v * 7919 + k) * 2654435761;
                    @(posedge clk); while (!cap_ready) @(posedge clk);
                    #0.1 cap_valid = 0;
                end
                // the producer signals done once its writes are visible (fault timing then does not race the writes)
                exp_w = exp_w + nv; guard = 0;
                while ((nw < exp_w || pw) && guard < 400) begin @(negedge clk); guard = guard + 1; end
                @(negedge clk); producer_done_valid = 1; producer_done_epoch = (o == NOP - 3) ? ep ^ 8'h55 : ep;
                @(negedge clk); producer_done_valid = 0;
                guard = 0;
                while (fence_valid === 1'bx || (!fault && nf < o + 1 && guard < 400)) begin @(negedge clk); guard = guard + 1; end
                if (fault) begin repeat (30) @(negedge clk); o = NOP; end
            end
        end
        repeat (60) @(negedge clk);
        fin = 1;
    end
endmodule
module tb_fence_p;
    parameter integer MUT = 0, SEED = 7;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    wire f0, f1;
    fence_env #(.PV(0), .SEED(SEED)) e0 (.clk(clk), .rst_n(rst_n), .fin(f0));
    fence_env #(.PV(1), .MUT(MUT), .SEED(SEED + 1000)) e1 (.clk(clk), .rst_n(rst_n), .fin(f1));
    integer i, bad = 0;
    initial begin
        repeat (4) @(posedge clk); rst_n = 1;
        wait (f0 && f1);
        if (e0.nw != e1.nw || e0.na != e1.na || e0.nf != e1.nf || e0.g_o.dut.fault !== e1.fault) bad = bad + 1;
        for (i = 0; i < e0.nw && i < e1.nw; i = i + 1) if (e0.wlog[i] !== e1.wlog[i]) bad = bad + 1;
        for (i = 0; i < e0.na && i < e1.na; i = i + 1) if (e0.alog[i] !== e1.alog[i]) bad = bad + 1;
        for (i = 0; i < e0.nf && i < e1.nf; i = i + 1) if (e0.flog[i] !== e1.flog[i]) bad = bad + 1;
        $display("FENCE_P %s writes=%0d/%0d acks=%0d/%0d fences=%0d/%0d fault=%0d/%0d bad=%0d", bad ? "FAIL" : "PASS",
            e0.nw, e1.nw, e0.na, e1.na, e0.nf, e1.nf, e0.fault, e1.fault, bad);
        $finish;
    end
    initial begin #2000000; $display("FENCE_P FAIL TIMEOUT"); $finish; end
endmodule
