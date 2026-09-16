`timescale 1ns/1ps
// ROUTE.BIASED_TOPK against the reference's own two lines, plus its refusals.
//
// The expectations come from tools/build_a3_biased_topk_vectors.py, which
// evaluates ``np.add(scores, bias, dtype=float32)`` and
// ``argsort(-keys, kind="stable")[:, :topk]`` -- the reference's exact
// expressions -- on the same widened BF16 codes this bench loads.
//
// TWO PROPERTIES ARE CHECKED THAT AN ARITHMETIC-ONLY BENCH WOULD MISS:
//   * the SELECTED IDS, not just their scores.  An engine that sampled its expert
//     counter one stage after the address emits every id one too high while the
//     scores, the count and the ordering all stay right.
//   * the weights are the UNBIASED scores.  Case bias_reorders is built so the
//     bias changes the winning set AND the emitted weights differ from those
//     experts' keys, so writing the key instead fails there and nowhere else.
module tb_a3_route_biased_topk;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_groups, cfg_experts, cfg_topk;
    reg        cfg_has_bias, cfg_bias_broadcast, cfg_has_weight_out, cfg_weight_fp32;
    reg        cfg_operand_fp32;
    reg [31:0] cfg_score_base, cfg_bias_base, cfg_id_out_base, cfg_weight_out_base;
    wire score_rd_en, bias_rd_en; wire [31:0] score_rd_addr, bias_rd_addr;
    reg [31:0] score_rd_data, bias_rd_data;
    wire id_we, wgt_we; wire [31:0] id_addr, id_data, wgt_addr, wgt_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] selected_experts, candidates;

    reg [31:0] smem [0:255];
    reg [31:0] bmem [0:255];
    reg [31:0] eid  [0:255];
    reg [31:0] ewgt [0:255];
    reg [31:0] gid  [0:255];
    reg [31:0] gwgt [0:255];
    integer j, errors = 0, idw, wgw, reorder_seen = 0;
    integer ncases, c, groups, experts, topk, hasb, bcast, wfp32, ofp32;
    integer fh, code; reg [1023:0] name, path;

    ot_a3_route_biased_topk dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_groups(cfg_groups), .cfg_experts(cfg_experts), .cfg_topk(cfg_topk),
        .cfg_has_bias(cfg_has_bias), .cfg_bias_broadcast(cfg_bias_broadcast),
        .cfg_operand_fp32(cfg_operand_fp32),
        .cfg_score_base(cfg_score_base), .cfg_bias_base(cfg_bias_base),
        .cfg_id_out_base(cfg_id_out_base),
        .cfg_has_weight_out(cfg_has_weight_out),
        .cfg_weight_fp32(cfg_weight_fp32),
        .cfg_weight_out_base(cfg_weight_out_base),
        .score_rd_en(score_rd_en), .score_rd_addr(score_rd_addr),
        .score_rd_data(score_rd_data),
        .bias_rd_en(bias_rd_en), .bias_rd_addr(bias_rd_addr),
        .bias_rd_data(bias_rd_data),
        .id_we(id_we), .id_addr(id_addr), .id_data(id_data),
        .wgt_we(wgt_we), .wgt_addr(wgt_addr), .wgt_data(wgt_data),
        .busy(busy), .done(done), .error_code(error_code),
        .selected_experts(selected_experts), .candidates(candidates)
    );

    always #1 clk = ~clk;
    //: A registered read, which is the timing the engine's one pipeline stage
    //: assumes and what the array's operand ports actually present.
    always @(posedge clk) if (score_rd_en) score_rd_data <= smem[score_rd_addr[7:0]];
    always @(posedge clk) if (bias_rd_en)  bias_rd_data  <= bmem[bias_rd_addr[7:0]];
    always @(posedge clk) if (id_we)  begin gid[id_addr[7:0]]   <= id_data;  idw = idw + 1; end
    always @(posedge clk) if (wgt_we) begin gwgt[wgt_addr[7:0]] <= wgt_data; wgw = wgw + 1; end

    task go; begin
        idw = 0; wgw = 0;
        for (j = 0; j < 256; j = j + 1) begin
            gid[j] = 32'hdead_0000; gwgt[j] = 32'hdead_0001;
        end
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d %d %d %d %d %d\n", name, groups,
                           experts, topk, hasb, bcast, wfp32, ofp32);
            for (j = 0; j < 256; j = j + 1) begin
                smem[j] = 0; bmem[j] = 0; eid[j] = 0; ewgt[j] = 0;
            end
            $sformat(path, "score_%0d.hex", c); $readmemh(path, smem);
            $sformat(path, "bias_%0d.hex", c);  $readmemh(path, bmem);
            $sformat(path, "expid_%0d.hex", c); $readmemh(path, eid);
            $sformat(path, "expwgt_%0d.hex", c); $readmemh(path, ewgt);

            cfg_groups = groups; cfg_experts = experts; cfg_topk = topk;
            cfg_has_bias = hasb[0]; cfg_bias_broadcast = bcast[0];
            cfg_has_weight_out = 1'b1; cfg_weight_fp32 = wfp32[0];
            cfg_operand_fp32 = ofp32[0];
            cfg_score_base = 0; cfg_bias_base = 0;
            cfg_id_out_base = 0; cfg_weight_out_base = 0;
            go;

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (idw !== groups * topk || selected_experts !== groups * topk) begin
                $display("FAIL %0s wrote %0d ids (counter %0d), expected %0d",
                         name, idw, selected_experts, groups * topk);
                errors = errors + 1;
            end
            if (candidates !== groups * experts) begin
                $display("FAIL %0s ranked %0d candidates, expected %0d",
                         name, candidates, groups * experts);
                errors = errors + 1;
            end
            for (j = 0; j < groups * topk; j = j + 1) begin
                if (gid[j] !== eid[j]) begin
                    $display("FAIL %0s id[%0d] got %0d expected %0d",
                             name, j, gid[j], eid[j]);
                    errors = errors + 1;
                end
                if (gwgt[j] !== ewgt[j]) begin
                    $display("FAIL %0s weight[%0d] got %08h expected %08h",
                             name, j, gwgt[j], ewgt[j]);
                    errors = errors + 1;
                end
            end
            if (name == "bias_reorders") reorder_seen = 1;
            $display("  %0s: %0d groups x %0d experts, k=%0d, fp32=%0d -> %0d ids, %0d candidates",
                     name, groups, experts, topk, ofp32, idw, candidates);
        end
        $fclose(fh);

        //: The suite must contain the case that makes the unbiased-weight rule
        //: non-vacuous, or every check above passes on a biased-weight engine.
        if (!reorder_seen) begin
            $display("FAIL the bias_reorders case is absent from cases.txt");
            errors = errors + 1;
        end

        // -- Refusals. A shape the contract forbids must fail closed, not clamp.
        cfg_groups = 2; cfg_experts = 8; cfg_topk = 9;   //: topk > MAX_K
        cfg_has_bias = 1; cfg_bias_broadcast = 1; cfg_has_weight_out = 0;
        cfg_weight_fp32 = 0; cfg_operand_fp32 = 0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL topk>MAX_K gave %0h", error_code); errors = errors + 1;
        end
        cfg_topk = 8; cfg_experts = 4;                   //: topk > experts
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL topk>experts gave %0h", error_code); errors = errors + 1;
        end
        cfg_experts = 8; cfg_topk = 0;                   //: k must be positive
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL topk=0 gave %0h", error_code); errors = errors + 1;
        end

        //: A nonfinite key is trap class 6 in the reference, refused here on the
        //: operand so a nonfinite score reaching a no-bias walk is caught too.
        cfg_groups = 1; cfg_experts = 4; cfg_topk = 2;
        cfg_has_bias = 1; cfg_bias_broadcast = 1;
        for (j = 0; j < 8; j = j + 1) begin smem[j] = 32'h00003f80; bmem[j] = 0; end
        bmem[2] = 32'h00007f80;                          //: +inf bias, BF16 code
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_OPERAND_NONFINITE) begin
            $display("FAIL nonfinite bias gave %0h", error_code); errors = errors + 1;
        end
        bmem[2] = 0; smem[1] = 32'h00007fc0;             //: NaN score, BF16 code
        cfg_has_bias = 0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_OPERAND_NONFINITE) begin
            $display("FAIL nonfinite score gave %0h", error_code); errors = errors + 1;
        end
        //: The same two refusals under binary32 operands, where the nonfinite
        //: field sits eight bits higher and a BF16-shaped check would miss it.
        cfg_operand_fp32 = 1'b1; cfg_has_bias = 1'b1;
        for (j = 0; j < 8; j = j + 1) begin smem[j] = 32'h3f80_0000; bmem[j] = 0; end
        bmem[2] = 32'h7f80_0000;                         //: +inf bias, FP32 code
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_OPERAND_NONFINITE) begin
            $display("FAIL fp32 nonfinite bias gave %0h", error_code); errors = errors + 1;
        end
        bmem[2] = 0; smem[1] = 32'h7fc0_0000;            //: NaN score, FP32 code
        cfg_has_bias = 0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_OPERAND_NONFINITE) begin
            $display("FAIL fp32 nonfinite score gave %0h", error_code); errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_route_biased_topk: %0d cases match the reference rule, ids and unbiased weights, and 7 refusals fail closed", ncases);
        else
            $display("FAIL a3_route_biased_topk: %0d errors", errors);
        $finish;
    end
endmodule
