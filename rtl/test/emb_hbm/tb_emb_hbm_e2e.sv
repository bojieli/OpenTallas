`timescale 1ps/1ps
// End-to-end bench of the Qwen3-8B input embedding in attached HBM (emb-hbm 2026-10-08).
//
//   loader (x3 BOOT_WR / BOOT_END words)  ->  hub (ot_qwen_die_hub_emb_top: x3 skid, EMB class, gateway)
//   SU consumer (ot_qfd_su_embed_pf, CRD 32, unchanged RTL)  <- SU_STG relays ->  hub SU face (ea / eq)
//   hub <-> 4 links of LINK_STG registered stations each way (core clock, forwarded both ways)
//   -> ot_qfd_link_far (strip-end endpoint, class split) -> ot_qfd_emb_strip (one a stack, core clock, beside qfd_kvc)
//   -> strip-column stations (D(pc) each way, core clock) -> the PC's core <-> HBM crossing (ot_async_fifo, standing in
//      for qfd_cdc) -> 32 x (ot_qwen_ctrl_pc_emb [ot_hbm_r14_stream_pc_srow] + ot_qfd_emb_pcport [SECDED72] +
//      tb_emb_dram_pc JEDEC checker / sparse store) a stack, HBM controller clock: 128 pseudo-channels.
// The KV stream runs beside it (KVMODE 1: a layer descriptor posted, banks opened ahead, no go = the AR state when the
// embedding is fetched; 2: the stream reading continuously).
// Checks: every fetched row is BIT-EXACT at the consumer (the SU row buffer's 64 code words + BF16 scale against the
// golden Qwen3-8B W8 codes, and every one of the 4,096 decoded FP32 values the SU delivers); no response before the
// boot load is checked (gate); single-bit ECC errors corrected (ce counted), a double-bit error detected and the fetch
// failed closed (no delivery, poison fault); zero JEDEC violations; zero protocol faults.  Mutants must FAIL.
// Golden / image files: tools/emb_hbm_bench.py (Qwen3-8B safetensors -> the deployed W8 quantizer).
module tb_emb_hbm_e2e
    import ot_qfd_emb_pkg::*;
;
    parameter integer TWIN = 0;
    parameter integer MUT_STRIP = 0;          // 1 wrong row, 2 wrong scale lane, 3 ECC correction skipped
    parameter integer MUT_GW = 0;             // 4 boot gate ignored
    parameter integer KVMODE = 1;
    parameter integer LINK_STG = 72;
    parameter integer SU_STG = 13;          // r21c emb_a / emb_cr: 12 relay hops + the SU master's station
    parameter integer EQ_STG = 22;          // r21c emb: 21 relay hops + the SU master's station
    parameter integer ROW0 = 24427;
    parameter integer TWIN_ROFF = -149;
    parameter integer S_STARVE = 8;
    parameter integer CR = 128;
    parameter integer MAXTOK = 512;
    parameter integer MAXBOOT = 80000;
    localparam integer NPC = 32;
    localparam integer CKP = 833, HKP = 1024;
    // ---------------------------------------------------------------- clocks / reset
    reg ck = 0, hclk = 0, rst_n = 0;
    always begin #(CKP/2) ck = 1; #(CKP - CKP/2) ck = 0; end
    always begin #(HKP/2) hclk = 1; #(HKP/2) hclk = 0; end
    // ---------------------------------------------------------------- golden / image
    reg [280:0] bootm [0:MAXBOOT-1];
    reg [31:0] meta [0:15];
    reg [17:0] toks [0:MAXTOK-1];
    reg [511:0] gcode [0:MAXTOK*65-1];
    reg [31:0] gfp [0:MAXTOK*4096-1];
    integer NTOK, NBOOT, CE_IX, UE_IX;
    // ---------------------------------------------------------------- SU consumer
    reg go_in = 0, a_src = 0; reg [17:0] tok = 0;
    wire go_out, pend, su_fault;
    reg [63:0] su_va_re = 0; reg [64*24-1:0] su_va_addr = 0;
    wire [64*32-1:0] su_va_q; wire [63:0] va_re; wire [64*24-1:0] va_addr;
    wire s_ea_v, s_ea_kind; wire [23:0] s_ea_addr; wire s_ea_cr, s_eq_v; wire [511:0] s_eq_d;
    ot_qfd_su_embed_pf #(.SW(64), .AW(24), .NW(18), .HID(4096), .CRD(32), .FI(1)) u_su (.clk(ck), .rst_n(rst_n),
        .go_in(go_in), .a_src(a_src), .tok(tok), .f_in(1'b0), .go_out(go_out), .f_out(), .pend(pend),
        .su_va_re(su_va_re), .su_va_addr(su_va_addr), .su_va_q(su_va_q), .va_re(va_re), .va_addr(va_addr),
        .va_q({64*32{1'b0}}), .ea_v(s_ea_v), .ea_kind(s_ea_kind), .ea_addr(s_ea_addr), .ea_cr(s_ea_cr),
        .eq_v(s_eq_v), .eq_data(s_eq_d), .fault(su_fault));
    // SU <-> hub relays (the SU master's IS / OS stations included in SU_STG)
    wire h_ea_v, h_ea_kind; wire [23:0] h_ea_addr; wire h_ea_cr, h_eq_v; wire [511:0] h_eq_d;
    ot_hdc_delay #(.W(1), .D(SU_STG), .RESET(1)) u_r0 (.clk(ck), .rst_n(rst_n), .d(s_ea_v), .q(h_ea_v));
    ot_hdc_delay #(.W(25), .D(SU_STG)) u_r1 (.clk(ck), .rst_n(rst_n), .d({s_ea_kind, s_ea_addr}), .q({h_ea_kind, h_ea_addr}));
    ot_hdc_delay #(.W(1), .D(SU_STG), .RESET(1)) u_r2 (.clk(ck), .rst_n(rst_n), .d(h_ea_cr), .q(s_ea_cr));
    ot_hdc_delay #(.W(1), .D(EQ_STG), .RESET(1)) u_r4 (.clk(ck), .rst_n(rst_n), .d(h_eq_v), .q(s_eq_v));
    ot_hdc_delay #(.W(512), .D(EQ_STG)) u_r3 (.clk(ck), .rst_n(rst_n), .d(h_eq_d), .q(s_eq_d));
    // ---------------------------------------------------------------- hub
    reg x3_v = 0; reg [511:0] x3_d = 0; reg [10:0] x3_tag = 0; wire x3_cr;
    wire ar_v; wire [511:0] ar_d; wire hub_fault, emb_ready, emb_fault; wire [5:0] hub_fc; wire [7:0] emb_fc;
    wire [4*528-1:0] hl_o, hl_i;
    ot_qwen_die_hub_emb_top #(.CR(CR), .MUT(MUT_GW)) u_hub (.ck(ck), .rst_n(rst_n), .fck0(ck), .fck1(ck), .fck2(ck),
        .fck3(ck), .l0_i(hl_i[0 +: 528]), .l0_o(hl_o[0 +: 528]), .l1_i(hl_i[528 +: 528]), .l1_o(hl_o[528 +: 528]),
        .l2_i(hl_i[1056 +: 528]), .l2_o(hl_o[1056 +: 528]), .l3_i(hl_i[1584 +: 528]), .l3_o(hl_o[1584 +: 528]),
        .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr), .ar_v(ar_v), .ar_d(ar_d), .ar_cr(1'b0),
        .fault(hub_fault), .fault_cause(hub_fc), .ea_v(h_ea_v), .ea_kind(h_ea_kind), .ea_addr(h_ea_addr), .ea_cr(h_ea_cr),
        .eq_v(h_eq_v), .eq_d(h_eq_d), .emb_ready(emb_ready), .emb_fault(emb_fault), .emb_fault_code(emb_fc));
    // ---------------------------------------------------------------- four stacks
    wire [3:0] far_fault, strip_fault; wire [31:0] st_ce [0:3]; wire [31:0] st_ue [0:3];
    wire [7:0] strip_fc [0:3];
    integer viol_total, srd_total, swr_total, ref_total;
    // static-read wait monitor (controller cycles from the s_v at a ctrl pin to its column command)
    integer wmax_tok = 0, wmax_all = 0; longint wsum = 0; integer wn = 0;
    genvar k, q;
    generate for (k = 0; k < 4; k = k + 1) begin : g_stk
        wire [527:0] down, up, fl_o;
        // hub -> stack (hub clock ck, forwarded) / stack -> hub (hclk, forwarded)
        ot_hdc_delay #(.W(528), .D(LINK_STG), .RESET(1)) u_dn (.clk(ck), .rst_n(rst_n), .d(hl_o[k*528 +: 528]), .q(down));
        ot_hdc_delay #(.W(528), .D(LINK_STG), .RESET(1)) u_up (.clk(ck), .rst_n(rst_n), .d(fl_o), .q(hl_i[k*528 +: 528]));
        wire e_v, e_cr, t_v, t_cr; wire [522:0] e_d, t_d;
        ot_qfd_link_far #(.CR(CR)) u_far (.ck(ck), .lclk(ck), .rst_n(rst_n), .l_i(down), .l_o(fl_o),
            .e_v(e_v), .e_d(e_d), .e_cr(e_cr), .k_v(), .k_d(), .k_cr(1'b0), .t_v(t_v), .t_d(t_d), .t_cr(t_cr),
            .kt_v(1'b0), .kt_d(523'd0), .kt_cr(), .fault(far_fault[k]));
        wire [NPC-1:0] s_m, s_cr, w_m, e_rv; wire s_we; wire [4:0] s_bank, s_col; wire [18:0] s_row; wire [255:0] w_d;
        wire [NPC*258-1:0] e_rd;
        ot_qfd_emb_strip #(.STK(k), .ROW0(ROW0), .TWIN(TWIN), .TWIN_ROFF(TWIN_ROFF), .MUT(MUT_STRIP)) u_strip (
            .clk(ck), .rst_n(rst_n), .i_v(e_v), .i_d(e_d), .i_cr(e_cr), .o_v(t_v), .o_d(t_d), .o_cr(t_cr),
            .s_m(s_m), .s_we(s_we), .s_bank(s_bank), .s_col(s_col), .s_row(s_row), .s_cr(s_cr), .w_m(w_m), .w_d(w_d),
            .e_v(e_rv), .e_d(e_rd), .fault(strip_fault[k]), .fault_code(strip_fc[k]), .ce_cnt(st_ce[k]), .ue_info(st_ue[k]));
        for (q = 0; q < NPC; q = q + 1) begin : g_pc
            // band stations: the PC's distance from the stack centre (12 mm PHY, 32 PCs) over the 430.56 um reach
            localparam integer OFF = ((q > 15) ? (q - 15) : (16 - q)) * 375 - 187;
            localparam integer D = (OFF + 430) / 431 + 1;
            // strip column (core clock): the command + write data down, the credit and the decoded beat back
            wire d_v, d_wv, d_we; wire [4:0] d_bank, d_col; wire [18:0] d_row; wire [255:0] d_wd;
            wire u_cr, u_ev; wire [257:0] u_ed;
            ot_hdc_delay #(.W(2), .D(D), .RESET(1)) u_b0 (.clk(ck), .rst_n(rst_n), .d({s_m[q], w_m[q]}), .q({d_v, d_wv}));
            ot_hdc_delay #(.W(30 + 256), .D(D)) u_b1 (.clk(ck), .rst_n(rst_n), .d({s_we, s_bank, s_col, s_row, w_d}),
                .q({d_we, d_bank, d_col, d_row, d_wd}));
            ot_hdc_delay #(.W(2), .D(D), .RESET(1)) u_b2 (.clk(ck), .rst_n(rst_n), .d({u_cr, u_ev}), .q({s_cr[q], e_rv[q]}));
            ot_hdc_delay #(.W(258), .D(D)) u_b3 (.clk(ck), .rst_n(rst_n), .d(u_ed), .q(e_rd[q*258 +: 258]));
            // the PC's core <-> HBM crossing (qfd_cdc stand-in): down {wv, we, bank, col, row, data}; credit; up beat
            wire x_v, c_scr, p_ev, x_cv, x_ev; wire [286:0] x_d; wire [257:0] p_ed;
            ot_async_fifo #(.WIDTH(287), .DEPTH(8)) u_xd (.wr_clk(ck), .wr_rst_n(rst_n), .wr_valid(d_v),
                .wr_ready(), .wr_data({d_wv, d_we, d_bank, d_col, d_row, d_wd}), .wr_overflow(),
                .rd_clk(hclk), .rd_rst_n(rst_n), .rd_valid(x_v), .rd_ready(1'b1), .rd_data(x_d), .rd_underflow());
            ot_async_fifo #(.WIDTH(1), .DEPTH(8)) u_xc (.wr_clk(hclk), .wr_rst_n(rst_n), .wr_valid(c_scr), .wr_ready(),
                .wr_data(1'b1), .wr_overflow(), .rd_clk(ck), .rd_rst_n(rst_n), .rd_valid(x_cv), .rd_ready(1'b1),
                .rd_data(), .rd_underflow());
            ot_async_fifo #(.WIDTH(258), .DEPTH(8)) u_xu (.wr_clk(hclk), .wr_rst_n(rst_n), .wr_valid(p_ev), .wr_ready(),
                .wr_data(p_ed), .wr_overflow(), .rd_clk(ck), .rd_rst_n(rst_n), .rd_valid(x_ev), .rd_ready(1'b1),
                .rd_data(u_ed), .rd_underflow());
            assign u_cr = x_cv; assign u_ev = x_ev;
            wire c_v = x_v, c_wv = x_v && x_d[286], c_we = x_d[285]; wire [4:0] c_bank = x_d[284:280], c_col = x_d[279:275];
            wire [18:0] c_row = x_d[274:256]; wire [255:0] c_wd = x_d[255:0];
            // KV stream driver (descriptor / go / landing credits)
            reg cmd_v = 0; reg [31:0] cmd = 0; reg [2:0] rcred = 0;
            wire cmd_cr, row_v, col_v, col_we, col_sr, busy, cfault; wire [2:0] row_op; wire [4:0] row_bank, col_bank, col_col;
            wire [18:0] row_row;
            ot_qwen_ctrl_pc_emb #(.ENABLE(1), .PC(q), .S_STARVE(S_STARVE), .TWIN(TWIN), .TWIN_ROFF(TWIN_ROFF)) u_ctl (
                .clk(hclk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd(cmd), .read_credit(rcred), .cmd_credit(cmd_cr),
                .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row), .col_v(col_v), .col_bank(col_bank),
                .col_col(col_col), .col_we(col_we), .busy(busy), .fault(cfault),
                .s_v(c_v), .s_we(c_we), .s_bank(c_bank), .s_col(c_col), .s_row(c_row), .s_cr(c_scr), .col_sr(col_sr));
            wire [287:0] wd; wire r_v, kv_v, pfault; wire [287:0] r_d, kv_d;
            ot_qfd_emb_pcport #(.MUT(MUT_STRIP == 3 ? 3 : 0)) u_port (.clk(hclk), .rst_n(rst_n), .col_v(col_v), .col_we(col_we), .col_sr(col_sr),
                .w_v(c_wv), .w_d(c_wd), .wd(wd), .r_v(r_v), .r_d(r_d), .kv_v(kv_v), .kv_d(kv_d), .em_v(p_ev), .em_d(p_ed),
                .fault(pfault));
            tb_emb_dram_pc u_dram (.clk(hclk), .rst_n(rst_n), .row_v(row_v), .row_op(row_op), .row_bank(row_bank),
                .row_row(row_row), .col_v(col_v), .col_we(col_we), .col_sr(col_sr), .col_bank(col_bank), .col_col(col_col),
                .wd(wd), .r_v(r_v), .r_d(r_d));
            // KV: landing credits back (all landings taken), descriptor (re)posting
            integer kv_land = 0, sent = 0, acked = 0, posted = 0;
            always @(posedge hclk) if (rst_n) begin
                if (kv_v) kv_land = kv_land + 1;
                if (cmd_cr) acked = acked + 1;
            end
            always @(negedge hclk) if (rst_n) begin
                rcred <= (kv_land > 7) ? 3'd7 : 3'(kv_land);
                kv_land = kv_land - ((kv_land > 7) ? 7 : kv_land);
                cmd_v <= 1'b0;
                if (KVMODE != 0 && sent - acked < 8 && !cmd_v) begin
                    if (posted == 0) begin cmd <= {2'b00, 11'd1024, 19'd7}; cmd_v <= 1'b1; sent = sent + 1; posted = 1; end
                    else if (KVMODE == 2 && posted == 1) begin cmd <= {2'b01, 30'd0}; cmd_v <= 1'b1; sent = sent + 1; posted = 2; end
                    else if (KVMODE == 2 && posted == 2 && !busy && sent == acked) begin
                        cmd <= {2'b00, 11'd1024, 19'd7}; cmd_v <= 1'b1; sent = sent + 1; posted = 1;
                    end
                end
            end
            // static wait monitor
            longint ts [0:15]; integer tw = 0, trd = 0; longint hc = 0;
            always @(posedge hclk) if (rst_n) begin
                hc = hc + 1;
                if (c_v && !c_we) begin ts[tw % 16] = hc; tw = tw + 1; end
                if (col_v && col_sr && !col_we) begin : wm
                    longint wt;
                    wt = hc - ts[trd % 16]; trd = trd + 1;
                    if (wt > wmax_tok) wmax_tok = wt;
                    if (wt > wmax_all) wmax_all = wt;
                    wsum = wsum + wt; wn = wn + 1;
                end
            end
        end
    end endgenerate
    // ---------------------------------------------------------------- loader (x3) and the checks
    integer x3c = 8;                          // x3 skid credits
    always @(posedge ck) if (rst_n && x3_cr) x3c = x3c + 1;
    task automatic x3_send(input [10:0] tg, input [511:0] d);
        begin
            @(negedge ck); while (x3c == 0) @(negedge ck);
            x3_v = 1; x3_tag = tg; x3_d = d; x3c = x3c - 1;
            @(negedge ck); x3_v = 0;
        end
    endtask
    integer stop;
    integer gseed = 20261008;
    integer errors = 0, early = 0, i, j, t, r, e, nlat = 0, lmin = 1 << 30, lmax = 0, ce_base, w_bad, ue_seen = 0;
    longint lsum = 0, tstart, cyc_ck = 0, t_ready = 0;
    integer lat [0:MAXTOK-1]; integer wmx [0:MAXTOK-1];
    always @(posedge ck) cyc_ck = cyc_ck + 1;
    always @(posedge ck) if (rst_n && s_eq_v && !emb_ready && t_ready == 0) early = early + 1;
    integer ndbg = 0;
    always @(posedge ck) if ($test$plusargs("dbg") && rst_n && |u_hub.u.e_take && ndbg < 80) begin
        ndbg = ndbg + 1;
        $display("SLOT ck=%0d take=%b tags=%h %h %h %h fault=%0d w=%0d seq=%0d", cyc_ck, u_hub.u.e_take, u_hub.u.lhd[522:512],
                 u_hub.u.lhd[1045:1035], u_hub.u.lhd[1568:1558], u_hub.u.lhd[2091:2081], emb_fault, u_hub.u.u_gw.w, u_hub.u.u_gw.seq);
    end
    always @(posedge ck) if ($test$plusargs("dbg") && rst_n && cyc_ck > 2300 && cyc_ck < 2500) begin
        if (g_stk[0].u_strip.o_v) $display("STRIP0 ck=%0d o_tag=%h pm=%0d pscale=%0d", cyc_ck, g_stk[0].u_strip.o_d[522:512], g_stk[0].u_strip.pm, g_stk[0].u_strip.pscale);
        if (g_stk[0].u_strip.pop_code || g_stk[0].u_strip.pop_scale) $display("POP0 ck=%0d pm=%0d code=%0d scale=%0d res=%0d", cyc_ck, g_stk[0].u_strip.pm, g_stk[0].u_strip.pop_code, g_stk[0].u_strip.pop_scale, g_stk[0].u_strip.tx_res);
        if (g_stk[0].t_v) $display("FARTX0 ck=%0d", cyc_ck);
    end
    reg emb_fault_q = 0;
    always @(posedge ck) begin
        emb_fault_q <= emb_fault;
        if (emb_fault && !emb_fault_q)
            $display("GWFAULT code=%h st=%0d w=%0d ct=%0d seq=%0d lk=%0d slot_tag=%h sv=%b", emb_fc, u_hub.u.u_gw.st,
                     u_hub.u.u_gw.w, u_hub.u.u_gw.ct, u_hub.u.u_gw.seq, u_hub.u.u_gw.lk, u_hub.u.u_gw.sl[522:512], u_hub.u.u_gw.sv);
    end
    string dir, latf;
    integer fd;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) dir = "build/emb_hbm_bench";
        $readmemh({dir, "/meta.hex"}, meta);
        NTOK = meta[2]; NBOOT = meta[3]; CE_IX = meta[4]; UE_IX = meta[5];
        $readmemh({dir, "/boot.hex"}, bootm, 0, NBOOT - 1);
        $readmemh({dir, "/tokens.hex"}, toks, 0, NTOK - 1);
        $readmemh({dir, "/gcode.hex"}, gcode, 0, NTOK * 65 - 1);
        $readmemh({dir, "/gfp.hex"}, gfp, 0, NTOK * 4096 - 1);
        repeat (8) @(negedge ck); rst_n = 1;
        repeat (40) @(negedge ck);
        // the first token's fetch is requested BEFORE the load: it must wait for the gate
        tok = toks[0]; a_src = 1; go_in = 1; @(negedge ck); go_in = 0; a_src = 0;
        // ---- boot load through the x3 path
        for (i = 0; i < NBOOT; i = i + 1)
            x3_send({1'b1, K_BOOT_WR, 1'b0, 3'd0, 4'd0}, {231'd0, bootm[i]});
        x3_send({1'b1, K_BOOT_END, 1'b0, 3'd0, 4'd0}, {448'd0, meta[1], meta[0]});
        $display("BOOT sent %0d sectors at ck %0d", NBOOT, cyc_ck);
        while (!emb_ready && !emb_fault) @(negedge ck);
        t_ready = cyc_ck;
        $display("BOOT ready=%0d fault=%0d code=%h at ck %0d", emb_ready, emb_fault, emb_fc, cyc_ck);
        if (!emb_ready) begin errors = errors + 1; finish_up(); end
        // ---- fetches
        stop = 0;
        for (t = 0; t < NTOK && !stop; t = t + 1) begin
            if (t == CE_IX) inject(t, 0);       // single-bit errors before this token's fetch
            if (t == UE_IX) inject(t, 1);       // a double-bit error
            ce_base = st_ce[0] + st_ce[1] + st_ce[2] + st_ce[3];
            wmax_tok = 0;
            if (t != 0) begin
                repeat ((($random(gseed) & 32'h7fffffff) % 311)) @(negedge ck);     // a random gap: the fetch meets every refresh phase
                tok = toks[t]; @(negedge ck); a_src = 1; go_in = 1; tstart = cyc_ck; @(negedge ck); go_in = 0; a_src = 0;
            end else tstart = t_ready;
            j = 0;
            while (!go_out && !emb_fault && j < 200000) begin @(negedge ck); j = j + 1; end
            if (t == UE_IX) begin
                repeat (3000) @(negedge ck);
                if (emb_fault && emb_fc[4] && !u_su.have && |strip_fault) begin ue_seen = 1; $display("UE token %0d: detected, fail closed (gw code %h)", toks[t], emb_fc); end
                else begin errors = errors + 1; $display("FAIL UE token %0d not failed closed (fault %0d code %h have %0d)", toks[t], emb_fault, emb_fc, u_su.have); end
                stop = 1;
            end else if (!go_out && !u_su.have) begin errors = errors + 1; $display("FAIL token %0d: no fill (gw fault %h)", toks[t], emb_fc); stop = 1; end
            else begin
            lat[t] = cyc_ck - tstart; wmx[t] = wmax_tok;
            if (t != 0) begin lsum = lsum + lat[t]; nlat = nlat + 1; if (lat[t] < lmin) lmin = lat[t]; if (lat[t] > lmax) lmax = lat[t]; end
            repeat (2) @(negedge ck);
            // the consumer's row buffer: 64 code words + the scale
            w_bad = 0;
            for (r = 0; r < 64; r = r + 1) if (u_su.rowbuf[r] !== gcode[t*65 + r]) w_bad = w_bad + 1;
            if (u_su.rscale !== gcode[t*65 + 64][15:0]) w_bad = w_bad + 1;
            // every decoded FP32 element the SU delivers
            // one 64-lane read a cycle; the value is on su_va_q one edge after the strobe
            for (r = 0; r < 64; r = r + 1) begin
                su_va_re = {64{1'b1}};
                for (e = 0; e < 64; e = e + 1) su_va_addr[e*24 +: 24] = 24'(r * 64 + e);
                @(negedge ck);
                for (e = 0; e < 64; e = e + 1) if (su_va_q[e*32 +: 32] !== gfp[t*4096 + r*64 + e]) w_bad = w_bad + 1;
            end
            su_va_re = 0;
            if (w_bad != 0 && $test$plusargs("dbg") && t < 2) begin
                for (r = 0; r < 66; r = r + 1) $display("DBG t=%0d w=%0d got=%h exp=%h", toks[t], r, (r < 64) ? u_su.rowbuf[r][63:0] : 64'(u_su.rscale), gcode[t*65 + ((r < 65) ? r : 64)][63:0]);
            end
            if (w_bad != 0) begin
                errors = errors + 1;
                $display("FAIL token %0d (ix %0d): %0d mismatches", toks[t], t, w_bad);
            end
            if (t == CE_IX && (st_ce[0] + st_ce[1] + st_ce[2] + st_ce[3]) - ce_base < 2) begin
                errors = errors + 1; $display("FAIL CE token %0d: corrected %0d < 2", toks[t], (st_ce[0] + st_ce[1] + st_ce[2] + st_ce[3]) - ce_base);
            end
            end
        end
        finish_up();
    end
    // single-bit flips in two sectors (CE) or two bits of one 64-b word (UE) of token toks[t], in the copy read
    task automatic inject(input integer ti, input integer ue);
        reg [24:0] ee; reg [25:0] lc;
        begin
            ee = 25'(toks[ti]) * 25'd128 + 25'd37;            // sector 37: stack 1, PC 5
            lc = emb_loc(ee);
            flip_at(lc, ue ? 3 : 100, ue ? 9 : -1);
            if (!ue) begin
                ee = 25'(toks[ti]) * 25'd128 + 25'd96;        // sector 96: stack 3, PC 0 (a check bit)
                lc = emb_loc(ee);
                flip_at(lc, 284, -1);
            end
        end
    endtask
    task automatic flip_at(input [25:0] lc, input integer ba, input integer bb);
        reg [18:0] rw;
        begin
            rw = 19'(ROW0) + 19'(lc[7:0]);
            case ({lc[24:23], lc[22:18]})
`include "tb_emb_flip_cases.svh"
            endcase
        end
    endtask
    integer vt, k2;
    task automatic finish_up;
        begin
            vt = 0;
`include "tb_emb_viol_sum.svh"
            $display("STATS ntok=%0d lat_min=%0d lat_mean=%0d lat_max=%0d (core cycles go->fill, excl. first) static_wait_max=%0d hclk wait_mean_x100=%0d boot_ready_ck=%0d early_rsp=%0d dram_viol=%0d ce=%0d ue_seen=%0d hub_fault=%0d far=%b strip=%b fc=%h/%h/%h/%h gwfc=%h su_fault=%0d",
                     nlat + 1, lmin, (nlat ? lsum / nlat : 0), lmax, wmax_all, (wn ? (wsum * 100) / wn : 0), t_ready, early, vt,
                     st_ce[0] + st_ce[1] + st_ce[2] + st_ce[3], ue_seen, hub_fault, far_fault, strip_fault,
                     strip_fc[0], strip_fc[1], strip_fc[2], strip_fc[3], emb_fc, su_fault);
            if (!$value$plusargs("lat=%s", latf)) latf = {dir, "/lat.txt"};
            fd = $fopen(latf, "w");
            for (k2 = 0; k2 < NTOK; k2 = k2 + 1) $fdisplay(fd, "%0d %0d %0d", toks[k2], lat[k2], wmx[k2]);
            $fclose(fd);
            if (early != 0) errors = errors + 1;
            if (vt != 0 || hub_fault || |far_fault || su_fault) errors = errors + 1;
            if (|strip_fault && !(UE_IX < NTOK && ue_seen)) errors = errors + 1;
            if (emb_fault && !(UE_IX < NTOK && ue_seen)) errors = errors + 1;
            if (errors == 0) $display("PASS emb_hbm_e2e TWIN=%0d KVMODE=%0d tokens=%0d", TWIN, KVMODE, NTOK);
            else $display("FAIL emb_hbm_e2e errors=%0d MUT_STRIP=%0d MUT_GW=%0d", errors, MUT_STRIP, MUT_GW);
            $finish;
        end
    endtask
endmodule
