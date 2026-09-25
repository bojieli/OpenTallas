`timescale 1ns/1ps
// Token-level simulation top of the V4.1 HBM comparator: the V4.1 hardwired
// decode core (W_HBM = 1) with its quantised FP8/FP4 weights in HBM behind the
// QE weight streamer (rtl/hdc/hbm/ot_hdc_qstream.sv) and the timing-faithful
// HBM model (rtl/hdc/kv/ot_hdc_hbm_model.sv, per-channel ready).  There is no
// quantised ROM: the words come from the HBM image and the fetch list of
// tools/hdc_program_v41.py --hbm (hbm_q.hex, qlist.hex); the ROM image is loaded
// only to CHECK every word the streamer delivers.  The other stores (BF16 ME
// weights, HE weights, Engram table, constants, KV cache) are as in
// tb_hdc_core_v41.sv.  Driven by Verilator (rtl/test/hdc_core_v41_whbm_harness.cpp).
// +QLEAD=n, +QRATE=r: the streamer's lead (cycles) and guaranteed rate (words per
// cycle x 256).
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
module tb_hdc_core_v41_whbm #(
    parameter integer NPC = 8,
    parameter integer LWIN = 10,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3;
    localparam integer HROM_WORDS = 1 << 19;
    localparam integer WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19, CROM_WORDS = 1 << 15;
    localparam integer KV_WORDS = 32768, VM_ELEMS = 65536, VOCAB = 4040, PROG_WORDS = 1 << PAW;

    reg [G*W*16-1:0]    wrom [0:WROM_WORDS-1];
    reg [HNL*32-1:0]    hrom [0:HROM_WORDS-1];
    reg [BL*QLB-1:0]    qrom [0:QROM_WORDS-1];     // CHECK ONLY: the ROM image
    localparam integer SPW = BL * QLB / 256, HMEM = 1 << 20, LAW = 12;
    reg [127:0]         qlist [0:(1 << LAW)-1];
    reg [255:0]         qwin [0:SPW-1][0:(1 << LWIN)-1];
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
    wire qrom_re; wire [AW-1:0] qrom_addr; wire [BL*QLB-1:0] qrom_q;
    wire qd_v, q_ok, wrel_v; wire [AW-1:0] qd_wbase; wire [7:0] qd_nb; wire [NW-1:0] qd_tiles;
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

    ot_hdc_core_v41 #(.W_HBM(1)) dut (
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
        .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qd_v(qd_v), .qd_wbase(qd_wbase), .qd_nb(qd_nb), .qd_tiles(qd_tiles), .q_ok(q_ok), .wrel_v(wrel_v));

    // ---- QE weight streamer, its window and fetch list, HBM ------------------------------------
    reg  [15:0] qlead, qrate;
    wire l_re; wire [LAW-1:0] l_addr; reg [127:0] l_q;
    wire xi_re; wire [AW-1:0] xi_addr; reg [31:0] xi_q;
    wire [SPW-1:0] qw_we; wire [SPW*LWIN-1:0] qw_waddr; wire [BL*QLB-1:0] qw_wdata;
    wire qw_re; wire [LWIN-1:0] qw_raddr; reg [BL*QLB-1:0] qw_q;
    wire hq_v, hq_rdy; wire [23:0] hq_addr; wire [5:0] hq_len; wire [LWIN-1:0] hq_tag;
    wire [NPC-1:0] hr_v, hr_rdy, pc_room; wire [NPC*LWIN-1:0] hr_tag; wire [NPC*5-1:0] hr_beat;
    wire [NPC*256-1:0] hr_data;
    wire qs_fault; wire [3:0] qs_why; wire [31:0] qs_fetched, qs_consumed;
    ot_hdc_qstream #(.BL(BL), .QLB(QLB), .AW(AW), .HAW(24), .NW(NW), .LWIN(LWIN), .NPC(NPC), .LENW(6),
                     .BEATW(5), .LAW(LAW)) u_qs (
        .clk(clk), .rst_n(rst_n), .cfg_base(24'd0), .cfg_lead(qlead), .cfg_rate(qrate),
        .tok_start(start), .pos(pos),
        .l_re(l_re), .l_addr(l_addr), .l_q(l_q), .vi_re(xi_re), .vi_addr(xi_addr), .vi_q(xi_q), .wrel_v(wrel_v),
        .qd_v(qd_v), .qd_nb(qd_nb), .qd_tiles(qd_tiles), .q_ok(q_ok),
        .qr_re(qrom_re), .qr_addr(qrom_addr), .qr_q(qrom_q),
        .win_we(qw_we), .win_waddr(qw_waddr), .win_wdata(qw_wdata), .win_re(qw_re), .win_raddr(qw_raddr),
        .win_q(qw_q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag), .hq_room(pc_room),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(qs_fault), .fault_why(qs_why), .st_fetched(qs_fetched), .st_consumed(qs_consumed));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(HMEM), .TAGW(LWIN), .LENW(6), .BEATW(5),
                       .CLK_PS(CLK_PS), .PC_RDY(1), .PC_ROOM(16)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .pc_room(pc_room), .req_we(1'b0),
        .req_addr(hq_addr), .req_len(hq_len), .req_tag(hq_tag), .req_wdata(256'd0),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));
    integer qb;
    always @(posedge clk) begin
        if (l_re) l_q <= qlist[l_addr];
        if (xi_re) xi_q <= vm[xi_addr[15:0]];
        for (qb = 0; qb < SPW; qb = qb + 1) begin
            if (qw_re) qw_q[qb*256 +: 256] <= qwin[qb][qw_raddr];
            if (qw_we[qb]) qwin[qb][qw_waddr[qb*LWIN +: LWIN]] <= qw_wdata[qb*256 +: 256];
        end
    end
    // every delivered word against the ROM image
    reg qchk_v; reg [AW-1:0] qchk_a;
    integer q_bad = 0, q_words = 0, q_stall = 0, q_ops = 0;
    always @(posedge clk) begin
        qchk_v <= qrom_re; qchk_a <= qrom_addr;
        if (qchk_v) begin
            q_words <= q_words + 1;
            if (qrom_q !== qrom[qchk_a[15:0]]) begin
                if (q_bad < 3) $display("QBAD cyc=%0d addr=%0d", cycles, qchk_a);
                q_bad = q_bad + 1;
            end
        end
        if (qd_v) q_ops <= q_ops + 1;
        //: cycles the sequencer waits only for the QE window
        if (dut.st == 6 && !dut.d_skip && dut.d_unit == 3 && dut.waited && dut.unit_ready && !dut.q_gate)
            q_stall <= q_stall + 1;
    end
    task qstats;
        integer p, sum_rd, sum_act, sum_conf, sum_ref;
        begin
            sum_rd = 0; sum_act = 0; sum_conf = 0; sum_ref = 0;
            for (p = 0; p < NPC; p = p + 1) begin
                sum_rd = sum_rd + u_hbm.st_rd[p]; sum_act = sum_act + u_hbm.st_act[p];
                sum_conf = sum_conf + u_hbm.st_conf[p]; sum_ref = sum_ref + u_hbm.st_ref[p];
            end
            $display("QSTREAM q_stall_cycles=%0d q_ops=%0d q_words=%0d q_bad=%0d qs_fault=%0d qs_why=%0d fetched=%0d consumed=%0d hbm_reads=%0d acts=%0d row_conflicts=%0d refreshes=%0d rd_lat_avg_ps=%0d rd_lat_max_ps=%0d",
                     q_stall, q_ops, q_words, q_bad, qs_fault, qs_why, qs_fetched, qs_consumed, sum_rd, sum_act,
                     sum_conf, sum_ref, (sum_rd > 0) ? u_hbm.st_rd_lat_sum / sum_rd : 0, u_hbm.st_rd_lat_max);
        end
    endtask

    // synchronous-read memories
    integer l, q;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
        if (ewrom_re) ewrom_q <= wrom[ewrom_addr[18:0]];
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
        $readmemh({dir, "/qlist.hex"}, qlist);
        for (i = 0; i < HMEM; i = i + 1) u_hbm.mem[i] = 256'd0;
        $readmemh({dir, "/hbm_q.hex"}, u_hbm.mem);
        if (!$value$plusargs("QLEAD=%d", qlead)) qlead = 512;
        if (!$value$plusargs("QRATE=%d", qrate)) qrate = 0;
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
                qstats();
                if (gen_bad == 0 && bad_vm == 0 && bad_kv == 0 && !qs_fault && q_bad == 0) $display("PASS");
                else $display("FAIL");
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
            qstats();
            if (next_token == expect_tok && !fault && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 && !qs_fault && q_bad == 0)
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
        if (qs_fault) begin
            $display("STREAM_FAULT cyc=%0d pc=%0d why=%0d", cycles, dut.pc, qs_why);
            qstats();
            $display("FAIL");
            $finish;
        end
        if (cyc > 50000000) begin
            $display("TIMEOUT pc=%0d st=%0d idles=%b", dut.pc, dut.st, dut.idles);
            $finish;
        end
    end
endmodule
