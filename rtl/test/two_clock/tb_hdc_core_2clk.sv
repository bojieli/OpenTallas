`timescale 1ns/1ps
// Split-clock decode bench of the Qwen ROM core (reduced G4 shape, vector stream unit, BF16 weight ROM, KV SRAM).
// Driven by rtl/test/two_clock/hdc_core_2clk_harness.cpp, which ticks a 3.6 GHz VCO and raises
//   sclk (the core: sequencer, stream unit, reducers, vector memory)       every 4 ticks (0.9 GHz) and
//   fclk (the matrix engine and its ROM / KV / x read ports, ME_CDC = 1)  every 3 ticks (1.2 GHz),
// or both on the same ticks for the single-clock references (+CLK=slow | fast).
//
// The DUT is ot_hdc_core_vector_weight_2clk (tools/qwen_two_clock_core_emit.py) or, with +define+PINNED_CORE, the
// pinned ot_hdc_core_vector_weight itself (the cycle-identity reference).  Memories follow the domains:
//   fclk: engine weight port (f_wrom_*), KV read port, vector-memory x read port (1R1W, slow write clock);
//   sclk: program, constants, stream-unit weight/embedding port, a/b/c reads, every vector-memory and KV write.
// All writes are non-blocking in one slow block in port order (engine, stream unit, reducer, maxima: the
// pinned bench's collision priority).  Each fast-domain read of a word written in the previous 8 ticks (two slow
// cycles) is counted as a dual-clock collision (must stay 0).
//
// Checks: default -- one decode step on the golden-prefilled KV, every logit, the whole vector memory and the whole
// KV cache bit-exact against the ISA model (tools/hdc_program.py images); +MULTI -- empty KV, the prompt then
// +NGEN generated tokens, every step's logits / vector memory / KV against the ISA model's per-step snapshot
// (+STEPEXP, expect_*_steps.hex) and the generated ids against the torch oracle.
module tb_hdc_core_2clk #(
    parameter integer G = 4,
    parameter integer SW = 8,
    parameter integer ME_CDC = 0,
    parameter integer CDC_DEPTH = 4,
    parameter integer SAFE_CHASE = 1
) (input wire sclk, input wire fclk, input wire [63:0] tick);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KV_WORDS = 1024;
    localparam integer VM_ELEMS = 4096, VOCAB = 4096, PROG_WORDS = 4096;
    localparam integer MAX_STEPS = 24;
    localparam integer START = 16;
    localparam [63:0] COLL_WIN = 8;

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]      crom [0:CROM_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]      vm   [0:VM_ELEMS-1];
    reg [W*32-1:0]  kv   [0:KV_WORDS-1];
    reg [63:0]      vm_wt [0:VM_ELEMS-1];
    reg [63:0]      kv_wt [0:KV_WORDS-1];
    reg [31:0]      e_vm [0:VM_ELEMS-1];
    reg [31:0]      e_kv [0:KV_WORDS*W-1];
    reg [31:0]      e_lg [0:VOCAB-1];
    reg [31:0]      lg   [0:VOCAB-1];
    reg [31:0] e_lg_step [0:MAX_STEPS*VOCAB-1];
    reg [31:0] e_vm_step [0:MAX_STEPS*VM_ELEMS-1];
    reg [31:0] e_kv_step [0:MAX_STEPS*KV_WORDS*W-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] cycles;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re, wrom_su; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire f_wrom_re; wire [AW-1:0] f_wrom_addr; reg [G*W*16-1:0] f_wrom_q;
    wire [SW-1:0] crom_re; wire [SW*AW-1:0] crom_addr; reg [SW*64-1:0] crom_q;
    wire kv_re; wire [SW-1:0] kv_we; wire [G*AW-1:0] kv_raddr; wire [SW*AW-1:0] kv_waddr;
    reg [G*W*32-1:0] kv_q; wire [SW*32-1:0] kv_wdata; wire kv_write_flush;
    wire [SW-1:0] va_re, vb_re, vc_re; wire [SW*AW-1:0] va_addr, vb_addr, vc_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    reg [SW*32-1:0] va_q, vb_q, vc_q;
    wire [SW-1:0] vw_su_we; wire vw_rd_we; wire [SW*AW-1:0] vw_su_addr; wire [AW-1:0] vw_rd_addr;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
    wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [SW*32-1:0] vw_su_data; wire [31:0] vw_rd_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire vw_mx_we; wire [AW-1:0] vw_mx_addr; wire [W-1:0] vw_mx_mask; wire [W*32-1:0] vw_mx_data;

`ifdef PINNED_CORE
    assign f_wrom_re = 1'b0; assign f_wrom_addr = '0;
    ot_hdc_core_vector_weight #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW)) dut (
        .clk(sclk),
`else
    ot_hdc_core_vector_weight_2clk #(.ME_CDC(ME_CDC), .ME_CDC_DEPTH(CDC_DEPTH), .ME_CDC_SAFE_CHASE(SAFE_CHASE),
                                     .W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW)) dut (
        .clk(sclk), .fclk(fclk), .f_wrom_re(f_wrom_re), .f_wrom_addr(f_wrom_addr), .f_wrom_q(f_wrom_q),
`endif
        .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(), .cycles(cycles), .fault(fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .int8_wrom_re(), .int8_wrom_addr(), .int8_wrom_q({(G*W*8){1'b0}}),
        .scale_re(), .scale_gre(), .scale_addr(), .scale_q({(G*W*16){1'b0}}),
        .embed_code_re(), .embed_code_addr(), .embed_code_q(512'd0),
        .embed_scale_re(), .embed_scale_addr(), .embed_scale_q(16'd0),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .kv_write_drained(1'b1), .kv_write_flush(kv_write_flush),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_mx_we(vw_mx_we), .vw_mx_addr(vw_mx_addr), .vw_mx_mask(vw_mx_mask), .vw_mx_data(vw_mx_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(), .kvd_jsh(),
        .kvd_tiles(), .kvd_k(), .kvd_nout(), .kvd_kindk(), .kvd_pos(), .kv_ok(1'b1),
        .wrom_su(wrom_su), .wd_v(), .wd_wbase(), .wd_sbase(), .wd_tiles(), .wd_k(), .wd_nout(),
        .w_ok(1'b1), .emb_ok(1'b1), .me_mem_ok(1'b1), .me_clk_en());

    integer l, q;
    integer collisions = 0;
    // +TRACE=file: every engine-side read and every vector-memory / KV write, in time order (debug of ordering)
    integer tf = 0;
    reg [8*512-1:0] tpath;
    initial if ($value$plusargs("TRACE=%s", tpath)) tf = $fopen(tpath, "w");
    always @(posedge fclk) if (tf != 0) begin
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) $fdisplay(tf, "RX %0d %0d %h", tick, vx_addr[q*AW +: 12], vm[vx_addr[q*AW +: 12]]);
        if (kv_re) for (q = 0; q < G; q = q + 1) $fdisplay(tf, "RK %0d %0d %h", tick, kv_raddr[q*AW +: 10], kv[kv_raddr[q*AW +: 10]]);
    end
    always @(posedge sclk) if (tf != 0) begin
        for (q = 0; q < G; q = q + 1) if (vw_me_we[q]) for (l = 0; l < W; l = l + 1) if (vw_me_mask[q*W + l])
            $fdisplay(tf, "WM %0d %0d %h", tick, {vw_me_addr[q*AW +: 8], 4'b0} + l, vw_me_data[32*(q*W + l) +: 32]);
        for (q = 0; q < SW; q = q + 1) if (vw_su_we[q]) $fdisplay(tf, "WS %0d %0d %h", tick, vw_su_addr[q*AW +: 12], vw_su_data[32*q +: 32]);
        if (vw_rd_we) $fdisplay(tf, "WR %0d %0d %h", tick, vw_rd_addr[11:0], vw_rd_data);
        if (vw_mx_we) for (l = 0; l < W; l = l + 1) if (vw_mx_mask[l]) $fdisplay(tf, "WX %0d %0d %h", tick, {vw_mx_addr[7:0], 4'b0} + l, vw_mx_data[32*l +: 32]);
        for (q = 0; q < SW; q = q + 1) if (kv_we[q]) $fdisplay(tf, "WK %0d %0d %h", tick, kv_waddr[q*AW +: 24], kv_wdata[32*q +: 32]);
        for (q = 0; q < SW; q = q + 1) begin
            if (va_re[q]) $fdisplay(tf, "RA %0d %0d %h", tick, va_addr[q*AW +: 12], vm[va_addr[q*AW +: 12]]);
            if (vb_re[q]) $fdisplay(tf, "RB %0d %0d %h", tick, vb_addr[q*AW +: 12], vm[vb_addr[q*AW +: 12]]);
            if (vc_re[q]) $fdisplay(tf, "RC %0d %0d %h", tick, vc_addr[q*AW +: 12], vm[vc_addr[q*AW +: 12]]);
        end
        if (dut.me_go) $fdisplay(tf, "GO_ME %0d pc=%0d", tick, dut.pc);
        if (dut.su_go) $fdisplay(tf, "GO_SU %0d pc=%0d", tick, dut.pc);
    end
    // ---- fast-domain read ports (engine) ----
    always @(posedge fclk) begin
        if (f_wrom_re) f_wrom_q <= wrom[f_wrom_addr[16:0]];
        for (q = 0; q < G; q = q + 1) if (kv_re) begin
            kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 10]];
            if (tick - kv_wt[kv_raddr[q*AW +: 10]] <= COLL_WIN) collisions = collisions + 1;
        end
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) begin
            vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
            if (tick - vm_wt[vx_addr[q*AW +: 12]] <= COLL_WIN) collisions = collisions + 1;
        end
    end
    // ---- slow-domain ports: reads, then every write in port order ----
    always @(posedge sclk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
        for (q = 0; q < SW; q = q + 1) begin
            if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 12]];
            if (va_re[q]) va_q[32*q +: 32] <= vm[va_addr[q*AW +: 12]];
            if (vb_re[q]) vb_q[32*q +: 32] <= vm[vb_addr[q*AW +: 12]];
            if (vc_re[q]) vc_q[32*q +: 32] <= vm[vc_addr[q*AW +: 12]];
            if (kv_we[q]) begin
                kv[kv_waddr[q*AW + 4 +: 10]][32*kv_waddr[q*AW +: 4] +: 32] <= kv_wdata[32*q +: 32];
                kv_wt[kv_waddr[q*AW + 4 +: 10]] <= tick;
            end
        end
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) begin
                        vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
                        vm_wt[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= tick;
                    end
        for (q = 0; q < SW; q = q + 1)
            if (vw_su_we[q]) begin
                vm[vw_su_addr[q*AW +: 12]] <= vw_su_data[32*q +: 32];
                vm_wt[vw_su_addr[q*AW +: 12]] <= tick;
            end
        if (vw_rd_we) begin vm[vw_rd_addr[11:0]] <= vw_rd_data; vm_wt[vw_rd_addr[11:0]] <= tick; end
        if (vw_mx_we)
            for (l = 0; l < W; l = l + 1)
                if (vw_mx_mask[l]) begin
                    vm[{vw_mx_addr[7:0], 4'b0} + l] <= vw_mx_data[32*l +: 32];
                    vm_wt[{vw_mx_addr[7:0], 4'b0} + l] <= tick;
                end
        // the result words of the one unwritten matrix-vector op are the logits
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l]) lg[{me_oaddr[q*AW +: 8], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
    end

    reg [8*512-1:0] dir;
    integer lc = 0, i, bad_lg, bad_vm, bad_kv, s_lg, s_vm, s_kv;
    reg multi = 1'b0, stepexp = 1'b0, finished = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0, t_start = 0, total_ticks = 0;
    reg [31:0] kv_e;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        if ($test$plusargs("MULTI")) multi = 1'b1;
        if ($test$plusargs("STEPEXP")) stepexp = 1'b1;
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = 0;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 0;
        if (multi) begin
            $readmemh({dir, "/prompt.hex"}, prompt);
            $readmemh({dir, "/generated.hex"}, gold_gen);
            for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
            if (stepexp) begin
                $readmemh({dir, "/expect_logits_steps.hex"}, e_lg_step);
                $readmemh({dir, "/expect_vm_steps.hex"}, e_vm_step);
                $readmemh({dir, "/expect_kv_steps.hex"}, e_kv_step);
            end
        end else
            $readmemh({dir, "/kv.hex"}, kv);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (i = 0; i < VM_ELEMS; i = i + 1) begin vm[i] = 32'd0; vm_wt[i] = 64'hFFFF_FFFF_FFFF_0000; end
        for (i = 0; i < KV_WORDS; i = i + 1) kv_wt[i] = 64'hFFFF_FFFF_FFFF_0000;
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    task automatic check_step(input integer s);
        begin
            s_lg = 0; s_vm = 0; s_kv = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg_step[s*VOCAB + i]) s_lg = s_lg + 1;
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm_step[s*VM_ELEMS + i]) begin
                if (s_vm < 3) $display("step %0d vm %0d rtl %h expect %h", s, i, vm[i], e_vm_step[s*VM_ELEMS + i]);
                s_vm = s_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv_step[s*KV_WORDS*W + i]) s_kv = s_kv + 1;
            end
        end
    endtask

    always @(posedge sclk) begin
        lc <= lc + 1;
        if (lc == 5) rst_n <= 1'b1;
        start <= (lc == START);
        if (lc == START) t_start <= tick;
        if (lc == START - 1 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && lc > START + 2 && done && !start && !finished) begin
            total_cycles = total_cycles + cycles;
            total_ticks = total_ticks + (tick - t_start);
            if (stepexp) begin
                check_step(step);
                bad_lg = bad_lg + s_lg; bad_vm = bad_vm + s_vm; bad_kv = bad_kv + s_kv;
            end
            $display("STEP2C step=%0d pos=%0d in=%0d out=%0d gold=%0d cycles=%0d ticks=%0d fault=%0d lg_bad=%0d vm_bad=%0d kv_bad=%0d",
                     step, pos, token, next_token, (step >= n_prompt - 1) ? gold_gen[step - (n_prompt - 1)] : 16'hFFFF,
                     cycles, tick - t_start, fault, s_lg, s_vm, s_kv);
            if (step >= n_prompt - 1 && (next_token != gold_gen[step - (n_prompt - 1)])) gen_bad = gen_bad + 1;
            if (fault) gen_bad = gen_bad + 1;
            if (step + 1 == n_prompt + n_gen - 1) begin
                $display("HDC2C_MULTI me_cdc=%0d steps=%0d generated=%0d token_mismatches=%0d logit_mismatches=%0d vm_mismatches=%0d kv_mismatches=%0d collisions=%0d total_cycles=%0d total_ticks=%0d",
                         ME_CDC, step + 1, n_gen, gen_bad, bad_lg, bad_vm, bad_kv, collisions, total_cycles, total_ticks);
                if (gen_bad == 0 && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 && collisions == 0 && stepexp)
                    $display("PASS"); else $display("FAIL");
                finished <= 1'b1;
                $finish;
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
            t_start <= tick;   // every step rewrites all VOCAB logits; the per-step check sees any stale entry
        end
        if (!multi && lc > START + 2 && done && !finished) begin
            finished <= 1'b1;
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                bad_lg = bad_lg + 1;
            end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm[i]) begin
                if (bad_vm < 5) $display("vm %0d rtl %h expect %h", i, vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 5) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
            $display("HDC2C me_cdc=%0d token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d ticks=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d collisions=%0d",
                     ME_CDC, token, pos, next_token, expect_tok, cycles, tick - t_start, fault, bad_lg, bad_vm, bad_kv, collisions);
            if (next_token == expect_tok && !fault && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 && collisions == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (lc > 20000000) begin
            $display("TIMEOUT pc=%0d st=%0d", dut.pc, dut.st);
            $display("FAIL");
            $finish;
        end
    end
    initial begin bad_lg = 0; bad_vm = 0; bad_kv = 0; s_lg = 0; s_vm = 0; s_kv = 0; end
endmodule
