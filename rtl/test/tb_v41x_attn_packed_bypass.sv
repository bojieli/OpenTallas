`timescale 1ns/1ps
// Bounded adapter/service handshake gate. The engine stub observes the exact
// stored-format word; it does not claim the engine's numeric result.
module tb_v41x_attn_packed_bypass;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, go = 0;
    reg [15:0] i_nout = 5, i_tiles = 1, i_k = 32;
    reg [23:0] i_ks = 1;
    reg packed_kv_v = 1, packed_kv_fault = 0;
    reg [3:0] packed_kv_m = 4'hf;
    reg [1059:0] packed_kv_w = {265'h17,265'h16,265'h15,265'h14};
    wire packed_kv_ready, kv_re, fault;
    integer beats = 0, cycles = 0;
    ot_hdc_v41x_att_adapt #(.H(4), .IL(4), .D(32), .TD(32), .NL(4),
        .TROWS(8), .NHMAX(4), .PACKED_KV(1)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .i_nout(i_nout), .i_tiles(i_tiles),
        .i_k(i_k), .i_wbase(24'd0), .i_ts(24'd1), .i_ks(i_ks), .i_js(24'd0),
        .i_xbase(24'd0), .i_xks(24'd1), .i_xjs(24'd0), .i_xcs(24'd0),
        .i_hg(2'd0), .i_ogs(24'd0), .i_round(1'b1), .i_obase(24'd0),
        .i_ots(24'd1), .i_ojs(24'd0), .i_mmode(1'b1), .i_oen(1'b1),
        .i_m(3'd0), .kv_re(kv_re), .kv_q(2048'd0), .packed_kv_v(packed_kv_v),
        .packed_kv_ready(packed_kv_ready), .packed_kv_m(packed_kv_m),
        .packed_kv_w(packed_kv_w), .packed_kv_fault(packed_kv_fault),
        .x_q({128{1'b0}}), .fault(fault)
    );
    task automatic run_op(input bit pv);
        begin
            @(negedge clk);
            rst_n = 0; go = 0; beats = 0; cycles = 0;
            i_nout = pv ? 32 : 5;
            i_k = pv ? 5 : 32;
            i_ks = pv ? 16 : 1;
            packed_kv_m = 4'hf;
            @(negedge clk); rst_n = 1; go = 1;
            @(negedge clk); go = 0;
            while (beats < 2 && cycles < 100) begin
                @(posedge clk);
                cycles = cycles + 1;
                if (kv_re) $fatal(1, "packed mode issued scalar KV read");
                if (packed_kv_ready) begin
                    if (!dut.u_attn.kv_v || dut.u_attn.kv_w !== packed_kv_w)
                        $fatal(1, "stored-format beat changed");
                    if (dut.u_attn.kv_m !== (beats == 0 ? 4'hf : 4'h1))
                        $fatal(1, "chronological tail mask mismatch");
                    beats = beats + 1;
                end
                @(negedge clk);
                if (beats != 0) packed_kv_m = 4'h1;
            end
            if (beats != 2) $fatal(1, "packed beat timeout (pv=%0d)", pv);
        end
    endtask
    initial begin
        run_op(0);
        run_op(1);
        $display("PASS packed adapter QK/PV bypass: two exact-format beats each, tail mask, zero scalar reads");
        $finish;
    end
endmodule
