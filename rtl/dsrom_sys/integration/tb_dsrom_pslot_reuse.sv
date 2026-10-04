`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_dsrom_pslot_reuse: ONE consumer stage of a DS-ROM reuse chain under the wavefront, at the S81 stage
// controller's widths (NW 21, VWA 15, FLIT 512): ot_rom_pkg_ctrl_wf_ps (WAVE = 1, WIN = 6, SOURCE = 0,
// SIDE_IN = 1) with SIDE_PSL = 3 (8 position slots) or SIDE_PSL = 0 (as built: one slot per user).
//
// The producing stage (the index-source layer: L2, L20 or L24) shares each position's top-512 selection with
// the consumer stage as one SIDE message (32 flits, 16 ids of 32 bits each); the consumer stage runs the reuse
// layers (L3.., L21.., L25..) that read it.  The stimulus (+STIM=file, prepared by tools/dsrom_pslot_reuse.py)
// is the producer's and the hop's message stream in arrival order: under the wavefront the producer is up to WIN
// positions ahead, so SIDE messages of later positions arrive while (or before) the consumer runs earlier ones.
// The injector offers the flits back to back whenever the controller takes them.
//
// CORE MODEL (labelled): the stage's decode core is a behavioural job of CORE_LAT cycles that reads the staged
// selection three times (one read per reuse layer, at the start, the middle and the end of the job) from the
// vector memory at  SIDE_RXB + (user << SIDE_USH) + core_side_off  -- the memory wrapper's per-user and per-slot
// offsets -- and compares every word with +EXP=file (per job and read: 32 words, the golden layer's ctx_in.sel
// for the real position, the labelled stand-in for the others).  The controller's expected-position register
// is preset to the first position (the user is already there; labelled, as in tb_dsrom_integ_reindex_wf).
// RELAY = 1: the selection rides in the hop instead (tools/hdc_program_v41_array.py `relay`: HIDDEN payload word 0
// the hop marker, words 1..32 the selection), read from the received payload; no SIDE.
// Prints JOB / READ lines and PASS / FAIL.
// ---------------------------------------------------------------------------
module tb_dsrom_pslot_reuse #(
    parameter integer PSL = 3,
    parameter integer RELAY = 0,                 // 1: the selection rides in the hop (HIDDEN payload words 1..32)
    parameter integer NJOBS = 2,
    parameter integer CORE_LAT = 400,
    parameter integer MAX_CYCLES = 200000
);
    localparam integer FLIT = 512, NW = 21, VWA = 15, USER_W = 10, MAXU = 4, SW = 32, SIDE_USH = 10, PSH = 5;
    localparam integer SIDE_RXB = 512;           // staging base inside the per-user segment (words)
    localparam [3:0] MT_HIDDEN = 4'd1, MT_SIDE = 4'd3;
    localparam integer HDR_TYPE = 16, HDR_USER = 32, HDR_POS = 40;
    reg clk = 1'b0;
    always #0.4165 clk = ~clk;                   // 1.2 GHz
    reg rst_n = 1'b0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ------------------------------------------------------------------ DUT
    reg               in_valid = 1'b0;
    wire              in_ready;
    reg  [FLIT-1:0]   in_data = {FLIT{1'b0}};
    reg               in_last = 1'b0;
    wire              out_valid, out_last;
    wire [FLIT-1:0]   out_data;
    wire              core_start;
    wire [NW-1:0]     core_token, core_pos;
    wire [USER_W-1:0] core_user;
    reg               core_done = 1'b0;
    wire [VWA-1:0]    core_side_off;
    wire              vm_we, vm_re, pr_re, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash, core_busy;
    wire [VWA-1:0]    vm_waddr, vm_raddr;
    wire [FLIT-1:0]   vm_wdata;
    reg  [FLIT-1:0]   vm_rq = {FLIT{1'b0}};
    wire [23:0]       kv_base;
    ot_rom_pkg_ctrl_wf_ps #(.PKG_ID(5), .FLIT(FLIT), .NW(NW), .AW(24), .VWA(VWA), .MAXU(MAXU), .USER_W(USER_W),
        .KVW(1024), .XWORDS(1), .RXWORDS(RELAY ? 1 + SW : 1), .RXB(0), .TXB(100), .SOURCE(0), .SEND_HIDDEN(1),
        .HID_DEST(6), .SIDE_IN(RELAY ? 0 : 1), .SIDE_USH(SIDE_USH), .SIDE_PSL(RELAY ? 0 : PSL), .SIDE_PSH(PSH), .WAVE(1), .WIN(6)) ctrl (
        .clk(clk), .rst_n(rst_n), .cfg_users(8'd1), .cfg_prompt_len({NW{1'b0}}), .cfg_gen_len({NW{1'b0}}),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(1'b1), .out_data(out_data), .out_last(out_last),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(core_done), .core_next_token({NW{1'b0}}), .core_next_val(32'd0), .core_side_off(core_side_off),
        .kv_base(kv_base), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re),
        .vm_raddr(vm_raddr), .vm_rq(vm_rq), .pr_re(pr_re), .pr_user(), .pr_pos(), .pr_q({NW{1'b0}}),
        .pr_blk(), .pr_qk(1'b0), .core_done_accepted(), .result_origin_valid(), .result_origin_user(),
        .result_origin_pos(), .result_origin_final(), .core_busy(core_busy), .tok_valid(tok_valid),
        .tok_user(), .tok_pos(), .tok_id(), .users_done(), .proto_fault(proto_fault), .wf_issue(wf_issue),
        .wf_reject(wf_reject), .wf_squash(wf_squash));

    // vector memory (one word per access, synchronous read)
    reg [FLIT-1:0] vm [0:(1 << VWA) - 1];
    always @(posedge clk) begin
        if (vm_we) vm[vm_waddr] <= vm_wdata;
        if (vm_re) vm_rq <= vm[vm_raddr];
    end

    // ------------------------------------------------------------------ stimulus: {last, flit} per line
    localparam integer MAXF = 8192;
    reg [FLIT:0] stim [0:MAXF-1];
    integer nflit = 0, fi = 0;
    reg [FLIT-1:0] expw [0:NJOBS * 3 * SW - 1];
    integer exp_pos [0:NJOBS-1];
    string stimf, expf;
    integer fd, k;
    initial begin
        if (!$value$plusargs("STIM=%s", stimf)) $fatal(1, "+STIM= required");
        if (!$value$plusargs("EXP=%s", expf)) $fatal(1, "+EXP= required");
        fd = $fopen(stimf, "r");
        while (!$feof(fd) && nflit < MAXF) begin
            if ($fscanf(fd, "%h\n", stim[nflit]) == 1) nflit = nflit + 1;
        end
        $fclose(fd);
        $readmemh(expf, expw);
        for (k = 0; k < NJOBS; k = k + 1) exp_pos[k] = -1;
    end
    always @(posedge clk) if (rst_n) begin
        if (in_valid && in_ready) fi <= fi + 1;
    end
    reg inj_en = 1'b0;                           // the injector starts after the position preset
    always @(*) begin
        in_valid = rst_n && inj_en && fi < nflit;
        in_data = (fi < nflit) ? stim[fi][FLIT-1:0] : {FLIT{1'b0}};
        in_last = (fi < nflit) ? stim[fi][FLIT] : 1'b0;
    end

    // ------------------------------------------------------------------ core model
    integer job = 0, t0 = 0, running = 0, r_errors = 0, reads = 0, w;
    integer first_pos;
    reg [NW-1:0] jpos;
    reg [USER_W-1:0] juser;
    reg [VWA-1:0] joff;
    task automatic read_check(input integer rd);
        integer e, base;
        begin
            e = 0;
            base = RELAY ? 1 : SIDE_RXB + (juser << SIDE_USH) + joff;
            for (w = 0; w < SW; w = w + 1)
                if (vm[base + w] !== expw[(job * 3 + rd) * SW + w]) e = e + 1;
            reads = reads + 1;
            r_errors = r_errors + e;
            $display("READ job=%0d pos=%0d layer_read=%0d cycle=%0d slot_off=%0d word_errors=%0d", job, jpos, rd, cyc,
                     joff, e);
        end
    endtask
    integer jn;
    always @(posedge clk) if (rst_n) begin
        jn = job;
        if (running && ctrl.job_done) begin      // the controller takes the finished job on this edge
            $display("JOB %0d done pos=%0d cycle=%0d", job, jpos, cyc);
            jn = job + 1;
            running = 0;
            core_done <= 1'b0;
        end
        if (core_start) begin
            if (running) $fatal(1, "core start while running");
            running = 1; t0 = cyc; jpos = core_pos; juser = core_user;
            $display("JOB %0d start pos=%0d user=%0d cycle=%0d", jn, core_pos, core_user, cyc);
        end
        job <= jn;
        if (running && !core_start) begin
            joff = core_side_off;                  // registered on the start edge
            if (cyc == t0 + 2) read_check(0);
            if (cyc == t0 + CORE_LAT / 2) read_check(1);
            if (cyc == t0 + CORE_LAT - 2) read_check(2);
            if (cyc >= t0 + CORE_LAT) core_done <= 1'b1;
        end
    end

    integer hid_out = 0;
    always @(posedge clk) if (rst_n && out_valid && out_data[HDR_TYPE +: 4] == MT_HIDDEN && !out_last) hid_out <= hid_out + 1;

    initial begin
        if (!$value$plusargs("P0=%d", first_pos)) first_pos = 1048575;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        ctrl.upos[0] = NW'(first_pos);           // labelled preset: the user is already at the first position
        @(negedge clk);
        inj_en = 1'b1;
    end
    always @(posedge clk) begin
        if (rst_n && proto_fault) begin
            $display("E proto_fault cycle=%0d", cyc); $display("FAIL proto_fault jobs=%0d", job); $finish;
        end
        if (rst_n && job == NJOBS && !running) begin
            if (r_errors == 0 && reads == 3 * NJOBS)
                $display("PASS jobs=%0d reads=%0d word_errors=0 cycles=%0d hidden_out=%0d", job, reads, cyc, hid_out);
            else
                $display("FAIL jobs=%0d reads=%0d word_errors=%0d", job, reads, r_errors);
            $finish;
        end
        if (cyc > MAX_CYCLES) begin $display("FAIL timeout jobs=%0d fi=%0d/%0d", job, fi, nflit); $finish; end
    end
endmodule
