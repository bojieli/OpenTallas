`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM-array packages as 4-die tensor groups (docs/ARCHITECTURE_ATLAS.html
// 6.6-6.8): every package is D decode cores (ot_hdc_core), one per die, each
// behind its tensor-group sequencer (rtl/rom/ot_rom_tp_seq.sv), the one-shot
// collective unit joining the dies over UCIe link models
// (rtl/rom/ot_rom_oneshot_allreduce.sv), and ONE package controller
// (rtl/rom/ot_rom_pkg_ctrl.sv) that presents the group to the array as a
// single core: its start goes to every die, its done is every die's done,
// the received hidden state is written into every die's vector memory, and
// the sent one is read from die 0's.
//
// NODES = 1: the package holds the whole model (embedding, 4 layers, lm_head);
//            its RESULT loops back to itself over a package link.
// NODES = L: a ring of L packages, package n holding layer n (package 0 the
//            embedding too, the last lm_head), exactly the layer pipeline of
//            rtl/test/tb_hdc_array.sv with a tensor group in place of each core.
//
// Checks (all bit for bit against tools/hdc_program.py --tp, the ISA-level
// tensor group that equals tools/hdc_golden.Model.decode_token_tp):
//   * every step of every user at the lm_head package: each die's {token,
//     logit} equals the expectation of that position (+DIR/expect_steps.hex),
//     and the four dies agree;
//   * every generated token against the torch oracle's (package 0);
//   * after the run, every die's KV cache, for every user, against the ISA
//     group's end-to-end cache (a package of the ring holds its layer only);
//     with NODES = 1 also every die's whole vector memory;
//   * no core, sequencer, collective or protocol fault.
// ---------------------------------------------------------------------------
module tb_hdc_package_tp #(
    parameter integer G = 4,
    parameter integer D = 4,             // dies per package (the tensor group)
    parameter integer NODES = 1,
    parameter integer USERS = 1,
    parameter integer LAT = 11,          // UCIe hop, cycles
    parameter integer BPC = 3600,        // UCIe bytes per cycle per die pair and direction
    parameter integer CDEPTH = 16,       // collective receive FIFO words
    parameter integer KVHALF = 256,      // KV words of the K half (one die)
    parameter integer KVLAYER = 64       // KV words per layer within a half
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, DAW = 6, TAGW = 32;
    localparam integer WROM_WORDS = 16384, CROM_WORDS = 4096;
    localparam integer KVW = 1024;
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer FLIT = 512, XWORDS = 8, MAXU = 16;
    localparam integer LINK_CH = 60;     // package-to-package channel cycles (tb_hdc_array)
    localparam integer RB = $clog2(D);

    reg [G*W*16-1:0] wrom [0:D*WROM_WORDS-1];
    reg [63:0]       crom [0:D*CROM_WORDS-1];
    reg [NW-1:0]     prompt [0:255];
    reg [NW-1:0]     gold [0:255];
    reg [63:0]       estep [0:255];
    reg [31:0]       evm [0:D*VM_ELEMS-1];
    reg [31:0]       ekv [0:D*KVW*W-1];
    reg [8*512-1:0]  dir;
    integer n_prompt = 16, n_gen = 3, n_users = USERS;
    reg rst_n = 1'b0;
    reg fin_d = 1'b0;
    integer cyc = 0;

    wire [NODES-1:0] tx_v, tx_r, tx_l, rx_v, rx_r, rx_l;
    wire [NODES*FLIT-1:0] tx_d, rx_d;
    wire [NODES*D-1:0] cfault_w, sfault_w, ufault_w;
    wire [NODES-1:0] pfault_w, busy_w;
    wire [7:0] users_done;
    wire tok_v; wire [7:0] tok_u; wire [NW-1:0] tok_p, tok_i;
    wire [NODES*32-1:0] l_stalls, c_stalls;

    genvar n, d;
    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_link
            ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                              .CREDITS(32)) u_link (
                .clk(clk), .rst_n(rst_n),
                .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                .out_valid(rx_v[(n + 1) % NODES]), .out_ready(rx_r[(n + 1) % NODES]),
                .out_data(rx_d[((n + 1) % NODES)*FLIT +: FLIT]), .out_last(rx_l[(n + 1) % NODES]),
                .credit_stalls(l_stalls[n*32 +: 32]));
        end
    endgenerate

    integer gen_n [0:USERS-1];
    integer kv_bad = 0, vm_bad = 0;
    reg check_now = 1'b0, check_d = 1'b0;
    integer bad = 0, finished = 0, gen_total = 0, steps_checked = 0;

    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_node
            localparam integer LAST = (n == NODES - 1);
            localparam [7:0] D1 = 8'h30 + n / 10;
            localparam [7:0] D0 = 8'h30 + n % 10;

            // package controller <-> tensor group
            wire          start, grp_done;
            wire [NW-1:0] token, pos;
            wire [AW-1:0] kv_base;
            wire          c_we, c_re; wire [7:0] c_waddr, c_raddr;
            wire [FLIT-1:0] c_wdata; reg [FLIT-1:0] c_rq;
            wire          pr_re; wire [7:0] pr_user; wire [NW-1:0] pr_pos; reg [NW-1:0] pr_q;
            wire [D-1:0]  s_done;
            wire [D*NW-1:0] s_tok; wire [D*32-1:0] s_val;
            wire [D-1:0]  s_cbusy;
            assign grp_done = &s_done;

            // collective unit
            wire [D-1:0] cv, crd, cl, cm, rv, rl, re_, uf;
            wire [D*FLIT-1:0] cd, rd;
            wire [D*TAGW-1:0] ct;
            wire [D*RB-1:0] rr;
            wire [D*3-1:0] ufc;
            ot_rom_oneshot_allreduce #(.N(D), .LANES(FLIT / 32), .TAGW(TAGW), .DEPTH(CDEPTH), .LAT(LAT),
                                       .BPC_NUM(BPC)) u_coll (
                .clk(clk), .rst_n(rst_n),
                .in_valid(cv), .in_ready(crd), .in_data(cd), .in_last(cl), .in_mode(cm), .in_tag(ct),
                .out_valid(rv), .out_data(rd), .out_last(rl), .out_rank(rr), .out_err(re_),
                .fault(uf), .fault_code(ufc), .link_stalls(c_stalls[n*32 +: 32]));
            assign ufault_w[n*D +: D] = uf;

            wire t_v; wire [7:0] t_u; wire [NW-1:0] t_p, t_i; wire [7:0] u_done;
            ot_rom_pkg_ctrl #(.PKG_ID(n), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(8), .MAXU(MAXU), .KVW(KVW),
                              .XWORDS(XWORDS), .RXB(0), .TXB(0), .SOURCE(n == 0),
                              .RESULT_PARTS(1), .SEND_HIDDEN(!LAST), .HID_DEST((n + 1) % NODES),
                              .SEND_RESULT(LAST), .RES_DEST(0), .COMBINE_IN(0), .ROW0(0)) ctrl (
                .clk(clk), .rst_n(rst_n),
                .cfg_users(n_users[7:0]), .cfg_prompt_len(n_prompt[NW-1:0]), .cfg_gen_len(n_gen[NW-1:0]),
                .in_valid(rx_v[n]), .in_ready(rx_r[n]), .in_data(rx_d[n*FLIT +: FLIT]), .in_last(rx_l[n]),
                .out_valid(tx_v[n]), .out_ready(tx_r[n]), .out_data(tx_d[n*FLIT +: FLIT]), .out_last(tx_l[n]),
                .core_start(start), .core_token(token), .core_pos(pos), .core_done(grp_done),
                .core_next_token(s_tok[0 +: NW]), .core_next_val(s_val[0 +: 32]), .kv_base(kv_base),
                .vm_we(c_we), .vm_waddr(c_waddr), .vm_wdata(c_wdata), .vm_re(c_re), .vm_raddr(c_raddr), .vm_rq(c_rq),
                .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
                .core_busy(busy_w[n]), .tok_valid(t_v), .tok_user(t_u), .tok_pos(t_p), .tok_id(t_i),
                .users_done(u_done), .proto_fault(pfault_w[n]));
            if (n == 0) begin : g_obs
                assign tok_v = t_v; assign tok_u = t_u; assign tok_p = t_p; assign tok_i = t_i;
                assign users_done = u_done;
            end
            always @(posedge clk) if (pr_re) pr_q <= prompt[pr_pos[7:0]];

            for (d = 0; d < D; d = d + 1) begin : g_die
                reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
                reg [63:0]           desc [0:63];
                reg [31:0]           vm [0:VM_ELEMS-1];
                reg [W*32-1:0]       kv [0:USERS*KVW-1];

                wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
                wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
                wire crom_re; wire [AW-1:0] crom_addr; reg [63:0] crom_q;
                wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; reg [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
                wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
                wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
                reg [31:0] va_q, vb_q, vc_q;
                wire vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
                wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
                wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [31:0] vw_su_data, vw_rd_data;
                wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
                wire [31:0] cycles;
                wire core_start, core_done, core_fault;
                wire [NW-1:0] core_tok, core_pos, core_ntok; wire [31:0] core_nval;
                wire [PAW-1:0] prog_base;
                wire desc_re; wire [DAW-1:0] desc_addr; reg [63:0] desc_q;
                wire s_vre, s_vwe; wire [7:0] s_vraddr, s_vwaddr; wire [FLIT-1:0] s_vwdata; reg [FLIT-1:0] s_vrq;

                ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW)) core (
                    .clk(clk), .rst_n(rst_n), .start(core_start), .token(core_tok), .pos(core_pos),
                    .done(core_done), .next_token(core_ntok), .next_val(core_nval),
                    .cycles(cycles), .fault(core_fault),
                    .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
                    .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
                    .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
                    .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
                    .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
                    .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
                    .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
                    .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
                    .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
                    .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
                    .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
                    .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
                    .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
                    .kvd_v(), .kvd_wbase(), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_jsh(), .kvd_tiles(), .kvd_k(),
                    .kvd_nout(), .kvd_kindk(), .kvd_pos(), .kv_ok(1'b1));
                assign cfault_w[n*D + d] = core_fault;

                ot_rom_tp_seq #(.N(D), .NW(NW), .PAW(PAW), .VWA(8), .DAW(DAW), .FW(FLIT), .TAGW(TAGW)) seq (
                    .clk(clk), .rst_n(rst_n),
                    .start(start), .token(token), .pos(pos),
                    .done(s_done[d]), .next_token(s_tok[d*NW +: NW]), .next_val(s_val[d*32 +: 32]),
                    .fault(sfault_w[n*D + d]), .coll_busy(s_cbusy[d]),
                    .core_start(core_start), .core_token(core_tok), .core_pos(core_pos), .core_done(core_done),
                    .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault),
                    .prog_base(prog_base), .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
                    .vm_re(s_vre), .vm_raddr(s_vraddr), .vm_rq(s_vrq),
                    .vm_we(s_vwe), .vm_waddr(s_vwaddr), .vm_wdata(s_vwdata),
                    .c_valid(cv[d]), .c_ready(crd[d]), .c_data(cd[d*FLIT +: FLIT]), .c_last(cl[d]), .c_mode(cm[d]),
                    .c_tag(ct[d*TAGW +: TAGW]),
                    .r_valid(rv[d]), .r_data(rd[d*FLIT +: FLIT]), .r_last(rl[d]), .r_rank(rr[d*RB +: RB]),
                    .r_err(re_[d]));

                integer k, q, l;
                reg [8*512-1:0] pdir;
                localparam [7:0] DC = 8'h30 + d;
                initial begin
                    if (!$value$plusargs("DIR=%s", pdir)) pdir = ".";
                    if (NODES == 1) begin
                        $readmemh({pdir, "/prog_d", DC, ".hex"}, prog);
                        $readmemh({pdir, "/desc_d", DC, ".hex"}, desc);
                    end else begin
                        $readmemh({pdir, "/prog_stage", D1, D0, "_d", DC, ".hex"}, prog);
                        $readmemh({pdir, "/desc_stage", D1, D0, "_d", DC, ".hex"}, desc);
                    end
                    for (k = 0; k < VM_ELEMS; k = k + 1) vm[k] = 32'd0;
                    for (k = 0; k < USERS * KVW; k = k + 1) kv[k] = {(W*32){1'b0}};
                end
                wire [AW-1:0] kv_wword = (kv_waddr >> 4) + kv_base;

                always @(posedge clk) begin
                    if (prog_re) prog_q <= prog[prog_base + prog_addr];
                    if (desc_re) desc_q <= desc[desc_addr];
                    if (wrom_re) wrom_q <= wrom[d*WROM_WORDS + wrom_addr[13:0]];
                    if (crom_re) crom_q <= crom[d*CROM_WORDS + crom_addr[11:0]];
                    for (q = 0; q < G; q = q + 1)
                        if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: AW] + kv_base];
                    for (q = 0; q < G; q = q + 1)
                        if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
                    if (va_re) va_q <= vm[va_addr[11:0]];
                    if (vb_re) vb_q <= vm[vb_addr[11:0]];
                    if (vc_re) vc_q <= vm[vc_addr[11:0]];
                    if (kv_we) kv[kv_wword][32*kv_waddr[3:0] +: 32] <= kv_wdata;
                    for (q = 0; q < G; q = q + 1)
                        if (vw_me_we[q])
                            for (l = 0; l < W; l = l + 1)
                                if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
                    if (vw_su_we) vm[vw_su_addr[11:0]] <= vw_su_data;
                    if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
                    // package controller: received flits into every die, sent ones from die 0
                    if (c_we) for (l = 0; l < W; l = l + 1) vm[{c_waddr, 4'b0} + l] <= c_wdata[32*l +: 32];
                    if (d == 0 && c_re) for (l = 0; l < W; l = l + 1) c_rq[32*l +: 32] <= vm[{c_raddr, 4'b0} + l];
                    // sequencer: collective words
                    if (s_vre) for (l = 0; l < W; l = l + 1) s_vrq[32*l +: 32] <= vm[{s_vraddr, 4'b0} + l];
                    if (s_vwe) for (l = 0; l < W; l = l + 1) vm[{s_vwaddr, 4'b0} + l] <= s_vwdata[32*l +: 32];
                end

                // per-die accounting: cycles the die is busy with a step, and in collectives
                reg [63:0] busy_cycles = 0, coll_cycles = 0;
                reg started = 1'b0, checked = 1'b0;
                integer uu, ww, ll, layer, kb, vb;
                reg [31:0] exp;
                always @(posedge clk) begin
                    if (start) started <= 1'b1;
                    if (started && !s_done[d]) busy_cycles <= busy_cycles + 1;
                    if (s_cbusy[d]) coll_cycles <= coll_cycles + 1;
                    if (check_now && !checked) begin
                        checked <= 1'b1;
                        kb = 0; vb = 0;
                        // every user's KV slice against the ISA group's end-to-end cache
                        // (a package of the ring holds its own layer only)
                        for (uu = 0; uu < n_users; uu = uu + 1)
                            for (ww = 0; ww < 2 * KVHALF; ww = ww + 1)
                                for (ll = 0; ll < W; ll = ll + 1) begin
                                    layer = (ww % KVHALF) / KVLAYER;
                                    exp = (NODES == 1 || layer == n) ? ekv[d*KVW*W + ww*W + ll] : 32'd0;
                                    if (kv[uu*KVW + ww][32*ll +: 32] !== exp) kb = kb + 1;
                                end
                        if (NODES == 1)
                            for (ww = 0; ww < VM_ELEMS; ww = ww + 1)
                                if (vm[ww] !== evm[d*VM_ELEMS + ww]) vb = vb + 1;
                        kv_bad = kv_bad + kb; vm_bad = vm_bad + vb;
                        $display("DIE node=%0d die=%0d busy_cycles=%0d coll_cycles=%0d kv_mismatches=%0d vm_mismatches=%0d",
                                 n, d, busy_cycles, coll_cycles, kb, vb);
                    end
                end
            end

            // the position of the running step (the controller's start)
            reg [NW-1:0] pos_r = 0;
            always @(posedge clk) if (start) pos_r <= pos;
            // step check at the lm_head package: every die's {token, logit} of the step
            reg grp_done_d = 1'b0;
            integer dd;
            always @(posedge clk) begin
                grp_done_d <= grp_done;
                if (LAST && rst_n && grp_done && !grp_done_d) begin
                    for (dd = 0; dd < D; dd = dd + 1)
                        if (s_tok[dd*NW +: NW] != estep[pos_r][32 +: 16] ||
                            s_val[dd*32 +: 32] != estep[pos_r][31:0]) begin
                            bad = bad + 1;
                            $display("STEP_MISMATCH node=%0d die=%0d pos=%0d token=%0d logit=%08x expect token=%0d logit=%08x",
                                     n, dd, pos_r, s_tok[dd*NW +: NW], s_val[dd*32 +: 32],
                                     estep[pos_r][32 +: 16], estep[pos_r][31:0]);
                        end
                    steps_checked = steps_checked + 1;
                end
            end
            // input token of every step at package 0
            always @(posedge clk) if (n == 0 && rst_n && start && token != estep[pos][48 +: 16]) begin
                bad = bad + 1;
                $display("INPUT_MISMATCH pos=%0d token=%0d expect=%0d", pos, token, estep[pos][48 +: 16]);
            end
        end
    endgenerate

    // -- generated tokens at package 0 ----------------------------------------------------
    integer i, u;
    always @(posedge clk) if (rst_n) begin
        if (tok_v && tok_p >= n_prompt - 1) begin
            if (tok_i != gold[gen_n[tok_u]]) begin
                bad = bad + 1;
                $display("MISMATCH user=%0d step=%0d got=%0d gold=%0d", tok_u, gen_n[tok_u], tok_i, gold[gen_n[tok_u]]);
            end
            $display("GEN user=%0d pos=%0d token=%0d cycle=%0d", tok_u, tok_p, tok_i, cyc);
            gen_n[tok_u] = gen_n[tok_u] + 1; gen_total = gen_total + 1;
            if (gen_n[tok_u] == n_gen) finished = finished + 1;
        end
    end

    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 3;
        if (!$value$plusargs("NUSERS=%d", n_users)) n_users = USERS;
        $readmemh({dir, "/wrom_d0.hex"}, wrom, 0 * WROM_WORDS);
        if (D > 1) $readmemh({dir, "/wrom_d1.hex"}, wrom, 1 * WROM_WORDS);
        if (D > 2) $readmemh({dir, "/wrom_d2.hex"}, wrom, 2 * WROM_WORDS);
        if (D > 3) $readmemh({dir, "/wrom_d3.hex"}, wrom, 3 * WROM_WORDS);
        $readmemh({dir, "/crom_d0.hex"}, crom, 0 * CROM_WORDS);
        if (D > 1) $readmemh({dir, "/crom_d1.hex"}, crom, 1 * CROM_WORDS);
        if (D > 2) $readmemh({dir, "/crom_d2.hex"}, crom, 2 * CROM_WORDS);
        if (D > 3) $readmemh({dir, "/crom_d3.hex"}, crom, 3 * CROM_WORDS);
        for (i = 0; i < D * KVW * W; i = i + 1) ekv[i] = 32'd0;
        $readmemh({dir, "/expect_vm_d0.hex"}, evm, 0 * VM_ELEMS);
        if (D > 1) $readmemh({dir, "/expect_vm_d1.hex"}, evm, 1 * VM_ELEMS);
        if (D > 2) $readmemh({dir, "/expect_vm_d2.hex"}, evm, 2 * VM_ELEMS);
        if (D > 3) $readmemh({dir, "/expect_vm_d3.hex"}, evm, 3 * VM_ELEMS);
        $readmemh({dir, "/expect_kv_d0.hex"}, ekv, 0 * KVW * W);
        if (D > 1) $readmemh({dir, "/expect_kv_d1.hex"}, ekv, 1 * KVW * W);
        if (D > 2) $readmemh({dir, "/expect_kv_d2.hex"}, ekv, 2 * KVW * W);
        if (D > 3) $readmemh({dir, "/expect_kv_d3.hex"}, ekv, 3 * KVW * W);
        $readmemh({dir, "/prompt.hex"}, prompt);
        $readmemh({dir, "/generated.hex"}, gold);
        $readmemh({dir, "/expect_steps.hex"}, estep);
        for (u = 0; u < USERS; u = u + 1) gen_n[u] = 0;
    end

    reg [31:0] l_stall_sum, c_stall_sum;
    always @(*) begin
        l_stall_sum = 0; c_stall_sum = 0;
        for (i = 0; i < NODES; i = i + 1) begin
            l_stall_sum = l_stall_sum + l_stalls[i*32 +: 32];
            c_stall_sum = c_stall_sum + c_stalls[i*32 +: 32];
        end
    end

    integer nd;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        fin_d <= (finished == n_users);
        if (fin_d) check_now <= 1'b1;
        check_d <= check_now;
        if (check_d) begin
            if (cfault_w != 0 || sfault_w != 0 || ufault_w != 0 || pfault_w != 0) begin
                bad = bad + 1;
                $display("FAULT core=%b seq=%b collective=%b protocol=%b", cfault_w, sfault_w, ufault_w, pfault_w);
            end
            $display("PKG_TP nodes=%0d dies=%0d users=%0d generated=%0d steps_checked=%0d mismatches=%0d kv_mismatches=%0d vm_mismatches=%0d total_cycles=%0d",
                     NODES, D, n_users, gen_total, steps_checked, bad, kv_bad, vm_bad, cyc);
            $display("USERS_DONE %0d", users_done);
            $display("LINK_STALLS %0d COLL_STALLS %0d", l_stall_sum, c_stall_sum);
            if (bad == 0 && kv_bad == 0 && vm_bad == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 20000000) begin $display("TIMEOUT finished=%0d", finished); $finish; end
    end
endmodule
