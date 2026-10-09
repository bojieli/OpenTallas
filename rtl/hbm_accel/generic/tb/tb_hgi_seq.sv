`timescale 1ns/1ps
// hbm-forks 2026-10-09: bench of the HGI-1 v1.0 sequencer (ot_hgi_seq), vectors from tools/hgi_seq_vectors.py.
//   CF-PROG  the hbm-sim compiler's Qwen3-8B token program (embed, 36 layers in one LOOP, head; 1,162 dispatches) at
//            pos 8,191 / 0: every dispatch equals the reference (whose effective bases / n equal hgi_sim Machine.eff);
//   CF-LOOP2 two nested loop levels (L outer, L1 inner, l1stride, LAST_ITER of the inner loop);
//   CF-IDXD  IDX.TOPK writes the I table at its RETIRE; expert fetch by id in a LOOP over k; n from VM (N_FROM_VM);
//            out-of-range id / I-table read / n -> status 3; the stale-table negative (+define+SEQ_STALE: the
//            indexed readers lose their IDX wait bit) must FAIL;
//   DS DYN   codes 16..40 at every slot (pos 2^20 - 1, 20, 777; ranks 0..3);
//   CF-CP    absent unit (SIMT, 13), op range, reserved CTL / DYN codes, END token range (151,935 OK / 151,936 / DS
//            131,071), doorbell token / position range, bad loops, a body over the ring, a unit fault (status 1).
// Every dispatch: unit port, header, SUT, the 7 effective descriptors, the 7 x 21-bit n, POS1, POS_SLOT1, L, L1; the
// `wait` rule against the bench's own outstanding counts.  Random fetch / unit / VM ready, fetch latency, unit retire
// delays (IDX and ARGMAX retire late: 40-60 cycles, so a missing wait reads a stale table).
// Prints HGI_SEQ PASS / FAIL.  Mutants: OT_HGI_SEQ_MUT_WAIT, OT_HGI_SEQ_MUT_LOOP, OT_HGI_SEQ_MUT_IDXL.
module tb_hgi_seq;
`include "hgi_seq_sizes.svh"
`include "hgi_seq_sizes_conf.svh"
`ifdef SEQ_CONF
    localparam integer NCASE = CONF_NCASE, NEXP = CONF_NEXP, NW = CONF_NW;
`elsif SEQ_STALE
    localparam integer NCASE = SEQ_NCASE_STALE, NEXP = SEQ_NEXP_STALE, NW = SEQ_NW;
`else
    localparam integer NCASE = SEQ_NCASE, NEXP = SEQ_NEXP, NW = SEQ_NW;
`endif
    localparam integer PAGE = 32'h10;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [159:0] md_d; reg [17:0] vocab; reg [20:0] ctxmax; reg [7:0] rank;
    reg db_v = 0; reg [17:0] db_token; reg [19:0] db_pos; wire db_rdy;
    wire f_req_v; reg f_req_rdy = 0; wire [39:0] f_req_addr; reg f_rsp_v = 0; reg [255:0] f_rsp_data;
    wire vr_v; reg vr_rdy = 0; wire [17:0] vr_addr; reg vr_rsp_v = 0; reg [31:0] vr_rsp_data;
    wire [15:0] u_v; reg [15:0] u_rdy = 0; wire [127:0] d_hdr; wire [255:0] d_sut; wire [1791:0] d_desc;
    wire [146:0] d_n; wire [20:0] d_pos1, d_pslot1; wire [15:0] d_L, d_L1;
    reg [15:0] u_done = 0, u_fault = 0; reg wr_quiet = 1;
    wire cpl_v; reg cpl_rdy = 0; wire [17:0] cpl_token; wire [19:0] cpl_pos; wire [31:0] cpl_job, cpl_cycles;
    wire [3:0] cpl_gen, cpl_status; wire busy; wire [4:0] cpl_ntok; wire [287:0] cpl_toks;
    reg [31:0] tks [0:NCASE*16-1];
`ifdef SEQ_CP
    // the die command processor (config path + sequencer): the case's cp_vocab / cp_ctx_max / image words go in through
    // the CFG window and CFG_COMMIT (busy / range checked, broadcast, settled) instead of being forced
    reg cmd_we = 0; reg [5:0] cmd_addr = 0; reg [63:0] cmd_wdata = 0;
    wire [39:0] cfg_bus; wire cfg_loaded; wire [2:0] cfg_err; wire [63:0] cfg_cp_act;
    ot_hgi_cp #(.USE_MACRO(`ifdef SEQ_MACRO 1 `else 0 `endif)) dut (.clk(clk), .rst_n(rst_n), .cmd_we(cmd_we),
        .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .units_busy(1'b0), .cfg_bus(cfg_bus), .cfg_loaded(cfg_loaded),
        .cfg_err(cfg_err), .cfg_cp_act(cfg_cp_act), .rank(rank),
        .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(32'h1234),
        .db_gen(4'h5), .db_entry(2'd0), .f_req_v(f_req_v), .f_req_rdy(f_req_rdy), .f_req_addr(f_req_addr),
        .f_rsp_v(f_rsp_v), .f_rsp_data(f_rsp_data), .vr_v(vr_v), .vr_rdy(vr_rdy), .vr_addr(vr_addr), .vr_rsp_v(vr_rsp_v),
        .vr_rsp_data(vr_rsp_data), .u_v(u_v), .u_rdy(u_rdy), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .d_n(d_n),
        .d_pos1(d_pos1), .d_pslot1(d_pslot1), .d_L(d_L), .d_L1(d_L1), .u_done(u_done), .u_fault(u_fault),
        .wr_quiet(wr_quiet), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_pos(cpl_pos),
        .cpl_job(cpl_job), .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles),
        .cpl_ntok(cpl_ntok), .cpl_toks(cpl_toks));
    assign busy = dut.u_seq.busy;
    task automatic cfg_pair(input [4:0] pr, input [31:0] lo, input [31:0] hi);
        begin @(negedge clk); cmd_we = 1; cmd_addr = {1'b1, pr}; cmd_wdata = {hi, lo}; @(negedge clk); cmd_we = 0; end
    endtask
    reg [31:0] mdw [0:NCASE*64-1];
`ifdef SEQ_CONF
    initial $readmemh("hgi_seq_md_conf.mem", mdw);
`elsif SEQ_STALE
    initial $readmemh("hgi_seq_md_stale.mem", mdw);
`else
    initial $readmemh("hgi_seq_md.mem", mdw);
`endif
    task automatic cfg_load(input integer cc, input [31:0] voc, input [31:0] ctx);
        integer w, pr; begin
            for (pr = 0; pr < 32; pr = pr + 1) cfg_pair(pr[4:0], mdw[cc*64 + 2*pr], mdw[cc*64 + 2*pr + 1]);
            @(negedge clk); cmd_we = 1; cmd_addr = 6'h3F; @(negedge clk); cmd_we = 0; repeat (4) @(negedge clk);
            w = 0; while ((dut.u_cfg.st_hold || !cfg_loaded) && w < 2000) begin @(negedge clk); w = w + 1; end
            repeat (3) @(negedge clk);
            if (cfg_err != 0 || !cfg_loaded) begin $display("FAIL cfg load err %0d loaded %0d", cfg_err, cfg_loaded); fails = fails + 1; end
            if (cfg_cp_act !== {ctx, voc}) begin $display("FAIL cfg read-back %h", cfg_cp_act); fails = fails + 1; end
        end
    endtask
`else
    ot_hgi_seq #(.USE_MACRO(`ifdef SEQ_MACRO 1 `else 0 `endif)) dut (.clk(clk), .rst_n(rst_n), .md_d(md_d), .cfg_vocab(vocab), .cfg_ctx_max(ctxmax), .rank(rank),
        .hold(1'b0), .busy(busy), .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(32'h1234),
        .db_gen(4'h5), .db_entry(2'd0), .f_req_v(f_req_v), .f_req_rdy(f_req_rdy), .f_req_addr(f_req_addr),
        .f_rsp_v(f_rsp_v), .f_rsp_data(f_rsp_data), .vr_v(vr_v), .vr_rdy(vr_rdy), .vr_addr(vr_addr), .vr_rsp_v(vr_rsp_v),
        .vr_rsp_data(vr_rsp_data), .u_v(u_v), .u_rdy(u_rdy), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .d_n(d_n),
        .d_pos1(d_pos1), .d_pslot1(d_pslot1), .d_L(d_L), .d_L1(d_L1), .u_done(u_done), .u_fault(u_fault),
        .wr_quiet(wr_quiet), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_pos(cpl_pos),
        .cpl_job(cpl_job), .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles),
        .cpl_ntok(cpl_ntok), .cpl_toks(cpl_toks));
`endif
    reg [127:0] img [0:NW-1];
    reg [95:0] vmi [0:CONF_NVMI-1];
    reg [255:0] ex [0:NEXP-1];
    reg [31:0] cfg [0:NCASE*12-1];
    reg [95:0] vmw [0:4095];
    reg [63:0] vm0 [0:SEQ_NVM0-1];
    integer nvmw = 0;
    initial begin
`ifdef SEQ_CONF
        $readmemh("hgi_seq_image_conf.mem", img);
        $readmemh("hgi_seq_expect_conf.mem", ex); $readmemh("hgi_seq_cfg_conf.mem", cfg);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmi_conf.mem", vmi);
        for (nvmw = 0; nvmw < NCASE*16; nvmw = nvmw + 1) tks[nvmw] = 0;
`elsif SEQ_STALE
        $readmemh("hgi_seq_image.mem", img);
        $readmemh("hgi_seq_expect_stale.mem", ex); $readmemh("hgi_seq_cfg_stale.mem", cfg); $readmemh("hgi_seq_toks_stale.mem", tks);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmw_stale.mem", vmw);
`else
        $readmemh("hgi_seq_image.mem", img);
        $readmemh("hgi_seq_expect.mem", ex); $readmemh("hgi_seq_cfg.mem", cfg); $readmemh("hgi_seq_toks.mem", tks);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmw.mem", vmw);
`endif
        $readmemh("hgi_seq_vm0.mem", vm0);
    end
    // ---- HBM: the image at byte PAGE*4096 (word w at +16 w); in-order sector responses after 2..8 cycles
    localparam [39:0] IMG = PAGE * 4096;
    function automatic [127:0] word_at(input [39:0] a);
        reg signed [41:0] w; begin w = ($signed({2'b0, a}) - $signed({2'b0, IMG})) / 16;
            word_at = (w >= 0 && w < NW) ? img[w] : 128'hDEAD; end
    endfunction
    reg [39:0] fq [0:63]; integer fqh = 0, fqn = 0, fdel = 0;
    always @(posedge clk) begin
        f_req_rdy <= ($urandom % 3) != 0;
        if (f_req_v && f_req_rdy) begin fq[(fqh + fqn) % 64] = f_req_addr; fqn = fqn + 1; end
        f_rsp_v <= 1'b0;
        if (fqn > 0) begin
            if (fdel > 0) fdel = fdel - 1;
            else begin
                f_rsp_v <= 1'b1; f_rsp_data <= {word_at(fq[fqh] + 16), word_at(fq[fqh])}; fqh = (fqh + 1) % 64; fqn = fqn - 1;
                fdel = $urandom % 3;
            end
        end
    end
    // ---- VM: the bench's memory; a unit's writes land at its RETIRE (vmw: dispatch index -> addr, value)
    reg [31:0] vm [0:262143];
    integer vdl = 0; reg vpend = 0; reg [17:0] va;
    always @(posedge clk) begin
        vr_rdy <= ($urandom % 2) != 0;
        vr_rsp_v <= 1'b0;
        if (vr_v && vr_rdy && !vpend) begin vpend = 1; va = vr_addr; vdl = 1 + $urandom % 4; end
        else if (vpend) begin
            vdl = vdl - 1;
            if (vdl == 0) begin vr_rsp_v <= 1'b1; vr_rsp_data <= vm[va]; vpend = 0; end
        end
    end
    // ---- units: accept, check, retire after a delay
    integer outst [0:15]; integer pend [0:15][0:31]; integer pdi [0:15][0:31]; integer pn [0:15];
    integer ei = 0, nd = 0, fails = 0, w, k, uu, j, fault_at = -1;
    reg [3:0] cu;
    task automatic retire_writes(input integer di);
        integer q; begin
            for (q = 0; q < 4096; q = q + 1)
                if (vmw[q][95:64] == di) vm[vmw[q][49:32]] = vmw[q][31:0];
        end
    endtask
    always @(posedge clk) begin
        u_rdy <= $urandom; u_done <= 0; u_fault <= 0;
        for (uu = 1; uu < 16; uu = uu + 1) begin
            for (k = 0; k < pn[uu]; k = k + 1) pend[uu][k] = pend[uu][k] - 1;
            if (pn[uu] > 0 && pend[uu][0] <= 0) begin
                u_done[uu] <= 1'b1; outst[uu] = outst[uu] - 1;
                retire_writes(pdi[uu][0]);
                for (k = 0; k < 31; k = k + 1) begin pend[uu][k] = pend[uu][k + 1]; pdi[uu][k] = pdi[uu][k + 1]; end
                pn[uu] = pn[uu] - 1;
            end
        end
        if (|(u_v & u_rdy)) begin
            cu = d_hdr[127:124];
            if (u_v !== (16'd1 << cu)) begin $display("FAIL dispatch port %h for unit %0d", u_v, cu); fails = fails + 1; end
            for (w = 1; w < 16; w = w + 1) if (d_hdr[102 + w] && outst[w] != 0) begin
                $display("FAIL wait rule: unit %0d dispatched while unit %0d has %0d outstanding", cu, w, outst[w]); fails = fails + 1; end
            if (ei + 11 > NEXP) begin $display("FAIL extra dispatch %0d", nd); fails = fails + 1; end
            else begin
                if (ex[ei][3:0] !== cu || ex[ei][19:4] !== d_L || ex[ei][35:20] !== d_L1 || ex[ei][56:36] !== d_pos1 ||
                    ex[ei][77:57] !== d_pslot1 || ex[ei + 1][127:0] !== d_hdr || ex[ei + 2] !== d_sut ||
                    ex[ei + 10][146:0] !== d_n) begin
                    $display("FAIL dispatch %0d unit %0d/%0d L %0d/%0d L1 %0d/%0d pos1 %0d pslot1 %0d hdr %b sut %b n %b",
                        nd, cu, ex[ei][3:0], d_L, ex[ei][19:4], d_L1, ex[ei][35:20], d_pos1 === ex[ei][56:36],
                        d_pslot1 === ex[ei][77:57], ex[ei+1][127:0] === d_hdr, ex[ei+2] === d_sut, ex[ei+10][146:0] === d_n);
                    fails = fails + 1;
                end
                for (j = 0; j < 7; j = j + 1) if (ex[ei + 3 + j] !== d_desc[j*256 +: 256]) begin
                    $display("FAIL dispatch %0d unit %0d descriptor %0d: base %h/%h n %h/%h", nd, cu, j,
                             d_desc[j*256 + 8 +: 40], ex[ei + 3 + j][47:8], d_desc[j*256 + 48 +: 20], ex[ei + 3 + j][67:48]);
                    fails = fails + 1;
                end
            end
            ei = ei + 11;
            outst[cu] = outst[cu] + 1;
            pend[cu][pn[cu]] = (cu == 9 || cu == 7) ? 40 + $urandom % 21 : $urandom % 21; pdi[cu][pn[cu]] = nd;
            pn[cu] = pn[cu] + 1;
            if (nd == fault_at) u_fault[cu] <= 1'b1;
            nd = nd + 1;
        end
    end
    integer c, n0, t, a;
    function automatic toks_ok(input integer cc);
        integer q; begin toks_ok = 1;
            for (q = 0; q < 16; q = q + 1) if (cpl_toks[q*18 +: 18] !== tks[cc*16 + q][17:0]) toks_ok = 0; end
    endfunction
    initial begin
        for (k = 0; k < 16; k = k + 1) begin outst[k] = 0; pn[k] = 0; end
        for (a = 0; a < 262144; a = a + 1) vm[a] = 0;
        rank = 0;
        repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            for (a = 0; a < SEQ_NVM0; a = a + 1) vm[vm0[a][49:32]] = vm0[a][31:0];
            for (a = 0; a < 16; a = a + 1) vm[32'hF000 + a] = 0;
            for (a = 0; a < 16; a = a + 1) vm[32'hF010 + a] = 0;
            vm[32'hF000] = 3; vm[32'hF100] = 1 << 21;
`ifdef SEQ_CONF
            for (a = 0; a < 262144; a = a + 1) vm[a] = 0;
            for (a = 0; a < CONF_NVMI; a = a + 1) if (vmi[a][95:64] == c) vm[vmi[a][49:32]] = vmi[a][31:0];
`endif
            md_d = {32'd1, PAGE, 32'd0, 32'd0, cfg[c*12 + 0]};
            vocab = cfg[c*12 + 4]; ctxmax = cfg[c*12 + 5]; rank = cfg[c*12 + 3];
`ifdef SEQ_CP
            cfg_load(c, cfg[c*12 + 4], cfg[c*12 + 5]);
`endif
            fault_at = (cfg[c*12 + 9] == 32'hFFFF) ? -1 : cfg[c*12 + 10] + cfg[c*12 + 9];
            n0 = nd; ei = cfg[c*12 + 10] * 11;
            if (nd != cfg[c*12 + 10]) begin $display("FAIL case %0d starts at dispatch %0d, expected %0d", c, nd, cfg[c*12 + 10]);
                fails = fails + 1; nd = cfg[c*12 + 10]; n0 = nd; end
            @(negedge clk); while (!db_rdy) @(negedge clk);
            db_token = cfg[c*12 + 1]; db_pos = cfg[c*12 + 2]; db_v = 1; @(negedge clk); db_v = 0;
            t = 0; while (!cpl_v && t < 400000) begin @(negedge clk); t = t + 1; end
            if (!cpl_v) begin $display("FAIL case %0d: no completion (dispatches %0d)", c, nd - n0); fails = fails + 1; end
            else if (cpl_token !== cfg[c*12 + 7][17:0] || cpl_status !== cfg[c*12 + 8][3:0] || nd - n0 !== cfg[c*12 + 6]) begin
                $display("FAIL case %0d: token %0d/%0d status %0d/%0d dispatches %0d/%0d", c, cpl_token, cfg[c*12 + 7],
                         cpl_status, cfg[c*12 + 8], nd - n0, cfg[c*12 + 6]); fails = fails + 1;
            end else if (cpl_ntok !== cfg[c*12 + 11][4:0] || (cpl_status == 0 && !toks_ok(c))) begin
                $display("FAIL case %0d: TOKX ntok %0d/%0d or tokens", c, cpl_ntok, cfg[c*12 + 11]); fails = fails + 1;
            end else $display("SEQ case %0d: %0d dispatches, token %0d status %0d, %0d cycles", c, nd - n0, cpl_token,
                              cpl_status, cpl_cycles);
            repeat ($urandom % 3) @(negedge clk);
            cpl_rdy = 1; @(negedge clk); cpl_rdy = 0;
            t = 0; while (busy && t < 2000) begin @(negedge clk); t = t + 1; end
            nd = cfg[c*12 + 10] + cfg[c*12 + 6];
        end
        if (fails == 0) $display("HGI_SEQ PASS cases=%0d dispatches=%0d", NCASE, nd);
        else $display("HGI_SEQ FAIL %0d", fails);
        $finish;
    end
endmodule
