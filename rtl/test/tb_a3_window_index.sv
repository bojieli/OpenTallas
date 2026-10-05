`timescale 1ns/1ps
// ROUTE.WINDOW_INDEX against the reference's rule, both phases, plus refusals.
module tb_a3_window_index;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_span, cfg_slots, cfg_window, cfg_context;
    reg        cfg_mask_full, cfg_decode;
    reg [31:0] cfg_pos_base, cfg_out_base;
    wire pos_rd_en; wire [31:0] pos_rd_addr; reg [31:0] pos_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, candidates;

    reg [31:0] pmem [0:31];
    reg [31:0] emem [0:255];
    reg [31:0] omem [0:255];
    integer j, errors = 0, writes;
    integer ncases, c, span, slots, window, mfull, ctxlen, dec, cand;
    integer fh, code; reg [1023:0] path;

    ot_a3_route_window_index dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_span(cfg_span), .cfg_slots(cfg_slots), .cfg_window(cfg_window),
        .cfg_mask_full(cfg_mask_full), .cfg_context(cfg_context),
        .cfg_decode(cfg_decode), .cfg_pos_base(cfg_pos_base),
        .cfg_out_base(cfg_out_base),
        .pos_rd_en(pos_rd_en), .pos_rd_addr(pos_rd_addr), .pos_rd_data(pos_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .candidates(candidates)
    );

    always #1 clk = ~clk;
    always @(posedge clk) if (pos_rd_en) pos_rd_data <= pmem[pos_rd_addr[4:0]];
    always @(posedge clk) if (out_we) begin omem[out_addr[7:0]] <= out_data; writes = writes + 1; end

    task go; begin
        writes = 0;
        for (j = 0; j < 256; j = j + 1) omem[j] = 32'hdead_0000;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%d %d %d %d %d %d %d\n",
                           span, slots, window, mfull, ctxlen, dec, cand);
            for (j = 0; j < 32; j = j + 1)  pmem[j] = 0;
            for (j = 0; j < 256; j = j + 1) emem[j] = 0;
            $sformat(path, "pos_%0d.hex", c); $readmemh(path, pmem);
            $sformat(path, "exp_%0d.hex", c); $readmemh(path, emem);
            cfg_span = span; cfg_slots = slots; cfg_window = window;
            cfg_mask_full = mfull[0]; cfg_context = ctxlen; cfg_decode = dec[0];
            cfg_pos_base = 0; cfg_out_base = 0;
            go;
            if (error_code !== 8'd0) begin
                $display("FAIL case %0d error=%0d", c, error_code); errors=errors+1; end
            if (out_count !== span*slots || writes !== span*slots) begin
                $display("FAIL case %0d count=%0d writes=%0d expected %0d",
                         c, out_count, writes, span*slots); errors=errors+1; end
            if (candidates !== cand) begin
                $display("FAIL case %0d candidates=%0d expected %0d",
                         c, candidates, cand); errors=errors+1; end
            for (j = 0; j < span*slots; j = j + 1)
                if (omem[j] !== emem[j]) begin
                    $display("FAIL case %0d elem %0d (row %0d slot %0d) got %08x exp %08x",
                             c, j, j/slots, j%slots, omem[j], emem[j]);
                    errors = errors + 1;
                end
        end
        $fclose(fh);

        // -- a query at or past the context is a fault, not a clamp ----------
        cfg_span = 1; cfg_slots = 8; cfg_window = 8; cfg_mask_full = 0;
        cfg_context = 4; cfg_decode = 0; pmem[0] = 4;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL a query at the context bound was accepted"); errors=errors+1; end

        // -- decode with a non-power-of-two window is refused, not approximated
        pmem[0] = 1; cfg_context = 32; cfg_window = 6; cfg_decode = 1;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL decode accepted a window of 6, which needs a real modulo");
            errors = errors + 1; end
        // -- and the same window is fine in prefill, which never wraps -------
        cfg_decode = 0;
        go;
        if (error_code !== 8'd0) begin
            $display("FAIL prefill refused a window of 6 though it never wraps");
            errors = errors + 1; end

        if (errors == 0)
            $display("PASS: window_index, both phases, context fault, non-power-of-two refused in decode only");
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
