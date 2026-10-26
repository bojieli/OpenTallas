module dsdv_idx_tx_n32__reference #(
    parameter integer V = 276,
    parameter integer IK = 4,
    parameter integer EK = 5,
    parameter integer UID = 8'h5C,
    parameter integer D = 8192,
    parameter integer IB = 64,
    parameter bit SRAM_MACRO = 0,
    parameter integer MUT = 0,
    parameter integer RDL = 0,      // STW-S81c-COLLA 10-22: score-store read capture at the macro pins (+1 lookup edge)
    parameter integer WDL = 0,      // score-store write landing per bank (+1 write edge)
    parameter integer WDC = 0,      // STW-S81c-COLLA2-TX 10-22: column-B copy of the score-store write port (0 cycles)
    parameter integer SCS = 0,      // STW-S81c-COLLA2-TX 10-22: grid-slot count compare carry-selected off slot_q (0 cycles)
    parameter integer RIL = 0,      // STW-S81c-COLLA2 10-22: score-store read issue landed at the macro pins (+1 lookup edge)
    parameter integer RHP = 0,      // STW-S81c-COLLA2 10-22: result-FIFO head prefetched into a register (0 cycles)
    parameter integer SPLIT = 0     // STW-S81c-TOK4 10-22: score store as two bank groups (column A hardened child), 0 cycles
) (
    input  wire          ck,
    input  wire          rst,       // active low (as dsdv_idx_tx / the bk_sel rst_n)
    input  wire [V-1:0]  vi,        // tap: u_sel.vi_s (the vmux output)
    input  wire [V-1:0]  vo,        // tap: u_sel.vo_s
    output reg  [V-1:0]  lo,        // tree link to the parent die
    output reg  [15:0]   st
);
    localparam integer AW = $clog2(D), IW = $clog2(IB);
    localparam integer IBD = (IB < 1024) ? 1024 : IB, IBA = $clog2(IBD);

    // ------------------------------------------------------------------ reset forest (control / valid bits only)
    // rl[0] pins + lookup control (24), rl[1] job / staging control (19), rl[2] CTL copies + faults (23),
    // rl[3] output selects + lo[0] (25), rl[4] status (16).
    wire [6:0] rl;
    ot_rst_relay #(.REGIONS(7), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst), .rst_n(rl));

    // ------------------------------------------------------------------ pin registers
    reg [V-1:0] vi_r, vo_r;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin vi_r[0] <= 1'b0; vo_r[0] <= 1'b0; end
        else begin vi_r[0] <= vi[0]; vo_r[0] <= vo[0]; end
    always @(posedge ck) begin vi_r[V-1:1] <= vi[V-1:1]; vo_r[V-1:1] <= vo[V-1:1]; end

    // ------------------------------------------------------------------ one-edge-early selects from the pins (kept)
    wire       n_p0w  = vi[0] && vi[3:1] == 3'(IK) && !vi[6] && !vi[7];      // BEAT part 0 of kind IK
    wire       n_octl = vo[0] && vo[3:1] == 3'd0 && vo[28:21] == 8'(UID) && vo[31:29] == 3'd2;
    wire       n_ep0  = vo[0] && vo[3:1] == 3'(EK) && !vo[6];                 // egress part 0
    (* keep = "true" *) reg [63:0] hsw;      // [8 l + c]: hs[l][32 c +: 32] write enable
    (* keep = "true" *) reg [31:0] shs;      // [8 l + c]: lane l one-hot for m_wd[32 c +: 32]
    (* keep = "true" *) reg [3:0]  scl_m, scl_w;
    (* keep = "true" *) reg [15:0] eph;      // e_lo[32 c +: 32] load
    (* keep = "true" *) reg [17:0] okk;      // [16]: second sn copy (t/u census okk[12] 34 loads); [17]: nx_sm[5:0] (x census okk[14] 38)
         // the CTL (o_ctl) copies, see the job block
    always @(posedge ck) begin : g_pre
        integer l_, c_;
        for (l_ = 0; l_ < 4; l_ = l_ + 1) begin
            for (c_ = 0; c_ < 16; c_ = c_ + 1)
                hsw[16*l_+c_] <= n_p0w && vi[5:4] == 2'(l_);
            for(c_=0;c_<8;c_=c_+1)shs[8*l_+c_] <= vi[5:4] == 2'(l_);
            scl_m[l_] <= vi[5:4] == 2'(l_);
            scl_w[l_] <= vi[5:4] == 2'(l_);
        end
        eph <= {16{n_ep0}};
    end
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) okk[15:0] <= 16'd0; else okk[15:0] <= {16{n_octl}};
    always @(posedge ck or negedge rl[3]) if (!rl[3]) okk[16] <= 1'b0; else okk[16] <= n_octl;   // own reset leaf (rl[2] at 33)
    always @(posedge ck or negedge rl[3]) if (!rl[3]) okk[17] <= 1'b0; else okk[17] <= n_octl;

    reg [7:0] fc_set, fc;

    // ------------------------------------------------------------------ capture
    wire        c_v  = vi_r[0] && vi_r[3:1] == 3'(IK);
    wire        c_p1 = vi_r[6], c_sg = vi_r[7];
    wire [3:0]  c_ty = vi_r[19:16];
    reg  [19:0] cur [0:3];
    reg  [255:0] hs [0:3];
    reg  [19:0] c_cur;
    integer li;
    always @* begin
        c_cur = 20'd0;
        for (li = 0; li < 4; li = li + 1) c_cur = c_cur | (cur[li] & {20{scl_m[li]}});
    end
    function automatic [255:0] lvmask(input [15:0] lv);
        integer i_; lvmask = 256'd0;
        for (i_ = 0; i_ < 16; i_ = i_ + 1) lvmask[16 * i_ +: 16] = {16{lv[i_]}};
    endfunction
    always @(posedge ck) begin : g_cap
        integer l_, c_;
        for (l_ = 0; l_ < 4; l_ = l_ + 1) begin
            if (scl_w[l_] && c_v && !c_p1 && c_sg && (c_ty == 4'd1 || c_ty == 4'd6)) cur[l_] <= vi_r[39:20];
            else if (scl_w[l_] && c_v && c_p1) cur[l_] <= c_cur + 20'd16;
            for(c_=0;c_<16;c_=c_+1)if(hsw[16*l_+c_])hs[l_][16*c_+:16]<=vi_r[20+16*c_+:16];
        end
    end
    // score-store write port: free-running data / address / mask (used only with m_we), m_we = a BEAT part 1
    reg         m_we; reg [AW-1:0] m_wa; reg [255:0] m_wd, m_wm;
    always @(posedge ck or negedge rl[0]) if (!rl[0]) m_we <= 1'b0; else m_we <= c_v && c_p1;
    reg  [255:0] m_wd_d;
    always @* begin : g_mwd
        integer l_, c_; reg [31:0] x_;
        for (c_ = 0; c_ < 8; c_ = c_ + 1) begin
            x_ = 32'd0;
            for (l_ = 0; l_ < 4; l_ = l_ + 1) x_ = x_ | (hs[l_][32 * c_ +: 32] & {32{shs[8 * l_ + c_]}});
            m_wd_d[32 * c_ +: 32] = x_;
        end
    end
    always @(posedge ck) begin : g_mw
        m_wa <= AW'(c_cur[19:4]);
        m_wm <= (MUT == 4) ? {256{1'b1}} : lvmask(vi_r[35:20]);
        m_wd <= m_wd_d;
    end
    // WDC: column-B write port = kept copies of m_we / m_wa / m_wd (same D, same reset, same edge)
    wire m_we_b; wire [AW-1:0] m_wa_b; wire [255:0] m_wd_b;
    generate if (WDC != 0) begin : g_wdc
        dsdv_tx_copy #(.W(1),.RESET(1),.ID(8100))u_we(.ck(ck),.rn(rl[0]),.d(c_v && c_p1),.q(m_we_b));
        dsdv_tx_copy #(.W(AW),.ID(8101))u_wa(.ck(ck),.rn(1'b1),.d(AW'(c_cur[19:4])),.q(m_wa_b));
        dsdv_tx_copy #(.W(256),.ID(8102))u_wd(.ck(ck),.rn(1'b1),.d(m_wd_d),.q(m_wd_b));
    end else begin : g_wdc0
        assign m_we_b = m_we; assign m_wa_b = m_wa; assign m_wd_b = m_wd;
    end endgenerate
    wire cap_unal = c_v && c_p1 && c_cur[3:0] != 4'd0;

    // ------------------------------------------------------------------ job fields (CTL on vo), kept-copy enables
    wire         o_v  = vo_r[0];
    wire [185:0] cp   = vo_r[21 +: 186];
    wire         o_eg = o_v && vo_r[3:1] == 3'(EK);
    reg  [1:0]  j_l; reg [7:0] j_pt, j_ot; reg [9:0] j_k; reg [19:0] j_hb; reg [15:0] j_dly; reg [2:0] j_r; reg [11:0] j_sm;
    always @(posedge ck) begin
        if(okk[0])begin j_l<=cp[22:21];j_pt<=cp[30:23];end
        if(okk[1])begin j_k<=cp[40:31];j_r<=cp[87:85];end
        if(okk[2])j_hb[9:0]<=cp[50:41];
        if(okk[3])j_hb[19:10]<=cp[60:51];
        if(okk[4])j_ot<=cp[68:61];
        if(okk[5])j_sm<=cp[99:88];
        if(okk[6])j_dly<=cp[84:69];
    end

    // ------------------------------------------------------------------ egress capture -> IDX buffer
    reg  [255:0] e_lo;
    always @(posedge ck) begin : g_elo
        integer c_;
        for(c_=0;c_<16;c_=c_+1)if(eph[c_])e_lo[16*c_+:16]<=vo_r[20+16*c_+:16];
    end
    reg          armed, busy, done, in_end, e_h;
    wire [511:0] e_w    = {vo_r[275:20], e_lo};
    wire         e_cpl  = o_eg && vo_r[6] && e_h;
    wire         e_mine = e_w[507:500] == j_ot;
    reg  [IW:0]  ib_w, ib_r;
    wire         ib_push = armed && e_cpl && e_mine && e_w[511:508] == 4'd3;
    wire         ib_re;
    wire [511:0] ib_q;
    dsdv_idx_txm #(.D(IBD), .SRAM_MACRO(SRAM_MACRO)) u_ib0 (.ck(ck), .re(ib_re), .ra(IBA'(ib_r[IW-1:0])),
        .rd(ib_q[255:0]), .we(ib_push), .wa(IBA'(ib_w[IW-1:0])), .wd(e_w[255:0]), .wm({256{1'b1}}));
    dsdv_idx_txm #(.D(IBD), .SRAM_MACRO(SRAM_MACRO)) u_ib1 (.ck(ck), .re(ib_re), .ra(IBA'(ib_r[IW-1:0])),
        .rd(ib_q[511:256]), .we(ib_push), .wa(IBA'(ib_w[IW-1:0])), .wd(e_w[511:256]), .wm({256{1'b1}}));

    // ------------------------------------------------------------------ lookup
    reg  [1:0]  fw;
    (* keep = "true" *) reg [19:0]fwk;        // fw[1] copies: iw[32 c +: 32] load
    wire fw_ctl,fw_lvl;
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(2000))u_fwc(.ck(ck),.rn(rl[0]),.d(fw[0]),.q(fw_ctl));
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(2001))u_fwl(.ck(ck),.rn(rl[0]),.d(fw[0]),.q(fw_lvl));
    reg         iw_v;
    assign      ib_re = !iw_v && fw == 2'b00 && ib_r != ib_w && armed;
    reg  [319:0] iw;                          // 16 x 20-b selected positions (bits [335:320] = lv go to lvl)
    reg  [15:0] lvl;
    reg [15:0] lvl_next;
    reg  [3:0]  rq_n;
    wire        rq_room = rq_n < 4'd5;
    reg  [3:0]  ne; reg ne_v;
    integer bi_;
    always @* begin
        ne = 4'd0; ne_v = 1'b0;
        for (bi_ = 15; bi_ >= 0; bi_ = bi_ - 1) if (lvl[bi_]) begin ne = 4'(bi_); ne_v = 1'b1; end
    end
    wire[19:0]ne_idx,ne_mem_idx;
    dsdv_tx_priority_mux #(.W(10),.OFF(0),.ID(6100))u_pix0(.ck(ck),.lvl_next(lvl_next),.iw(iw),.q(ne_idx[9:0]));
    dsdv_tx_priority_mux #(.W(10),.OFF(10),.ID(6101))u_pix1(.ck(ck),.lvl_next(lvl_next),.iw(iw),.q(ne_idx[19:10]));
    dsdv_tx_priority_mux #(.W(8),.OFF(4),.ID(6102))u_pim0(.ck(ck),.lvl_next(lvl_next),.iw(iw),.q(ne_mem_idx[11:4]));
    dsdv_tx_priority_mux #(.W(8),.OFF(12),.ID(6103))u_pim1(.ck(ck),.lvl_next(lvl_next),.iw(iw),.q(ne_mem_idx[19:12]));
    assign ne_mem_idx[3:0]=4'd0; // not consumed by score-memory address
    wire lk_go=iw_v&&ne_v&&rq_room;
    always @* begin
        lvl_next=fw_lvl?ib_q[335:320]:lvl;
        if(lk_go)lvl_next[ne]=1'b0;
    end
    wire [255:0] m_rd;
    dsdv_idx_txm_n32 #(.D(D), .SRAM_MACRO(SRAM_MACRO), .RDL(RDL), .WDL(WDL), .WDC(WDC), .RIL(RIL), .RIL_MUT(MUT == 5), .SPLIT(SPLIT)) u_sm (.ck(ck), .re(lk_go), .ra(AW'(ne_mem_idx[19:4])), .rd(m_rd),
        .we(m_we), .wa(m_wa), .wd(m_wd), .wm(m_wm),.wm_next((MUT==4)?16'hffff:vi_r[35:20]),
        .we_b(m_we_b), .wa_b(m_wa_b), .wd_b(m_wd_b));
    localparam integer LP = 2 + ((RDL != 0) ? 1 : 0) + ((RIL != 0) ? 1 : 0);   // lookup pipe: issue -> rd valid
    reg  [LP-1:0] lp_v; reg [19:0] lp_i [0:LP-1];
    reg  [35:0] rf [0:7];
    reg  [2:0]  rf_w, rf_r; reg [3:0] rf_n;
    wire [3:0]  sel_f = (MUT == 1) ? lp_i[LP-1][3:0] + 4'd1 : lp_i[LP-1][3:0];
    // STW-S81c-TOK4 10-22 (x gate native census: lp_i[LP-1][3:0] drove the 16-way decode, 80..125 loads): with RIL the
    // beat select is a REGISTERED one-hot formed from lp_i[LP-2] on the same edge that loads lp_i[LP-1] (0 cycles, each
    // bit 16 loads).
    wire [3:0]  sel_p = (MUT == 1) ? lp_i[LP-2][3:0] + 4'd1 : lp_i[LP-2][3:0];
    (* keep = "true" *) reg [15:0] sel_oh;
    always @(posedge ck) sel_oh <= 16'd1 << sel_p;
    reg  [15:0] lk_s;
    always @* begin
        lk_s = 16'd0;
        for (bi_ = 0; bi_ < 16; bi_ = bi_ + 1)
            lk_s = lk_s | (m_rd[16 * bi_ +: 16] & {16{(RIL != 0) ? sel_oh[bi_] : sel_f == 4'(bi_)}});
    end
    wire        rf_pop;
    wire        rf_pop_r;               // read-select copy feed (second pop predicate instance)
    wire        lk_idle = !iw_v && fw == 2'b00 && lp_v == '0 && ib_r == ib_w;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin
            fw <= 2'b00; iw_v <= 1'b0; lp_v <= '0; rf_w <= 3'd0; rf_r <= 3'd0; rf_n <= 4'd0; ib_r <= '0;
        end else begin
            fw <= {fw[0], ib_re};
            if (ib_re) ib_r <= ib_r + 1'b1;
            if (fw_ctl) iw_v <= 1'b1;
            if (lk_go && (lvl & ~(16'd1 << ne)) == 16'd0) iw_v <= 1'b0;
            if (iw_v && !ne_v) iw_v <= 1'b0;
            lp_v <= LP'({lp_v, lk_go});
            if (lp_v[LP-1]) rf_w <= rf_w + 1'b1;
            if (rf_pop) rf_r <= rf_r + 1'b1;
            rf_n <= rf_n + (lp_v[LP-1] ? 4'd1 : 4'd0) - (rf_pop ? 4'd1 : 4'd0);
        end
    always @(posedge ck) begin : g_lk
        integer c_;
        fwk <= {20{fw[0]}};
        for(c_=0;c_<20;c_=c_+1)if(fwk[c_])iw[16*c_+:16]<=ib_q[16*c_+:16];
        lvl<=lvl_next;
        lp_i[0] <= ne_idx; for (c_ = 1; c_ < LP; c_ = c_ + 1) lp_i[c_] <= lp_i[c_ - 1];

    end
    always @* begin : g_rqn
        integer q_; rq_n = rf_n;
        for (q_ = 0; q_ < LP; q_ = q_ + 1) rq_n = rq_n + 4'(lp_v[q_]);
    end

    // ------------------------------------------------------------------ window store (2 buffers) + beat descriptor
    reg         wv;                          // a window is open (in buffer act)
    reg         act;                         // buffer of the open window
    reg  [19:0] w0c;                         // the open window's base
    wire [19:0] w0b [0:1]; wire [15:0] wlvb [0:1]; wire [255:0] wscb [0:1];
    reg  [19:0] lcur;                        // the parent lane's cursor
    reg  [2:0]  bq_n;                        // beats left in the descriptor
    reg  [1:0]  bix;                         // next beat index of the descriptor
    reg         d_h, d_buf, d_rb, d_em, d_last;   // descriptor: HDR / buffer / REBASE first / empty / last
    reg         hdr_q, fin;
    reg  [15:0] tc; reg [2:0] rc; reg [11:0] sn;
    reg         slot_q;                      // = the grid slot of this cycle (precomputed from the next state)
    wire[35:0]rh;
    wire[2:0]rf_read_next=rf_r+3'(rf_pop_r),rf_write_next=rf_w+3'(lp_v[LP-1]);
    wire rf_pop_h;                      // RHP: third pop predicate instance (head select of fields 5..8)
    wire rf_pop_k;                      // RIL: fourth pop predicate instance (head select of fields 6..8)
    wire [71:0] rf_go;                  // RHP: entry a field c write enable of this edge (the g_rf_write go copies)
    generate for(genvar c=0;c<9;c=c+1)begin:g_rf_read
        wire[2:0]sel;
        dsdv_tx_copy #(.W(3),.RESET(1),.ID(3000+c))u(.ck(ck),.rn(rl[5+(c>=5)]),.d(rf_read_next),.q(sel));
        if (RHP == 0) begin : g_comb
            reg[3:0]part;
            always @*begin part=0;for(integer a=0;a<8;a=a+1)part=part|(rf[a][4*c+:4]&{4{sel==3'(a)}});end
            assign rh[4*c+:4]=part;
        end else begin : g_pf
            // STW-S81c-COLLA2 10-22 (TX v/w REJECTED: reg->reg -164.6 on the 16-level sel -> rf read mux -> r_in compare
            // -> pop -> next state -> srb stage): the head rh = rf[sel] after every edge is REGISTERED.  In the cycle
            // before, both candidates rf'[sel] and rf'[sel + 1] are formed (rf' = rf with this edge's write go/data
            // bypassed in) and the pop of this cycle (sel' = sel + pop) only selects: rh_q == rf'[sel'] == the old
            // combinational rh after the edge -> same values at the same edges (0 cycles).
            wire[2:0]sel1;
            dsdv_tx_copy #(.W(3),.RESET(1),.ID(3100+c))u1(.ck(ck),.rn(rl[5+(c>=5)]),.d(rf_read_next+3'd1),.q(sel1));
            wire[35:0]wdat={lp_i[LP-1],lk_s};
            reg[3:0]c0,c1;
            always @*begin
                c0=0;c1=0;
                for(integer a=0;a<8;a=a+1)begin
                    c0=c0|((rf_go[a*9+c]?wdat[4*c+:4]:rf[a][4*c+:4])&{4{sel==3'(a)}});
                    c1=c1|((rf_go[a*9+c]?wdat[4*c+:4]:rf[a][4*c+:4])&{4{sel1==3'(a)}});
                end
            end
            (* keep = "true" *) reg[3:0]hq;
            // RIL (x gate census u_popb 52 loads): fields 0..2 popb, 3..5 poph, 6..8 popk
            wire pp = (RIL != 0) ? ((c<3)?rf_pop_r:(c<6)?rf_pop_h:rf_pop_k) : ((c<5)?rf_pop_r:rf_pop_h);
            always @(posedge ck) hq <= (MUT != 6 && pp) ? c1 : c0;   // MUT 6: prefetch ignores the pop
            assign rh[4*c+:4]=hq;
        end
    end
    for(genvar a=0;a<8;a=a+1)begin:g_rf_write
        for(genvar c=0;c<9;c=c+1)begin:g_field
            wire go;
            dsdv_tx_copy #(.W(1),.ID(4000+a*9+c))u(.ck(ck),.rn(1'b1),.d(lp_v[LP-2]&&(rf_write_next==3'(a))),.q(go));
            assign rf_go[a*9+c]=go;
            wire[35:0]data={lp_i[LP-1],lk_s};
            always @(posedge ck)if(go)rf[a][4*c+:4]<=data[4*c+:4];
        end
    end endgenerate
    wire [19:0] r_i  = rh[35:16];
    wire        r_in = wv && r_i[19:4] == w0c[19:4];
    wire        pop  = slot_q && bq_n != 3'd0;
    wire        flush_ok = (bq_n == 3'd0 && !pop) || (bq_n == 3'd1 && pop);
    dsdv_tx_pop_pred #(.ID(7000)) u_popa (.any(rf_n != 4'd0), .armed(armed), .hdr_q(hdr_q), .fin(fin), .wv(wv), .r_in(r_in),
        .flush_ok(flush_ok), .pop(rf_pop));
    dsdv_tx_pop_pred #(.ID(7001)) u_popb (.any(rf_n != 4'd0), .armed(armed), .hdr_q(hdr_q), .fin(fin), .wv(wv), .r_in(r_in),
        .flush_ok(flush_ok), .pop(rf_pop_r));
    generate if (RHP != 0) begin : g_poph
        dsdv_tx_pop_pred #(.ID(7002)) u_poph (.any(rf_n != 4'd0), .armed(armed), .hdr_q(hdr_q), .fin(fin), .wv(wv), .r_in(r_in),
            .flush_ok(flush_ok), .pop(rf_pop_h));
    end else begin : g_poph0
        assign rf_pop_h = rf_pop_r;
    end endgenerate
    generate if (RHP != 0 && RIL != 0) begin : g_popk
        dsdv_tx_pop_pred #(.ID(7003)) u_popk (.any(rf_n != 4'd0), .armed(armed), .hdr_q(hdr_q), .fin(fin), .wv(wv), .r_in(r_in),
            .flush_ok(flush_ok), .pop(rf_pop_k));
    end else begin : g_popk0
        assign rf_pop_k = rf_pop_h;
    end endgenerate
    wire        in_done = in_end && lk_idle && rf_n == 4'd0;
    wire        fl  = armed && hdr_q && !fin && flush_ok && ((rf_pop && wv && !r_in) || (in_done && rf_n == 4'd0));
    wire        o_ctl_c = okk[7];            // control copy
    wire        o_ctl_t = okk[10];            // tc / rc / sn copy
    wire        o_ctl_j = okk[13];            // next-state job-field copy
    wire ct_tick_pred,ct_delay_hi,hdr_lcur;
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(6010))u_ctp(.ck(ck),.rn(rl[6]),.d(n_octl),.q(ct_tick_pred));
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(6011))u_cdh(.ck(ck),.rn(rl[6]),.d(n_octl),.q(ct_delay_hi));
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(6012))u_hlc(.ck(ck),.rn(rl[6]),.d(nx_hdr_q),.q(hdr_lcur));
    wire ct_tick_lo;                    // RIL (x census u_ctp 34 loads): nx_tc_pred[7:0] clear copy
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(6013))u_ctq(.ck(ck),.rn(rl[6]),.d(n_octl),.q(ct_tick_lo));
    wire [15:0] nx_tc_inc = (armed&&tc!=16'hffff)?tc+16'd1:tc;
    wire [15:0] nx_tc_pred = {ct_tick_pred ? 8'd0 : nx_tc_inc[15:8], ((RIL != 0) ? ct_tick_lo : ct_tick_pred) ? 8'd0 : nx_tc_inc[7:0]};
    wire fl_lcur = armed&&hdr_lcur&&!fin&&flush_ok&&
        ((rf_pop&&wv&&!r_in)||(in_done&&rf_n==4'd0));
    wire [19:0] nx_lcur_private = (armed&&!hdr_lcur&&!okk[8]) ? j_hb :
        ((fl_lcur&&wv)?w0c+20'd16:lcur);
    wire        g_on = armed && tc >= j_dly + ((MUT == 3) ? 16'(j_r) : 16'd0);
    wire        lastf = in_done && rf_n == 4'd0 && (MUT != 2);
    wire        nb_t = wv ? ~act : act;      // buffer a new window opens in
    // next state (mirrors dsdv_idx_tx's update order exactly)
    reg         nx_armed, nx_busy, nx_done, nx_in_end, nx_wv, nx_act, nx_hdr_q, nx_fin, nx_slot;
    reg  [15:0] nx_tc; reg [2:0] nx_rc; reg [11:0] nx_sn; reg [2:0] nx_bq_n; reg [1:0] nx_bix;
    reg         nx_d_h, nx_d_buf, nx_d_rb, nx_d_em, nx_d_last; reg [19:0] nx_lcur, nx_w0c;
    reg  [15:0] nx_dly; reg [11:0] nx_sm; reg [2:0] nx_r;
    reg  [11:0] sn_i, sn_h; reg sn_inc, nx_snlt;
    always @* begin
        nx_armed = armed; nx_busy = busy; nx_done = done; nx_in_end = in_end; nx_wv = wv; nx_act = act;
        nx_hdr_q = hdr_q; nx_fin = fin; nx_tc = tc; nx_rc = rc; nx_sn = sn; nx_bq_n = bq_n; nx_bix = bix;
        nx_d_h = d_h; nx_d_buf = d_buf; nx_d_rb = d_rb; nx_d_em = d_em; nx_d_last = d_last; nx_lcur = lcur; nx_w0c = w0c;
        if (armed && e_cpl && e_mine && e_w[511:508] == 4'd4) nx_in_end = 1'b1;
        if (o_ctl_c) begin
            nx_armed = 1'b1; nx_busy = 1'b1; nx_done = 1'b0; nx_in_end = 1'b0; nx_wv = 1'b0; nx_fin = 1'b0; nx_hdr_q = 1'b0;
        end
        if(okk[10])nx_tc=0;else if(armed&&tc!=16'hffff)nx_tc=tc+16'd1;
        if(okk[11])nx_rc=0;else if(armed&&g_on&&!done)nx_rc=(rc==0)?j_r-3'd1:rc-3'd1;
        begin
            // SCS: both candidates (sn + 1 / sn, same okk clears) and their compares against nx_sm are formed off
            // slot_q; slot_q only selects (same values as the plain form below)
            sn_i=sn+12'd1; sn_h=sn;
            if(okk[12])begin sn_i[5:0]=6'd0; sn_h[5:0]=6'd0; end
            if(okk[16])begin sn_i[11:6]=6'd0; sn_h[11:6]=6'd0; end
            sn_inc=armed&&g_on&&!done&&slot_q;
            nx_sn=sn_inc?sn_i:sn_h;
        end
        // staging: HDR first, else pop / flush
        if (armed && !hdr_q && !okk[8]) begin
            nx_d_h = 1'b1; nx_bq_n = 3'd1; nx_bix = 2'd0; nx_hdr_q = 1'b1; nx_lcur = j_hb;
        end else begin
            if (pop) begin nx_bq_n = bq_n - 3'd1; nx_bix = bix + 2'd1; end
            if (fl) begin
                nx_d_h = 1'b0; nx_d_buf = act; nx_d_em = !wv; nx_d_rb = wv && w0c != lcur; nx_d_last = lastf; nx_bix = 2'd0;
                nx_bq_n = (wv && w0c != lcur) ? 3'd3 : 3'd2;
                if (wv) nx_lcur = w0c + 20'd16;
                if (in_done && rf_n == 4'd0) nx_fin = 1'b1;
            end
        end
        // window open
        if (rf_pop && !r_in) begin nx_wv = 1'b1; nx_w0c = {r_i[19:4], 4'd0}; nx_act = nb_t; end
        if (fin && bq_n == 3'd0 && armed && !done) begin nx_done = 1'b1; nx_busy = 1'b0; end
        // the next cycle's grid slot
        nx_dly = {ct_delay_hi?cp[84:77]:j_dly[15:8],okk[13]?cp[76:69]:j_dly[7:0]}; nx_sm = {okk[14] ? cp[99:94] : j_sm[11:6], ((RIL != 0) ? okk[17] : okk[14]) ? cp[93:88] : j_sm[5:0]}; nx_r = okk[15] ? cp[87:85] : j_r;
        nx_snlt = (SCS != 0) ? (sn_inc ? (sn_i < nx_sm) : (sn_h < nx_sm)) : (nx_sn < nx_sm);
        nx_slot = nx_armed && nx_tc_pred >= nx_dly + ((MUT == 3) ? 16'(nx_r) : 16'd0) && nx_rc == 3'd0 && nx_snlt && !nx_done;
    end
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin
            armed <= 1'b0; busy <= 1'b0; done <= 1'b0; in_end <= 1'b0; e_h <= 1'b0; ib_w <= '0; wv <= 1'b0;
            hdr_q <= 1'b0; fin <= 1'b0; bq_n <= 3'd0; slot_q <= 1'b0;
        end else begin
            armed <= nx_armed; busy <= nx_busy; done <= nx_done; in_end <= nx_in_end; wv <= nx_wv;
            hdr_q <= nx_hdr_q; fin <= nx_fin; bq_n <= nx_bq_n; slot_q <= nx_slot;
            if (o_eg && !vo_r[6]) e_h <= 1'b1;
            else if (o_eg && vo_r[6]) e_h <= 1'b0;
            if (ib_push) ib_w <= ib_w + 1'b1;
        end
    always @(posedge ck) begin
        act <= nx_act; w0c <= nx_w0c; tc <= nx_tc; rc <= nx_rc; sn <= nx_sn; bix <= nx_bix; lcur <= nx_lcur_private;
        d_h <= nx_d_h; d_buf <= nx_d_buf; d_rb <= nx_d_rb; d_em <= nx_d_em; d_last <= nx_d_last;
    end
    // window buffers: field f of buffer b written with the result score when the result lands in b
    wire        t_acc0  = rf_pop && r_in && !act,  t_acc1  = rf_pop && r_in && act;
    wire        t_open0 = rf_pop && !r_in && !nb_t, t_open1 = rf_pop && !r_in && nb_t;
    wire [15:0] r_oh = 16'd1 << r_i[3:0];
    generate for(genvar b=0;b<2;b=b+1)begin:g_window_score
        wire accept=(b==0)?(t_acc0||t_open0):(t_acc1||t_open1);
        for(genvar f=0;f<16;f=f+1)begin:g_field
            wire en;
            dsdv_tx_score_enable #(.ID(16*b+f))u_enable(.accept(accept),.onehot(r_oh[f]),.en(en));
            dsdv_tx_score_field #(.ID(16*b+f))u_field(.ck(ck),.en(en),.d(rh[15:0]),.q(wscb[b][16*f+:16]));
        end
        wire acc=(b==0)?t_acc0:t_acc1;
        for(genvar f=0;f<4;f=f+1)begin:g_valid
            wire open;
            dsdv_tx_open_enable #(.BANK(b),.ID(4*b+f))u_enable(.pop(rf_pop),.inwin(r_in),.target(nb_t),.en(open));
            dsdv_tx_window_valid #(.ID(4*b+f))u(.ck(ck),.open(open),.acc(acc),.mask(r_oh[4*f+:4]),.q(wlvb[b][4*f+:4]));
        end
        wire[19:0]base={r_i[19:4],4'd0};
        for(genvar f=0;f<2;f=f+1)begin:g_addr
            wire open;
            dsdv_tx_open_enable #(.BANK(b),.ID(100+2*b+f))u_enable(.pop(rf_pop),.inwin(r_in),.target(nb_t),.en(open));
            dsdv_tx_window_addr #(.ID(2*b+f))u(.ck(ck),.open(open),.d(base[10*f+:10]),.q(w0b[b][10*f+:10]));
        end
    end endgenerate

    // ------------------------------------------------------------------ output: registered kept selects -> lo
    // beat type of descriptor (h, rb, ix): HDR | REBASE (rb, 0) | BEAT part 0 (rb ? 1 : 0) | BEAT part 1 (rb ? 2 : 1)
    wire        nx_pop = nx_slot && nx_bq_n != 3'd0;
    wire        nx_isr  = !nx_d_h && nx_d_rb && nx_bix == 2'd0;
    wire        nx_isb0 = !nx_d_h && (nx_d_rb ? nx_bix == 2'd1 : nx_bix == 2'd0);
    wire        nx_isb1 = !nx_d_h && (nx_d_rb ? nx_bix == 2'd2 : nx_bix == 2'd1);
    (* keep = "true" *) reg [15:0] sb0;      // [8 b + c]: BEAT part-0 scores of buffer b, bits [32 c +: 32]
    (* keep = "true" *) reg [1:0]  srb, sb1; // REBASE base / part-1 lane-valid of buffer b
    (* keep = "true" *) reg        s_b0, s_b1, s_h, s_p;   // any part 0 / any part 1 / HDR / any beat
    always @(posedge ck or negedge rl[3])
        if (!rl[3]) begin sb0 <= 16'd0; srb <= 2'd0; sb1 <= 2'd0; s_b0 <= 1'b0; s_b1 <= 1'b0; s_h <= 1'b0; s_p <= 1'b0; lo[0] <= 1'b0; end
        else begin : g_sel
            integer b_, c_;
            for (b_ = 0; b_ < 2; b_ = b_ + 1) begin
                for (c_ = 0; c_ < 8; c_ = c_ + 1) sb0[8 * b_ + c_] <= nx_pop && nx_isb0 && !nx_d_em && nx_d_buf == b_[0];
                srb[b_] <= nx_pop && nx_isr && nx_d_buf == b_[0];
                sb1[b_] <= nx_pop && nx_isb1 && !nx_d_em && nx_d_buf == b_[0];
            end
            s_b0 <= nx_pop && nx_isb0; s_b1 <= nx_pop && nx_isb1; s_h <= nx_pop && nx_d_h; s_p <= nx_pop;
            lo[0] <= s_p;
        end
    wire s_h_data;
    dsdv_tx_copy #(.W(1),.RESET(1),.ID(5000))u_shd(.ck(ck),.rn(rl[3]),.d(nx_pop&&nx_d_h),.q(s_h_data));
    wire [255:0] wmk0 = wscb[0] & lvmask(wlvb[0]), wmk1 = wscb[1] & lvmask(wlvb[1]);   // stale fields masked
    always @(posedge ck) begin : g_lo
        integer c_;
        reg [255:0] dd; reg [11:0] tt;
        dd = {224'd0, {32{s_h_data}} & {j_l, j_k, j_hb}};                          // HDR {L, K, HB}
        dd[255:252] = dd[255:252] | ({4{s_b1}} & 4'd2);                       // part 1 {2, PT, 0, last, lv}
        dd[251:244] = dd[251:244] | ({8{s_b1}} & j_pt);
        dd[16]      = dd[16] | (s_b1 && d_last);
        dd[19:0]    = dd[19:0] | ({20{srb[0]}} & w0b[0]) | ({20{srb[1]}} & w0b[1]);   // REBASE {0, base}
        dd[15:0]    = dd[15:0] | ({16{sb1[0]}} & wlvb[0]) | ({16{sb1[1]}} & wlvb[1]);
        for (c_ = 0; c_ < 8; c_ = c_ + 1)                                      // part 0 scores
            dd[32 * c_ +: 32] = dd[32 * c_ +: 32] | ({32{sb0[c_]}} & wmk0[32 * c_ +: 32]) | ({32{sb0[8 + c_]}} & wmk1[32 * c_ +: 32]);
        tt = s_h ? {4'd1, j_pt} : (srb != 2'd0) ? {4'd6, j_pt} : s_b0 ? {4'd2, j_pt} : 12'd0;
        lo[V-1:1] <= {dd, tt, s_h || srb != 2'd0, s_b1, {2{s_p}} & j_l, {3{s_p}} & 3'(IK)};
    end

    // ------------------------------------------------------------------ faults / status
    always @(posedge ck or negedge rl[2])
        if (!rl[2]) begin fc_set <= 8'd0; fc <= 8'd0; end
        else begin
            fc_set <= 8'd0;
            if (o_eg && vo_r[6] && !e_h) fc_set[0] <= 1'b1;                           // part 1 without part 0
            if (ib_push && (ib_w - ib_r) == (IW + 1)'(IB)) fc_set[1] <= 1'b1;          // IDX buffer overflow
            if (okk[9] && busy) fc_set[2] <= 1'b1;                                     // a job while one is active
            if (okk[9] && (cp[87:85] == 3'd0 || cp[20:16] < 5'd8)) fc_set[3] <= 1'b1;
            if (rf_pop && !r_in && wv && r_i[19:4] < w0c[19:4]) fc_set[4] <= 1'b1;     // selection not ascending
            if (armed && !done && sn == j_sm && g_on) fc_set[5] <= 1'b1;               // grid exhausted, job not done
            if (cap_unal) fc_set[6] <= 1'b1;
            if (rf_n == 4'd8 && lp_v[LP-1] && !rf_pop) fc_set[7] <= 1'b1;
            fc <= fc | fc_set;
        end
    always @(posedge ck or negedge rl[4])
        if (!rl[4]) st <= 16'd0;
        else st <= {fc, 4'b0, done, armed, busy, fc != 8'd0};
endmodule
