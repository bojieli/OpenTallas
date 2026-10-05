`timescale 1ns/1ps
// Unit bench of the DS ROM system control-plane blocks: ot_dsrom_host_cq,
// ot_dsrom_stall_export and ot_dsrom_stage_guard.  Self-checking; prints one
// "CASE <name> PASS|FAIL" line per check and "UNITS PASS|FAIL" at the end.
// Run: iverilog -g2012 -o x rtl/dsrom_sys/ot_dsrom_{host_cq,stall_export,stage_guard}.sv \
//        rtl/test/dsrom_sys/tb_dsrom_ctrlplane_units.sv && vvp x
module tb_dsrom_ctrlplane_units;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    integer fails = 0, seed = 7;
    task automatic check(input string name, input bit ok);
        begin
            $display("CASE %s %s", name, ok ? "PASS" : "FAIL");
            if (!ok) fails = fails + 1;
        end
    endtask

    // ============================== host CQ ==============================
    localparam integer MAXU = 4, PMAX = 4, TAGW = 8, CQD = 16, CW = 2 + TAGW + 8 + 16 + 16 + 32;
    reg cmd_v = 0; wire cmd_r; reg [1:0] op = 0; reg [7:0] tag = 0, cu = 0; reg [15:0] cp = 0, ct = 0;
    wire cpl_v; reg cpl_r = 1; wire [CW-1:0] cpl;
    wire [7:0] cfg_u; wire [15:0] cfg_p, cfg_g;
    reg pr_re = 0; reg [7:0] pr_u = 0; reg [15:0] pr_p = 0; wire [15:0] pr_q;
    reg tv = 0; reg [7:0] tu = 0; reg [15:0] tp = 0, ti = 0; reg [7:0] udone = 0;
    reg [31:0] cause = 32'hA5A5_0001;
    wire act, wd, flt; wire [31:0] wcause; wire [3:0] fcode; wire [31:0] s_tok, s_spec, s_cst, s_high;
    ot_dsrom_host_cq #(.MAXU(MAXU), .PMAX(PMAX), .NW(16), .TAGW(TAGW), .CQ_DEPTH(CQD), .CAUSEW(32),
                       .WDOG(500), .UCW(8)) dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_v), .cmd_ready(cmd_r), .cmd_op(op), .cmd_tag(tag),
        .cmd_user(cu), .cmd_pos(cp), .cmd_token(ct), .cpl_valid(cpl_v), .cpl_ready(cpl_r), .cpl_data(cpl),
        .cfg_users(cfg_u), .cfg_prompt_len(cfg_p), .cfg_gen_len(cfg_g),
        .pr_re(pr_re), .pr_user(pr_u), .pr_pos(pr_p), .pr_q(pr_q),
        .tok_valid(tv), .tok_user(tu), .tok_pos(tp), .tok_id(ti), .users_done(udone),
        .stall_cause(cause), .active(act), .wdog(wd), .wdog_cause(wcause), .fault(flt), .fault_code(fcode),
        .st_tokens(s_tok), .st_spec_reads(s_spec), .st_cpl_stall(s_cst), .st_cq_high(s_high));

    // completion collector with random back-pressure
    integer bp = 0;
    reg [CW-1:0] got [0:255];
    integer ngot = 0;
    always @(posedge clk) begin
        if (cpl_v && cpl_r) begin got[ngot] = cpl; ngot = ngot + 1; end
        cpl_r <= ($urandom(seed) % 100) >= bp;
    end
    task automatic cmd(input [1:0] o, input [7:0] t, input [7:0] u, input [15:0] p, input [15:0] k);
        begin
            @(negedge clk); cmd_v = 1; op = o; tag = t; cu = u; cp = p; ct = k;
            @(posedge clk); while (!cmd_r) @(posedge clk);
            @(negedge clk); cmd_v = 0;
        end
    endtask
    function automatic [1:0] kind(input [CW-1:0] c); kind = c[CW-1 -: 2]; endfunction
    function automatic [15:0] ctok(input [CW-1:0] c); ctok = c[32 +: 16]; endfunction
    function automatic [15:0] cpos(input [CW-1:0] c); cpos = c[48 +: 16]; endfunction
    function automatic [7:0] cusr(input [CW-1:0] c); cusr = c[64 +: 8]; endfunction
    function automatic [7:0] ctag(input [CW-1:0] c); ctag = c[72 +: 8]; endfunction

    // ============================== stall export ==============================
    reg sx_act = 0, sx_prog = 0, sx_tr = 1; reg [3:0] sx_c = 0;
    wire [4*32-1:0] sx_cnt; wire sx_stuck; wire [3:0] sx_snap; wire [31:0] sx_sc, sx_ir, sx_im, sx_drops;
    wire sx_tv; wire [35:0] sx_td;
    ot_dsrom_stall_export #(.NC(4), .STUCK(50), .TRACE_DEPTH(4)) sx (
        .clk(clk), .rst_n(rst_n), .active(sx_act), .progress(sx_prog), .cause(sx_c), .cnt(sx_cnt),
        .stuck(sx_stuck), .stuck_snap(sx_snap), .stuck_cycle(sx_sc), .idle_run(sx_ir), .idle_max(sx_im),
        .trace_valid(sx_tv), .trace_ready(sx_tr), .trace_data(sx_td), .trace_drops(sx_drops));
    integer sx_ntrace = 0;
    always @(posedge clk) if (sx_tv && sx_tr) sx_ntrace = sx_ntrace + 1;

    // ============================== stage guard ==============================
    reg g_v = 0, g_l = 0; reg [511:0] g_d = 0; wire g_r, g_ov, g_ol; wire [511:0] g_od;
    wire g_f; wire [3:0] g_code; wire [63:0] g_hdr; wire [31:0] g_msgs, g_flits;
    reg g_rst = 0;
    ot_dsrom_stage_guard #(.FLIT(512), .NW(16), .MAXU(4), .MY_ID(2), .SRC_MASK(64'h2), .TYPE_MASK(16'h0006),
                           .LEN_HID(3), .LEN_SIDE(1)) gd (
        .clk(clk), .rst_n(g_rst), .cfg_users(8'd2), .in_valid(g_v), .in_ready(g_r), .in_data(g_d), .in_last(g_l),
        .out_valid(g_ov), .out_ready(1'b1), .out_data(g_od), .out_last(g_ol), .fault(g_f), .fault_code(g_code),
        .fault_hdr(g_hdr), .st_msgs(g_msgs), .st_flits(g_flits));
    function automatic [511:0] hdr(input [7:0] d, input [7:0] s, input [3:0] t, input [7:0] l, input [7:0] u,
                                   input [15:0] p);
        hdr = 0; hdr[7:0] = d; hdr[15:8] = s; hdr[19:16] = t; hdr[31:24] = l; hdr[39:32] = u; hdr[55:40] = p;
    endfunction
    task automatic gmsg(input [7:0] d, input [7:0] s, input [3:0] t, input [7:0] l, input [7:0] u, input [15:0] p,
                        input integer flits);
        integer f;
        begin
            for (f = 0; f < flits; f = f + 1) begin
                @(negedge clk); g_v = 1; g_d = (f == 0) ? hdr(d, s, t, l, u, p) : {16{32'(f)}}; g_l = (f == flits - 1);
            end
            @(negedge clk); g_v = 0; g_l = 0;
        end
    endtask
    task automatic greset; begin @(negedge clk); g_rst = 0; @(negedge clk); g_rst = 1; end endtask

    // global bound: a mutant that wedges the command port must still end with a verdict
    initial begin #400000; $display("UNITS FAIL fails=timeout"); $finish; end
    integer i, u, p, base, nt, ok;
    reg [15:0] prom [0:MAXU*PMAX-1];
    initial begin
        for (i = 0; i < MAXU * PMAX; i = i + 1) prom[i] = 16'h100 + i;
        repeat (3) @(posedge clk); rst_n = 1;
        // --- CQ-1: LAUNCH before prompts are written is refused (R_PROMPT = 3)
        cmd(2'd2, 8'h11, 8'd2, 16'd3, 16'd2);
        repeat (4) @(posedge clk);
        check("cq_refuse_missing_prompt", ngot == 1 && kind(got[0]) == 3 && ctok(got[0]) == 3 && !act && cfg_u == 0);
        // --- CQ-2: out-of-bound prompt write refused (R_BOUND = 1)
        cmd(2'd1, 8'h12, 8'd9, 16'd0, 16'd5);
        repeat (4) @(posedge clk);
        check("cq_refuse_bound", ngot == 2 && kind(got[1]) == 3 && ctok(got[1]) == 1);
        // --- CQ-3: a run that cannot be reserved in the CQ is refused (R_SPACE = 4): 4 users x (4+8-1)+2 > 16
        for (u = 0; u < 4; u = u + 1) for (p = 0; p < 4; p = p + 1) cmd(2'd1, 0, u, p, prom[u*PMAX+p]);
        cmd(2'd2, 8'h13, 8'd4, 16'd4, 16'd8);
        repeat (4) @(posedge clk);
        check("cq_refuse_space", ngot == 3 && kind(got[2]) == 3 && ctok(got[2]) == 4 && !act);
        // --- CQ-4: a good run, 2 users, prompt 3, gen 2 => 2*4 tokens + DONE, 70% completion back-pressure
        bp = 70; base = ngot;
        cmd(2'd2, 8'h5A, 8'd2, 16'd3, 16'd2);
        repeat (2) @(posedge clk);
        ok = act && cfg_u == 2 && cfg_p == 3 && cfg_g == 2;
        // the device reads prompts (pos < 3 real, pos 3 speculative) and emits tokens back-to-back
        for (u = 0; u < 2; u = u + 1) for (p = 0; p < 4; p = p + 1) begin
            @(negedge clk); pr_re = 1; pr_u = u; pr_p = p; @(negedge clk); pr_re = 0;
            if (pr_q != (p < 3 ? prom[u*PMAX+p] : 16'd0)) ok = 0;
        end
        for (p = 0; p < 4; p = p + 1) for (u = 0; u < 2; u = u + 1) begin
            @(negedge clk); tv = 1; tu = u; tp = p; ti = 16'h300 + 16*u + p;
        end
        @(negedge clk); tv = 0; udone = 2;
        repeat (200) @(posedge clk);
        nt = 0;
        for (i = base; i < ngot; i = i + 1) if (kind(got[i]) == 1) begin
            if (ctag(got[i]) != 8'h5A || ctok(got[i]) != 16'h300 + 16*cusr(got[i]) + cpos(got[i])) ok = 0;
            nt = nt + 1;
        end
        check("cq_run_tokens_exact_backpressure", ok && nt == 8 && kind(got[ngot-1]) == 2 && !flt && !act &&
              cfg_u == 0 && s_spec == 2 && s_cst > 0);
        // --- CQ-5: identity -- a duplicate token position latches F_TOK_ID (3)
        udone = 0; base = ngot;
        cmd(2'd2, 8'h5B, 8'd1, 16'd2, 16'd1);
        @(negedge clk); tv = 1; tu = 0; tp = 0; ti = 1; @(negedge clk); tp = 0; @(negedge clk); tv = 0;
        repeat (20) @(posedge clk);
        check("cq_identity_duplicate_faults", flt && fcode == 3);
        // --- CQ-6: watchdog: no further tokens -> WDOG ERROR completion carrying the stall cause
        repeat (600) @(posedge clk);
        ok = 0;
        for (i = base; i < ngot; i = i + 1) if (kind(got[i]) == 3 && ctok(got[i]) == 5) ok = 1;
        check("cq_watchdog_cause", wd && wcause == 32'hA5A5_0001 && ok);

        // --- SX-1: counters, stuck snapshot, trace, drops
        sx_act = 1; sx_c = 4'b0101;
        repeat (10) @(posedge clk);
        @(negedge clk); sx_prog = 1; @(negedge clk); sx_prog = 0; sx_c = 4'b1001;
        repeat (70) @(posedge clk);
        check("sx_stuck_snapshot", sx_stuck && sx_snap == 4'b1001 && sx_im >= 50 && sx_cnt[0 +: 32] >= 80);
        sx_tr = 0;
        for (i = 0; i < 8; i = i + 1) begin @(negedge clk); sx_c = i[3:0]; end
        @(negedge clk); sx_tr = 1; repeat (10) @(posedge clk);
        check("sx_trace_drops_counted", sx_drops > 0 && sx_ntrace + sx_drops >= 10);

        // --- GD: stage guard
        g_rst = 1;
        gmsg(2, 1, 1, 3, 0, 0, 4);  gmsg(2, 1, 1, 3, 1, 0, 4);  gmsg(2, 1, 2, 0, 0, 1, 1);  gmsg(2, 1, 1, 3, 0, 2, 4);
        repeat (2) @(posedge clk);
        check("gd_good_stream", !g_f && g_msgs == 4 && g_flits == 13);
        greset; gmsg(3, 1, 1, 3, 0, 0, 4); repeat (2) @(posedge clk); check("gd_bad_dest", g_f && g_code == 1);
        greset; gmsg(2, 0, 1, 3, 0, 0, 4); repeat (2) @(posedge clk); check("gd_bad_src", g_f && g_code == 2);
        greset; gmsg(2, 1, 3, 1, 0, 0, 2); repeat (2) @(posedge clk); check("gd_bad_type", g_f && g_code == 3);
        greset; gmsg(2, 1, 1, 2, 0, 0, 3); repeat (2) @(posedge clk); check("gd_bad_len", g_f && g_code == 4);
        greset; gmsg(2, 1, 1, 3, 0, 0, 3); gmsg(2, 1, 1, 3, 0, 1, 4); repeat (2) @(posedge clk);
        check("gd_early_last", g_f && g_code == 5);
        greset; gmsg(2, 1, 1, 3, 3, 0, 4); repeat (2) @(posedge clk); check("gd_bad_user", g_f && g_code == 6);
        greset; gmsg(2, 1, 1, 3, 0, 0, 4); gmsg(2, 1, 1, 3, 0, 2, 4); repeat (2) @(posedge clk);
        check("gd_skipped_pos", g_f && g_code == 7);
        $display("UNITS %s fails=%0d", fails == 0 ? "PASS" : "FAIL", fails);
        $finish;
    end
endmodule
