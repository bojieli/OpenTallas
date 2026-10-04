`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Directed bench: two OP_SINK issued to ot_hdc_v41_xu (or the v41x adapter, +define+XU_ADAPT)
// with a programmable gap after the first op's result write.  The MTP ITER program issues the
// first draft stage's Sinkhorn ops back to back (pc 4384 -> 4385 -> 4386); a one-position
// program never does.  The second op's request must not be lost while the Sinkhorn unit still
// shows the first op's result (ot_hdc_sinkhorn_mc: busy = ubusy || ov for one unit clock).
// For every gap in 0 .. 2*SK_STEP the second op must write within TMO cycles and its result
// must equal the first op's (same input).  Prints one line per gap and PASS/FAIL.
// ---------------------------------------------------------------------------
module tb_hdc_v41_xu_sink_b2b;
    localparam integer AW = 24, NW = 16, IKW = 5, SK_STEP = 7, TMO = 2000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg go = 0;
    wire ready, idle;
    reg [1:0] i_op = 2'd1;
    reg [AW-1:0] i_src = 24'd64, i_dst = 24'd128;
    wire vr_re, xr_re, vw_we, w_we, cr_re, er_re, fault;
    wire [AW-1:0] vr_addr, xr_addr, vw_addr, w_addr, cr_addr, er_addr;
    wire [31:0] vw_data, w_mask;
    wire [1023:0] w_data;
    wire [15:0] sel_first;
    reg [1023:0] xr_q;
    reg [1023:0] ein;
    integer i;
    initial begin
        // a positive 4 x 4 mix (row-max exponentials lie in (0, 1])
        ein = 0;
        for (i = 0; i < 16; i = i + 1) ein[32*i +: 32] = 32'h3E800000 + (i * 32'h00051EB8);
    end
    always @(posedge clk) if (xr_re) xr_q <= ein;   // vector memory: registered 32-element read
`ifdef XU_ADAPT
    wire [3:0] vsl_re; wire [4*AW-1:0] vsl_addr;
    ot_hdc_v41x_xu_adapt #(.AW(AW), .NW(NW), .K(16), .IKW(IKW), .SK_STEP(SK_STEP)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle), .i_op(i_op), .i_src(i_src), .i_dst(i_dst),
        .i_n(16'd16), .i_k(5'd0), .i_layer(1'b0), .i_bf16(1'b0), .token(16'd0), .first(1'b0), .i_hslot(3'd0),
        .rst_v(1'b0), .rst_slot(3'd0), .sel_first(sel_first), .prime_v(1'b0), .prime_first(1'b0), .prime_cid(12'd0),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(32'd0), .xr_re(xr_re), .xr_addr(xr_addr), .xr_q(xr_q),
        .vsl_re(vsl_re), .vsl_addr(vsl_addr), .vsl_q('0),
        .vw_we(vw_we), .vw_addr(vw_addr), .vw_data(vw_data), .w_we(w_we), .w_addr(w_addr), .w_mask(w_mask),
        .w_data(w_data), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(64'd0), .er_re(er_re), .er_addr(er_addr),
        .er_q(264'd0), .fault(fault));
`else
    ot_hdc_v41_xu #(.AW(AW), .NW(NW), .K(16), .IKW(IKW), .SK_STEP(SK_STEP)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle), .i_op(i_op), .i_src(i_src), .i_dst(i_dst),
        .i_n(16'd16), .i_k(5'd0), .i_layer(1'b0), .token(16'd0), .first(1'b0), .i_hslot(3'd0),
        .rst_v(1'b0), .rst_slot(3'd0), .sel_first(sel_first), .prime_v(1'b0), .prime_first(1'b0), .prime_cid(12'd0),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(32'd0), .xr_re(xr_re), .xr_addr(xr_addr), .xr_q(xr_q),
        .vw_we(vw_we), .vw_addr(vw_addr), .vw_data(vw_data), .w_we(w_we), .w_addr(w_addr), .w_mask(w_mask),
        .w_data(w_data), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(64'd0), .er_re(er_re), .er_addr(er_addr),
        .er_q(264'd0), .fault(fault));
`endif

    // every bench action happens mid-cycle (#0.25 after the edge), so it never races the DUT's edge
    // issue one SINK: hold go until a cycle with ready high has ended (the DUT accepted at that edge)
    task automatic issue;
        reg acc;
        begin
            go = 1'b1; acc = 1'b0;
            while (!acc) begin
                acc = ready;
                @(posedge clk); #0.25;
            end
            go = 1'b0;
        end
    endtask
    // wait for the result write; returns the cycle count (or -1 on timeout)
    task automatic wait_w(output integer cyc, output reg [511:0] y);
        integer c;
        begin
            c = 0; cyc = -1;
            while (c < TMO && cyc < 0) begin
                if (w_we) begin cyc = c; y = w_data[511:0]; end
                else begin @(posedge clk); #0.25; c = c + 1; end
            end
        end
    endtask

    integer gap, phase, g, c1, c2, nfail, nhang;
    reg [511:0] y1, y2;
    initial begin
        nfail = 0; nhang = 0;
        for (phase = 0; phase < SK_STEP; phase = phase + 1)
        for (gap = 0; gap <= 2 * SK_STEP; gap = gap + 1) begin
            rst_n = 0; go = 0;
            repeat (3) @(posedge clk);
            #0.25 rst_n = 1;
            repeat (phase + 1) begin @(posedge clk); #0.25; end   // sweeps the unit-clock phase of the first issue
            issue; wait_w(c1, y1);
            for (g = 0; g < gap; g = g + 1) begin @(posedge clk); #0.25; end
            issue; wait_w(c2, y2);
            if (c1 < 0 || c2 < 0) begin
                nhang = nhang + 1; nfail = nfail + 1;
                $display("phase=%0d gap=%0d HANG c1=%0d c2=%0d", phase, gap, c1, c2);
            end else if (y1 !== y2 || fault) begin
                nfail = nfail + 1;
                $display("phase=%0d gap=%0d MISMATCH c1=%0d c2=%0d fault=%0d", phase, gap, c1, c2, fault);
            end else
                $display("phase=%0d gap=%0d ok c1=%0d c2=%0d", phase, gap, c1, c2);
        end
        $display("%s cases=%0d fail=%0d hang=%0d", (nfail == 0) ? "PASS" : "FAIL", SK_STEP * (2 * SK_STEP + 1), nfail, nhang);
        $finish;
    end
endmodule
