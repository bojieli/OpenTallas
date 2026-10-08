// qwen-band-integrate 2026-10-08: the r21m split spine end to end against the monolithic spine.
// Reference: ot_qwen_me_spine_h_w12 (the monolithic spine: 16 full lanes, result groups in group order) writing its
// result / maxima rows into a behavioural memory at its engine edges.  DUT: ot_qfd_spine_band = the tree top in BAND
// mode (control element RX = 5 + 2 LNK, BANDF, ot_qfd_band_upper inside, DLY = OS + CLNK + 2 + LNK) + 6 band-lane blocks
// (ot_qfd_band_lanes) on LNK-relayed word links and a CLNK-relayed control link + the port groups in the band-local
// frame (ot_qwen_me_spport_w12 BANDF) + the qwen-vm-me result path: 6 band serializers (ot_qfd_res_ser, 8 slots = the
// band's slots) into the banked vector memory's merge (ot_qfd_sp_vector_memory_bv), land_cnt back to the tree top.
// One gated engine clock (the stall loop) drives both spines.  Checked every engine edge: issue-side outputs equal
// (ready, x reads, ROM / KV strobes, broadcast, x network); result-side outputs equal to the reference's delayed
// RD = 5 + 2 LNK engine edges (ov, scale_re, argmax, maxima row); each burst's written rows (address, mask, masked
// data), in position order, equal to the reference burst's rows in group order (band-major slot order = ascending
// group); the DUT's progress never ahead; at every DUT idle rise every touched row equal to the reference; the final
// image; no fault (the band / upper lockstep checks included).  Splits SMIN..SMAX uniformly (counted per split).
// Mutants (must FAIL): BMUT 1 (band level TCUT+2 pairing), UMUT 2 (upper level TCUT+4 pairing), PBANDF 0 (port groups
// indexed by position), DMUT 1 (the upper's control delay without the CLNK relays).
module tb_qfd_spine_band;
    parameter integer W = 16, IL = 8, AW = 24, NW = 18;
    parameter integer TCUT = 3, GT = 48 << TCUT, TG = 4, SMIN = TCUT, SMAX = TCUT + 6, NS = 8;
    parameter integer LNK = 0, CLNK = 0, BMUT = 0, UMUT = 0, PBANDF = 1, DMUT = 0;
    parameter integer QB = 8;              // quiet windows: 2^QB of every 2^(QB+2) engine edges without issue
    parameter integer BD = 4, XVM = 1, NWS = 1, TWS = 2, ORD = 1, MEM_EXTRA = 0, SCALE_LOCAL = 0;
    parameter integer ACC_LAT = 7, TREE_LAT = 7, MUL_LAT = 6, FAST_ISSUE = 1, KV_PREP = 3;
    parameter integer MAXT = 3, MAXK = 4, SEED = 1, SMUT = 0, CYCLES = 30000, DB = 16, RSD = 4, CRB = 4;
    localparam integer NPG = GT >> SMIN, NXC = 1 << SMAX, NPT = GT >> TCUT, IBW = 3*NW + 13*AW + 13;
    localparam integer NB = NPG / NS, ELEMS = 65536, NRB = 16, RW = AW - 4;
    localparam integer LAWT = $clog2((ELEMS / 16 + NRB - 1) / NRB);
    localparam integer RD = 5 + 2 * LNK;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    // ---- engine clock ----
    wire me_ok;
    reg  me_want;
    reg  [RSD:0] okd;
    always @(posedge clk or negedge rst_n) if (!rst_n) okd <= 0; else okd <= {okd[RSD-1:0], me_ok};
    reg  stall_on, stim_on;
    reg  [63:0] ecyc;
    wire me_en = me_want && (okd[RSD-1] || !stall_on);
    wire gclk;
    ot_hdc_cg u_cg (.clk(clk), .en(me_en || !rst_n), .gclk(gclk));
    // ---- engine-time stimulus (as tb_qfd_tree_top_lockstep; result / maxima addresses inside the memory) ----
    reg go;
    reg [NW-1:0] i_nout, i_tiles, i_k;
    reg i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax;
    reg [AW-1:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase;
    reg [2:0] i_jsh;
    reg [3:0] i_split;
    reg [NPT*W*32-1:0] t_lvl;
    reg [NXC*32-1:0] x_q;
    function automatic [31:0] rfloat(input [31:0] r); rfloat = {r[31], 8'd100 + {3'd0, r[27:23]}, r[22:0]}; endfunction
    function automatic [15:0] rscale(input [31:0] a, input integer lane);
        reg [31:0] h;
        begin h = a * 32'h9E3779B1 + lane * 32'h85EBCA6B; h = h ^ (h >> 15); rscale = {h[15], 8'd120 + {5'd0, h[2:0]}, h[13:7]}; end
    endfunction
    integer n;
    always @(posedge gclk) begin
        if (!rst_n) go <= 1'b0;
        else begin
            go <= stim_on && (ecyc[QB+1 -: 2] != 2'd3) && (($urandom % 4) == 0);   // quiet windows: the units go idle
            i_tiles <= 1 + ($urandom % MAXT); i_k <= 1 + ($urandom % MAXK);
            i_wsrc <= ($urandom % 3) == 0; i_round <= $urandom % 2;
            i_mmode <= ($urandom % 4) == 0; i_oen <= ($urandom % 8) != 0;
            i_amax <= ($urandom % 3) == 0; i_rmax <= ($urandom % 4) == 0;
            i_wbase <= $urandom; i_ts <= $urandom; i_ks <= $urandom; i_js <= $urandom; i_xbase <= $urandom;
            i_xks <= $urandom; i_xjs <= $urandom; i_xcs <= $urandom; i_wcs <= $urandom;
            // result rows stay inside the bench memory (ELEMS / 16 rows; a row past it would alias in the VM)
            i_nout <= $urandom % 8192;
            i_obase <= $urandom % 512; i_ots <= $urandom % 4; i_ojs <= $urandom % 4;
            i_mbase <= 50000 + ($urandom % 8192); i_jsh <= $urandom % 4;
            i_split <= SMIN + ($urandom % (SMAX - SMIN + 1));
        end
        for (n = 0; n < NPT * W; n = n + 1) t_lvl[n*32 +: 32] <= rfloat($urandom);
        for (n = 0; n < NXC; n = n + 1) x_q[n*32 +: 32] <= $urandom;
    end
`define SPINE_PORTS(P) \
        .clk(gclk), .rst_n(rst_n), .go(go), .ready(P``ready), .idle(P``idle), \
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc), \
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js), \
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs), \
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round), \
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs), \
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase), \
        .scale_re(P``scale_re), .scale_gre(P``scale_gre), .scale_addr(P``scale_addr), .scale_q(P``scale_q), \
        .x_re(P``x_re), .x_addr(P``x_addr), .x_q(x_q), \
        .wrom_re(P``wrom_re), .wrom_addr(P``wrom_addr), .kv_re(P``kv_re), \
        .tgo(P``tgo), .tb(P``tb), .xl_d(P``xl_d), .t_lvl(t_lvl), .fab_fault(1'b0), \
        .ov(P``ov), .o_we(P``o_we), .o_addr(P``o_addr), .o_mask(P``o_mask), .o_data(P``o_data), \
        .am_idx(P``am_idx), .am_val(P``am_val), .am_any(P``am_any), \
        .mx_we(P``mx_we), .mx_addr(P``mx_addr), .mx_mask(P``mx_mask), .mx_data(P``mx_data), \
        .progress(P``progress), .fault(P``fault)
`define SPINE_WIRES(P) \
    wire P``ready, P``idle, P``scale_re, P``wrom_re, P``kv_re, P``tgo, P``ov, P``am_any, P``mx_we, P``fault; \
    wire [NPG-1:0] P``scale_gre, P``o_we; wire [NPG*AW-1:0] P``scale_addr, P``o_addr; \
    reg  [NPG*W*16-1:0] P``scale_q; wire [NXC-1:0] P``x_re; wire [NXC*AW-1:0] P``x_addr; \
    wire [AW-1:0] P``wrom_addr, P``mx_addr; wire [IBW-1:0] P``tb; wire [NXC*32-1:0] P``xl_d; \
    wire [NPG*W-1:0] P``o_mask; wire [NPG*W*32-1:0] P``o_data; wire [NW-1:0] P``am_idx; wire [31:0] P``am_val; \
    wire [W-1:0] P``mx_mask; wire [W*32-1:0] P``mx_data; wire [15:0] P``progress;
    `SPINE_WIRES(a_)
    `SPINE_WIRES(b_)
    wire [15:0] land_cnt;
    ot_qwen_me_spine_h_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .MEM_EXTRA(MEM_EXTRA), .SCALE_LOCAL(SCALE_LOCAL),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .MUL_LAT(MUL_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP))
        u_a (`SPINE_PORTS(a_));
    ot_qfd_spine_band #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT),
        .BD(BD), .XVM(XVM), .NWS(NWS), .TWS(TWS), .ORD(ORD), .MEM_EXTRA(MEM_EXTRA), .SCALE_LOCAL(SCALE_LOCAL),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .MUL_LAT(MUL_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP),
        .LANDED(1), .LNK(LNK), .CLNK(CLNK), .BMUT(BMUT), .UMUT(UMUT), .PBANDF(PBANDF), .DMUT(DMUT))
        u_b (.land_cnt(land_cnt), `SPINE_PORTS(b_));
    integer g, l;
    always @(posedge gclk) begin
        for (g = 0; g < NPG; g = g + 1) begin
            if (a_scale_gre[g]) for (l = 0; l < W; l = l + 1) a_scale_q[(g*W + l)*16 +: 16] <= rscale(a_scale_addr[g*AW +: AW], l);
            if (b_scale_gre[g]) for (l = 0; l < W; l = l + 1) b_scale_q[(g*W + l)*16 +: 16] <= rscale(b_scale_addr[g*AW +: AW], l);
        end
    end
    // ---- DUT result path ----
    wire [NB-1:0] l_v, l_end, l_nul, l_cr, l_ok, l_fault;
    wire [NB*RW-1:0] l_row;
    wire [NB*16-1:0] l_mask;
    wire [NB*512-1:0] l_data;
    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_ser
        ot_qfd_res_ser #(.NS(NS), .W(16), .AW(AW), .RW(RW), .DB(DB), .RS(RSD + 2), .CRB(CRB), .MUT(gb == 0 ? SMUT : 0)) u_s (
            .clk(clk), .rst_n(rst_n), .me_en(me_en), .i_ov(b_ov), .i_we(b_o_we[gb*NS +: NS]),
            .i_addr(b_o_addr[gb*NS*AW +: NS*AW]), .i_mask(b_o_mask[gb*NS*16 +: NS*16]), .i_data(b_o_data[gb*NS*512 +: NS*512]),
            .o_v(l_v[gb]), .o_end(l_end[gb]), .o_nul(l_nul[gb]), .o_row(l_row[gb*RW +: RW]), .o_mask(l_mask[gb*16 +: 16]),
            .o_data(l_data[gb*512 +: 512]), .o_cr(l_cr[gb]), .rok(l_ok[gb]), .fault(l_fault[gb]));
    end endgenerate
    wire m_xf, m_xh, m_wf, m_wh;
    ot_qfd_sp_vector_memory_bv #(.ELEMS(ELEMS), .NRB(NRB), .AW(AW), .SMIN(3), .SMAX(7), .XVM(12), .BMAX(4), .ND(9),
        .DSET({8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0}), .SW(8), .NSU(3), .NB(NB), .CRB(CRB)) vm (
        .clk(clk), .rst_n(rst_n), .me_en(me_en), .x_dv(1'b0), .x_dc(24'd0), .x_dcs(24'd1), .x_dsp(4'd3), .x_q(),
        .x_rdy(), .x_fault(m_xf), .x_hazard(m_xh),
        .s_re0(3'd0), .s_re1(3'd0), .s_a0(72'd0), .s_a1(72'd0), .s_q(),
        .sw_mask(8'd0), .sw_a0(24'd0), .sw_a1(24'd0), .sw_data(256'd0),
        .rd_v(1'b0), .rd_addr(24'd0), .rd_data(32'd0),
        .w_v(1'b0), .w_row(20'd0), .w_mask(16'd0), .w_data(512'd0),
        .r_v(1'b0), .r_rdy(), .r_row(20'd0), .r_qv(), .r_q(),
        .mx_we(b_mx_we), .mx_addr(b_mx_addr), .mx_mask(b_mx_mask), .mx_data(b_mx_data),
        .rb_v(l_v), .rb_end(l_end), .rb_nul(l_nul), .rb_row(l_row), .rb_mask(l_mask), .rb_data(l_data), .rb_cr(l_cr),
        .rb_ok(l_ok), .me_ok(me_ok), .land_cnt(land_cnt), .w_fault(m_wf), .w_hazard(m_wh));
    // ---- reference memory (engine edges, base order: result groups ascending, then maxima) and the DUT shadow ----
    reg [511:0] refm [0:ELEMS/16-1];
    reg [511:0] shadow [0:ELEMS/16-1];
    reg         touched [0:ELEMS/16-1];
    integer r, sb;
    integer oob = 0;
    always @(posedge gclk) if (rst_n) begin
        for (g = 0; g < NPG; g = g + 1) if (a_o_we[g]) begin
            r = a_o_addr[g*AW +: AW];
            if (r >= ELEMS / 16) oob = oob + 1;
            if (r < ELEMS / 16) begin
                for (l = 0; l < W; l = l + 1) if (a_o_mask[g*W + l]) refm[r][32*l +: 32] = a_o_data[(g*W + l)*32 +: 32];
                touched[r] = 1'b1;
            end
        end
        if (a_mx_we) begin
            r = a_mx_addr;
            if (r < ELEMS / 16) begin
                for (l = 0; l < W; l = l + 1) if (a_mx_mask[l]) refm[r][32*l +: 32] = a_mx_data[l*32 +: 32];
                touched[r] = 1'b1;
            end
        end
    end
    always @(posedge clk) if (rst_n)
        for (sb = 0; sb < NRB; sb = sb + 1) if (vm.bw_we[sb]) begin
            r = vm.bw_line[sb*LAWT +: LAWT] * NRB + sb;
            for (l = 0; l < 16; l = l + 1) if (vm.bw_mask[sb*16 + l]) shadow[r][32*l +: 32] <= vm.bw_data[sb*512 + 32*l +: 32];
        end
    // ---- the reference's result side, RD engine edges late ----
    localparam integer RSW = 1 + 1 + 1 + NW + 32 + 1 + AW + W + W*32 + NPG + NPG*AW + NPG*W + NPG*W*32;
    reg [RSW*(RD+1)-1:0] rline;
    wire [RSW-1:0] rnow = {a_ov, a_scale_re, a_am_any, a_am_idx, a_am_val, a_mx_we, a_mx_addr, a_mx_mask, a_mx_data,
                           a_o_we, a_o_addr, a_o_mask, a_o_data};
    always @(posedge gclk) rline <= {rline[RSW*RD-1:0], rnow};
    wire d_ov, d_scale_re, d_am_any, d_mx_we;
    wire [NW-1:0] d_am_idx; wire [31:0] d_am_val; wire [AW-1:0] d_mx_addr; wire [W-1:0] d_mx_mask; wire [W*32-1:0] d_mx_data;
    wire [NPG-1:0] d_o_we; wire [NPG*AW-1:0] d_o_addr; wire [NPG*W-1:0] d_o_mask; wire [NPG*W*32-1:0] d_o_data;
    assign {d_ov, d_scale_re, d_am_any, d_am_idx, d_am_val, d_mx_we, d_mx_addr, d_mx_mask, d_mx_data,
            d_o_we, d_o_addr, d_o_mask, d_o_data} = rline[RSW*(RD-1) +: RSW];
    // ---- lockstep compare on engine edges ----
    reg [63:0] mism, ops, results, prog_ahead, ovbad, rows_cmp, burst_bad;
    reg [63:0] first_bad;
    reg [63:0] split_ops [0:15];
    reg [ORD:0] o_ov_d;
    integer bad, c, ia, ib, na, nb2, sp;
    always @(posedge gclk) begin
        if (!rst_n) begin
            mism <= 0; ops <= 0; results <= 0; first_bad <= 0; ecyc <= 0; prog_ahead <= 0; ovbad <= 0; o_ov_d <= 0;
            rows_cmp <= 0; burst_bad <= 0;
            for (sp = 0; sp < 16; sp = sp + 1) split_ops[sp] <= 0;
        end else begin
            ecyc <= ecyc + 1;
            o_ov_d <= {o_ov_d[ORD-1:0], u_b.g_port[0].u_pt.o_ov};
            if (ecyc > RD + 2) begin
                bad = 0;
                // issue side: same edge
                if (a_ready !== b_ready || a_x_re !== b_x_re || a_wrom_re !== b_wrom_re ||
                    a_wrom_addr !== b_wrom_addr || a_kv_re !== b_kv_re || a_tgo !== b_tgo || a_tb !== b_tb ||
                    a_xl_d !== b_xl_d) bad = bad | 1;
                for (c = 0; c < NXC; c = c + 1)
                    if (a_x_re[c] && a_x_addr[c*AW +: AW] !== b_x_addr[c*AW +: AW]) bad = bad | 2;
                // result side: RD edges later
                if (d_ov !== b_ov || d_scale_re !== b_scale_re || d_am_any !== b_am_any || d_am_idx !== b_am_idx ||
                    d_am_val !== b_am_val || d_mx_we !== b_mx_we) bad = bad | 4;
                if (d_mx_we && (d_mx_addr !== b_mx_addr || d_mx_mask !== b_mx_mask || d_mx_data !== b_mx_data)) bad = bad | 8;
                // the burst's rows: reference groups ascending vs DUT positions ascending
                if (d_ov) begin
                    ia = 0; ib = 0; na = 0; nb2 = 0;
                    for (c = 0; c < NPG; c = c + 1) begin if (d_o_we[c]) na = na + 1; if (b_o_we[c]) nb2 = nb2 + 1; end
                    if (na != nb2) bad = bad | 16;
                    else begin
                        while (ia < NPG) begin
                            while (ia < NPG && !d_o_we[ia]) ia = ia + 1;
                            while (ib < NPG && !b_o_we[ib]) ib = ib + 1;
                            if (ia < NPG) begin
                                if (d_o_addr[ia*AW +: AW] !== b_o_addr[ib*AW +: AW] || d_o_mask[ia*W +: W] !== b_o_mask[ib*W +: W])
                                    bad = bad | 16;
                                for (l = 0; l < W; l = l + 1)
                                    if (d_o_mask[ia*W + l] && d_o_data[(ia*W + l)*32 +: 32] !== b_o_data[(ib*W + l)*32 +: 32])
                                        bad = bad | 16;
                                ia = ia + 1; ib = ib + 1;
                            end
                        end
                    end
                    rows_cmp <= rows_cmp + na;
                    if (bad & 16) burst_bad <= burst_bad + 1;
                end
                if (b_fault !== 1'b0 || a_fault !== 1'b0) bad = bad | 32;
                if (bad != 0) begin mism <= mism + 1; if (first_bad == 0) first_bad <= {ecyc[55:0], bad[7:0]}; end
                if (b_progress > a_progress) prog_ahead <= prog_ahead + 1;
                if (ORD > 0 && o_ov_d[ORD-1] !== b_ov) ovbad <= ovbad + 1;
                if (go && a_ready) begin ops <= ops + 1; split_ops[i_split] <= split_ops[i_split] + 1; end
                if (a_ov) results <= results + 1;
            end
        end
    end
    // ---- idle soundness: at every DUT idle rise, every touched row equals the reference ----
    reg b_idle_d;
    integer idle_checks, idle_bad, img_bad, i, cyc;
    always @(posedge clk) b_idle_d <= b_idle;
    initial begin
        idle_checks = 0; idle_bad = 0; img_bad = 0; me_want = 1; stall_on = 0; stim_on = 1;
        i = $urandom(SEED);
        for (i = 0; i < ELEMS / 16; i = i + 1) begin refm[i] = 0; shadow[i] = 0; touched[i] = 0; end
        repeat (8) @(negedge clk); rst_n = 1;
        repeat (8) @(negedge clk); stall_on = 1;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            me_want = ($urandom % 8) != 0;
            if (b_idle && !b_idle_d && ecyc > 4) begin
                idle_checks = idle_checks + 1;
                for (i = 0; i < ELEMS / 16; i = i + 1) if (touched[i] && shadow[i] !== refm[i]) idle_bad = idle_bad + 1;
            end
        end
        me_want = 1; stim_on = 0;
        repeat (16) @(negedge clk);
        for (i = 0; i < 20000 && !(b_idle && a_idle); i = i + 1) @(negedge clk);
        repeat (64) @(negedge clk);
        for (i = 0; i < ELEMS / 16; i = i + 1) if (touched[i] && shadow[i] !== refm[i]) img_bad = img_bad + 1;
        for (i = SMIN; i <= SMAX; i = i + 1) $display("split %0d ops %0d", i, split_ops[i]);
        if (mism == 0 && prog_ahead == 0 && ovbad == 0 && idle_bad == 0 && img_bad == 0 && !(|l_fault) && !m_wf && !m_wh &&
            !m_xf && !m_xh && results > 300 && idle_checks > 5 && rows_cmp > 0 && oob == 0)
            $display("PASS qfd_spine_band GT=%0d TCUT=%0d splits=%0d..%0d LNK=%0d CLNK=%0d RD=%0d engine_edges=%0d ops=%0d bursts=%0d rows=%0d landed=%0d idle_checks=%0d",
                     GT, TCUT, SMIN, SMAX, LNK, CLNK, RD, ecyc, ops, results, rows_cmp, land_cnt, idle_checks);
        else
            $display("FAIL qfd_spine_band oob=%0d mism=%0d first=%0d/%0d burst_bad=%0d prog_ahead=%0d ovbad=%0d idle_bad=%0d img_bad=%0d faults ser%b w%0d wh%0d bursts=%0d rows=%0d idle_checks=%0d",
                     oob, mism, first_bad >> 8, first_bad & 8'hff, burst_bad, prog_ahead, ovbad, idle_bad, img_bad, l_fault, m_wf, m_wh, results, rows_cmp, idle_checks);
        $finish;
    end
endmodule
