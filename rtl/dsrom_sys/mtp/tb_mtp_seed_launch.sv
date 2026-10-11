`timescale 1ns/1ps
// tb_mtp_seed_launch (mtp-dsbind 2026-10-10): exact gate of dsfd_mtp_seed_launch (primary-die seed descriptor ->
// seed program).  The descriptor comes from a grant-protocol sender (ot_dsrom_mtp_ltx, as the collective MTP lane's
// u_os) through FWD / RET relay stations; the VM is an RTT receiver (random acceptance) answering in order after VLAT
// with a data pattern unique to every (address, beat); E behavioural seed elements (seed_ctl intake protocol: level
// out_x_rdy at idle, exactly 240 beats, out_done after a per-element processing time) joined at the die (AND rdy,
// done when the last finishes), through XH stations each way.
// Checks: every beat of every launched row equals the VM word of the expected (user, position); rows in order; one
// program-start event per good descriptor with {user, anchor, y, epoch}; the sticky fault equals the case's
// expectation; a rejected descriptor launches nothing.
//   +CASE=pos_basic | pos_win | neg_drop | neg_stale | neg_replay
// Prints SEEDL_RESULT case=.. result=PASS|FAIL ... desc_to_x=<cycles> done_to_ps=<cycles>.
module tb_mtp_seed_launch;
    localparam integer NW = 21, UW = 10, SW = UW + 3 * NW + 4, PW = UW + 2 * NW + 4, AW = 24, WIN = 256, MAXU = 8;
    localparam integer FWD = 9, RET = 9, VF = 6, VR = 6, VLAT = 12, XH = 4, E = 4;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    // ---------------- stimulus queue ----------------
    reg [SW-1:0] dq [0:63]; reg [PW-1:0] eq [0:63]; reg [4+UW+NW-1:0] rq_exp [0:4095]; integer uep [0:15];
    initial for (ue_i = 0; ue_i < 16; ue_i = ue_i + 1) uep[ue_i] = 0;
    integer nd = 0, ne = 0, nr = 0, exp_fault = 0, ue_i;
    reg [255:0] cs;
    function [SW-1:0] desc(input integer u, input integer anc, input integer nrow, input integer y, input integer ep);
        desc = {UW'(u), NW'(anc), NW'(nrow), NW'(y), 4'(ep)};
    endfunction
    task good(input integer u, input integer anc, input integer nrow, input integer y, input integer ep);
        integer p, lo;
        begin
            dq[nd] = desc(u, anc, nrow, y, ep); nd = nd + 1;
            eq[ne] = {UW'(u), NW'(anc), NW'(y), 4'(ep)}; ne = ne + 1;
            lo = (nrow > WIN) ? anc + 1 - WIN : anc - nrow + 1;
            for (p = lo; p <= anc; p = p + 1) begin rq_exp[nr] = {4'(uep[u]), UW'(u), NW'(p)}; nr = nr + 1; end
            uep[u] = ep;                 // rows of the next block are issued under the new epoch
        end
    endtask
    task bad(input integer u, input integer anc, input integer nrow, input integer y, input integer ep);
        begin dq[nd] = desc(u, anc, nrow, y, ep); nd = nd + 1; end
    endtask
    initial begin
        if (!$value$plusargs("CASE=%s", cs)) cs = "pos_basic";
        if (cs == "pos_basic") begin
            good(0, 2, 3, 11, 0);        // prefill: positions 0..2
            good(1, 1, 2, 21, 0);        // user 1 prefill 0..1
            good(0, 5, 3, 12, 0);        // a = 2 accepted + bonus: committed 3..5, epoch kept
            good(1, 3, 2, 22, 1);        // rejection: epoch + 1
            good(0, 6, 1, 13, 1);
            good(0, 12, 6, 14, 1);       // all accepted (g = 5): 6 rows
        end else if (cs == "pos_win") begin
            good(2, 299, 300, 31, 0);    // prefill longer than the drafter window: the last 256 rows
            good(2, 301, 2, 32, 1);
        end else if (cs == "neg_drop") begin
            good(0, 2, 3, 11, 0);
            // (0, 5, 3, ..) LOST on the lane
            bad(0, 8, 3, 13, 0);         // rows 6..8: gap 3..5 -> must be rejected (fault[0])
            exp_fault = 1;
        end else if (cs == "neg_stale") begin
            good(0, 2, 3, 11, 0);
            good(0, 5, 3, 12, 1);        // rejection: epoch 0 -> 1
            bad(0, 7, 2, 13, 0);         // rows 6..7 contiguous but epoch 0 < 1: stale (fault[1])
            exp_fault = 2;
        end else if (cs == "neg_replay") begin
            good(0, 2, 3, 11, 0);
            good(0, 5, 3, 12, 1);
            bad(0, 5, 3, 12, 1);         // the same descriptor again: rows already seeded (fault[0])
            exp_fault = 1;
        end
    end
    // ---------------- descriptor sender (grant protocol) through FWD / RET stations ----------------
    integer di = 0; reg s_v; wire s_r; reg [SW-1:0] s_d;
    wire lv; wire [SW-1:0] ld; wire g_far, g_near;
    always @(*) begin s_v = di < nd; s_d = dq[di]; end
    always @(posedge clk) if (rst_n && s_v && s_r) di <= di + 1;
    ot_dsrom_mtp_ltx #(.W(SW)) u_tx (.clk(clk), .rst_n(rst_n), .c_valid(s_v), .c_ready(s_r), .c_data(s_d),
        .l_valid(lv), .l_ready(g_near), .l_data(ld));
    wire [SW:0] f_mrs; wire t_mrs;
    tb_seedl_relay #(.W(SW + 1), .HOPS(FWD)) u_f (.clk(clk), .rst_n(rst_n), .i({ld, lv}), .o(f_mrs));
    tb_seedl_relay #(.W(1), .HOPS(RET)) u_g (.clk(clk), .rst_n(rst_n), .i(t_mrs), .o(g_near));
    // ---------------- VM: RTT receiver of requests, in-order responses after VLAT ----------------
    wire [AW:0] t_vrq; wire vq_far, vq_near; wire [AW:0] vrq_far;
    tb_seedl_relay #(.W(AW + 1), .HOPS(VF)) u_vf (.clk(clk), .rst_n(rst_n), .i(t_vrq), .o(vrq_far));
    tb_seedl_relay #(.W(1), .HOPS(VR)) u_vr (.clk(clk), .rst_n(rst_n), .i(vq_far), .o(vq_near));
    wire cv; wire [AW-1:0] ca; reg cr;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(VF + VR + 4), .ENABLE_RTT(1), .FORWARD_HOPS(VF), .RETURN_HOPS(VR)) u_vrx (
        .clk(clk), .rst_n(rst_n), .l_valid(vrq_far[0]), .l_ready(vq_far), .l_data(vrq_far[AW:1]),
        .c_valid(cv), .c_ready(cr), .c_data(ca));
    integer seed = 7;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 7; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    always @(posedge clk) cr <= ($random(seed) & 3) != 0;              // VM accepts 3 of 4 cycles
    function [1023:0] vmword(input [AW-1:0] a);
        integer k; reg [31:0] h;
        begin
            for (k = 0; k < 32; k = k + 1) begin
                h = {a[23:0], 8'(k)} * 32'h9E3779B1 ^ 32'h7F4A7C15; vmword[32*k +: 32] = h;
            end
        end
    endfunction
    reg [1024:0] vpipe [0:VLAT-1]; integer vk;
    always @(posedge clk) begin
        vpipe[0] <= {vmword(ca), cv && cr && rst_n};
        for (vk = 1; vk < VLAT; vk = vk + 1) vpipe[vk] <= vpipe[vk - 1];
    end
    wire [1024:0] f_vrs;
    tb_seedl_relay #(.W(1025), .HOPS(VR)) u_vs (.clk(clk), .rst_n(rst_n), .i(vpipe[VLAT - 1]), .o(f_vrs));
    // ---------------- seed elements (seed_ctl intake protocol) + die join ----------------
    wire [1024:0] t_x, x_far; wire [1:0] f_x; reg [1:0] x_join;
    tb_seedl_relay #(.W(1025), .HOPS(XH)) u_xf (.clk(clk), .rst_n(rst_n), .i(t_x), .o(x_far));
    tb_seedl_relay #(.W(2), .HOPS(XH)) u_xr (.clk(clk), .rst_n(rst_n), .i(x_join), .o(f_x));
    integer errs = 0;
    integer nin [0:E-1]; integer tproc [0:E-1]; reg idle [0:E-1]; reg rdy [0:E-1]; integer j; integer ndone;
    reg all_rdy;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (j = 0; j < E; j = j + 1) begin nin[j] = 0; tproc[j] = 0; idle[j] = 1; rdy[j] <= 0; end
            ndone = 0; x_join <= 0;
        end else begin
            x_join[1] <= 1'b0;
            for (j = 0; j < E; j = j + 1) begin
                rdy[j] <= idle[j];
                if (x_far[0]) begin
                    if (nin[j] == 240) begin $display("SEEDL_ERR beat beyond 240 at element %0d", j); errs = errs + 1; end
                    nin[j] = nin[j] + 1; idle[j] = 0;
                    if (nin[j] == 240) tproc[j] = 300 + 37 * j + ($random(seed) & 63);
                end else if (nin[j] == 240 && tproc[j] > 0) begin
                    tproc[j] = tproc[j] - 1;
                    if (tproc[j] == 0) begin nin[j] = 0; idle[j] = 1; ndone = ndone + 1; end
                end
            end
            if (ndone == E) begin x_join[1] <= 1'b1; ndone = 0; end
            all_rdy = 1; for (j = 0; j < E; j = j + 1) all_rdy = all_rdy & rdy[j];
            x_join[0] <= all_rdy;
        end
    end
    // ---------------- DUT ----------------
    wire [PW:0] t_ps; wire [3:0] t_flt;
    dsfd_mtp_seed_launch #(.NW(NW), .USER_W(UW), .MAXU(MAXU), .WIN(WIN), .VM_AW(AW), .FWD_C(FWD), .RET_C(RET)) dut (
        .ck(clk), .rst(rst_n), .f_mrs(f_mrs), .t_mrs(t_mrs), .f_clr({UW'(0), 1'b0}), .t_vrq(t_vrq), .f_vrq(vq_near),
        .f_vrs(f_vrs), .t_x(t_x), .f_x(f_x), .t_ps(t_ps), .t_flt(t_flt));
    // ---------------- checker ----------------
    integer rows = 0, beat = 0, starts = 0, cyc = 0;
    integer t_desc = -1, t_x1 = -1, t_done = -1, d2x = -1, d2p = -1, gap = -1, t_gd = -1;
    reg [AW-1:0] ea;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            if (f_mrs[0] && t_desc < 0) t_desc = cyc;
            if (t_x[0] && t_gd >= 0) begin if (cyc - t_gd > gap) gap = cyc - t_gd; t_gd = -1; end
            if (t_x[0]) begin
                if (t_x1 < 0 && t_desc >= 0) begin t_x1 = cyc; if (d2x < 0) d2x = t_x1 - t_desc; end
                if (rows >= nr) begin $display("SEEDL_ERR unexpected row"); errs = errs + 1; end
                else begin
                    ea = (AW'(rq_exp[rows][4+UW+NW-1:UW+NW]) << 19) | (AW'(rq_exp[rows][UW+NW-1:NW]) << 16) | (AW'(rq_exp[rows][7:0]) << 8) | AW'(beat);
                    if (t_x[1024:1] !== vmword(ea)) begin
                        if (errs < 5) $display("SEEDL_ERR row %0d beat %0d data mismatch", rows, beat);
                        errs = errs + 1;
                    end
                    beat = beat + 1;
                    if (beat == 240) begin beat = 0; rows = rows + 1; end
                end
            end
            if (f_x[1]) begin t_done = cyc; t_gd = cyc; end
            if (t_ps[0]) begin
                if (d2p < 0 && t_done >= 0) d2p = cyc - t_done;
                if (starts >= ne || t_ps[PW:1] !== eq[starts]) begin
                    $display("SEEDL_ERR program start %0d mismatch", starts); errs = errs + 1;
                end
                starts = starts + 1; t_desc = -1; t_x1 = -1; t_gd = -1;
            end
        end
    end
    initial begin
        repeat (8) @(posedge clk);
        rst_n = 1;
        wait (di == nd);
        repeat (2000) @(posedge clk);
        while (rows < nr && cyc < 2_000_000) @(posedge clk);
        repeat (3000) @(posedge clk);
        if (rows != nr) begin $display("SEEDL_ERR rows %0d of %0d", rows, nr); errs = errs + 1; end
        if (starts != ne) begin $display("SEEDL_ERR starts %0d of %0d", starts, ne); errs = errs + 1; end
        if (t_flt !== 4'(exp_fault)) begin $display("SEEDL_ERR fault %b expected %b", t_flt, 4'(exp_fault)); errs = errs + 1; end
        $display("SEEDL_RESULT case=%0s result=%s rows=%0d starts=%0d fault=%b cyc=%0d desc_to_x=%0d done_to_ps=%0d row_gap=%0d",
                 cs, errs == 0 ? "PASS" : "FAIL", rows, starts, t_flt, cyc, d2x, d2p, gap);
        $finish;
    end
endmodule

module tb_seedl_relay #(parameter integer W = 1, parameter integer HOPS = 0) (
    input wire clk, rst_n, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (HOPS == 0) begin : g0 assign o = i; end
    else begin : gp
        reg [W-1:0] p [0:HOPS-1]; integer j;
        always @(posedge clk) begin
            if (!rst_n) for (j = 0; j < HOPS; j = j + 1) p[j] <= '0;
            else begin p[0] <= i; for (j = 1; j < HOPS; j = j + 1) p[j] <= p[j-1]; end
        end
        assign o = p[HOPS-1];
    end endgenerate
endmodule
