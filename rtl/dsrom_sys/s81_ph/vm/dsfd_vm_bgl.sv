// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_bgl (el1013-s81-bgq28, 2026-10-13): ONE bank of the VM bank tile as a hard leaf, replicated x8 under the
// wires-only parent dsfd_vm_bgq28h.  Replaces the flat dsfd_vm_bgr tile (bgr28 spine r6: GRT 20,000 markers; 5,441
// feed-through bits on every horizontal cut, 0.89 of the M5 tracks over the SRAM column; 63,416 sinks on one root at
// 619 ps insertion).  UNTESTED AS OF THIS COMMIT: no bench has been built or run on this file (see the stream log).
//
// Every N / S signal is registered at the pin: request bus rb0 (N pin flops) -> rb1 (S pin flops), return bus
// ra (N) -> rt (S), status sq (N) -> so (S).  Leaf hop = 2 cycles on BOTH buses, so the return bus stays in lockstep
// with the request bus and the o_* -> f_* skew of a chain of leaves is HL + 1 = QD + 5 + ED (= dsfd_vm_bgr: the
// master's MD is unchanged).  Tile hop = 2 x 8 = 16 cycles (dsfd_vm_bgr: 6).
//
// Timeline of one op, t = the cycle it sits in rb0:
//   t+1   e_sel / e_cnt (E1 bank match FUSED with the E2 port-order prefix; dsfd_vm_bgr: E1 t+1, E2 t+2); rb1
//   t+2   y_* (E3 slot data select, read off rb1 = the S pin flops: no enqueue-alignment copy of the bus)
//   ...   queue / serve / macro as dsfd_vm_bgr, one cycle earlier; one extra read-data stage (r2) puts the return
//         FIFO write back on dsfd_vm_bgr's cycle (t+8 for an unqueued read), so fn / und / ds are cycle-identical
//   t+HL  local due vector (lh tail): the leaf keeps only its OWN history (read-valid + own-bank hit of the NPR read
//         ports, 2 x NPR bits x HL) instead of the tile's NP x (1 + BB) x HL history
//   t+HL+1 d_v / own / d_j;  t+HL+2 rt (the slot entered ra at t+HL+1)
// No signal fans out beyond the leaf: the bank id is strapped at the W pins (grp, bi) and registered once.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_bgl #(
    parameter integer NP = 28,
    parameter integer NPR = 10,
    parameter integer NB = 32,
    parameter integer NBL = 8,
    parameter integer QD = 4,
    parameter integer RQ = 8,
    parameter integer MACRO = 1,
    parameter integer DW = 128
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rs,
    input  wire [$clog2(NB/NBL)-1:0] grp,      // static strap (W)
    input  wire [$clog2(NBL)-1:0]    bi,       // static strap (W): bank index in the tile, tied by the parent
    input  wire [NP-1:0]       i_v,
    input  wire [NP-1:0]       i_we,
    input  wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*(DW/32)-1:0] i_mask,
    input  wire [NP*DW-1:0]    i_d,
    output wire [NP-1:0]       f_v,
    output wire [NP-1:0]       f_we,
    output wire [NP*($clog2(NB)+9)-1:0] f_row,
    output wire [NP*(DW/32)-1:0] f_mask,
    output wire [NP*DW-1:0]    f_d,
    input  wire [NPR-1:0]      r_v,
    input  wire [NPR*DW-1:0]   r_d,
    input  wire [3:0]          r_f,
    input  wire [$clog2(QD):0] r_o,
    output wire [NPR-1:0]      o_v,
    output wire [NPR*DW-1:0]   o_d,
    output wire [3:0]          o_f,
    output wire [$clog2(QD):0] o_o
);
    localparam integer GW = $clog2(NB / NBL);
    localparam integer LB = $clog2(NBL);
    localparam integer BB = $clog2(NB);
    localparam integer RA = BB + 9;
    localparam integer PW = (NP > 1) ? $clog2(NP) : 1;
    localparam integer QW = $clog2(QD);
    localparam integer RW = $clog2(RQ);
    localparam integer KQ = (NP < QD) ? NP : QD;
    localparam integer KW = (KQ > 1) ? $clog2(KQ) : 1;
    localparam integer ED = 3;                     // = dsfd_vm_bgr EP 2
    localparam integer HL = QD + 4 + ED;
`ifdef OT_VMBGL_HOP1
    localparam integer HOP1 = 1;
`else
    localparam integer HOP1 = 0;
`endif
    localparam integer HHL = HL - HOP1;
    localparam integer MW = DW / 32, NW = DW / 32;
    localparam integer OW = $clog2(QD) + 1;
    localparam [NP-1:0] RMASK = {NP{1'b1}} >> (NP - NPR);
    initial if (DW != 128 || GW + LB != BB) $error("dsfd_vm_bgl: DW 128, NB = groups x NBL");
    wire clk = ck[0];

    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_i = rst_s[1];
    reg [BB-1:0] gidq;
`ifdef OT_VMBGL_MUT_ID
    // MUTANT: leaf 1 answers as bank 0 (two leaves on one id, bank 1 unserved).  NOT bi ^ 1: that permutes the banks
    // consistently and is functionally invisible (master gate bgl_mut_id PASSed with it, 2026-10-13)
    always @(posedge clk) gidq <= (bi == 1) ? {grp, {LB{1'b0}}} : {grp, bi};
`else
    always @(posedge clk) gidq <= {grp, bi};
`endif

    // ------------------------------------------------------------------ request bus: N pin flops, S pin flops
    reg [NP-1:0]    rb0_v, rb1_v, rb0_we, rb1_we;
    reg [NP*RA-1:0] rb0_row, rb1_row;
    reg [NP*MW-1:0] rb0_m, rb1_m;
    reg [NP*DW-1:0] rb0_d, rb1_d;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin rb0_v <= {NP{1'b0}}; rb1_v <= {NP{1'b0}}; end
        else begin rb0_v <= i_v; rb1_v <= rb0_v; end
    always @(posedge clk) begin
        rb0_we <= i_we; rb0_row <= i_row; rb0_m <= i_mask; rb0_d <= i_d;
        rb1_we <= rb0_we; rb1_row <= rb0_row; rb1_m <= rb0_m; rb1_d <= rb0_d;
    end
`ifdef OT_VMBGL_MUT_RELAY
    // Mutate the relay by one cycle in either implementation.
    assign f_v = HOP1 ? rb1_v : rb0_v; assign f_we = HOP1 ? rb1_we : rb0_we;
    assign f_row = HOP1 ? rb1_row : rb0_row; assign f_mask = HOP1 ? rb1_m : rb0_m;
    assign f_d = HOP1 ? rb1_d : rb0_d;
`else
    assign f_v = HOP1 ? rb0_v : rb1_v; assign f_we = HOP1 ? rb0_we : rb1_we;
    assign f_row = HOP1 ? rb0_row : rb1_row; assign f_mask = HOP1 ? rb0_m : rb1_m;
    assign f_d = HOP1 ? rb0_d : rb1_d;
`endif
    wire wo_rd_any = |(rb0_v & ~rb0_we & ~RMASK);

    // ------------------------------------------------------------------ E1 + E2 fused: hits -> one-hot slot selects
    localparam integer NG = 4, GZ = (NP + NG - 1) / NG, CW = $clog2(NP + 1);
    reg [NP-1:0] hit, ho;
    reg [CW-1:0] lpre [0:NP-1];
    reg [CW-1:0] gt [0:NG-1];
    reg [CW-1:0] goff [0:NG-1];
    reg [CW-1:0] opre [0:NP-1];
    reg [CW-1:0] tot;
    reg [NP-1:0] sel_c [0:QD-1];
    integer g2, i2, j2;
    always @* begin
        for (i2 = 0; i2 < NP; i2 = i2 + 1) hit[i2] = rb0_v[i2] && rb0_row[i2*RA +: BB] == gidq;
        for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_VMBGL_MUT_ORDER
            ho[i2] = hit[NP-1-i2];
`else
            ho[i2] = hit[i2];
`endif
        for (g2 = 0; g2 < NG; g2 = g2 + 1) begin
            gt[g2] = {CW{1'b0}};
            for (i2 = g2 * GZ; i2 < (g2 + 1) * GZ && i2 < NP; i2 = i2 + 1) begin
                lpre[i2] = gt[g2];
                gt[g2] = gt[g2] + ho[i2];
            end
        end
        goff[0] = {CW{1'b0}};
        for (g2 = 1; g2 < NG; g2 = g2 + 1) goff[g2] = goff[g2-1] + gt[g2-1];
        tot = goff[NG-1] + gt[NG-1];
        for (i2 = 0; i2 < NP; i2 = i2 + 1) opre[i2] = goff[i2 / GZ] + lpre[i2];
        for (j2 = 0; j2 < QD; j2 = j2 + 1)
            for (i2 = 0; i2 < NP; i2 = i2 + 1)
`ifdef OT_VMBGL_MUT_ORDER
                sel_c[j2][NP-1-i2] = ho[i2] && opre[i2] == j2;
`else
                sel_c[j2][i2] = ho[i2] && opre[i2] == j2;
`endif
    end
    reg [NP-1:0] e_sel [0:QD-1];
    reg [QW+PW:0] e_cnt;
    integer j3;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin
            e_cnt <= 0;
            for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= {NP{1'b0}};
        end else begin
            e_cnt <= (tot > QD) ? QD + 1 : tot;
            for (j3 = 0; j3 < QD; j3 = j3 + 1) e_sel[j3] <= sel_c[j3];
        end

    // ------------------------------------------------------------------ E3 off the S pin flops (rb1), registered
    reg [QD-1:0] w_v, w_we;
    reg [PW-1:0] w_p [0:QD-1];
    reg [8:0]    w_r [0:QD-1];
    reg [MW-1:0] w_m [0:QD-1];
    reg [DW-1:0] w_d [0:QD-1];
    integer j4, p4;
    always @* for (j4 = 0; j4 < QD; j4 = j4 + 1) begin
        w_v[j4] = |e_sel[j4];
        w_we[j4] = |(e_sel[j4] & rb1_we);
        w_p[j4] = {PW{1'b0}}; w_r[j4] = 9'd0; w_m[j4] = {MW{1'b0}}; w_d[j4] = {DW{1'b0}};
        for (p4 = 0; p4 < NP; p4 = p4 + 1) begin
            if (e_sel[j4][p4]) w_p[j4] = w_p[j4] | p4;
            w_r[j4] = w_r[j4] | ({9{e_sel[j4][p4]}} & rb1_row[p4*RA + BB +: 9]);
            w_m[j4] = w_m[j4] | ({MW{e_sel[j4][p4]}} & rb1_m[p4*MW +: MW]);
            w_d[j4] = w_d[j4] | ({DW{e_sel[j4][p4]}} & rb1_d[p4*DW +: DW]);
        end
    end
    reg [QD-1:0] y_v, y_we;
    reg [PW-1:0] y_p [0:QD-1];
    reg [8:0]    y_r [0:QD-1];
    reg [MW-1:0] y_m [0:QD-1];
    reg [DW-1:0] y_d [0:QD-1];
    reg [QW+PW:0] y_cnt;
    integer j5;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin y_v <= {QD{1'b0}}; y_cnt <= 0; end
        else begin y_v <= w_v; y_cnt <= e_cnt; end
    always @(posedge clk) begin
        y_we <= w_we;
        for (j5 = 0; j5 < QD; j5 = j5 + 1) begin
            y_p[j5] <= w_p[j5]; y_r[j5] <= w_r[j5]; y_m[j5] <= w_m[j5]; y_d[j5] <= w_d[j5];
        end
    end

    // ------------------------------------------------------------------ op queue (= dsfd_vm_bgr bank)
    reg [QD-1:0] q_we;
    reg [PW-1:0] q_p [0:QD-1];
    reg [8:0]    q_r [0:QD-1];
    reg [MW-1:0] q_m [0:QD-1];
    reg [DW-1:0] q_dd [0:QD-1];
    reg [QW-1:0] qh, qt;
    reg [QW:0]   occ;
    reg          ovf;
    wire         serve = occ != 0;
    wire [QW+PW+1:0] need = occ - serve + y_cnt;
    reg [QW-1:0] qtr [0:NW-1];
    reg [QW-1:0] qhr [0:NW-1];
    integer wr;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin
            qh <= 0; qt <= 0; occ <= 0; ovf <= 1'b0;
            for (wr = 0; wr < NW; wr = wr + 1) begin qtr[wr] <= 0; qhr[wr] <= 0; end
        end else begin
            if (need > QD) begin
                ovf <= 1'b1;
                qt <= qt + (QD - (occ - serve));
                occ <= QD;
            end else begin
                qt <= qt + y_cnt;
                occ <= need;
            end
            if (serve) qh <= qh + 1'b1;
            for (wr = 0; wr < NW; wr = wr + 1) begin
                if (need > QD) qtr[wr] <= qtr[wr] + (QD - (occ - serve));
                else qtr[wr] <= qtr[wr] + y_cnt;
                if (serve) qhr[wr] <= qhr[wr] + 1'b1;
            end
        end
    integer j6, j7;
    always @(posedge clk)
        for (j6 = 0; j6 < QD; j6 = j6 + 1)
            if (y_v[j6] && occ - serve + j6 < QD) begin
                q_we[(qt + j6) & (QD-1)] <= y_we[j6];
                q_p [(qt + j6) & (QD-1)] <= y_p[j6];
                q_r [(qt + j6) & (QD-1)] <= y_r[j6];
                q_m [(qt + j6) & (QD-1)] <= y_m[j6];
                for (j7 = 0; j7 < NW; j7 = j7 + 1)
                    q_dd[(qtr[j7] + j6) & (QD-1)][32*j7 +: 32] <= y_d[j6][32*j7 +: 32];
            end

    // ------------------------------------------------------------------ serve register -> macro
    reg          s_we, s_re;
    reg [PW-1:0] s_p;
    reg [8:0]    s_r;
    reg [DW-1:0] s_dd;
    reg [MW-1:0] s_m;                              // word mask kept as MW flops, expanded at the macro pins
    integer e;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin s_we <= 1'b0; s_re <= 1'b0; end
        else begin s_we <= serve & q_we[qh]; s_re <= serve & ~q_we[qh]; end
    always @(posedge clk) begin
        s_p <= q_p[qh]; s_r <= q_r[qh];
        for (e = 0; e < NW; e = e + 1) s_dd[32*e +: 32] <= q_dd[qhr[e]][32*e +: 32];
`ifdef OT_VMBGL_MUT_MASK
        s_m <= {MW{1'b1}};                         // MUTANT: every write is a full-word write
`else
        s_m <= q_m[qh];
`endif
    end
    wire [DW-1:0] s_bm;
    genvar gm;
    generate for (gm = 0; gm < MW; gm = gm + 1) begin : g_bm
        assign s_bm[32*gm +: 32] = {32{s_m[gm]}};
    end endgenerate
    wire [DW-1:0] rd;
    generate if (MACRO) begin : g_sram
        (* keep = 1 *) ot_sram_1r1w_512x128_m4_r2c2 u_m (
            .clk(clk), .r_ce_in(s_re), .r_addr_in(s_r), .rd_out(rd),
            .w_ce_in(s_we), .w_addr_in(s_r), .wd_in(s_dd), .w_mask_in(s_bm),
            .rr_en(2'd0), .rr_addr(14'd0), .cr_en(2'd0), .cr_sel(14'd0));
    end else begin : g_flop
        reg [127:0] mem [0:511];
        reg [127:0] r_q;
        integer bi2;
        always @(posedge clk) begin
            if (s_re) r_q <= mem[s_r];
            if (s_we) for (bi2 = 0; bi2 < 128; bi2 = bi2 + 1) if (s_bm[bi2]) mem[s_r][bi2] <= s_dd[bi2];
        end
        assign rd = r_q;
    end endgenerate
    // read data: m, r (= dsfd_vm_bgr) + r2 (re-aligns the FIFO write with dsfd_vm_bgr after the fused E1 / E2)
    reg          m_v, r_vv, r2_v;
    reg [PW-1:0] m_p, r_p, r2_p;
    reg [DW-1:0] r_dd, r2_d;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin m_v <= 1'b0; r_vv <= 1'b0; r2_v <= 1'b0; end
        else begin m_v <= s_re; r_vv <= m_v; r2_v <= r_vv; end
    always @(posedge clk) begin m_p <= s_p; r_p <= m_p; r2_p <= r_p; r_dd <= rd; r2_d <= r_dd; end

    // ------------------------------------------------------------------ local read history (own ports only)
    reg [NPR-1:0] lh_v [0:HHL-1];                   // read issued on port p (any bank): the return-valid slot
    reg [NPR-1:0] lh_o [0:HHL-1];                   // ... and it is this bank's
    integer hh, p;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) for (hh = 0; hh < HHL; hh = hh + 1) begin lh_v[hh] <= {NPR{1'b0}}; lh_o[hh] <= {NPR{1'b0}}; end
        else begin
            lh_v[0] <= rb0_v[NPR-1:0] & ~rb0_we[NPR-1:0];
            lh_o[0] <= hit[NPR-1:0] & ~rb0_we[NPR-1:0];
            for (hh = 1; hh < HHL; hh = hh + 1) begin lh_v[hh] <= lh_v[hh-1]; lh_o[hh] <= lh_o[hh-1]; end
        end
    wire [NPR-1:0] hz_v = lh_v[HHL-1], hz_o = lh_o[HHL-1];
    reg [KW-1:0] jc [0:NPR-1];
    reg [PW:0] dcnt;
    integer q;
    always @* begin
        dcnt = 0;
        for (p = 0; p < NPR; p = p + 1) begin
            jc[p] = {KW{1'b0}};
            for (q = 0; q < p; q = q + 1) if (hz_o[q]) jc[p] = jc[p] + 1'b1;
            if (hz_o[p]) dcnt = dcnt + 1'b1;
        end
    end
    reg [NPR-1:0] d_v, own;
    reg [KW-1:0] d_j [0:NPR-1];
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin d_v <= {NPR{1'b0}}; own <= {NPR{1'b0}}; end
        else begin d_v <= hz_v; own <= hz_o; end
    always @(posedge clk)
        for (p = 0; p < NPR; p = p + 1)
`ifdef OT_VMBGL_MUT_J0
            d_j[p] <= {KW{1'b0}};
`else
            d_j[p] <= jc[p];
`endif

    // HOP1 removes one forwarding stage and advances the due slot and FIFO write together.
    // Local E1/E2/E3 selection stays identical; rb1 is an internal movable bank-data stage.
    wire fifo_v = HOP1 ? r_vv : r2_v;
    wire [DW-1:0] fifo_d = HOP1 ? r_dd : r2_d;
    wire [PW-1:0] fifo_p = HOP1 ? r_p : r2_p;
    // ------------------------------------------------------------------ return FIFO + due slots (= dsfd_vm_bgr bank)
    reg [DW-1:0] f_dd [0:RQ-1];
    reg [PW-1:0] f_p [0:RQ-1];
    reg [RW-1:0] fh, ft;
    reg [RW-1:0] fhr [0:NW-1];
    reg [RW:0]   fn;
    reg          und;
    reg [DW-1:0] ds [0:KQ-1];
    reg [PW-1:0] dsp [0:KQ-1];
    integer wf, wf2, kk;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin fh <= 0; ft <= 0; fn <= 0; und <= 1'b0; for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= 0; end
        else begin
            if (fifo_v) ft <= ft + 1'b1;
            fh <= fh + dcnt;
            for (wf = 0; wf < NW; wf = wf + 1) fhr[wf] <= fhr[wf] + dcnt;
            fn <= fn + fifo_v - dcnt;
            if (dcnt > fn) und <= 1'b1;
        end
    always @(posedge clk) begin
        if (fifo_v) begin f_dd[ft] <= fifo_d; f_p[ft] <= fifo_p; end
        for (kk = 0; kk < KQ; kk = kk + 1) begin
            for (wf2 = 0; wf2 < NW; wf2 = wf2 + 1)
                ds[kk][32*wf2 +: 32] <= f_dd[(fhr[wf2] + kk) & (RQ-1)][32*wf2 +: 32];
            dsp[kk] <= f_p[(fh + kk) & (RQ-1)];
        end
    end

    // ------------------------------------------------------------------ return bus: N pin flops, S pin flops
    reg [NPR-1:0]    ra_v, rt_v;
    reg [NPR*DW-1:0] ra_d, rt_d;
    reg [NPR*DW-1:0] part;
    always @* for (p = 0; p < NPR; p = p + 1) part[p*DW +: DW] = own[p] ? ds[d_j[p]] : {DW{1'b0}};
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin ra_v <= {NPR{1'b0}}; rt_v <= {NPR{1'b0}}; end
        else begin ra_v <= r_v; rt_v <= (HOP1 ? r_v : ra_v) | d_v; end
    always @(posedge clk) begin ra_d <= r_d; rt_d <= (HOP1 ? r_d : ra_d) | part; end
    assign o_v = rt_v;
    assign o_d = rt_d;

    // ------------------------------------------------------------------ status lane: N pin flops, S pin flops
    reg mis_r, stf;
    reg [2:0] stc;
    reg [OW-1:0] sto;
    reg [3:0] sq_f, so_f;
    reg [OW-1:0] sq_o, so_o;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin
            mis_r <= 1'b0; stf <= 1'b0; stc <= 3'd0; sto <= {OW{1'b0}};
            sq_f <= 4'd0; so_f <= 4'd0; sq_o <= {OW{1'b0}}; so_o <= {OW{1'b0}};
        end else begin
            for (p = 0; p < NPR; p = p + 1) if (own[p] && dsp[d_j[p]] != p) mis_r <= 1'b1;
            stc <= stc | {und, mis_r, ovf | wo_rd_any};
            stf <= stf | und | mis_r | ovf | wo_rd_any;
            if (occ > sto) sto <= occ;
            sq_f <= r_f; sq_o <= r_o;
            so_f <= (HOP1 ? r_f : sq_f) | {stf, stc};
            so_o <= (sto > (HOP1 ? r_o : sq_o)) ? sto : (HOP1 ? r_o : sq_o);
        end
    assign o_f = so_f;
    assign o_o = so_o;
endmodule

// dsfd_vm_bgl28: the hard leaf at the dsfd_vm_bgq28 parameters (hardened once, placed x8)
module dsfd_vm_bgl28 (
    input  wire [0:0] ck, input wire [0:0] rs, input wire [1:0] grp, input wire [2:0] bi,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
);
`ifdef OT_VMBGL_FLOPMEM
    localparam integer MACRO = 0;
`else
    localparam integer MACRO = 1;
`endif
    dsfd_vm_bgl #(.NP(28), .NPR(10), .NB(32), .NBL(8), .QD(4), .RQ(8), .MACRO(MACRO), .DW(128)) u (
        .ck(ck), .rs(rs), .grp(grp), .bi(bi), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d),
        .f_v(f_v), .f_we(f_we), .f_row(f_row), .f_mask(f_mask), .f_d(f_d), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o),
        .o_v(o_v), .o_d(o_d), .o_f(o_f), .o_o(o_o));
endmodule

// dsfd_vm_bgq28h: the wires-only parent = the dsfd_vm_bgq28 pin list over 8 abutted dsfd_vm_bgl28 leaves (N -> S).
// No cell of its own except the bank-index straps (constants) and whatever the clock spine places.
module dsfd_vm_bgq28h (
    input  wire [0:0] ck, input wire [0:0] rs, input wire [1:0] grp,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
);
    localparam integer NL = 8;
    wire [27:0] cv [0:NL], cwe [0:NL];
    wire [28*14-1:0] crow [0:NL];
    wire [28*4-1:0] cm [0:NL];
    wire [28*128-1:0] cd [0:NL];
    wire [9:0] cov [0:NL];
    wire [10*128-1:0] cod [0:NL];
    wire [3:0] cof [0:NL];
    wire [2:0] coo [0:NL];
    assign cv[0] = i_v; assign cwe[0] = i_we; assign crow[0] = i_row; assign cm[0] = i_mask; assign cd[0] = i_d;
    assign cov[0] = r_v; assign cod[0] = r_d; assign cof[0] = r_f; assign coo[0] = r_o;
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_l
        wire [2:0] bk = k;
        (* keep = 1 *) dsfd_vm_bgl28 u_l (
            .ck(ck), .rs(rs), .grp(grp), .bi(bk),
            .i_v(cv[k]), .i_we(cwe[k]), .i_row(crow[k]), .i_mask(cm[k]), .i_d(cd[k]),
            .f_v(cv[k+1]), .f_we(cwe[k+1]), .f_row(crow[k+1]), .f_mask(cm[k+1]), .f_d(cd[k+1]),
            .r_v(cov[k]), .r_d(cod[k]), .r_f(cof[k]), .r_o(coo[k]),
            .o_v(cov[k+1]), .o_d(cod[k+1]), .o_f(cof[k+1]), .o_o(coo[k+1]));
    end endgenerate
    assign f_v = cv[NL]; assign f_we = cwe[NL]; assign f_row = crow[NL]; assign f_mask = cm[NL]; assign f_d = cd[NL];
    assign o_v = cov[NL]; assign o_d = cod[NL]; assign o_f = cof[NL]; assign o_o = coo[NL];
endmodule
