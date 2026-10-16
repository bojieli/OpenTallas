`timescale 1ns/1ps
`default_nettype none
// Bench: ot_hbm_svc_sm_xcal runs in LOCKSTEP with the actual svg go path (ot_hbm_svc_sm_issuer FIXED_GO=1 ->
// ot_smh_calendar_static W135, exactly as ot_hbm_svc_sm_group / ot_hbm_svc_sm_feed_programmed wire them).
// Both calendars get their own programme; the descriptor table and the run launch are the SAME writes (die fan-out of
// cp_svg b_* / run_*).  Every output cycle the assembled 192-bit SM command {xcal.cmd_ext, svg.sm_command} and the
// kv_desc must belong to the same programme word (pc identity encoded in both halves), carry magic 0xa2 when non-zero
// (the ot_hbm_sm_attn_front_static rule), and the count of issued words must equal the programme's.
// Run: iverilog -g2012 -DMUT=<n>; PASS iff MUT=0.  The bench drives block/cache residency high (HBM boundary in time).
module tb_hbm_svc_sm_xcal;
`ifndef MUT
`define MUT 0
`endif
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg cfg_we = 0, xcfg_we = 0, desc_we = 0, run_v = 0;
    reg [9:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg [6:0] desc_addr = 0; reg [255:0] desc_data = 0;
    reg [6:0] run_base = 0; reg [7:0] run_count = 0;
    // ---- svg go path (issuer + programme calendar, as in the svg)
    wire running, run_done, ifault, reserve_v, start_v, pstart_v;
    wire [31:0] rb; wire [14:0] rrb; wire [11:0] rt; wire [1:0] rbank, sbank; wire [15:0] re, se, ploops;
    wire [6:0] rrows; wire [9:0] rtag, pbase; wire [10:0] plimit;
    wire [134:0] programme; wire programme_v, p_active, p_done, p_fault; wire [31:0] ordinal;
    ot_hbm_svc_sm_issuer #(.LBANKS(4), .FIXED_GO(1)) issuer (.clk(clk), .rst_n(rst_n), .desc_we(desc_we),
        .desc_addr(desc_addr), .desc_data(desc_data), .run_v(run_v), .run_base(run_base), .run_count(run_count),
        .running(running), .run_done(run_done), .fault(ifault), .reserve_v(reserve_v), .reserve_ready(1'b1),
        .reserve_base(rb), .reserve_row_base(rrb), .reserve_total(rt), .reserve_bank(rbank), .reserve_epoch(re),
        .reserve_rows(rrows), .reserve_tag_base(rtag), .block_ready(4'hf), .cache_ready(2'b11), .cache_owned(2'b00),
        .start_v(start_v), .start_bank(sbank), .start_epoch(se), .program_start_v(pstart_v),
        .program_start_base(pbase), .program_start_limit(plimit), .program_start_loops(ploops), .program_done(p_done));
    ot_smh_calendar_static #(.W(135)) svg_cal (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .start_v(pstart_v), .start_base(pbase), .start_limit(plimit), .start_loops(ploops),
        .calendar(programme), .calendar_v(programme_v), .ordinal(ordinal), .active(p_active), .done(p_done),
        .fault(p_fault));
    wire [82:0] sm_command = programme_v ? programme[82:0] : 83'd0;
    // ---- DUT
    wire [108:0] cmd_ext; wire [63:0] kv_desc; wire x_active, x_done, x_fault;
    ot_hbm_svc_sm_xcal #(.MUT(`MUT)) dut (.clk(clk), .rst_n(rst_n), .cfg_we(xcfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_we(desc_we), .desc_addr(desc_addr), .desc_data(desc_data), .run_v(run_v),
        .run_base(run_base), .run_count(run_count), .cmd_ext(cmd_ext), .kv_desc(kv_desc), .active(x_active),
        .done(x_done), .fault(x_fault));
    wire [191:0] command = {cmd_ext, sm_command};
    // ---- programme content: svg word pc -> payload {1, pc, 3'b101}; xcal word pc -> magic + pc + kv run
    function automatic [255:0] sw(input [9:0] pc);
        sw = 0; sw[255:240] = 16'hc7a1; sw[233:224] = pc; sw[82] = 1'b1; sw[49:40] = pc; sw[2:0] = 3'b101;
    endfunction
    function automatic [255:0] xw(input [9:0] pc);
        reg [172:0] w;
        begin
            w = 0;
            w[108:101] = 8'ha2;                 // command[191:184]
            w[32] = 1'b1;                        // command[115] = kv load
            w[11:2] = pc;                        // pc identity in command[94:85] (BE control field, bench marker)
            w[172:109] = {16'd0, 16'(pc + 1), 32'h1000 + 32'(pc)};
            xw = 0; xw[255:240] = 16'hc7a1; xw[233:224] = pc; xw[172:0] = w;
        end
    endfunction
    function automatic [255:0] dw(input [6:0] row, input [9:0] b, input [10:0] l, input [15:0] lp, input [23:0] at,
                                  input [1:0] land);
        dw = 0; dw[255:240] = 16'h5d15; dw[239:233] = row; dw[31:0] = 32'h100 * row; dw[48:47] = land;
        dw[64:49] = 16'(row); dw[71:65] = 7'd1; dw[81:72] = 10'(row); dw[91:82] = b; dw[102:92] = l;
        dw[118:103] = lp; dw[142:119] = at;
    endfunction
    integer i, matched = 0, errors = 0, expect_words = 0, cyc = 0;
    reg [9:0] pcs, pcx;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if ((sm_command != 0) != (cmd_ext != 0)) begin
            errors = errors + 1;
            if (errors < 5) $display("MISALIGN cyc %0d svg %0d ext %0d", cyc, sm_command != 0, cmd_ext != 0);
        end else if (sm_command != 0) begin
            pcs = sm_command[49:40]; pcx = cmd_ext[11:2];
            if (command[191:184] != 8'ha2 || pcs != pcx || kv_desc != {16'd0, 16'(pcs + 1), 32'h1000 + 32'(pcs)} ||
                !command[115]) begin
                errors = errors + 1;
                if (errors < 5) $display("FIELD cyc %0d pc svg %0d ext %0d kv %h", cyc, pcs, pcx, kv_desc);
            end else matched = matched + 1;
        end
    end
    task automatic run_once(input [6:0] rb_, input [7:0] n_);
        begin
            @(negedge clk) run_v = 1; run_base = rb_; run_count = n_;
            @(negedge clk) run_v = 0;
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);
        for (i = 0; i < 64; i = i + 1) begin
            @(negedge clk) cfg_we = 1; xcfg_we = 0; cfg_addr = i; cfg_data = sw(i);
            @(negedge clk) cfg_we = 0; xcfg_we = 1; cfg_addr = i; cfg_data = xw(i);
        end
        @(negedge clk) xcfg_we = 0; cfg_we = 0;
        // run A: three programmes on compiler go slots (edges from the run launch)
        @(negedge clk) desc_we = 1; desc_addr = 0; desc_data = dw(0, 0, 5, 2, 40, 0);
        @(negedge clk) desc_addr = 1; desc_data = dw(1, 10, 13, 1, 80, 1);
        @(negedge clk) desc_addr = 2; desc_data = dw(2, 20, 24, 3, 120, 2);
        // run B (rows 3..4): back-to-back programmes, minimum spacing
        @(negedge clk) desc_addr = 3; desc_data = dw(3, 30, 38, 1, 30, 3);
        @(negedge clk) desc_addr = 4; desc_data = dw(4, 40, 41, 5, 47, 0);
        @(negedge clk) desc_we = 0;
        repeat (4) @(negedge clk);
        run_once(0, 3);  expect_words = expect_words + 5 * 2 + 3 + 4 * 3;
        repeat (220) @(negedge clk);
        run_once(3, 2);  expect_words = expect_words + 8 + 5;
        repeat (150) @(negedge clk);
        $display("words matched %0d / expected %0d, errors %0d, faults svg issuer %0d cal %0d xcal %0d, run_done seen",
                 matched, expect_words, errors, ifault, p_fault, x_fault);
        if (errors == 0 && matched == expect_words && !ifault && !p_fault && !x_fault) $display("XCAL_LOCKSTEP PASS");
        else $display("XCAL_LOCKSTEP FAIL");
        $finish;
    end
endmodule
`default_nettype wire
