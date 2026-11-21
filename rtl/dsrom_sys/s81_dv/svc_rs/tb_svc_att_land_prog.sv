`timescale 1ns/1ps
// LAND-BENCH-2 (OPUS-FIX-S81-SVC-R6, 11-21): PROGRAMME-DRIVEN lock-step of the S81 service share's landing store,
// flop form (f = dsdv_svc_att, no memory defines) vs the SRAM landing store (m = -DOT_SVC_ATT_LAND_SRAM [+ $MDEFS]) and two
// negative controls: ml = m with the landing macros read ONE CYCLE LATE (bench copy dsdv_svc_land_mem_late, made by
// run_att_land_prog.sh), mq = m + -DOT_SVC_ATT_MEM_MACRO -DOT_SVC_ATT_MEM_MACRO_MUT (the sw / wq / qmem macros read one
// cycle late).  Replaces the random-frame tb_svc_att_mem as the land proof: its random frames kept the share in sticky
// fault (f_fault_cycles 24,733 of 24,738 checks, bench 2295988) and it had no landing-store coverage.
// Stimulus = the legal tb_svc_att_cut_prog programme (CFG / OWN_ROW / WIN_LOAD / SEL_IDS / ROWS / ATTN_Q / SMJ / PV / GO,
// H 8 two passes, PC model, host writes, warm reset between ops), NOP ops (default 4), plus with ROWX = 1 a ROWX export
// job per op before GO (even ops: held-list export RO = 0 with every 4th rank held, so the two export reads of a word
// hit the SAME bank; odd ops: rank-order export RO = 1, NP 3), which reads the landing store through ports 0 / 1.
// Every output of m (and ml, mq) is compared with f every cycle.  Coverage (m's u_land_mem ports): writes per bank and
// writer (PC0, PC1, ROWS), reads and nonzero reads per read lane, export reads, same-bank double reads.
// PASS = m 0 mismatching cycles AND ml, mq caught AND every bank written by a PC writer and by ROWS AND every read lane
// has nonzero reads AND (ROWX = 1) export reads and same-bank double reads > 0 AND f fault cycles <= 10 % of checks.
// plusargs as tb_svc_att_cut_prog (+seed= +nop= +po_k= +pvo_k= +gogap= +lat= +latr= +wrst= +hwn=) + +xwait= (cycles
// between ROWS and the export frame).
module tb_svc_att_land_prog;
    parameter integer ROWX = 0;
    parameter integer MAXCYC = 60000;
    localparam integer H = 8;
    localparam [3:0] SID = 4'd3, TILE = 4'd5;
    localparam [7:0] GD = 8'd17;
    localparam [9:0] PVS = 10'd40;
    // the compared output vector (MSB first): qrq 682 | l_v | l_d | pv_ov | pv_od | o 43 | sm_rd | fault_code | x 52
    localparam integer AW = 682 + 1 + H*132 + 20 + 1 + 513 + 43 + 512 + 32 + 52;
    localparam integer RW = AW - 682;                // everything below qrq (+2 lanes)
    localparam integer O_X = 0, O_FC = 52, O_SMRD = 84, O_O = 596, O_PVOD = 639, O_PVOV = 1152, O_LD = 1153,
                       O_LV = 1153 + H*132 + 20;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer XWAIT = 300, OWNM = 3, XE = 0;
    integer cyc = 0, SEED = 1, NOP = 4, PO_K = 200, PVO_K = 250, GOGAP = 300, LAT = 6, LATR = 8, WRST = 1, HWN = 24;
    // ---------------------------------------------------------------- stimulus
    reg q_v = 0; reg [511:0] q_d = 0; reg hw_v = 0; reg [290:0] hw_d = 0;
    reg [1:0] qrk = 0, qwd = 0, qrv = 0; reg [511:0] qr_data = 0; reg [33:0] qr_tag = 0; reg [7:0] qr_beat = 0;
    function automatic [31:0] xs(input [31:0] x); reg [31:0] y; y = x ^ (x << 13); y = y ^ (y >> 17); xs = y ^ (y << 5); endfunction
    reg [31:0] rp, rh, rm;                           // rng states: programme, host / idle, PC model
    function automatic [4:0] pcmap(input [29:0] s); reg [29:0] x; x = (s >> 2) ^ (s >> 7) ^ (s >> 12); pcmap = x[4:0]; endfunction
    function automatic [511:0] hdr(input [3:0] t, input [11:0] len, input [511:0] spec, input mine);
        hdr = spec; hdr[511:508] = t; hdr[507] = 1'b0; hdr[506:503] = {3'd0, mine}; hdr[491:480] = len;
    endfunction
    integer n_frames = 0, n_words = 0, prog_done = 0, n_go = 0, n_hw = 0, n_xf = 0;
    function automatic [511:0] rwp();                // a random word from the programme rng
        for (int i = 0; i < 16; i++) begin rp = xs(rp); rwp[32*i +: 32] = rp; end
    endfunction
    function automatic [511:0] rwh();                // a random word from the idle / host rng
        for (int i = 0; i < 16; i++) begin rh = xs(rh); rwh[32*i +: 32] = rh; end
    endfunction
    task automatic word(input [511:0] w);
        @(negedge clk); q_v = 1'b1; q_d = w; n_words = n_words + 1;
    endtask
    task automatic idle(input integer n);
        repeat (n) begin @(negedge clk); q_v = 1'b0; q_d = rwh(); end   // idle data is noise (must be ignored)
    endtask
    // ---------------------------------------------------------------- programme
    integer o, j, r, i, T, WC, NS, WF, US, NPW, PO, PVO, nrw;
    reg [7:0] TG; reg [511:0] w; reg [31:0] sid_g [0:511]; integer ord [0:1023];
    initial begin
        if ($value$plusargs("seed=%d", SEED)) ;
        if ($value$plusargs("nop=%d", NOP)) ;
        if ($value$plusargs("po_k=%d", PO_K)) ;
        if ($value$plusargs("pvo_k=%d", PVO_K)) ;
        if ($value$plusargs("gogap=%d", GOGAP)) ;
        if ($value$plusargs("lat=%d", LAT)) ;
        if ($value$plusargs("latr=%d", LATR)) ;
        if ($value$plusargs("wrst=%d", WRST)) ;
        if ($value$plusargs("hwn=%d", HWN)) ;
        if ($value$plusargs("xwait=%d", XWAIT)) ;
        rp = 32'h9E37_79B9 ^ SEED; rh = 32'h85EB_CA6B ^ (SEED << 3); rm = 32'hC2B2_AE35 ^ (SEED << 7);
        idle(8); rst_n = 1'b1; idle(30);
        for (o = 0; o < NOP; o = o + 1) begin
            WC = (o % 2 == 0) ? 12 : 7; NS = (o % 2 == 0) ? 40 : 25; WF = (o % 2 == 0) ? 100 : 125;
            US = (o % 2 == 0) ? 3 : 9; TG = (o % 2 == 0) ? 8'h5a : 8'h21;
            T = WC + NS; NPW = (T + 3) / 4; OWNM = (ROWX != 0 && o % 2 == 0) ? 4 : 3;
            PO = 2 * T + PO_K; PVO = PO + 2 * NPW + 8 * ((T + 31) / 32) + PVO_K;
            $display("PROG op=%0d T=%0d wcount=%0d nsel=%0d wfirst=%0d user=%0d tag=%02h PO=%0d PVO=%0d cyc=%0d", o, T, WC, NS, WF, US, TG, PO, PVO, cyc);
            // CFG: WB 0x100, ST valid 0, ALLQ, PV identity owner {user, tag} valid
            w = 0; w[29:0] = 30'h100; w[32] = 1'b1; w[31:30] = 2'd0; w[54] = 1'b1; w[53] = 1'b1; w[50:33] = {10'(US), TG};
            word(hdr(4'd12, 12'd0, w, 1'b1)); n_frames = n_frames + 1; idle(2);
            // OWN_ROW x WC: the window slots WF .. WF + WC - 1 of user US
            for (r = 0; r < WC; r = r + 1) begin
                w = rwp(); w[479:459] = 21'(WF + r); w[458:449] = 10'(US);
                word(hdr(4'd3, 12'd16, w, 1'b1)); n_frames = n_frames + 1;
                for (i = 0; i < 16; i = i + 1) word(rwp());
                if (r % 4 == 3) idle(1 + rp % 3);
            end
            idle(4);
            // a frame for other slices (mask 0): ignored here
            word(hdr(4'd1, 12'd3, rwp(), 1'b0)); word(rwp()); word(rwp()); word(rwp()); n_frames = n_frames + 1;
            // WIN_LOAD
            w = 0; w[29:0] = 30'h1000 + 30'(o * 30'h400); w[88:81] = 8'(WC); w[98:89] = 10'(NS); w[119:99] = 21'(WF);
            w[458:449] = 10'(US); w[502:495] = TG; w[479:459] = 21'(WF + WC);
            word(hdr(4'd2, 12'd0, w, 1'b1)); n_frames = n_frames + 1; idle(2);
            // SEL_IDS: rank r owned (die 0, stack 0) when r % 3 == 0: PC r[1], block 3 r + o, row k = r % 16;
            // else held by another die of this stack (r % 3 == 1) or another stack (r % 3 == 2)
            for (r = 0; r < NS; r = r + 1) begin
                rp = xs(rp);
                if (r % OWNM == 0) sid_g[r] = {11'(rp), 12'(3 * r + o), 1'(r >> 1), 2'd0, 2'd0, 4'(r % 16)};
                else if (r % OWNM == 1) sid_g[r] = {11'(rp), 12'(rp >> 11), 1'(rp), 2'd0, 2'd1, 4'(rp)};
                else sid_g[r] = {11'(rp), 12'(rp >> 11), 1'(rp), 2'd2, 2'(rp), 4'(rp)};
            end
            w = 0; w[9:0] = 10'd0; w[19:10] = 10'(NS);
            word(hdr(4'd7, 12'((NS + 15) / 16), w, 1'b1)); n_frames = n_frames + 1;
            for (i = 0; i < (NS + 15) / 16; i = i + 1) begin
                w = rwp();
                for (r = 0; r < 16; r = r + 1) if (16 * i + r < NS) w[32*r +: 32] = sid_g[16 * i + r];
                word(w);
            end
            idle(3);
            // ROWS: every non-owned rank for this pair (tile[3:1]) + every 2nd one also for another pair; shuffled
            nrw = 0;
            for (r = 0; r < NS; r = r + 1) if (r % OWNM != 0) begin
                ord[nrw] = 8 * r + TILE[3:1]; nrw = nrw + 1;
                if (r % 2 == 0) begin ord[nrw] = 8 * r + ((TILE[3:1] + 1 + r % 5) % 8); nrw = nrw + 1; end
            end
            for (i = nrw - 1; i > 0; i = i - 1) begin rp = xs(rp); r = rp % (i + 1); j = ord[i]; ord[i] = ord[r]; ord[r] = j; end
            word(hdr(4'd6, 12'(nrw), 512'd0, 1'b1)); n_frames = n_frames + 1;
            for (i = 0; i < nrw; i = i + 1) begin
                w = rwp(); w[9:0] = 10'(ord[i] / 8); w[30:10] = sid_g[ord[i] / 8][20:0]; w[33:31] = 3'(ord[i] % 8);
                word(w);
            end
            idle(4);
            if (ROWX != 0) begin
                // ROWX export (type 11, len 0) of this die's held rows, after they have landed (PC fetch); ends before GO
                idle(XWAIT);
                w = 0; w[15:0] = 16'd8;
                if (o % 2 == 0) begin                       // RO = 0 held list: ceil(held / 2) words, LAST, XB 0
                    XE = ((NS + OWNM - 1) / OWNM + 1) / 2; XE = ((XE + 4) / 5) * 5;
                    w[21:16] = 6'(XE); w[28:22] = 7'd0; w[29] = 1'b1; w[30] = 1'b0;
                end else begin                              // RO = 1 rank-order slots: NXW 5, NP 3, XP 20
                    XE = 5; w[21:16] = 6'd5; w[30] = 1'b1; w[34:31] = 4'd2; w[46:35] = 12'd20; XE = 2 * 20 + 5;
                end
                word(hdr(4'd11, 12'd0, w, 1'b1)); n_frames = n_frames + 1; n_xf = n_xf + 1;
                idle(GD + 8 + PVS + 1 + XE + 40);
            end
            for (j = 0; j < 2; j = j + 1) begin
                // ATTN_Q pass j
                w = 0; w[448] = 1'(j);
                word(hdr(4'd1, 12'd128, w, 1'b1)); n_frames = n_frames + 1;
                for (i = 0; i < 128; i = i + 1) word(rwp());
                idle(2);
                // SMJ SE job (kind 4) + 2 parameter rows
                w = 0; w[0] = 1'b1; w[4:1] = 4'd4; w[12:5] = 8'(8'h30 + 2 * o + j);
                word(hdr(4'd9, 12'd2, w, 1'b1)); n_frames = n_frames + 1;
                w = 0; w[64 +: 7] = 7'((T + 15) / 16); w[96 +: 32] = 32'h3dc00000; w[128 +: 3] = 3'($clog2((T + 15) / 16)); word(w);
                w = 0; for (i = 0; i < 16; i = i + 1) w[32*i +: 32] = 32'hc0000000 | (i << 18); word(w);
                idle(2);
                // SMJ operand rows ([13]): 3 rows, head mask with this tile, then 2 rows, mask without it
                w = 0; w[0] = 1'b0; w[4:1] = 4'd6; w[12:5] = 8'h44; w[13] = 1'b1; w[29:14] = 16'h00ff | (16'd1 << TILE);
                word(hdr(4'd9, 12'd3, w, 1'b1)); n_frames = n_frames + 1;
                for (i = 0; i < 3; i = i + 1) word(rwp());
                w = 0; w[4:1] = 4'd6; w[12:5] = 8'h45; w[13] = 1'b1; w[29:14] = ~(16'd1 << TILE);
                word(hdr(4'd9, 12'd2, w, 1'b1)); n_frames = n_frames + 1;
                for (i = 0; i < 2; i = i + 1) word(rwp());
                idle(2);
                // PV: the pass's p words
                word(hdr(4'd5, 12'(NPW), 512'd0, 1'b1)); n_frames = n_frames + 1;
                for (i = 0; i < NPW; i = i + 1) word(rwp());
                idle(GOGAP);
                // GO
                w = 0; w[15:0] = 16'(PO); w[31:16] = 16'(PVO); w[47:32] = 16'd0; w[48] = (j == 0);
                word(hdr(4'd13, 12'd0, w, 1'b1)); n_frames = n_frames + 1; n_go = n_go + 1;
                idle(GD + PVO + PVS + 40 + 80);
            end
            // SMJ kind 5 (broadcast) + 2 parameter rows
            w = 0; w[0] = 1'b1; w[4:1] = 4'd5; w[12:5] = 8'(8'h50 + o);
            word(hdr(4'd9, 12'd2, w, 1'b1)); n_frames = n_frames + 1; word(rwp()); word(rwp());
            idle(40);
            if (WRST != 0 && o + 1 < NOP) begin
                @(negedge clk); rst_n = 1'b0; idle(20); rst_n = 1'b1; idle(20);
                $display("PROG warm reset done cyc=%0d", cyc);
            end
        end
        idle(100);
        prog_done = 1;
    end
    // ---------------------------------------------------------------- host sector writes (hw lane, this slice's PCs)
    reg [29:0] h_adr [0:63];
    initial begin : hsel
        integer n; reg [29:0] a; reg [4:0] pm; n = 0; a = 30'h5000;
        while (n < 64) begin pm = pcmap(a); if (pm[4:1] == SID) begin h_adr[n] = a; n = n + 1; end a = a + 30'd3; end
    end
    always @(negedge clk) begin
        hw_v = 1'b0; rh = xs(rh); hw_d = {3'(rh), 32'(rh * 7), {8{xs(rh)}}};      // noise when not valid
        if (rst_n && cyc > 200 && n_hw < HWN && cyc % 97 == 0) begin
            hw_v = 1'b1; hw_d = {2'b00, 1'b1, 2'b00, h_adr[n_hw % 64], {8{32'(rh ^ n_hw)}}}; n_hw = n_hw + 1;
        end
    end
    // ---------------------------------------------------------------- page-cache model (both PCs, from f's qrq)
    reg [340:0] rqm [0:1][0:63]; integer rq_t [0:1][0:63]; integer rq_w [0:1], rq_r [0:1], rq_b [0:1];
    reg [255:0] mem [longint];
    integer n_rd = 0, n_wr = 0, n_rbeat = 0, pc_err = 0;
    initial begin rq_w[0] = 0; rq_w[1] = 0; rq_r[0] = 0; rq_r[1] = 0; rq_b[0] = 0; rq_b[1] = 0; end
    function automatic [255:0] mrd(input integer k, input [29:0] a);
        longint key; key = {33'd0, 1'(k), a};
        if (mem.exists(key)) mrd = mem[key];
        else for (int i = 0; i < 8; i++) mrd[32*i +: 32] = xs(32'(a) * 32'h9E3779B1 + 32'(k * 977 + i * 131 + 1));
    endfunction
    wire [681:0] f_qrq;
    always @(negedge clk) begin : pcm
        integer k, h; reg [340:0] q; reg [255:0] d; longint key;
        qrk = 0; qwd = 0; qrv = 0; qr_beat = 0;
        rm = xs(rm); qr_tag = {2'(rm), 32'(rm)}; qr_data = {16{xs(rm)}};          // noise when not valid
        for (k = 0; k < 2; k = k + 1) begin
            if (f_qrq[341*k]) begin
                if (rq_w[k] - rq_r[k] >= 64) pc_err = pc_err + 1;
                rm = xs(rm);
                rqm[k][rq_w[k] % 64] = f_qrq[341*k +: 341]; rq_t[k][rq_w[k] % 64] = cyc + LAT + 32'(rm % 32'(LATR + 1)); rq_w[k] = rq_w[k] + 1;
            end
            if (rq_r[k] != rq_w[k] && cyc >= rq_t[k][rq_r[k] % 64]) begin
                h = rq_r[k] % 64; q = rqm[k][h];
                if (q[1]) begin                                                       // write: merge by strobe
                    key = {33'd0, 1'(k), q[31:2]}; d = mrd(k, q[31:2]);
                    for (int b = 0; b < 32; b++) if (q[53 + b]) d[8*b +: 8] = q[85 + 8*b +: 8];
                    mem[key] = d; qwd[k] = 1'b1; qrk[k] = 1'b1; rq_r[k] = rq_r[k] + 1; n_wr = n_wr + 1;
                end else begin                                                        // read: len beats in order
                    qrv[k] = 1'b1; qr_tag[17*k +: 17] = q[52:36]; qr_beat[4*k +: 4] = 4'(rq_b[k]);
                    qr_data[256*k +: 256] = mrd(k, q[31:2] + 30'(rq_b[k])); n_rbeat = n_rbeat + 1;
                    rq_b[k] = rq_b[k] + 1;
                    if (rq_b[k] >= 32'(q[35:32])) begin rq_b[k] = 0; qrk[k] = 1'b1; rq_r[k] = rq_r[k] + 1; n_rd = n_rd + 1; end
                end
            end
        end
        if (!rst_n) begin rq_r[0] = rq_w[0]; rq_r[1] = rq_w[1]; rq_b[0] = 0; rq_b[1] = 0; qrk = 0; qwd = 0; qrv = 0; end   // flush on reset
    end
    // ---------------------------------------------------------------- DUT copies (all same timing)
`define ATT_OUTS(P) \
        .l_v(P``_l_v), .l_d(P``_l_d), .pv_ov(P``_pv_ov), .pv_od(P``_pv_od), \
        .sm_st(P``_o[0]), .sm_kind(P``_o[4:1]), .sm_jid(P``_o[12:5]), .sm_rv(P``_o[13]), .sm_rp(P``_o[14]), .sm_rj(P``_o[17:15]), \
        .sm_rd(P``_sm_rd), .go_o(P``_o[18]), .tjob_o(P``_o[28:19]), .done(P``_o[29]), .tagj(P``_o[37:30]), .hcr(P``_o[39:38]), \
        .hack(P``_o[41:40]), .fault(P``_o[42]), .fault_code(P``_fc), .pio_o(P``_x[15:0]), .pvo_o(P``_x[31:16]), .jc_o(P``_x[47:32]), \
        .st_o(P``_x[49:48]), .allq_o(P``_x[50]), .hb_o(P``_x[51])
`define ATT_PORTS_F(P) \
        .clk(clk), .rst_n(rst_n), .sid(SID), .tile(TILE), .gd(GD), .pvs(PVS), .root(1'b0), \
        .q_v(q_v), .q_d(q_d), .hw_v(hw_v), .hw_d(hw_d), .qrq(P``_qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), \
        .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat), `ATT_OUTS(P)
`define ATT_WIRES(P) \
    wire P``_l_v; wire [H*132+19:0] P``_l_d; wire P``_pv_ov; wire [512:0] P``_pv_od; wire [42:0] P``_o; \
    wire [511:0] P``_sm_rd; wire [31:0] P``_fc; wire [51:0] P``_x; \
    wire [AW-1:0] P``_all = {P``_qrq, P``_l_v, P``_l_d, P``_pv_ov, P``_pv_od, P``_o, P``_sm_rd, P``_fc, P``_x};
    wire [681:0] m_qrq, ml_qrq, mq_qrq;
    `ATT_WIRES(f)
    `ATT_WIRES(m)
    `ATT_WIRES(ml)
    `ATT_WIRES(mq)
    dsdv_svc_att_f  #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .ROWX(ROWX)) u_f  (`ATT_PORTS_F(f));
    dsdv_svc_att_m  #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .ROWX(ROWX)) u_m  (`ATT_PORTS_F(m));
    dsdv_svc_att_ml #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .ROWX(ROWX)) u_ml (`ATT_PORTS_F(ml));
    dsdv_svc_att_mq #(.H(H), .SRAM_MACRO(1), .PV_IDENTITY(1), .ROWX(ROWX)) u_mq (`ATT_PORTS_F(mq));
    // ---------------------------------------------------------------- landing-store coverage (m's u_land_mem ports)
    wire [2:0] lv_we = u_m.u_land_mem.we; wire [29:0] lv_wa = u_m.u_land_mem.wa; wire [47:0] lv_ra = u_m.u_land_mem.ra;
    wire [1023:0] lv_rd = u_m.u_land_mem.rd; wire lv_xem = u_m.x_em;
    integer cw [0:3][0:2], cr [0:3], cnz [0:3], cx_rd = 0, cx_nz = 0, cx_same = 0;
    initial for (int b = 0; b < 4; b++) begin cr[b] = 0; cnz[b] = 0; for (int w = 0; w < 3; w++) cw[b][w] = 0; end
    reg [3:0] lv_re_q = 0; reg lv_xem_q = 0;
    always @(posedge clk) begin
        for (int w = 0; w < 3; w++)
            if (lv_we[w] && 32'(lv_wa[10*w +: 10]) < 640) cw[lv_wa[10*w +: 2]][w] = cw[lv_wa[10*w +: 2]][w] + 1;
        for (int r = 0; r < 4; r++) begin
            lv_re_q[r] <= 32'(lv_ra[12*r +: 12]) < 640;
            if (32'(lv_ra[12*r +: 12]) < 640) cr[r] = cr[r] + 1;
            if (lv_re_q[r] && lv_rd[256*r +: 256] != 0) cnz[r] = cnz[r] + 1;       // the registered read, one edge later
        end
        lv_xem_q <= lv_xem;
        if (lv_xem) begin
            cx_rd = cx_rd + 1;
            if (lv_ra[1:0] == lv_ra[13:12] && 32'(lv_ra[11:0]) < 640 && 32'(lv_ra[23:12]) < 640) cx_same = cx_same + 1;
        end
        if (lv_xem_q && (lv_rd[255:0] != 0 || lv_rd[511:256] != 0)) cx_nz = cx_nz + 1;
    end
    // ---------------------------------------------------------------- lock-step check
    // lane groups: 0 qrq (+1), 1 scores l_v / l_d, 2 P.V pv_ov / pv_od, 3 SM row sm_rv / sm_rp / sm_rj / sm_rd,
    // 4 the other o lanes (sm_st / kind / jid, go, tjob, done, tagj, hcr, hack, fault), 5 fault_code + taps x
    function automatic [5:0] grp(input [AW-1:0] a, input [AW-1:0] d);
        grp[0] = a[AW-1:RW] != d[AW-1:RW];
        grp[1] = a[O_LV:O_LD] != d[O_LV:O_LD];
        grp[2] = a[O_PVOV:O_PVOD] != d[O_PVOV:O_PVOD];
        grp[3] = (a[O_O+17:O_O+13] != d[O_O+17:O_O+13]) || (a[O_SMRD+511:O_SMRD] != d[O_SMRD+511:O_SMRD]);
        grp[4] = (a[O_O+12:O_O] != d[O_O+12:O_O]) || (a[O_O+42:O_O+18] != d[O_O+42:O_O+18]);
        grp[5] = a[O_SMRD-1:0] != d[O_SMRD-1:0];
    endfunction
    integer chk = 0, err_c = 0, err_m2 = 0, err_m3 = 0, first_c = -1, first_m2 = -1, first_m3 = -1, n_xo = 0;
    integer gc [0:5], g2 [0:5], g3 [0:5];
    integer n_l = 0, n_pv = 0, n_pvh = 0, n_smst = 0, n_smrv = 0, n_smr = 0, n_flt = 0, n_done = 0, n_goo = 0, n_q = 0, n_hcr = 0, n_hack = 0, first_flt = -1;
    reg [31:0] fc_or = 0;
    initial for (int g = 0; g < 6; g++) begin gc[g] = 0; g2[g] = 0; g3[g] = 0; end
    string dfn; integer fdmp = 0;
    initial if ($value$plusargs("dump=%s", dfn)) fdmp = $fopen(dfn, "w");
    wire [5:0] gm_c = grp(m_all, f_all), gm_2 = grp(ml_all, f_all), gm_3 = grp(mq_all, f_all);
    always @(posedge clk) begin
        if (fdmp != 0) $fwrite(fdmp, "%0d %h %h %h %h %h %h %h %h %h %h\n", cyc, rst_n, q_v, q_d, hw_v, hw_d, qrk, qwd, qrv, {qr_tag, qr_beat}, qr_data);
        cyc <= cyc + 1;
        if (cyc > 12 && rst_n) begin
            chk = chk + 1;
            if (gm_c != 0) begin
                err_c = err_c + 1;
                if (first_c < 0) begin
                    first_c = cyc;
                    $display("FIRST_MISMATCH m cyc=%0d groups=%b (0 qrq,1 score,2 pv,3 sm row,4 other o,5 fc/x)", cyc, gm_c);
                    $display("  m.o=%h f.o=%h m.x=%h f.x=%h m.fc=%h f.fc=%h m.pv_ov=%b f.pv_ov=%b m.l_v=%b f.l_v=%b",
                             m_o, f_o, m_x, f_x, m_fc, f_fc, m_pv_ov, f_pv_ov, m_l_v, f_l_v);
                end
            end
            if (gm_2 != 0) begin err_m2 = err_m2 + 1; if (first_m2 < 0) first_m2 = cyc; end
            if (gm_3 != 0) begin err_m3 = err_m3 + 1; if (first_m3 < 0) first_m3 = cyc; end
            for (int g = 0; g < 6; g++) begin gc[g] = gc[g] + 32'(gm_c[g]); g2[g] = g2[g] + 32'(gm_2[g]); g3[g] = g3[g] + 32'(gm_3[g]); end
            if (f_l_v) n_l = n_l + 1;
            if (f_pv_ov) n_pv = n_pv + 1;
            if (f_pv_ov && lv_xem_q) n_xo = n_xo + 1;
            if (f_pv_ov && f_pv_od[512]) n_pvh = n_pvh + 1;
            if (f_o[0]) n_smst = n_smst + 1;
            if (f_o[13]) n_smrv = n_smrv + 1;
            if (f_o[13] || f_o[14] || f_o[17:15] != 0) n_smr = n_smr + 1;
            if (f_o[42]) begin n_flt = n_flt + 1; if (first_flt < 0) first_flt = cyc; end
            if (f_o[29]) n_done = n_done + 1;
            if (f_o[18]) n_goo = n_goo + 1;
            if (f_qrq[0] || f_qrq[341]) n_q = n_q + 1;
            if (f_o[39:38] != 0) n_hcr = n_hcr + 1;
            if (f_o[41:40] != 0) n_hack = n_hack + 1;
            fc_or = fc_or | f_fc;
        end
        if (prog_done != 0 || cyc == MAXCYC) begin
            if (prog_done == 0) $display("TIMEOUT programme not finished at MAXCYC=%0d", MAXCYC);
            $display("LAND_PROG seed=%0d rowx=%0d checks=%0d frames=%0d q_words=%0d go_frames=%0d rowx_frames=%0d host_writes=%0d pc_reads=%0d pc_read_beats=%0d pc_writes=%0d pc_model_err=%0d",
                     SEED, ROWX, chk, n_frames, n_words, n_go, n_xf, n_hw, n_rd, n_rbeat, n_wr, pc_err);
            $display("LAND_PROG_F score_beats(l_v)=%0d pv_words(pv_ov)=%0d pv_beats(head words)=%0d export_words=%0d sm_starts=%0d sm_row_beats=%0d go_o=%0d done=%0d qrq_cycles=%0d fault_cycles=%0d (%0d.%0d%% of checks) first_fault=%0d fault_code_or=%08h",
                     n_l, n_pv, n_pvh, n_xo, n_smst, n_smrv, n_goo, n_done, n_q, n_flt, (n_flt * 100) / (chk > 0 ? chk : 1), ((n_flt * 1000) / (chk > 0 ? chk : 1)) % 10, first_flt, fc_or);
            for (int bk = 0; bk < 4; bk++)
                $display("LAND_COV bank=%0d writes pc0=%0d pc1=%0d rows=%0d | read lane %0d: reads=%0d nonzero_reads=%0d", bk, cw[bk][0], cw[bk][1], cw[bk][2], bk, cr[bk], cnz[bk]);
            $display("LAND_COV export_read_cycles=%0d export_nonzero_reads=%0d same_bank_double_reads=%0d", cx_rd, cx_nz, cx_same);
            $display("LAND_PROG_GROUPS (qrq,score,pv,smrow,o,fcx) m=%0d,%0d,%0d,%0d,%0d,%0d ml=%0d,%0d,%0d,%0d,%0d,%0d mq=%0d,%0d,%0d,%0d,%0d,%0d",
                     gc[0], gc[1], gc[2], gc[3], gc[4], gc[5], g2[0], g2[1], g2[2], g2[3], g2[4], g2[5], g3[0], g3[1], g3[2], g3[3], g3[4], g3[5]);
            $display("%s SRAM landing store vs flop form: mismatching cycles=%0d first=%0d", err_c == 0 ? "PASS" : "FAIL", err_c, first_c);
            $display("%s mutant ml (landing macros read one cycle late): mismatching cycles=%0d first=%0d", err_m2 != 0 ? "CAUGHT" : "MISSED", err_m2, first_m2);
            $display("%s mutant mq (sw / wq / qmem macros read one cycle late): mismatching cycles=%0d first=%0d", err_m3 != 0 ? "CAUGHT" : "MISSED", err_m3, first_m3);
            begin : verdict
                bit cov_ok; cov_ok = 1;
                for (int bk = 0; bk < 4; bk++) if (cw[bk][0] + cw[bk][1] == 0 || cw[bk][2] == 0 || cnz[bk] == 0) cov_ok = 0;
                if (ROWX != 0 && (cx_nz == 0 || cx_same == 0 || n_xo == 0)) cov_ok = 0;
                $display("LAND_PROG_VERDICT %s (m mismatches=%0d, ml %s, mq %s, landing coverage %s, f fault %0d of %0d checks, programme %s)",
                         (err_c == 0 && err_m2 != 0 && err_m3 != 0 && cov_ok && n_flt * 10 <= chk && prog_done != 0) ? "PASS" : "FAIL", err_c,
                         err_m2 != 0 ? "caught" : "MISSED", err_m3 != 0 ? "caught" : "MISSED", cov_ok ? "ok" : "ZERO", n_flt, chk,
                         prog_done != 0 ? "done" : "TIMEOUT");
            end
            if (fdmp != 0) $fclose(fdmp);
            $finish;
        end
    end
endmodule
