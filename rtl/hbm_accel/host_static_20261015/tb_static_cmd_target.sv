`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/cp1: ot_static_cmd_target through the REAL host ingress (ot_hbm_host_static_ingress, AXI-lite F20..F30).
// Three collars as on the die: svg (MODE 0, TARGET 64), x-load issuer (MODE 1, CW 108, TARGET 100), DMA dispatcher
// (MODE 1, CW 308 = 2 rows/entry, RELF 2, TARGET 104), plus one VM calendar target (ot_static_program_target PCW 10,
// TARGET 96).  Checks every window write, the run launch, every command's exact fire cycle
// (cycle == C_launch + 2 + LEAD + loop*period + at), the DMA rebased issue/drain fields, the calendar start, and the
// faults (too-close commands, cfg while active).  -DMUT=1 (late fire) and -DMUT=2 (target id ignored) must FAIL.
`ifndef MUT
`define MUT 0
`endif
module tb_static_cmd_target;
    localparam integer LEAD = 8;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    // AXI
    reg awv = 0, wv = 0, arv = 0, rr = 1, br = 1; reg [11:0] awa = 0, ara = 0; reg [31:0] wd = 0;
    wire awr, wr, bv, arr, rv; wire [1:0] bresp; wire [31:0] rdata;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    reg any_active;
    ot_hbm_host_static_ingress #(.TARGET_MASK((256'd1<<64)|(256'd1<<96)|(256'd1<<100)|(256'd1<<104)|(256'd1<<105))) ing(
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(br), .s_bresp(bresp), .s_arvalid(arv), .s_arready(arr),
        .s_araddr(ara), .s_rvalid(rv), .s_rready(rr), .s_rdata(rdata), .block_ready(1'b1), .program_active(any_active),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    // ---- collars
    wire s_awe, s_bwe, s_run, s_cv, s_cfgd, s_flt, s_act; wire [9:0] s_aa; wire [6:0] s_ba; wire [255:0] s_ad, s_bd;
    wire [6:0] s_rb; wire [7:0] s_rc; wire [31:0] s_cyc; wire [0:0] s_cmd;
    reg svg_running = 0;
    ot_static_cmd_target #(.TARGET(8'd64), .MODE(0), .AWA(10), .AWB(7), .RBW(7), .RCW(8), .NA(2), .NF(1), .MUT(`MUT)) t_svg(
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active({svg_running, 1'b0}), .tgt_fault(1'b0),
        .a_we(s_awe), .a_addr(s_aa), .a_data(s_ad), .b_we(s_bwe), .b_addr(s_ba), .b_data(s_bd),
        .run_v(s_run), .run_base(s_rb), .run_count(s_rc), .cmd_v(s_cv), .cmd(s_cmd), .cycle(s_cyc),
        .configured(s_cfgd), .fault(s_flt), .active(s_act));
    wire x_cv, x_cfgd, x_flt, x_act; wire [107:0] x_cmd; wire [31:0] x_cyc;
    ot_static_cmd_target #(.TARGET(8'd100), .MODE(1), .CW(108), .RELF(0), .LEAD(LEAD), .MUT(`MUT)) t_xl(
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active(1'b0), .tgt_fault(1'b0),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(x_cv), .cmd(x_cmd), .cycle(x_cyc), .configured(x_cfgd), .fault(x_flt), .active(x_act));
    wire d_cv, d_cfgd, d_flt, d_act; wire [307:0] d_cmd; wire [31:0] d_cyc;
    ot_static_cmd_target #(.TARGET(8'd104), .MODE(1), .CW(308), .RELF(2), .LEAD(LEAD), .MUT(`MUT)) t_dma(
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active(1'b0), .tgt_fault(1'b0),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(d_cv), .cmd(d_cmd), .cycle(d_cyc), .configured(d_cfgd), .fault(d_flt), .active(d_act));
    // negative collar: commands one cycle apart (must fault, never issue late)
    wire n_cv, n_cfgd, n_flt, n_act; wire [107:0] n_cmd;
    ot_static_cmd_target #(.TARGET(8'd105), .MODE(1), .CW(108), .LEAD(LEAD), .MUT(`MUT)) t_neg(
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active(1'b0), .tgt_fault(1'b0),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(n_cv), .cmd(n_cmd), .cycle(), .configured(n_cfgd), .fault(n_flt), .active(n_act));
    wire c_we, c_sv, c_cfgd, c_flt; wire [9:0] c_wa, c_sb; wire [10:0] c_sl; wire [15:0] c_lp; wire [255:0] c_wd;
    ot_static_program_target #(.TARGET(8'd96), .PCW(10)) t_cal(.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .program_active(1'b0), .program_cfg_we(c_we), .program_cfg_addr(c_wa),
        .program_cfg_data(c_wd), .program_start_v(c_sv), .program_start_base(c_sb), .program_start_limit(c_sl),
        .program_start_loops(c_lp), .configured(c_cfgd), .fault(c_flt));
    always @* any_active = s_act | x_act | d_act;
    // ---- AXI write
    integer errors = 0;
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha, hw; ha = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            while (!bv) @(posedge clk);
            if (bresp != 0) begin $display("ERROR bresp %0d at %h data %h", bresp, a, d); errors = errors + 1; end
            @(posedge clk);
        end
    endtask
    task automatic row(input [7:0] tgt, input [11:0] addr, input [255:0] data);
        begin
            axw(12'hf20, {12'd0, addr, tgt});
            for (integer p = 0; p < 8; p = p + 1) axw(12'hf24, data[p*32 +: 32]);
        end
    endtask
    task automatic desc(input [7:0] tgt, input [11:0] base, input [12:0] lim, input [15:0] loops);
        begin axw(12'hf20, {12'd0, 12'd0, tgt}); axw(12'hf28, {7'd0, lim, base}); axw(12'hf2c, {16'd0, loops}); end
    endtask
    // ---- expectations
    reg [255:0] DA, DB, DC; reg [107:0] XP [0:2]; reg [31:0] XAT [0:2]; reg [307:0] DP [0:1]; reg [31:0] DAT [0:1];
    localparam [31:0] XPER = 32'd150;
    integer saw_a = 0, saw_b = 0, saw_run = 0, saw_cal_w = 0, saw_cal_s = 0, nx = 0, nd = 0, nneg = 0;
    reg [31:0] C_launch; reg launched = 0;
    always @(posedge clk) if (rst_n) begin
        if (launch_v && !launched) begin launched <= 1; C_launch <= s_cyc; end
        if (s_awe) begin if (s_aa == 10'd5 && s_ad == DA) saw_a = saw_a + 1; else begin errors = errors + 1; $display("ERROR svg A write %h", s_aa); end end
        if (s_bwe) begin if (s_ba == 7'd3 && s_bd == DB) saw_b = saw_b + 1; else begin errors = errors + 1; $display("ERROR svg B write %h", s_ba); end end
        if (s_run) begin if (s_rb == 7'd3 && s_rc == 8'd7) saw_run = saw_run + 1; else begin errors = errors + 1; $display("ERROR run %0d %0d", s_rb, s_rc); end end
        if (c_we) begin if (c_wa == 10'd9 && c_wd == DC) saw_cal_w = saw_cal_w + 1; else begin errors = errors + 1; $display("ERROR cal write"); end end
        if (c_sv) begin if (c_sb == 10'd2 && c_sl == 11'd40 && c_lp == 16'd3) saw_cal_s = saw_cal_s + 1; else begin errors = errors + 1; $display("ERROR cal start"); end end
        if (x_cv) begin : XC
            integer e, l; reg [31:0] exp_c;
            e = nx % 3; l = nx / 3;
            exp_c = C_launch + 2 + LEAD + l * XPER + XAT[e];
            if (x_cmd !== XP[e] || x_cyc !== exp_c) begin errors = errors + 1;
                $display("ERROR xload cmd %0d: cycle %0d exp %0d payload_ok %0d", nx, x_cyc, exp_c, x_cmd === XP[e]); end
            nx = nx + 1;
        end
        if (d_cv) begin : DC_
            reg [31:0] exp_c; reg [307:0] ep;
            exp_c = C_launch + 2 + LEAD + DAT[nd];
            ep = DP[nd]; ep[31:0] = ep[31:0] + C_launch + 2 + LEAD; ep[63:32] = ep[63:32] + C_launch + 2 + LEAD;
            if (d_cmd !== ep || d_cyc !== exp_c) begin errors = errors + 1;
                $display("ERROR dma cmd %0d: cycle %0d exp %0d issue %0d exp %0d", nd, d_cyc, exp_c, d_cmd[31:0], ep[31:0]); end
            nd = nd + 1;
        end
        if (n_cv) nneg = nneg + 1;
    end
    // ---- programme
    initial begin : TMO #300000; $display("TB_STATIC_CMD_TARGET FAIL timeout"); $finish; end
    initial begin
        DA = {8{32'hA5A50001}} ^ 256'h1234; DB = {8{32'h5A5A0003}} ^ 256'h77; DC = {8{32'hC0DE0009}};
        XP[0] = {7'd5, 2'd0, 2'd1, 32'd64, 4'd2, 21'd512, 40'h0000001000};
        XP[1] = {7'd9, 2'd1, 2'd1, 32'd128, 4'd8, 21'd2048, 40'h0000020000};
        XP[2] = {7'd1, 2'd2, 2'd1, 32'd8, 4'd1, 21'd64, 40'h00000ABC08};
        XAT[0] = 32'd0; XAT[1] = 32'd17; XAT[2] = 32'd90;
        DP[0] = {16'h0042, 1'b1, {7{32'h13572468}}, 3'b101, 32'd60, 32'd30};   // {epoch,bank,mv227,drain_rel,issue_rel}
        DP[1] = {16'h0043, 1'b0, {7{32'h9abcdef0}}, 3'b011, 32'd160, 32'd120};
        DAT[0] = 32'd20; DAT[1] = 32'd110;
        repeat (5) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
        // svg: window A row 5, window B row 3, run [3,10)
        row(8'd64, 12'h005, DA); row(8'd64, 12'h403, DB); desc(8'd64, 12'd3, 13'd10, 16'd1);
        // calendar target 96: programme row 9, start [2,40) x3
        row(8'd96, 12'h009, DC); desc(8'd96, 12'd2, 13'd40, 16'd3);
        // x-load: period word, entries 4..6, loops 2
        row(8'd100, 12'hC00, {224'd0, XPER});
        for (integer e = 0; e < 3; e = e + 1) row(8'd100, 12'h800 + 12'(4 + e), {116'd0, XP[e], XAT[e]});
        desc(8'd100, 12'd4, 13'd7, 16'd2);
        // DMA: 2 rows per entry, entries 0..1
        for (integer e = 0; e < 2; e = e + 1) begin : DW
            reg [511:0] ent; ent = {172'd0, DP[e], DAT[e]};
            row(8'd104, 12'h800 + 12'(2 * e), ent[255:0]); row(8'd104, 12'h800 + 12'(2 * e + 1), ent[511:256]);
        end
        desc(8'd104, 12'd0, 13'd2, 16'd1);
        // negative: four commands one cycle apart (the table cannot be read that fast: must FAULT, never issue late)
        for (integer e = 0; e < 4; e = e + 1) row(8'd105, 12'h800 + 12'(e), {116'd0, XP[e % 3], 32'(5 + e)});
        desc(8'd105, 12'd0, 13'd4, 16'd1);
        if (s_flt || x_flt || d_flt || n_flt || c_flt || ing_fault) begin errors = errors + 1; $display("ERROR fault before launch"); end
        repeat (10) @(posedge clk); axw(12'hf30, 32'd1);
        repeat (400) @(posedge clk);
        // cfg while the svg target reports running -> fault
        svg_running = 1; repeat (3) @(posedge clk);
        if (s_flt) begin errors = errors + 1; $display("ERROR svg fault without cause"); end
        force cfg_v = 1'b1; force cfg_target = 8'd64; @(posedge clk); release cfg_v; release cfg_target; repeat (4) @(posedge clk);
        if (!s_flt) begin errors = errors + 1; $display("ERROR cfg while running not faulted"); end
        if (saw_a != 1 || saw_b != 1 || saw_run != 1 || saw_cal_w != 1 || saw_cal_s != 1) begin errors = errors + 1;
            $display("ERROR counts a%0d b%0d run%0d calw%0d cals%0d", saw_a, saw_b, saw_run, saw_cal_w, saw_cal_s); end
        if (nx != 6) begin errors = errors + 1; $display("ERROR xload issued %0d of 6", nx); end
        if (nd != 2) begin errors = errors + 1; $display("ERROR dma issued %0d of 2", nd); end
        if (!n_flt || nneg > 3) begin errors = errors + 1; $display("ERROR too-close commands: fault %0d issued %0d", n_flt, nneg); end
        if (x_flt || d_flt || x_act || d_act) begin errors = errors + 1; $display("ERROR seq status flt %0d %0d act %0d %0d", x_flt, d_flt, x_act, d_act); end
        $display("launch->first x-load fire: cycle %0d = C_launch %0d + 2 + LEAD %0d + at 0", C_launch + 2 + LEAD, C_launch, LEAD);
        if (errors == 0) $display("TB_STATIC_CMD_TARGET PASS mut=%0d xload=%0d dma=%0d too_close_issued=%0d_of_4_then_fault", `MUT, nx, nd, nneg);
        else $display("TB_STATIC_CMD_TARGET FAIL mut=%0d errors=%0d", `MUT, errors);
        $finish;
    end
endmodule
`default_nettype wire
