`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_s5_xhead3 (QW-S5-XHEAD 10-21, structural successor of qfd_dv_s5_xhead = rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv
// at 5949f90af: ot_qfd_xhead NH 8 NATIVE_AFFINE 1 LEAF_READ_PIN_PIPE 1 FILL_LEAD 5 DX 14 + tids strap + retag).
// SAME PORTS as qfd_dv_s5_xhead (what qfd_dv_s5b_su8p2_lp u_xh0..3 instantiate); values unchanged.
//
// Why: the mapped census of qfd_dv_s5_xhead failed 75 drivers > 32 (fill shift selects foff 2,177-2,585 loads, fep 1,707,
// g_q 877, g_pin 759, phd 516, vd 266, pd 256, ep_rd 161, dp_xb ~100, dp_ep/dp_v/dq_ep, one-flop reset 80); the bounded
// netlist successor (xheadJ) fixed fanout with buffer helpers and reached 771.8 ps depth.  Here every wide consumer
// gets its OWN kept register copy (<= 32 loads per copy, each copy fed by <= 32-load nets), no buffer trees:
//   * one new input stage P (pin registers; 5 copies of foff) in front of the old pin stage R, which is a bank of kept
//     copies: 128 + 8 + 1 foff copies (one per 8-bit half lane of the fill rotation, 8 for the mask, 1 for lw_off), 33 fep,
//     4 fb / fb-1 / fb+1, 25 go, 8 d_v / d_ep, per-row k one-hots, per-row tid quads;
//   * the descriptor window pipeline is retimed one stage earlier (P->R mask, R->A products, A->B emin, B->write
//     W / start / integrity): no adder follows another adder in one stage (the old stage C did 24-bit add -> 19-bit add);
//   * the W+1 / W-1 window copies are replaced by fb-1 / fb+1 compares (exactly equal: see ctl below), first_abs by the
//     6-bit start + per-epoch k / 3k: 768 window flops instead of 4,032, no 512-way epoch select;
//   * the read sequencer's "now" signals (rd/ph/rep/row select, i*k + k_i offsets, pool) are registered one edge ahead
//     from the next-state logic (descriptor write forwarded), replicated per row group;
//   * the answer delay lines end in per-chunk kept one-hot phase / valid / pool copies;
//   * the corridor retag moves in front of the n_q / s_q registers (every output pin is a flop Q, 0 levels);
//   * reset: ot_rst_relay (2 sync + 1 kept relay stage, 12 regional copies <= 32 flops each); control / valid only.
// PRICE (static schedule, compiler-visible): +1 edge on every path through a_d (fill -> leaf write, go/ib -> corridor
// DX 14 -> 15, read request issue) and +1 reset release (3 edges, l_rst_n included).  Leaf answers (lq) and the fault
// chain (fault_i -> fault) keep their latency; relative timing inside the column (FILL_LEAD, QD, TDM) is unchanged,
// so the leaf answers lq arrive one edge later with their requests.  Bench: tb_qfd_dv_s5_xhead3 lockstep
// new(t+1) == old(t) on every output with lq / fault_i fed one edge later to the new master.
// Bench mutants (must FAIL): OT_S5_XH3_MUT_RETAG (N retag as S), OT_S5_XH3_MUT_ROT (one lane rotate copy reads the
// wrong foff bit), OT_S5_XH3_MUT_POOLW (pooled S tile window without its +1 beat), OT_S5_XH3_MUT_FWD (read pool/k
// forwarding of a same-edge descriptor write dropped).
// =====================================================================================================================
module qfd_dv_s5_xhead3 #(parameter integer HEAD_MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [5:0]     cid,
    input  wire           fault_i,
    input  wire [1566:0]  a_d,
    output wire [515:0]   n_d,
    output wire [515:0]   s_d,
    output wire [1:0]     lw_v, lw_ep, lc_v, lc_ep,
    output wire [11:0]    lw_off,
    output wire [127:0]   lw_m,
    output wire [2047:0]  lw_d,
    output wire [143:0]   lw_ctl,
    output wire [7:0]     lr_v, lr_t, lr_ep,
    output wire [223:0]   lr_p,
    input  wire [511:0]   lq,
    input  wire [7:0]     lq_v,
    input  wire [7:0]     lq_bad,
    output wire           l_rst_n,
    output wire           fault
);
    localparam integer AW = 24, NW = 18, XCW = 12, NH = 8, NR = 16, NE = 4, TG = 4, IL = 8, SMIN = 7, SMAX = 11;
    localparam integer NCOLD = 48;
    localparam integer IBW = 3 * NW + 13 * AW + 13;      // 379
    localparam integer BW = AW - 6;                      // 18
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;   // 73
    localparam integer FW = DESC + 2 + BW + 6 + 64 + 1024;     // 1187
    localparam integer CW = 1 + IBW + 128 + 8;           // 516
    localparam integer MUT = HEAD_MUT;
    localparam integer F_FOFF = DESC + 2 + BW;           // 93

    // ------------------------------------------------------------------------------------------------- reset relay
    localparam integer NRG = 12;
    wire [NRG-1:0] rr;
    ot_rst_relay #(.REGIONS(NRG), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rl (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    assign l_rst_n = rr[0];

    // ------------------------------------------------------------------------------------------------- strap
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = (NCOLD >= 4) ? 4 : NCOLD; br = (2 * NH >= 4) ? 4 : 2 * NH;
            lbc = (bc >= 4) ? 2 : (bc >= 2) ? 1 : 0; lbr = (br >= 4) ? 2 : (br >= 2) ? 1 : 0;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
            end
            tid = bc * br * blk + z;
        end
    endfunction
    reg [5:0] cid_q;
    reg [16*NR-1:0] tids, tid_q;
    integer ri;
    always @(posedge ck) begin
        cid_q <= cid;
        for (ri = 0; ri < NR; ri = ri + 1) tids[ri * 16 +: 16] <= 16'(tid(int'(cid_q), ri));
        tid_q <= tids;
    end

    // static maps (as ot_qfd_xhead): leaf / tile of row r, TDM edge of row r
    function automatic integer lf(input integer rw);
        lf = (rw < NH) ? (rw >> 1) : NE + ((NH - 1 - (rw - NH)) >> 1);
    endfunction
    function automatic integer tb(input integer rw);
        tb = (rw < NH) ? (rw & 1) : ((NH - 1 - (rw - NH)) & 1);
    endfunction
    function automatic integer row_edge(input integer rw);
        begin
            if (rw < NE) row_edge = rw;
            else if (rw < NH) row_edge = rw - NE;
            else if (rw - NH >= NE) row_edge = NH - 1 - (rw - NH);
            else row_edge = NE - 1 - (rw - NH);
        end
    endfunction
    function automatic [7:0] retag(input [7:0] t, input integer side_s);
        reg [2:0] a, b;
        begin
            a = t[2:0]; b = t[6:4];
            if (side_s ? !a[2] : a[2]) a = a ^ 3'd3;
            if (side_s ? !b[2] : b[2]) b = b ^ 3'd3;
            retag = {t[7], b, t[3], a};
        end
    endfunction

    // ------------------------------------------------------------------------------------------------- stage P (pins)
    (* keep = "true" *) reg              p_g;
    reg  [IBW-1:0]   p_ib;
    reg  [FW-1:0]    p_f;                                   // foff bits of p_f unused (p_foff copies below)
    (* keep = "true" *) reg  [5:0]       p_foff [0:4];
    (* keep = "true" *) reg  [3:0]       p_fep;
    integer pi;
    always @(posedge ck or negedge rr[1]) if (!rr[1]) p_g <= 1'b0; else p_g <= a_d[0];
    always @(posedge ck) begin
        p_ib <= a_d[1 +: IBW];
        p_f  <= a_d[1 + IBW +: FW];
        for (pi = 0; pi < 5; pi = pi + 1) p_foff[pi] <= a_d[1 + IBW + F_FOFF +: 6];
        p_fep <= {4{a_d[1 + IBW + DESC + 1]}};
    end
    wire [3:0]       p_sp = p_f[2 + AW + 2*XCW +: 4];
    wire [NW-1:0]    p_k  = p_f[2 + AW + 2*XCW + 4 +: NW];
    wire [BW-1:0]    p_fb = p_f[DESC + 2 +: BW];

    // ------------------------------------------------------------------------------------------------- stage R (= the
    // old pin stage, kept copies)
    localparam integer NG = 25;                              // go: [0] fill delay line, [1..24] ib_q 16-bit chunks
    localparam integer NV = 8;                               // d_v / d_ep: [0..4] epoch descriptor chunks, [5] FSM /
                                                             // fault, [6] lc outputs, [7] stage A
    localparam integer NFO = 137;                            // foff: [0..127] data half lanes, [128..135] mask, [136] lw_off
    (* keep = "true" *) reg  [NG-1:0]    r_g;
    reg  [IBW-1:0]   r_ib;
    reg  [FW-1:0]    r_f;
    (* keep = "true" *) reg  [NV-1:0]    r_dv, r_dep;
    (* keep = "true" *) reg  [112:0]     r_fep;              // row r: [7r + 2j + h] compare j (d0, +1, -1) half h, [7r+6] start;
                                                             // [112] st / lw_ep
    (* keep = "true" *) reg  [BW-1:0]    r_fb [0:3], r_fbm1 [0:3], r_fbp1 [0:3];
    (* keep = "true" *) reg  [3:0]       r_fbnz, r_fbnao;
    (* keep = "true" *) reg  [5:0]       r_foff [0:NFO-1];
    (* keep = "true" *) reg  [SMAX:0]    r_q [0:NR-1];                           // quad q = tid mod (S / TG)   (old da_q, one edge early)
    (* keep = "true" *) reg  [4:0]       r_ks [0:NR];        // one-hot {32, 24, 8, 6, 2} of d_k: [r] row r, [NR] fault
    wire [4:0] p_ks = {p_k == 32, p_k == 24, p_k == 8, p_k == 6, p_k == 2};
    integer k, r, e, i, c;
    always @(posedge ck or negedge rr[1])
        if (!rr[1]) r_g <= {NG{1'b0}}; else r_g <= {NG{p_g}};
    always @(posedge ck) begin
        r_ib <= p_ib;
        r_f  <= p_f;
        r_dv <= {NV{p_f[0]}};
        r_dep <= {NV{p_f[1]}};
        for (k = 0; k < 113; k = k + 1) r_fep[k] <= p_fep[k / 29];
        for (c = 0; c < 4; c = c + 1) begin
            r_fb[c] <= p_fb; r_fbm1[c] <= p_fb - 1'b1; r_fbp1[c] <= p_fb + 1'b1;
            r_fbnz[c] <= (p_fb != {BW{1'b0}}); r_fbnao[c] <= (p_fb != {BW{1'b1}});
        end
        for (k = 0; k < NFO; k = k + 1) r_foff[k] <= p_foff[k / 28];
        for (r = 0; r < NR; r = r + 1)
            r_q[r] <= tid_q[16*r +: 16] & ((({{SMAX{1'b0}}, 1'b1}) << (p_sp - $clog2(TG))) - 1'b1);
        for (r = 0; r <= NR; r = r + 1) r_ks[r] <= p_ks;
    end
    // fill fields (old f_q)
    wire              d_v   = r_f[0];
    wire [AW-1:0]     d_xb  = r_f[2 +: AW];
    wire [XCW-1:0]    d_xcs = r_f[2 + AW +: XCW];
    wire [XCW-1:0]    d_xks = r_f[2 + AW + XCW +: XCW];
    wire [3:0]        d_sp  = r_f[2 + AW + 2*XCW +: 4];
    wire [NW-1:0]     d_k   = r_f[2 + AW + 2*XCW + 4 +: NW];
    wire              d_rnd = r_f[2 + AW + 2*XCW + 4 + NW];
    wire              fv    = r_f[DESC];
    wire [63:0]       fm    = r_f[DESC + 2 + BW + 6 +: 64];
    wire [1023:0]     fd    = r_f[DESC + 2 + BW + 6 + 64 +: 1024];

    // ------------------------------------------------------------------------------------------------- go delay
    reg gl1, gl2, gl3;
    (* keep = "true" *) reg [7:0] gl4;                       // [0] g_q copies, [1] RD/PH/row selects, [2] k/pool epoch,
                                                             // [3]/[4] REP copy groups a/b, [5]/[6] k_i offset (IK copies 0-1 / 2-3)
    localparam integer NGQ = 36;                             // g_q: [0..23] ib_c chunks, [24] FSM, [25] go checks, [26] DX,
                                                             //      [27] k/pool epoch, [28]/[29] REP groups a/b, [30..35] counter halves
    (* keep = "true" *) reg [NGQ-1:0] gq_c;
    always @(posedge ck or negedge rr[2])
        if (!rr[2]) begin gl1 <= 1'b0; gl2 <= 1'b0; gl3 <= 1'b0; gl4 <= 8'b0; end
        else begin gl1 <= r_g[0]; gl2 <= gl1; gl3 <= gl2; gl4 <= {8{gl3}}; end
    always @(posedge ck or negedge rr[3])
        if (!rr[3]) gq_c[23:0] <= 24'd0; else gq_c[23:0] <= {24{gl4[0]}};
    always @(posedge ck or negedge rr[2])
        if (!rr[2]) gq_c[NGQ-1:24] <= {(NGQ-24){1'b0}}; else gq_c[NGQ-1:24] <= {(NGQ-24){gl4[7]}};
    wire g_q = gq_c[24];
    reg [8:0] gdx;                                           // g_q delayed DX - FILL_LEAD = 9
    always @(posedge ck or negedge rr[5])
        if (!rr[5]) gdx <= 9'd0; else gdx <= {gdx[7:0], gq_c[26]};
    wire g_dx = gdx[8];

    // ib hold registers (ib_q for the check, ib_c + ib_c2 on the way out), enables from kept go copies
    reg [IBW-1:0] ib_q, ib_c, ib_c2;
    always @(posedge ck) begin
        for (c = 0; c < 24; c = c + 1)
            for (i = 0; i < 16; i = i + 1)
                if (16 * c + i < IBW) begin
                    if (r_g[1 + c]) ib_q[16 * c + i] <= r_ib[16 * c + i];
                    if (gq_c[c]) ib_c[16 * c + i] <= ib_q[16 * c + i];
                end
        ib_c2 <= ib_c;
    end

    // ------------------------------------------------------------------------------------------------- descriptor
    // epoch fields claimed by a descriptor (old e_xb/e_xcs/e_xks/e_sp/e_k/e_rnd), written in 5 chunks with own enables
    localparam integer EVW = AW + 2 * XCW + 4 + NW + 1;     // 71
    wire [EVW-1:0] dvec = {d_rnd, d_k, d_sp, d_xks, d_xcs, d_xb};
    reg  [EVW-1:0] ev [0:1];
    always @(posedge ck)
        for (c = 0; c < 5; c = c + 1)
            for (e = 0; e < 2; e = e + 1)
                if (r_dv[c] && (r_dep[c] == e[0]))
                    for (i = 0; i < 15; i = i + 1)
                        if (15 * c + i < EVW) ev[e][15 * c + i] <= dvec[15 * c + i];
    // stage A: product of the row's quad and k (old stage B), 4 k - 1 (footprint - 1)
    reg              a_v;
    (* keep = "true" *) reg [1:0] a_vc, a_epc;               // feed the 32 stage-B enable copies
    reg              a_ep;
    (* keep = "true" *) reg [AW-1:0] a_xb [0:3];
    reg  [AW-1:0]    a_pr [0:NR-1];
    reg  [AW-1:0]    a_fm;
    reg  [5:0]       a_k;
    reg  [AW-1:0]    q24;
    always @(posedge ck or negedge rr[4])
        if (!rr[4]) begin a_v <= 1'b0; a_vc <= 2'b0; end else begin a_v <= r_dv[7]; a_vc <= {2{r_dv[7]}}; end
    always @(posedge ck) begin
        a_ep <= r_dep[7]; a_epc <= {2{r_dep[7]}};
        for (c = 0; c < 4; c = c + 1) a_xb[c] <= d_xb;
        a_fm <= TG * d_k - 1;
        a_k <= d_k[5:0];
        for (r = 0; r < NR; r = r + 1) begin
            q24 = ({{(AW-SMAX-1){1'b0}}, r_q[r]} << 4) + ({{(AW-SMAX-1){1'b0}}, r_q[r]} << 3);
            a_pr[r] <= ({AW{r_ks[r][0]}} & ({{(AW-SMAX-1){1'b0}}, r_q[r]} << 3)) |
                       ({AW{r_ks[r][1]}} & q24) |
                       ({AW{r_ks[r][2]}} & ({{(AW-SMAX-1){1'b0}}, r_q[r]} << 5)) |
                       ({AW{r_ks[r][3]}} & (q24 << 2)) |
                       ({AW{r_ks[r][4]}} & ({{(AW-SMAX-1){1'b0}}, r_q[r]} << 7));
        end
    end
    // stage B: emin = xb + product (old stage C's first adder), pool flags, k / 3k
    reg              b_v, b_ep;
    (* keep = "true" *) reg [31:0] b_vc, b_epc;              // window write enables: row r halves 2r, 2r + 1
    (* keep = "true" *) reg [2:0]  b_vk, b_epk;              // epoch store enables: [0] pool, [1] k, [2] 3k
    reg  [AW-1:0]    b_emin [0:NR-1];
    (* keep = "true" *) reg [NR-1:0] b_pool;                 // per-row copies
    reg              b_poolm, b_pf128;
    (* keep = "true" *) reg [7:0] b_fm8 [0:1];
    reg  [5:0]       b_k;                                    // epoch store / forwarding
    reg  [7:0]       b_k3;
    // pooled-read integrity threshold: every element i of row r reads up to start + (i+1) k - 1 <= start + 4k - 1
    // (no 8-bit wrap: start <= 63, 3k <= 189), so the old per-(r, i) check is start + 4k - 1 >= 128 (k != 0)
    (* keep = "true" *) reg [8:0] b_k4m1 [0:3];              // 4k - 1 (k != 0), else 0; copy per 4 rows
    (* keep = "true" *) reg [3:0] b_knz;
    always @(posedge ck or negedge rr[4])
        if (!rr[4]) begin b_v <= 1'b0; b_vc[15:0] <= 16'd0; end
        else begin b_v <= a_v; b_vc[15:0] <= {16{a_vc[0]}}; end
    always @(posedge ck or negedge rr[5])
        if (!rr[5]) begin b_vc[31:16] <= 16'd0; b_vk <= 3'd0; end
        else begin b_vc[31:16] <= {16{a_vc[1]}}; b_vk <= {3{a_vc[1]}}; end
    always @(posedge ck) begin
        b_ep <= a_ep;
        b_epc <= {{16{a_epc[1]}}, {16{a_epc[0]}}};
        b_epk <= {3{a_epc[1]}};
        for (r = 0; r < NR; r = r + 1) b_emin[r] <= a_xb[r / 4] + a_pr[r];
        b_pool <= {NR{a_fm >= 64}};
        b_poolm <= (a_fm >= 64);
        b_pf128 <= (a_fm >= 128);
        for (c = 0; c < 2; c = c + 1) b_fm8[c] <= a_fm[7:0];
        b_k <= a_k;
        b_k3 <= 8'(3 * a_k);
        for (c = 0; c < 4; c = c + 1) begin b_k4m1[c] <= 9'(4 * a_k) - 9'd1; b_knz[c] <= (a_k != 6'd0); end
    end
    // write stage (old end of stage C): W (beat), start, pool fault, pooled-read integrity (old stage D input)
    reg  [BW-1:0]    w_W [0:NR-1];
    reg              pfault_n, pbad_n;
    always @* begin
        pfault_n = b_pf128;
        pbad_n = 1'b0;
        for (r = 0; r < NR; r = r + 1) begin
`ifdef OT_S5_XH3_MUT_POOLW
            w_W[r] = b_emin[r][AW-1:6];
`else
            w_W[r] = b_emin[r][AW-1:6] + ((b_pool[r] && r >= NH) ? 1'b1 : 1'b0);
`endif
            if (r < NH && b_pool[r])
                if (b_emin[r] != b_emin[NH + NH - 1 - r] || {1'b0, b_emin[r][5:0]} + b_fm8[r / 4] >= 8'd128) pfault_n = 1'b1;
            if (b_knz[r / 4] && ({3'b000, b_emin[r][5:0]} + b_k4m1[r / 4] >= 9'd128)) pbad_n = 1'b1;
        end
    end
    reg  [BW-1:0]    e_W  [0:1][0:NR-1];
    reg  [5:0]       e_lo [0:1][0:NR-1];
    (* keep = "true" *) reg [3:0] e_poolc0, e_poolc1;         // per-epoch pool flag, copy per 4 rows (write control start);
                                                             // plain vectors (a dynamically indexed array becomes a memory
                                                             // and its copies merge: gate try 2, 98 loads)
    reg              e_pool [0:1];
    reg  [5:0]       e_k6 [0:1];
    reg  [7:0]       e_k3 [0:1];
    always @(posedge ck) begin
        for (e = 0; e < 2; e = e + 1)
            for (r = 0; r < NR; r = r + 1) begin
                if (b_vc[2*r] && b_epc[2*r] == e[0]) e_W[e][r][11:0] <= w_W[r][11:0];
                if (b_vc[2*r+1] && b_epc[2*r+1] == e[0]) begin
                    e_W[e][r][BW-1:12] <= w_W[r][BW-1:12];
                    e_lo[e][r] <= b_emin[r][5:0];
                end
            end
        if (b_vk[0]) e_pool[b_epk[0]] <= b_poolm;
        if (b_vk[0] && !b_epk[0]) e_poolc0 <= {4{b_poolm}};
        if (b_vk[0] && b_epk[0]) e_poolc1 <= {4{b_poolm}};
        if (b_vk[1]) e_k6[b_epk[1]] <= b_k;
        if (b_vk[2]) e_k3[b_epk[2]] <= b_k3;
    end
    // old stage D: the epoch's pooled-read integrity flag
    reg dq_v, dq_ep, dq_pool, dq_bad;
    reg e_pbad [0:1];
    always @(posedge ck or negedge rr[5]) if (!rr[5]) dq_v <= 1'b0; else dq_v <= b_v;
    always @(posedge ck) begin
        dq_ep <= b_ep; dq_pool <= b_poolm; dq_bad <= pbad_n;
        if (dq_v) e_pbad[dq_ep] <= dq_pool && dq_bad;
    end

    // ------------------------------------------------------------------------------------------------- leaf write
    // fill rotation: lanes to positions (foff + l) mod 64, each lane's stage select its own kept foff copy
    wire [1023:0] rd_s [0:6];
    wire [63:0]   rm_s [0:6];
    assign rd_s[0] = fd;
    assign rm_s[0] = fm;
    genvar rs, gl;
    generate for (rs = 0; rs < 6; rs = rs + 1) begin : g_rot
        localparam integer K = 1 << rs;
        for (gl = 0; gl < 64; gl = gl + 1) begin : g_l
`ifdef OT_S5_XH3_MUT_ROT
            wire sel0 = (gl == 5) ? r_foff[2*gl][(rs + 1) % 6] : r_foff[2*gl][rs];
`else
            wire sel0 = r_foff[2*gl][rs];
`endif
            wire sel1 = r_foff[2*gl+1][rs];
            assign rd_s[rs+1][16*gl +: 8] = sel0 ? rd_s[rs][16*((gl + 64 - K) % 64) +: 8] : rd_s[rs][16*gl +: 8];
            assign rd_s[rs+1][16*gl+8 +: 8] = sel1 ? rd_s[rs][16*((gl + 64 - K) % 64)+8 +: 8] : rd_s[rs][16*gl+8 +: 8];
            assign rm_s[rs+1][gl] = r_foff[128 + gl / 8][rs] ? rm_s[rs][(gl + 64 - K) % 64] : rm_s[rs][gl];
        end
    end endgenerate
    // write control per tile: d = fb - W in {0, +1, -1}.  The old W+1 / W-1 copies are 19-bit ({0,W} +/- 1) mod 2^19,
    // so fb == W+1 <=> fb != 0 && W == fb-1, and fb == W-1 <=> fb != all-ones && W == fb+1 (18-bit), compared for both
    // epochs and selected by the kept fep copy of the row.
    reg  [1:0]        st [0:1];
    reg  [NH*18-1:0]  ctl;
    reg  d0, dp1, dm1, plr;
    reg  [5:0] lor, wo_s;
    always @* begin
        ctl = {(NH*18){1'b0}};
        for (r = 0; r < NR; r = r + 1) begin
            // each half compare selected by its own fep copy (the epoch select may be pushed into the operands)
            d0  = (r_fep[7*r]     ? (r_fb[r/4][8:0] == e_W[1][r][8:0]) : (r_fb[r/4][8:0] == e_W[0][r][8:0])) &&
                  (r_fep[7*r + 1] ? (r_fb[r/4][17:9] == e_W[1][r][17:9]) : (r_fb[r/4][17:9] == e_W[0][r][17:9])) && (MUT != 9);
            dp1 = r_fbnz[r/4] &&
                  (r_fep[7*r + 2] ? (r_fbm1[r/4][8:0] == e_W[1][r][8:0]) : (r_fbm1[r/4][8:0] == e_W[0][r][8:0])) &&
                  (r_fep[7*r + 3] ? (r_fbm1[r/4][17:9] == e_W[1][r][17:9]) : (r_fbm1[r/4][17:9] == e_W[0][r][17:9])) && (MUT != 7);
            dm1 = r_fbnao[r/4] &&
                  (r_fep[7*r + 4] ? (r_fbp1[r/4][8:0] == e_W[1][r][8:0]) : (r_fbp1[r/4][8:0] == e_W[0][r][8:0])) &&
                  (r_fep[7*r + 5] ? (r_fbp1[r/4][17:9] == e_W[1][r][17:9]) : (r_fbp1[r/4][17:9] == e_W[0][r][17:9])) && (MUT != 8);
            plr = r_fep[7*r + 6] ? e_poolc1[r / 4] : e_poolc0[r / 4];
            lor = r_fep[7*r + 6] ? e_lo[1][r] : e_lo[0][r];
            wo_s = plr ? 6'd0 : lor;
            ctl[18*lf(r) + 9*tb(r) +: 9] = {d0 || dp1 || dm1, dm1 ? 2'b10 : dp1 ? 2'b01 : 2'b00, wo_s};
        end
    end
    wire lwv_d = fv && (st[r_fep[112]] != 2'd0);
    (* keep = "true" *) reg  [1:0]        lw_v_r, lw_ep_r, lc_v_r, lc_ep_r;
    (* keep = "true" *) reg  [5:0]        lw_off_r [0:1];
    (* keep = "true" *) reg  [63:0]       lw_m_r [0:1];
    (* keep = "true" *) reg  [1023:0]     lw_d_r [0:1];
    reg  [NH*18-1:0]  lw_ctl_r;
    always @(posedge ck or negedge rr[11])
        if (!rr[11]) begin lw_v_r <= 2'b0; lc_v_r <= 2'b0; end
        else begin lw_v_r <= {2{lwv_d}}; lc_v_r <= {2{r_dv[6]}}; end
    always @(posedge ck) begin
        lw_ep_r <= {2{r_fep[112]}}; lc_ep_r <= {2{r_dep[6]}};
        for (c = 0; c < 2; c = c + 1) begin
            lw_off_r[c] <= r_foff[136]; lw_m_r[c] <= rm_s[6]; lw_d_r[c] <= rd_s[6];
        end
        lw_ctl_r <= ctl;
    end
    assign lw_v = lw_v_r; assign lw_ep = lw_ep_r; assign lc_v = lc_v_r; assign lc_ep = lc_ep_r;
    assign lw_off = {lw_off_r[1], lw_off_r[0]}; assign lw_m = {lw_m_r[1], lw_m_r[0]};
    assign lw_d = {lw_d_r[1], lw_d_r[0]}; assign lw_ctl = lw_ctl_r;

    // ------------------------------------------------------------------------------------------------- go / TDM FSM
    reg  [NH*64-1:0] lqp;                                    // the leaves' answers, registered at this tile's pins
    reg  [NH-1:0]    lqvp, lqbp;
    reg              fi_q;
    reg              miss;
    wire [NW-1:0] b_tiles = ib_q[IBW - 2*NW +: NW];
    wire [NW-1:0] b_kk    = ib_q[IBW - 3*NW +: NW];
    wire          b_wsrc  = ib_q[13*AW + 12];
    wire [AW-1:0] b_xbase = ib_q[8*AW + 12 +: AW];
    wire [AW-1:0] b_xks   = ib_q[7*AW + 12 +: AW];
    wire [AW-1:0] b_xjs   = ib_q[6*AW + 12 +: AW];
    wire [AW-1:0] b_xcs   = ib_q[5*AW + 12 +: AW];
    wire [3:0]    b_split = ib_q[5*AW + 5 +: 4];
    wire          b_round = ib_q[4*AW + 4];
    reg           busy, flt, fault_r;
    (* keep = "true" *) reg [3:0] rep_c;                     // the epoch being read: [0] FSM, [1] k/pool, [2]/[3] REP a/b
    wire          rep = rep_c[0];
    (* keep = "true" *) reg [9:0] ep_rd_c;                   // the next epoch a go consumes: [0] FSM, [1..5] epoch field
                                                             // chunks, [6] go check state, [7] k/pool, [8]/[9] REP a/b
    wire          ep_rd = ep_rd_c[0];
    reg  [2:0]    ph;
    reg  [NW-1:0] rnd_left, k_i, k_last;
    // tuple end (busy && ph == IL-1), k_i == k_last and rnd_left == 0 registered one edge ahead from the next state, kept
    // copies: [0] last / FSM, [1] / [2] the low / high halves of the 18-bit counters (each half its own select gates)
    (* keep = "true" *) reg [2:0] te_c, keq_c, rz_c;
    wire          last = te_c[0] && keq_c[0] && rz_c[0];
    reg           busy_n, rep_n, ep_rd_n;
    reg  [2:0]    ph_n;
    reg  [NW-1:0] rnd_n, k_i_n, k_last_n;
    reg  [NW-1:0] rnd_dec, k_inc, tiles_m1, k_m1;
    integer hb;
    always @* begin
        busy_n = busy; rep_n = rep; ep_rd_n = ep_rd; ph_n = ph;
        if (g_q) begin
            rep_n = (MUT == 4) ? ~ep_rd : ep_rd;
            ep_rd_n = ~ep_rd;
            busy_n = 1'b1; ph_n = 3'd1;
        end else if (busy) begin
            ph_n = ph + 1'b1;
            if (last) busy_n = 1'b0;
        end
        rnd_dec = rnd_left - 1'b1; k_inc = k_i + 1'b1; tiles_m1 = b_tiles - 1'b1; k_m1 = b_kk - 1'b1;
        for (hb = 0; hb < NW; hb = hb + 1) begin
            // half h = hb / 9: g_q copies 30 + h (rnd), 32 + h (k_i), 34 + h (k_last); te/keq/rz copies 1 + h
            rnd_n[hb] = gq_c[30 + hb / 9] ? tiles_m1[hb] :
                        (te_c[1 + hb / 9] && keq_c[1 + hb / 9] && !rz_c[1 + hb / 9]) ? rnd_dec[hb] : rnd_left[hb];
            k_i_n[hb] = gq_c[32 + hb / 9] ? 1'b0 :
                        te_c[1 + hb / 9] ? (keq_c[1 + hb / 9] ? 1'b0 : k_inc[hb]) : k_i[hb];
            k_last_n[hb] = gq_c[34 + hb / 9] ? k_m1[hb] : k_last[hb];
        end
    end
    // descriptor checks (NATIVE_AFFINE): x_ks 1, x_cs = k, k in {2, 6, 8, 24, 32}; split range
    wire aff_bad = (d_xks != 1) || (d_xcs != d_k) || !(|r_ks[NR]);
    wire sp_bad  = (d_sp < SMIN) || (d_sp > SMAX);
    reg  [EVW-1:0] evr;
    always @* for (i = 0; i < EVW; i = i + 1) evr[i] = ev[ep_rd_c[1 + i / 15]][i];
    wire [AW-1:0]  e_xb_r  = evr[0 +: AW];
    wire [XCW-1:0] e_xcs_r = evr[AW +: XCW];
    wire [XCW-1:0] e_xks_r = evr[AW + XCW +: XCW];
    wire [3:0]     e_sp_r  = evr[AW + 2*XCW +: 4];
    wire [NW-1:0]  e_k_r   = evr[AW + 2*XCW + 4 +: NW];
    wire           e_rnd_r = evr[AW + 2*XCW + 4 + NW];
    reg  [12:0]   go_bad_bits;
    // read-sequencer "now" registers (one edge ahead from the next state: RD = g_q | busy, PH, REP, row selects)
    localparam integer NREP = 18;                            // [r] row r start select, [16] lr_ep, [17] fault
    reg           RD;
    reg  [2:0]    PH;
    (* keep = "true" *) reg [NREP-1:0] REPc;
    (* keep = "true" *) reg [7:0]      RDc;                  // row select groups: RSEL[j] = RDc[j/4] & PHc[j/4][edge]
    (* keep = "true" *) reg [3:0]      PHc [0:7];            // one-hot TDM edge (< NE) of PH
    reg  [2*NR-1:0] RSEL;                                    // [2r] row r elements 0, 1 + valid, [2r+1] elements 2, 3
    (* keep = "true" *) reg [7:0]      IKc [0:3][0:3];       // (i * k + k_i) mod 256 per element i, copy per 4 rows
    (* keep = "true" *) reg [8:0]      POOLc;                // [0..7] row pairs, [8] answer delay line
    // the next read epoch (= old rep_now one edge ahead), computed three times from separate kept state copies so no
    // gate drives more than its own group: rep_n = g_q ? ep_rd' : rep, ep_rd_n = g_q ? ~ep_rd : ep_rd
    function automatic rep_nx(input gl, input gq, input epr, input rp);
        reg epn, rpn;
        begin
            epn = gq ? ~epr : epr;
            rpn = gq ? ((MUT == 4) ? ~epr : epr) : rp;
            rep_nx = gl ? ((MUT == 4) ? ~epn : epn) : rpn;
        end
    endfunction
    wire          REP_k  = rep_nx(gl4[2], gq_c[27], ep_rd_c[7], rep_c[1]);
    wire          REP_a  = rep_nx(gl4[3], gq_c[28], ep_rd_c[8], rep_c[2]);
    wire          REP_b  = rep_nx(gl4[4], gq_c[29], ep_rd_c[9], rep_c[3]);
    wire          RD_x   = gl4[1] | busy_n;
    wire [2:0]    PH_x   = gl4[1] ? 3'd0 : ph_n;
    wire [5:0]    KOF_x0 = gl4[5] ? 6'd0 : k_i_n[5:0];
    wire [5:0]    KOF_x1 = gl4[6] ? 6'd0 : k_i_n[5:0];
`ifdef OT_S5_XH3_MUT_FWD
    wire          fwd    = 1'b0;
`else
    wire          fwd    = b_v && (b_ep == REP_k);
`endif
    wire [5:0]    k6_x   = fwd ? b_k : e_k6[REP_k];
    wire [7:0]    k3_x   = fwd ? b_k3 : e_k3[REP_k];
    wire          pool_x = fwd ? b_poolm : e_pool[REP_k];
    always @(posedge ck or negedge rr[6])
        if (!rr[6]) begin
            st[0] <= 2'd0; st[1] <= 2'd0; ep_rd_c <= 10'd0; busy <= 1'b0; flt <= 1'b0; ph <= 3'd0; rep_c <= 4'b0;
            fault_r <= 1'b0; te_c <= 3'd0;
        end else begin
            te_c <= {3{busy_n && (ph_n == IL - 1)}};
            fault_r <= flt | fi_q;
            if (r_dv[5]) begin
                if (aff_bad) flt <= 1'b1;
                if (st[r_dep[5]] != 2'd0) flt <= 1'b1;
                st[r_dep[5]] <= 2'd1;
                if (sp_bad) flt <= 1'b1;
            end
            if (b_v && pfault_n) flt <= 1'b1;
            if ((g_q && e_pbad[REPc[17]]) || |go_bad_bits) flt <= 1'b1;
            if (|lqbp) flt <= 1'b1;
            if (miss) flt <= 1'b1;
            if (g_q) begin
                if (busy && last) st[(MUT == 4) ? ~rep : rep] <= 2'd0;
                st[ep_rd] <= 2'd2;
            end else if (last) st[(MUT == 4) ? ~rep : rep] <= 2'd0;
            busy <= busy_n; ph <= ph_n; rep_c <= {4{rep_n}}; ep_rd_c <= {10{ep_rd_n}};
        end
    always @(posedge ck or negedge rr[11])
        if (!rr[11]) go_bad_bits <= 13'd0;
        else go_bad_bits <= gq_c[25] ? {
                busy && !last, b_kk == 0, b_tiles == 0, b_round != e_rnd_r, b_kk != e_k_r,
                b_split != e_sp_r, b_xks != {{(AW-XCW){1'b0}}, e_xks_r},
                b_xcs != {{(AW-XCW){1'b0}}, e_xcs_r}, b_xbase != e_xb_r,
                b_xjs != 0, b_wsrc, st[ep_rd_c[6]] != 2'd1, 1'b0} : 13'd0;
    // k_i / k_last / rnd_left hold through reset (assigned only outside it, as in ot_qfd_xhead): idle next state = hold
    always @(posedge ck) begin
        k_i <= k_i_n; k_last <= k_last_n; rnd_left <= rnd_n;
        keq_c <= {3{k_i_n == k_last_n}}; rz_c <= {3{rnd_n == {NW{1'b0}}}};
    end
    always @(posedge ck or negedge rr[7])
        if (!rr[7]) begin RD <= 1'b0; PH <= 3'd0; REPc <= {NREP{1'b0}}; end
        else begin RD <= RD_x; PH <= PH_x; REPc <= {{9{REP_b}}, {9{REP_a}}}; end
    always @(posedge ck or negedge rr[8])
        if (!rr[8]) RDc <= 8'd0; else RDc <= {8{RD_x}};
    always @(posedge ck)
        for (c = 0; c < 8; c = c + 1) PHc[c] <= {PH_x == 3'd3, PH_x == 3'd2, PH_x == 3'd1, PH_x == 3'd0};
    always @* for (r = 0; r < 2 * NR; r = r + 1) RSEL[r] = RDc[r / 4] && PHc[r / 4][row_edge(r / 2)];
    always @(posedge ck) begin
        for (c = 0; c < 4; c = c + 1) begin
            IKc[0][c] <= {2'b00, (c < 2) ? KOF_x0 : KOF_x1};
            IKc[1][c] <= {2'b00, k6_x} + {2'b00, (c < 2) ? KOF_x0 : KOF_x1};
            IKc[2][c] <= {1'b0, k6_x, 1'b0} + {2'b00, (c < 2) ? KOF_x0 : KOF_x1};
            IKc[3][c] <= k3_x + {2'b00, (c < 2) ? KOF_x0 : KOF_x1};
        end
        POOLc <= {9{pool_x}};
    end
    // leaf read requests: position (start + i k + k_i) mod 256 (old first_abs + k_i), pooled: bit 6 picks the tile
    reg  [NH*28-1:0] rp;
    reg  [NH-1:0]    rv, rt;
    reg  [7:0]       ab;
    reg  [5:0]       lo_r;
    always @* begin
        rp = {(NH*28){1'b0}}; rv = {NH{1'b0}}; rt = {NH{1'b0}};
        for (r = 0; r < NR; r = r + 1) begin
            lo_r = REPc[r] ? e_lo[1][r] : e_lo[0][r];
            if (RSEL[2*r]) begin
                rv[lf(r)] = 1'b1;
                if (tb(r) != 0) rt[lf(r)] = 1'b1;
            end
            for (i = 0; i < 4; i = i + 1) begin
                ab = {2'b00, lo_r} + IKc[i][r / 4];
                if (RSEL[2*r + i/2])
                    rp[28*lf(r) + 7*i +: 7] = POOLc[r / 2] ? {(r < NH) ? !ab[6] : ab[6], ab[5:0]} : {1'b1, ab[5:0]};
            end
        end
    end
    reg  [NH-1:0]    lr0_v, lr0_t;
    (* keep = "true" *) reg [NH-1:0] lr0_ep;
    reg  [NH*28-1:0] lr0_p;
    always @(posedge ck or negedge rr[7]) if (!rr[7]) lr0_v <= {NH{1'b0}}; else lr0_v <= rv;
    always @(posedge ck) begin lr0_t <= rt; lr0_ep <= {NH{REPc[16]}}; lr0_p <= rp; end
    assign lr_v = lr0_v; assign lr_t = lr0_t; assign lr_ep = lr0_ep; assign lr_p = lr0_p;

    // ------------------------------------------------------------------------------------------------- answers
    // delay lines QD = 8 of ph_now / (rd_now && ph_now < NE) / pool_now: 7 plain stages, the 8th as kept per-chunk
    // decoded copies (one-hot phase e < NE, valid, pool)
    localparam integer QD = 8;
    reg  [2:0]   phl [1:QD-1];
    reg          vdl [1:QD-1];
    reg          pdl [1:QD-1];
    always @(posedge ck or negedge rr[9])
        if (!rr[9]) for (k = 1; k < QD; k = k + 1) vdl[k] <= 1'b0;
        else begin vdl[1] <= RD && (PH < NE); for (k = 2; k < QD; k = k + 1) vdl[k] <= vdl[k-1]; end
    always @(posedge ck) begin
        phl[1] <= PH; pdl[1] <= POOLc[8];
        for (k = 2; k < QD; k = k + 1) begin phl[k] <= phl[k-1]; pdl[k] <= pdl[k-1]; end
    end
    wire [3:0] pho_x = {phl[QD-1] == 3'd3, phl[QD-1] == 3'd2, phl[QD-1] == 3'd1, phl[QD-1] == 3'd0};
    (* keep = "true" *) reg [3:0]  PHO [0:16];               // [0..15] 16-bit source chunks, [16] tags / miss
    (* keep = "true" *) reg [16:0] VDc;                      // [0..15] 16-bit output chunks, [16] tags / miss
    (* keep = "true" *) reg [15:0] PDc;
    always @(posedge ck or negedge rr[10])
        if (!rr[10]) VDc <= 17'd0; else VDc <= {17{vdl[QD-1]}};
    always @(posedge ck) begin
        for (k = 0; k <= 16; k = k + 1) PHO[k] <= pho_x;
        PDc <= {16{pdl[QD-1]}};
    end
    always @(posedge ck) lqp <= lq;
    always @(posedge ck or negedge rr[9])
        if (!rr[9]) begin lqvp <= {NH{1'b0}}; lqbp <= {NH{1'b0}}; end else begin lqvp <= lq_v; lqbp <= lq_bad; end
    always @(posedge ck or negedge rr[11]) if (!rr[11]) fi_q <= 1'b0; else fi_q <= fault_i;
    // TDM edge e: N rows e (A), e + NE (B), S rows NH + NH-1-e (A), NH + NE-1-e (B); one-hot source select per chunk
    reg  [63:0] qs4 [0:3];                                   // na, nb, sa, sb
    reg  [255:0] xo;                                         // {xs, xn}
    reg  [2:0]   na, nb, sa, sb;
    reg  [7:0]   tn, ts;
    integer src, bt;
    always @* begin
        for (src = 0; src < 4; src = src + 1) begin
            qs4[src] = 64'd0;
            for (bt = 0; bt < 64; bt = bt + 1)
                for (e = 0; e < NE; e = e + 1)
                    if (PHO[4*src + bt/16][e])
                        qs4[src][bt] = qs4[src][bt] | lqp[64*lf((src == 0) ? e : (src == 1) ? e + NE :
                                                              (src == 2) ? NH + NH - 1 - e : NH + NE - 1 - e) + bt];
        end
        for (bt = 0; bt < 128; bt = bt + 1) begin
            // xn bit bt: chunk bt/16; xs bit bt: chunk 8 + bt/16
            if (MUT == 6) begin
                xo[bt]       = VDc[bt/16] && ((bt < 64) ? qs4[0][bt] : qs4[1][bt-64]);
                xo[128 + bt] = VDc[8 + bt/16] && (PDc[8 + bt/16] ? ((bt < 64) ? qs4[0][bt] : qs4[1][bt-64])
                                                                 : ((bt < 64) ? qs4[2][bt] : qs4[3][bt-64]));
            end else begin
                xo[bt]       = VDc[bt/16] && (((bt < 64) ? qs4[0][bt] : qs4[1][bt-64]) ||
                                              (PDc[bt/16] && ((bt < 64) ? qs4[2][bt] : qs4[3][bt-64])));
                xo[128 + bt] = VDc[8 + bt/16] && (((bt < 64) ? qs4[2][bt] : qs4[3][bt-64]) ||
                                                  (PDc[8 + bt/16] && ((bt < 64) ? qs4[0][bt] : qs4[1][bt-64])));
            end
        end
        miss = 1'b0; na = 3'd0; nb = 3'd0; sa = 3'd0; sb = 3'd0;
        for (e = 0; e < NE; e = e + 1)
            if (PHO[16][e]) begin
                miss = !lqvp[lf(e)] || !lqvp[lf(e + NE)] || !lqvp[lf(NH + NH - 1 - e)] || !lqvp[lf(NH + NE - 1 - e)];
                na = e; nb = e + NE; sa = NH - 1 - e; sb = NE - 1 - e;
            end
        if (MUT == 3) begin na = na + 1'b1; nb = nb + 1'b1; sa = sa + 1'b1; sb = sb + 1'b1; end
        if (VDc[16]) begin tn = {1'b1, nb, 1'b1, na}; ts = {1'b1, sb, 1'b1, sa}; end
        else begin tn = 8'd0; ts = 8'd0; miss = 1'b0; end
    end
    (* keep = "true" *) reg [CW-1:0] n_q, s_q;
    always @(posedge ck) begin
`ifdef OT_S5_XH3_MUT_RETAG
        n_q <= {retag(tn, 1), xo[127:0], ib_c2, g_dx};
`else
        n_q <= {retag(tn, 0), xo[127:0], ib_c2, g_dx};
`endif
        s_q <= {retag(ts, 1), xo[255:128], ib_c2, g_dx};
    end
    assign n_d = n_q;
    assign s_d = s_q;
    assign fault = fault_r;
endmodule
