// DIE-KV-66/LEC 11-04 reset edges at the PC core pins (qkd_kvs_pcc / qkd_kvs_pcc_h_head_p rst_n + hrst_n).
// These pins are NOT a wavefront tap of the die root: every bound kv3_pc parent drives both from the data lane
// i_host_hbm_rst_n_q[0], ie host sequencer hbm_rst_n (qkd_host_rst_role_pins, por_n = local root tap) -> reset-less
// ot_dp_st stations + ot_dp_clk_landing_cas per hop.  So the DIE-KV-26 bench does not cover them.
// Chain here: pad por_n -> root (as DIE-KV-26) -> DEPTH relays -> REAL sequencer -> NH hops of REAL landing + stations ->
// pin.  link_up held high = earliest legal release.  Window = consecutive low locked edges right before the last release
// of an arm (an X or stale value during a landing restart breaks the count, it is never credited).
// por arms (power-on, por_n pulses, lock loss in reset) are checked against CONTRACT.  soft_rst is measured, reported apart.
// MUT 1: lock qualifier STABLE 4.  MUT 2: lock qualifier bypassed.  MUT 3: sequencer bypassed (pin lane fed by the root tap).
`timescale 1ps/1ps
module tb_kvpcc_reset_contract;
    parameter integer MUT = 0;
    parameter integer CONTRACT = 16;
    parameter integer DEPTH = 8;
    parameter integer NH = 3;
    parameter integer STN = 6;
    parameter integer LINK_TRAIN = 0;   // 0: link_up held high (stale, worst case); N: link_up low until N edges after link_rst_n rises
    localparam integer STABLE = (MUT == 1) ? 4 : 16;
    reg clk = 0; always #416 clk = ~clk;
    reg por_n = 0, locked = 0, soft_r = 0;
    wire rst_por_n, rst_lq, rst_root_n;
    ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(por_n), .sync_rst_n(rst_por_n));
    ot_dp_lockq #(.STABLE(STABLE)) u_rst_lockq (.clk(clk), .d(rst_por_n), .locked(locked), .q(rst_lq));
    assign rst_root_n = (MUT == 2) ? rst_por_n : rst_lq;
    wire [DEPTH:0] w; assign w[0] = rst_root_n;
    genvar g, h, s;
    generate for (g = 0; g < DEPTH; g = g + 1) begin : rl
        ot_dp_rrelay u (.clk(clk), .d(w[g]), .q(w[g+1]));
    end endgenerate
    wire tap = w[DEPTH];
    wire link_up, hbm_rst_n, host_rst_n, link_rst_n, boot_go, die_rst_n, sys_ready, boot_fault;
    wire [3:0] boot_state, boot_err; wire [31:0] boot_cycles;
    qkd_host_rst_role_pins #(.NL(6), .ND(8)) u_rst (.clk(clk), .por_n(tap), .soft_rst(soft_r), .die_id(3'd0), .link_up({6{link_up}}),
        .boot_done(8'h00), .boot_ok(8'h00), .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n),
        .boot_go(boot_go), .die_rst_n(die_rst_n), .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state),
        .boot_err(boot_err), .boot_cycles(boot_cycles));
    integer lt = 0; always @(posedge clk) if (link_rst_n !== 1'b1) lt <= 0; else if (lt < LINK_TRAIN) lt <= lt + 1;
    assign link_up = (LINK_TRAIN == 0) ? 1'b1 : (lt >= LINK_TRAIN);
    wire src = (MUT == 3) ? tap : hbm_rst_n;
    wire [NH:0] lane; assign lane[0] = src;
    wire [NH-1:0] rdy, flt;
    generate for (h = 0; h < NH; h = h + 1) begin : hop
        wire [1:0] lq; wire [STN:0] st; wire [STN:0] et;
        ot_dp_clk_landing_cas #(.W(2), .DEPTH(4)) u_land (.fclk(clk), .t_rst_n(tap), .clk(clk), .rst_n(tap), .strap_k(6'd2),
            .d({1'b1, lane[h]}), .q(lq), .ready(rdy[h]), .fault(flt[h]));
        assign st[0] = lq[0]; assign et[0] = lq[1];
        for (s = 0; s < STN; s = s + 1) begin : stn
            ot_dp_st #(.W(1)) u (.clk(clk), .rst_n(tap), .d(st[s]), .ea(et[s]), .q(st[s+1]), .eq(et[s+1]));
        end
        assign lane[h+1] = st[STN];
    end endgenerate
    wire pin = lane[NH];
    integer c = 0, last = 0, rises = 0, minpor = 1 << 30, minsoft = 1 << 30, arms = 0, softs = 0, fails = 0, extra = 0;
    reg was_low = 0;
    always @(posedge clk) begin
        if (pin === 1'b0) begin was_low <= 1; if (locked) c <= c + 1; end
        else begin
            if (was_low && pin === 1'b1) begin last = c; rises = rises + 1; end
            was_low <= 0; c <= 0;
        end
    end
    task close_arm(input integer is_soft); begin
        if (rises == 0 || pin !== 1'b1) begin fails = fails + 1; $display("FATAL: arm saw no release (rises=%0d pin=%b) t=%0t", rises, pin, $time); end
        else if (is_soft) begin if (last < minsoft) minsoft = last; end
        else begin
            if (last < minpor) minpor = last;
            if (last < CONTRACT) begin fails = fails + 1; $display("FATAL: pin released after %0d locked edges (contract %0d) t=%0t", last, CONTRACT, $time); end
        end
        if (rises > 1) extra = extra + rises - 1;
        rises = 0; end endtask
    task settle; begin repeat (400) @(posedge clk); end endtask
    integer i;
    initial begin
        arms = 1; repeat (10) @(posedge clk); #100 por_n = 1; repeat (12) @(posedge clk); #37 locked = 1; settle; close_arm(0);
        for (i = 0; i < 8; i = i + 1) begin @(posedge clk); #((i * 97) % 800); por_n = 0; arms = arms + 1; #(50 + i * 270); por_n = 1; settle; close_arm(0); end
        @(posedge clk); por_n = 0; arms = arms + 1; repeat (5) @(posedge clk); #11 locked = 0; repeat (6) @(posedge clk);
        por_n = 1; repeat (3) @(posedge clk); #23 locked = 1; settle; close_arm(0);
        for (i = 1; i <= 3; i = i + 1) begin @(posedge clk); #1 soft_r = 1; repeat (i) @(posedge clk); #1 soft_r = 0; softs = softs + 1; settle; close_arm(1); end
        if (|flt !== 1'b0 || &rdy !== 1'b1) begin fails = fails + 1; $display("FATAL: landing ready=%b fault=%b", rdy, flt); end
        if (fails == 0) $display("KVPCCRST_PASS arms=%0d min_edges_por=%0d contract=%0d stable=%0d depth=%0d hops=%0d extra_rises=%0d softs=%0d min_edges_soft=%0d", arms, minpor, CONTRACT, STABLE, DEPTH, NH, extra, softs, minsoft);
        else $display("KVPCCRST_FAIL fails=%0d min_edges_por=%0d min_edges_soft=%0d", fails, minpor, minsoft);
        $finish;
    end
endmodule
