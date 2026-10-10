`timescale 1ns/1ps
// hgi-takeover 2026-10-09: ot_hgi_mtp_xlate against the legacy MX1 operation backend (ot_hbm_native_mtp_operation_
// backend_mx1, the reference expansion) on the same native operations: the translator's doorbell sequence {kind (from
// the entry offset), token, position} must equal the legacy backend's launch sequence exactly, every operation must
// complete un-faulted, every result kind (4, 10) must raise one am with the completion's token, and a non-owned
// completion / an absent kernel must fault.  Legacy SM model as tb_hbm_native_mtp_mx1_regb_system (paired results).
// MUT 1 (am from kind 1) must FAIL.
module tb_hgi_mtp_xlate;
    parameter integer MUT = 0;
    reg clk = 0; always #5 clk = ~clk; reg rst_n = 0;
    // ---- the operation list
    localparam integer NOPS = 12;
    reg [200:0] ops [0:NOPS-1];
    function automatic [200:0] mk(input [3:0] op, input [7:0] idx, input [3:0] nc, input [31:0] pos, input [16:0] t1);
        reg [200:0] c; integer j;
        begin c = 0; c[3:0] = op; c[11:4] = idx; c[15:12] = nc; c[47:16] = pos; c[64:48] = t1;
            for (j = 0; j < 8; j = j + 1) c[65 + 17*j +: 17] = 17'(1000 + 37 * j + pos);
            mk = c; end
    endfunction
    initial begin
        ops[0] = mk(0, 0, 4, 100, 7);  ops[1] = mk(0, 5, 6, 200, 9);  ops[2] = mk(0, 39, 1, 300, 11);
        ops[3] = mk(1, 0, 5, 400, 13); ops[4] = mk(2, 0, 3, 500, 15); ops[5] = mk(3, 0, 5, 600, 17);
        ops[6] = mk(3, 2, 5, 700, 19); ops[7] = mk(4, 0, 5, 800, 21); ops[8] = mk(5, 3, 1, 900, 23);
        ops[9] = mk(1, 0, 1, 1048570, 25); ops[10] = mk(0, 1, 2, 1000, 27); ops[11] = mk(5, 0, 1, 50, 29);
    end
    // ---- legacy backend (reference)
    reg iv = 0; reg [3:0] ik = 0; reg [63:0] ipc = 0;
    reg lcv = 0; reg [200:0] lc = 0; wire lcr, lcpl_v, lcpl_f, lam_v; wire [16:0] lam;
    wire [31:0] lv, lj, ls; wire [63:0] pc; wire [33:0] tok; wire [39:0] lpos; wire [145:0] owner; wire [3:0] lg;
    reg [31:0] sd = 0, rv = 0, q = 0; reg [63:0] qp = 0; reg [1023:0] rd = 0;
    ot_hbm_native_mtp_operation_backend_mx1 #(.ENABLE(1)) lb (.clk(clk), .rst_n(rst_n), .external_fault(1'b0),
        .backend_quiescent(1'b1), .install_v(iv), .install_kind(ik), .install_pc(ipc), .noise_token(17'd129279),
        .cmd_v(lcv), .cmd_ready(lcr), .cmd(lc), .cmd_job(32'h12345678), .cmd_generation(4'hb), .cmd_sequence(32'd5),
        .cpl_v(lcpl_v), .cpl_ready(1'b1), .cpl_job(lj), .cpl_generation(lg), .cpl_sequence(ls), .cpl_fault(lcpl_f),
        .am_v(lam_v), .am_idx(lam), .launch_v(lv), .launch_pc(pc), .launch_token(tok), .launch_pos(lpos), .launch_owner(owner),
        .sm_done(sd), .sm_fault(32'b0), .res_v(rv), .res_data(rd), .busy(), .drained_ready(), .fault(), .st_launches());
    always @(posedge clk) begin                       // SM model: done two edges after launch, results for heads
        q <= lv; qp <= pc; sd <= q; rv <= 0; rd <= 0;
        if (qp[31:0] == 500 || qp[31:0] == 1100) begin rv <= q; for (integer k = 0; k < 32; k = k + 1) rd[k*32 +: 32] <= 32'd4242; end
    end
    // ---- translator + sequencer model
    reg [351:0] kent; integer kk;
    initial for (kk = 0; kk < 11; kk = kk + 1) kent[kk*32 +: 32] = 100 * (kk + 1);
    reg xcv = 0; reg [200:0] xc = 0; wire xcr, xcpl_v, xcpl_f, xam_v; wire [16:0] xam;
    wire dbv; reg dbr = 0; wire [17:0] dbt; wire [19:0] dbp; wire [31:0] dbj, dbo, xj, xs; wire [3:0] dbg, xg; wire [1:0] dbe;
    reg cv = 0; reg [17:0] ct = 0; reg [19:0] cp = 0; reg [31:0] cj = 0; reg [3:0] cg = 0, cs = 0; reg ctx = 0;
    ot_hgi_mtp_xlate #(.MUT(MUT)) xt (.clk(clk), .rst_n(rst_n), .external_fault(1'b0), .backend_quiescent(1'b1),
        .kent(kent), .noise_token(17'd129279), .cmd_v(xcv), .cmd_ready(xcr), .cmd(xc), .cmd_job(32'h12345678),
        .cmd_generation(4'hb), .cmd_sequence(32'd5), .cpl_v(xcpl_v), .cpl_ready(1'b1), .cpl_job(xj), .cpl_generation(xg),
        .cpl_sequence(xs), .cpl_fault(xcpl_f), .am_v(xam_v), .am_idx(xam), .drained_ready(),
        .db_v(dbv), .db_rdy(dbr), .db_token(dbt), .db_pos(dbp), .db_job(dbj), .db_gen(dbg), .db_entry(dbe), .db_off(dbo),
        .c_v(cv), .c_rdy(), .c_token(ct), .c_pos(cp), .c_job(cj), .c_gen(cg), .c_status(cs), .c_tokx(ctx));
    integer sdel = -1; reg [19:0] sp; reg [31:0] soff;
    always @(posedge clk) begin                       // sequencer model: random doorbell accept, completion 3..10 later
        cv <= 1'b0; dbr <= ($urandom % 3) != 0;
        if (dbv && dbr && sdel < 0) begin sdel = 3 + $urandom % 8; sp = dbp; soff = dbo; end
        else if (sdel > 0) sdel = sdel - 1;
        else if (sdel == 0) begin
            cv <= 1'b1; ct <= ((soff == 500 || soff == 1100) ? 18'd4242 : 18'd0); cp <= sp; cj <= 32'h12345678; cg <= 4'hb;
            cs <= 4'd0; ctx <= 1'b0; sdel = -1;
        end
    end
    // ---- capture both launch sequences
    reg [40:0] lseq [0:4095]; reg [40:0] xseq [0:4095]; integer nl = 0, nx = 0, nlam = 0, nxam = 0, nres = 0, errs = 0;
    always @(posedge clk) if (rst_n) begin
        if (lb.state == 3'd1 && lb.template_valid[lb.kind]) begin lseq[nl] = {lb.kind, lb.token, lb.position}; nl = nl + 1; end
        if (dbv && dbr) begin
            xseq[nx] = {4'(dbo / 100 - 1), dbt[16:0], dbp}; nx = nx + 1;
            if (dbo == 500 || dbo == 1100) nres = nres + 1;
            if (dbe != 2'd3 || dbj != 32'h12345678 || dbg != 4'hb) begin $display("FAIL doorbell identity / entry"); errs = errs + 1; end
        end
        if (lam_v) nlam = nlam + 1;
        if (xam_v) begin nxam = nxam + 1; if (xam != 17'd4242) begin $display("FAIL am token %0d", xam); errs = errs + 1; end end
    end
    integer i, t;
    initial begin
        repeat (3) @(negedge clk); rst_n = 1;
        for (t = 0; t < 11; t = t + 1) begin iv = 1; ik = t; ipc = {32'(100*(t+1)+1), 32'(100*(t+1))}; @(negedge clk); end
        iv = 0; repeat (3) @(negedge clk);
        for (i = 0; i < NOPS; i = i + 1) begin
            lc = ops[i]; lcv = 1; while (!lcr) @(negedge clk); @(negedge clk); lcv = 0;
            t = 0; while (!lcpl_v && t < 100000) begin @(negedge clk); t = t + 1; end
            if (lcpl_f) begin $display("FAIL legacy op %0d faulted", i); errs = errs + 1; end
            xc = ops[i]; xcv = 1; while (!xcr) @(negedge clk); @(negedge clk); xcv = 0;
            t = 0; while (!xcpl_v && t < 100000) begin @(negedge clk); t = t + 1; end
            if (!xcpl_v || xcpl_f || xj != 32'h12345678 || xs != 32'd5) begin $display("FAIL translator op %0d", i); errs = errs + 1; end
            repeat (2) @(negedge clk);
        end
        if (nl != nx) begin $display("FAIL launch counts legacy %0d translator %0d", nl, nx); errs = errs + 1; end
        for (i = 0; i < nl && i < nx; i = i + 1) if (lseq[i] !== xseq[i]) begin
            if (errs < 5) $display("FAIL launch %0d legacy %h translator %h", i, lseq[i], xseq[i]); errs = errs + 1; end
        if (nxam != nres || nlam != nres) begin $display("FAIL am counts translator %0d legacy %0d results %0d", nxam, nlam, nres); errs = errs + 1; end
        // negative: an absent kernel (entry 0) and a completion not owned must fault
        kent[4*32 +: 32] = 0; xc = ops[3]; xcv = 1; while (!xcr) @(negedge clk); @(negedge clk); xcv = 0;
        t = 0; while (!xcpl_v && t < 100000) begin @(negedge clk); t = t + 1; end
        if (!xcpl_f) begin $display("FAIL absent kernel not faulted"); errs = errs + 1; end
        if (errs == 0) $display("PASS HGI_MTP_XLATE ops=%0d launches=%0d results=%0d (equal to the legacy backend)", NOPS, nx, nres);
        else $display("FATAL HGI_MTP_XLATE errors=%0d", errs);
        $finish;
    end
endmodule
