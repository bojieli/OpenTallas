`timescale 1ns/1ps
// Token-level simulation top of the V4.1 hardwired decode core: behavioural
// synchronous-read memories loaded from tools/hdc_program_v41.py images.
// Driven by Verilator (rtl/test/hdc_core_v41_harness.cpp).
//
// Default: one decode step at +POS for +TOKEN from the golden-prefilled state
// (KV image, persistent vector memory, Engram hash history primed with the
// preceding tokens), then a bit-exact check of every logit, the whole vector
// memory and the whole KV cache against the ISA-level model.
// +MULTI: start from an EMPTY state, run the +NPROMPT prompt tokens through
// the core, then generate +NGEN tokens feeding each output back; compare the
// generated ids with the ISA model's, and the final vector memory and KV cache
// with its final state.
// +TRACE prints every issue (cycle, pc, unit) for the per-op breakdown.
module tb_hdc_core_v41 (input wire clk);
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3;
    localparam integer HROM_WORDS = 1 << 19;
    localparam integer WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19, CROM_WORDS = 1 << 15;
    localparam integer KV_WORDS = 32768, VM_ELEMS = 65536, VOCAB = 4040, PROG_WORDS = 1 << PAW;

    reg [G*W*16-1:0]    wrom [0:WROM_WORDS-1];
    reg [HNL*32-1:0]    hrom [0:HROM_WORDS-1];
    reg [BL*QLB-1:0]    qrom [0:QROM_WORDS-1];
    reg [263:0]         erom [0:EROM_WORDS-1];
    reg [63:0]          crom [0:CROM_WORDS-1];
    reg [W*32-1:0]      kv   [0:KV_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]          vm   [0:VM_ELEMS-1];
    reg [31:0]          e_vm [0:VM_ELEMS-1];
    reg [31:0]          e_kv [0:KV_WORDS*W-1];
    reg [31:0]          e_lg [0:VOCAB-1];
    reg [31:0]          lg   [0:VOCAB-1];
    reg [31:0]          kvimg [0:KV_WORDS*W-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] next_val, cycles;
    reg prime_v = 1'b0, prime_first = 1'b0;
    reg [11:0] prime_cid = 0;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re, ewrom_re; wire [AW-1:0] wrom_addr, ewrom_addr; reg [G*W*16-1:0] wrom_q, ewrom_q;
    wire qrom_re; wire [AW-1:0] qrom_addr; reg [BL*QLB-1:0] qrom_q;
    wire hrom_re; wire [AW-1:0] hrom_addr; reg [HNL*32-1:0] hrom_q;
    wire vh_re; wire [AW-1:0] vh_addr; reg [31:0] vh_q;
    wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
    wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
    wire [3:0] crom_re; wire [4*AW-1:0] crom_addr; reg [4*64-1:0] crom_q;
    wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
    wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; reg [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    wire [3:0] vs_re; wire [4*AW-1:0] vs_addr; reg [4*32-1:0] vs_q;
    wire vi_re, vq_re, vr_re, wqr_re, wxr_re;
    wire [AW-1:0] vi_addr, vq_addr, vr_addr, wqr_addr, wxr_addr;
    reg [31:0] vi_q, vq_q, vr_q;
    reg [1023:0] wqr_q, wxr_q;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data;
    wire vw_su_we, vw_rd_we, vw_xe_we, ww_q_we, ww_x_we;
    wire [AW-1:0] vw_su_addr, vw_rd_addr, vw_xe_addr, ww_q_addr, ww_x_addr;
    wire [31:0] vw_su_data, vw_rd_data, vw_xe_data, ww_q_mask, ww_x_mask;
    wire [1023:0] ww_q_data, ww_x_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [4:0] unit_busy; wire [2:0] issue_unit;

    ot_hdc_core_v41 dut (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
        .prime_v(prime_v), .prime_first(prime_first), .prime_cid(prime_cid),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
        .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
        .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q), .vh_re(vh_re), .vh_addr(vh_addr), .vh_q(vh_q),
        .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
        .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
        .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit));

    // synchronous-read memories
    integer l, q;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
        if (ewrom_re) ewrom_q <= wrom[ewrom_addr[18:0]];
        if (qrom_re) qrom_q <= qrom[qrom_addr[15:0]];
        if (hrom_re) hrom_q <= hrom[hrom_addr[18:0]];
        if (vh_re) vh_q <= vm[vh_addr[15:0]];
        if (ww_h_we) for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[ww_h_addr[15:0] + q] <= ww_h_data[32*q +: 32];
        if (erom_re) erom_q <= erom[erom_addr[18:0]];
        for (q = 0; q < 4; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
        if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
        for (q = 0; q < G; q = q + 1) if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15]];
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 16]];
        for (q = 0; q < 4; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[vs_addr[q*AW +: 16]];
        if (vi_re) vi_q <= vm[vi_addr[15:0]];
        if (vq_re) vq_q <= vm[vq_addr[15:0]];
        if (vr_re) vr_q <= vm[vr_addr[15:0]];
        if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[wqr_addr[15:0] + q];
        if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[wxr_addr[15:0] + q];
        if (kv_we) kv[kv_waddr[18:4]][32*kv_waddr[3:0] +: 32] <= kv_wdata;
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 12], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        if (vw_su_we) vm[vw_su_addr[15:0]] <= vw_su_data;
        if (vw_rd_we) vm[vw_rd_addr[15:0]] <= vw_rd_data;
        if (vw_xe_we) vm[vw_xe_addr[15:0]] <= vw_xe_data;
        if (ww_q_we) for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[ww_q_addr[15:0] + q] <= ww_q_data[32*q +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[15:0] + q] <= ww_x_data[32*q +: 32];
        // the result words of the one unwritten matrix-vector op are the logits
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l] && ({me_oaddr[q*AW +: 12], 4'b0} + l) < VOCAB)
                        lg[{me_oaddr[q*AW +: 12], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
    end

    reg [8*512-1:0] dir;
    integer cyc = 0, i, bad_lg, bad_vm, bad_kv, n_prime = 0, pfirst = 0, prime_i = 0;
    reg trace = 1'b0, multi = 1'b0, running = 1'b0, dbg = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    reg [NW-1:0] prime [0:7];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0;
    integer busy_me = 0, busy_su = 0, busy_qe = 0, busy_xu = 0, busy_he = 0, all_idle = 0;
    always @(posedge clk) if (dut.st != 0) begin
        if (unit_busy[0]) busy_me <= busy_me + 1;
        if (unit_busy[1]) busy_su <= busy_su + 1;
        if (unit_busy[2]) busy_qe <= busy_qe + 1;
        if (unit_busy[3]) busy_xu <= busy_xu + 1;
        if (unit_busy[4]) busy_he <= busy_he + 1;
        if (unit_busy == 0) all_idle <= all_idle + 1;
    end
    reg [31:0] kv_e;
    reg [4:0] busy_q = 5'd0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if ($test$plusargs("DBG")) dbg = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        if (!$value$plusargs("NPRIME=%d", n_prime)) n_prime = 0;
        if (!$value$plusargs("PFIRST=%d", pfirst)) pfirst = 0;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/qrom.hex"}, qrom);
        $readmemh({dir, "/hrom.hex"}, hrom);
        $readmemh({dir, "/erom.hex"}, erom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        if ($test$plusargs("MULTI")) multi = 1'b1;
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = 0;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 0;
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
        if (multi) begin
            $readmemh({dir, "/prompt.hex"}, prompt);
            $readmemh({dir, "/generated.hex"}, gold_gen);
            $readmemh({dir, "/expect_multi_vm.hex"}, e_vm);
            $readmemh({dir, "/expect_multi_kv.hex"}, e_kv);
        end else begin
            $readmemh({dir, "/kv.hex"}, kvimg);
            for (i = 0; i < KV_WORDS * W; i = i + 1) kv[i / W][32*(i % W) +: 32] = kvimg[i];
            $readmemh({dir, "/vm_init.hex"}, vm);
            $readmemh({dir, "/prime.hex"}, prime);
            $readmemh({dir, "/expect_vm.hex"}, e_vm);
            $readmemh({dir, "/expect_kv.hex"}, e_kv);
            $readmemh({dir, "/expect_logits.hex"}, e_lg);
        end
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    task check_state(input integer check_logits);
        begin
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            if ($test$plusargs("DUMP")) $writememh({dir, "/rtl_vm.hex"}, vm);
            if (check_logits)
                for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                    if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                    bad_lg = bad_lg + 1;
                end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm[i]) begin
                if (bad_vm < 10) $display("vm %0d rtl %h expect %h", i, vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 10) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
        end
    endtask

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        // prime the Engram hash history with the tokens before POS (single step)
        prime_v <= 1'b0;
        if (!multi && cyc >= 8 && prime_i < n_prime) begin
            prime_v <= 1'b1; prime_cid <= prime[prime_i][11:0]; prime_first <= (prime_i == 0) && pfirst;
            prime_i <= prime_i + 1;
        end
        start <= (cyc == 30);
        if (cyc == 29 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && cyc > 32 && done && !start) begin
            total_cycles = total_cycles + cycles;
            $display("STEP pos=%0d in=%0d out=%0d gold=%0d cycles=%0d fault=%0d", pos, token, next_token,
                     (step >= n_prompt - 1) ? gold_gen[step - (n_prompt - 1)] : 0, cycles, fault);
            if (step >= n_prompt - 1 && (next_token != gold_gen[step - (n_prompt - 1)])) gen_bad = gen_bad + 1;
            if (fault) gen_bad = gen_bad + 1;
            if (step + 1 == n_prompt + n_gen - 1) begin
                check_state(0);
                $display("HDC41_MULTI steps=%0d generated=%0d mismatches=%0d total_cycles=%0d vm_mismatch=%0d kv_mismatch=%0d",
                         step + 1, n_gen, gen_bad, total_cycles, bad_vm, bad_kv);
                if (gen_bad == 0 && bad_vm == 0 && bad_kv == 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
        end
        if (!multi && cyc > 32 && done) begin
            check_state(1);
            $display("HDC41 token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, expect_tok, cycles, fault, bad_lg, bad_vm, bad_kv);
            $display("UTIL me_busy=%0d su_busy=%0d qe_busy=%0d xu_busy=%0d he_busy=%0d all_idle=%0d", busy_me,
                     busy_su, busy_qe, busy_xu, busy_he, all_idle);
            if (next_token == expect_tok && !fault && bad_lg == 0 && bad_vm == 0 && bad_kv == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (dbg && (vw_su_we || vw_rd_we || kv_we))
            $display("DBG cyc=%0d su_we=%0d a=%0d d=%h rd_we=%0d a=%0d d=%h kv_we=%0d a=%0d d=%h", cycles, vw_su_we,
                     vw_su_addr, vw_su_data, vw_rd_we, vw_rd_addr, vw_rd_data, kv_we, kv_waddr, kv_wdata);
        if (dbg && (unit_busy != busy_q))
            $display("BUSY cyc=%0d units=%b", cycles, unit_busy);
        busy_q <= unit_busy;
        if (trace && issue_unit != 0)
            $display("ISSUE cyc=%0d pc=%0d unit=%0d", cycles, dut.pc, issue_unit);
        if (cyc > 50000000) begin
            $display("TIMEOUT pc=%0d st=%0d idles=%b", dut.pc, dut.st, dut.idles);
            $finish;
        end
    end
endmodule
