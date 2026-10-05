// ---------------------------------------------------------------------------
// Cross-tile accumulate: a K=256 contraction as two chained 128-deep tiles.
//
// The half-depth weight bank is 27,590.5 um2 against the full-depth pair's
// 41,367.9 and closes post-route -- measured, and a 1.329x iso-area ratio -- but
// a 128-deep bank holds half a reduction tile of a product that declares
// tile_depth=256, so the whole gain was scoped to Qwen3 and unavailable to
// either DeepSeek product.  ``acc_continue`` removes that scope: a continuing
// pass does not clear the accumulators, so a deep contraction is a SEQUENCE of
// passes over consecutive tiles, which is how a tensor core walks a large K.
//
// This bench is the exactness proof, and it needs no reference model because the
// reference is the other structure: ONE unit with a 256-deep bank walks all 256
// columns in one pass, a SECOND unit with a 128-deep bank walks columns 0..127,
// is refilled with 128..255 and walks those with ``acc_continue`` asserted, and
// every lane's 40-bit accumulator is compared bit for bit.  Equality is the
// claim: the split costs nothing in value.
//
// Exactness is structural rather than lucky.  The accumulator is carry-save in a
// fixed-point window whose exponent is ``cfg_scale``, an INPUT, so both passes
// land their terms on the same bit positions and the sum is independent of the
// order the terms arrive in -- the same property the unit already claims within
// one pass.  The bench also asserts the negative: a chain whose ``cfg_scale``
// moves raises ``acc_scale_violation``, because terms aligned two different ways
// must not be added silently.
//
// Run:
//   iverilog -g2012 -o /tmp/acc rtl/proto/ot_mac_lane.sv rtl/proto/ot_mac_tile.sv \
//       rtl/proto/ot_compute_unit.sv rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv \
//       rtl/test/tb_compute_unit_acc_chain.sv && /tmp/acc
// ---------------------------------------------------------------------------
`timescale 1ns/1ps

module tb_compute_unit_acc_chain;
    localparam integer LANES = 16;
    localparam integer ACC_W = 40;
    localparam integer KDEEP = 256;
    localparam integer KHALF = 128;

    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0;

    // ---- shared stimulus -------------------------------------------------
    reg [15:0] wgt_mem [0:KDEEP*LANES-1];
    reg [15:0] act_mem [0:KDEEP-1];
    integer k, l, guard, mism, seed;
    integer deep_cycles, half_cycles_a, half_cycles_b;
    reg [ACC_W-1:0] deep_res [0:LANES-1];
    reg [ACC_W-1:0] split_res [0:LANES-1];

    // A BF16 pattern with a bounded exponent range, so every term lands inside
    // the window and the comparison is about the chain and not about dropping.
    function [15:0] pattern(input integer index);
        reg [7:0] exponent;
        reg [6:0] mantissa;
        begin
            exponent  = 8'd124 + (index % 5);
            mantissa  = index[6:0] ^ 7'h2b;
            pattern   = {index[7], exponent, mantissa};
        end
    endfunction

    // ---- the deep unit: one 256-column pass ------------------------------
    reg         d_start = 1'b0, d_wr_en = 1'b0, d_act_we = 1'b0;
    reg [8:0]   d_cfg_k = KDEEP[8:0];
    reg [7:0]   d_wr_addr = 8'b0;
    reg [16*LANES-1:0] d_wr_data = {(16*LANES){1'b0}};
    reg [8:0]   d_act_waddr = 9'b0;
    reg [15:0]  d_act_wdata = 16'b0;
    reg [4:0]   d_res_sel = 5'b0;
    wire        d_busy, d_done, d_refill_ready, d_stalled, d_viol;
    wire [8:0]  d_refill_col;
    wire [ACC_W-1:0] d_res_data;
    wire [LANES-1:0] d_dropped;

    ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(256)) deep (
        .clk(clk), .rst_n(rst_n), .start(d_start), .cfg_k(d_cfg_k),
        .cfg_scale(8'd127), .wgt_reload(1'b1), .acc_continue(1'b0),
        .busy(d_busy), .done(d_done), .acc_scale_violation(d_viol),
        .wr_en(d_wr_en), .wr_addr(d_wr_addr), .wr_data(d_wr_data),
        .act_we(d_act_we), .act_waddr(d_act_waddr), .act_wdata(d_act_wdata),
        .refill_valid(1'b1), .refill_data({(16*LANES){1'b0}}),
        .refill_col(d_refill_col), .refill_ready(d_refill_ready),
        .stalled(d_stalled),
        .res_sel(d_res_sel), .res_data(d_res_data), .dropped_mask(d_dropped)
    );

    // ---- the half-depth unit: two chained 128-column passes --------------
    reg         h_start = 1'b0, h_wr_en = 1'b0, h_act_we = 1'b0;
    reg         h_cont = 1'b0;
    reg [7:0]   h_scale = 8'd127;
    reg [8:0]   h_cfg_k = KHALF[8:0];
    reg [7:0]   h_wr_addr = 8'b0;
    reg [16*LANES-1:0] h_wr_data = {(16*LANES){1'b0}};
    reg [8:0]   h_act_waddr = 9'b0;
    reg [15:0]  h_act_wdata = 16'b0;
    reg [4:0]   h_res_sel = 5'b0;
    wire        h_busy, h_done, h_refill_ready, h_stalled, h_viol;
    wire [8:0]  h_refill_col;
    wire [ACC_W-1:0] h_res_data;
    wire [LANES-1:0] h_dropped;

    ot_compute_unit #(.LANES(LANES), .ACC_W(ACC_W), .K_MAX(128)) half (
        .clk(clk), .rst_n(rst_n), .start(h_start), .cfg_k(h_cfg_k),
        .cfg_scale(h_scale), .wgt_reload(1'b1), .acc_continue(h_cont),
        .busy(h_busy), .done(h_done), .acc_scale_violation(h_viol),
        .wr_en(h_wr_en), .wr_addr(h_wr_addr), .wr_data(h_wr_data),
        .act_we(h_act_we), .act_waddr(h_act_waddr), .act_wdata(h_act_wdata),
        .refill_valid(1'b1), .refill_data({(16*LANES){1'b0}}),
        .refill_col(h_refill_col), .refill_ready(h_refill_ready),
        .stalled(h_stalled),
        .res_sel(h_res_sel), .res_data(h_res_data), .dropped_mask(h_dropped)
    );

    task fill_half_bank(input integer base);
        begin
            for (k = 0; k < KHALF; k = k + 1) begin
                h_wr_en = 1'b1; h_wr_addr = k[7:0];
                for (l = 0; l < LANES; l = l + 1)
                    h_wr_data[16*l +: 16] = wgt_mem[(base + k)*LANES + l];
                @(posedge clk);
            end
            h_wr_en = 1'b0;
            // The activation register file is addressed by the WALK's column
            // counter, which restarts at zero on every start, so the second
            // tile's activations are written to the same 0..127 slots.  That is
            // the chain's own requirement and not a bench shortcut: a pass reads
            // its own tile's operands from column zero.
            for (k = 0; k < KHALF; k = k + 1) begin
                h_act_we = 1'b1; h_act_waddr = k[8:0];
                h_act_wdata = act_mem[base + k];
                @(posedge clk);
            end
            h_act_we = 1'b0;
            @(posedge clk);
        end
    endtask

    task run_half(input continue_chain);
        begin
            h_cont = continue_chain;
            h_start = 1'b1; @(posedge clk); h_start = 1'b0;
            h_cont = 1'b0;
            guard = 0;
            while (!h_done && guard < 100000) begin @(posedge clk); guard = guard + 1; end
            if (!h_done) begin
                $display("FAIL: half-depth pass timed out after %0d cycles", guard);
                $finish;
            end
        end
    endtask

    initial begin
        for (k = 0; k < KDEEP; k = k + 1) begin
            act_mem[k] = pattern(k * 3 + 1);
            for (l = 0; l < LANES; l = l + 1)
                wgt_mem[k*LANES + l] = pattern(k * 7 + l * 5 + 2);
        end

        repeat (4) @(posedge clk); rst_n = 1'b1; @(posedge clk);

        // -- reference: all 256 columns in one pass ------------------------
        for (k = 0; k < KDEEP; k = k + 1) begin
            d_wr_en = 1'b1; d_wr_addr = k[7:0];
            for (l = 0; l < LANES; l = l + 1)
                d_wr_data[16*l +: 16] = wgt_mem[k*LANES + l];
            @(posedge clk);
        end
        d_wr_en = 1'b0;
        for (k = 0; k < KDEEP; k = k + 1) begin
            d_act_we = 1'b1; d_act_waddr = k[8:0]; d_act_wdata = act_mem[k];
            @(posedge clk);
        end
        d_act_we = 1'b0;
        @(posedge clk);
        d_start = 1'b1; @(posedge clk); d_start = 1'b0;
        guard = 0;
        while (!d_done && guard < 100000) begin @(posedge clk); guard = guard + 1; end
        if (!d_done) begin $display("FAIL: deep pass timed out"); $finish; end
        deep_cycles = guard;
        for (l = 0; l < LANES; l = l + 1) begin
            d_res_sel = l[4:0]; @(posedge clk); deep_res[l] = d_res_data;
        end

        // -- under test: 0..127, then 128..255 continuing -------------------
        fill_half_bank(0);
        run_half(1'b0);
        half_cycles_a = guard;
        fill_half_bank(KHALF);
        run_half(1'b1);
        half_cycles_b = guard;
        for (l = 0; l < LANES; l = l + 1) begin
            h_res_sel = l[4:0]; @(posedge clk); split_res[l] = h_res_data;
        end
        // The throughput cost of the split, in the unit's own cycles: one extra
        // walk setup and one extra drain, against a walk half as long each time.
        $display("CYCLES: one 256-deep pass %0d; two chained 128-deep passes %0d + %0d = %0d (overhead %0d)",
                 deep_cycles, half_cycles_a, half_cycles_b,
                 half_cycles_a + half_cycles_b,
                 (half_cycles_a + half_cycles_b) - deep_cycles);

        mism = 0;
        for (l = 0; l < LANES; l = l + 1)
            if (split_res[l] !== deep_res[l]) begin
                if (mism < 6)
                    $display("LANE %0d: chained %010x one-pass %010x",
                             l, split_res[l], deep_res[l]);
                mism = mism + 1;
            end
        if (h_viol !== 1'b0) begin
            $display("FAIL: a same-scale chain raised acc_scale_violation");
            $finish;
        end

        // -- the negative: a chain whose window moves must be refused ------
        fill_half_bank(0);
        run_half(1'b0);
        h_scale = 8'd126;
        fill_half_bank(KHALF);
        run_half(1'b1);
        if (h_viol !== 1'b1) begin
            $display("FAIL: a chain whose cfg_scale moved did not raise acc_scale_violation");
            $finish;
        end

        if (mism == 0)
            $display("PASS: %0d lanes -- two chained 128-deep tiles are bit-identical to one 256-deep pass, and a moved window is refused",
                     LANES);
        else
            $display("FAIL: %0d lanes differ between the chained and one-pass forms", mism);
        $finish;
    end
endmodule
