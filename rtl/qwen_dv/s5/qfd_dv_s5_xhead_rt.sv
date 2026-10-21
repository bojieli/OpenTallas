`timescale 1ns/1ps
// QW-SLICE7-LEAVES 10-20 (XHEAD successor input): ot_qfd_xhead_rt = ot_qfd_xhead (rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv,
// claude/qw-slice6-heads-1019 f4746778a) copied verbatim except that the slice-side tag retag of qfd_dv_s5_xhead
// (N side 0, S side 1) is applied to tn / ts BEFORE the n_q / s_q output registers (was one combinational level after them
// in the qfd_dv_s5_xhead wrapper).  The retag is a pure function of the 8-bit tag, so moving it in front of the register
// changes no value and no edge (0 cycles).  XH_MUT 1 = the N retag taken as S (the OT_S5_XH_MUT bench mutant).
// This module is the generic-synthesis INPUT of the bounded constructor (tools/qwen_dv/bound_math_netlist.py); the
// production master is the constructed netlist qfd_dv_s5_xhead_bounded (see results/arch/qw_slice7_1020/xhead).
module ot_qfd_xhead_rt #(
    parameter integer XH_MUT = 0,
    parameter integer AW   = 24,
    parameter integer NW   = 18,
    parameter integer XCW  = 12,
    parameter integer TG   = 4,
    parameter integer IL   = 8,
    parameter integer NH   = 8,          // tiles per corridor (half column)
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer NATIVE_AFFINE = 0,
    parameter integer LEAF_READ_PIN_PIPE = 0, // explicit extra raw read pin capture, compiler-visible
    parameter integer LEAF_BANK_PIPE = 0, // candidate real leaf pipeline, one extra read edge
    parameter integer REQ_PIPE = 0,       // read-request relay stages after lr (flat column: head -> far leaf ~650 um
                                          // in one edge fails TT; +REQ_PIPE read edges, compiler-visible through DX)
    parameter integer DX   = 10 + LEAF_READ_PIN_PIPE + LEAF_BANK_PIPE + REQ_PIPE, // FILL_LEAD + 8 (lr register 1, leaf 5, answer pin register 1, launch 1)
    parameter integer FILL_LEAD = 2,     // the tap's two-entry attention-write queue (a queued beat can trail a go by 2)
    parameter integer LOCAL_RST = 0,     // opt-in: rst_n captured by a 2-flop synchroniser at the pin + 1 regional
                                         // stage (ot_rst_pipe); release +3 edges, cold init only, 0 normal edges
    parameter integer ONWARD_REG = 0,    // opt-in: b_d leaves from its own pin registers (duplicate of f_q / ib_pin /
                                         // g_pin on the same edge: 0 cycles), the internal copies feed only logic;
                                         // 2: input + output onward registers (+1 edge per head-row hop)
    parameter integer MUT  = 0           // 3: the TDM sends each line to the wrong station (wrong line);
                                         // 4: reads the other epoch (stale buffer); 6: pooled line without its B half
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [16*2*NH-1:0] tids,
    input  wire          fault_i,
    input  wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] a_d,
    output wire          a_r,
    output wire [1+(3*NW+13*AW+13)+(2+AW+2*XCW+4+NW+1)+(2+(AW-6)+6+64+1024)-1:0] b_d,
    input  wire          b_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] n_d,
    input  wire          n_r,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] s_d,
    input  wire          s_r,
    // leaf write chains (two: N leaves 0 .. NH/2-1, S leaves NH/2 .. NH-1), leaf read buses (one per leaf)
    output wire [1:0]    lw_v,
    output wire [1:0]    lw_ep,
    output wire [2*6-1:0] lw_off,
    output wire [2*64-1:0] lw_m,
    output wire [2*1024-1:0] lw_d,
    output wire [NH*18-1:0] lw_ctl,
    output wire [1:0]    lc_v,
    output wire [1:0]    lc_ep,
    output wire [NH-1:0] lr_v,
    output wire [NH-1:0] lr_t,
    output wire [NH-1:0] lr_ep,
    output wire [NH*28-1:0] lr_p,
    input  wire [NH*64-1:0] lq,
    input  wire [NH-1:0] lq_v,
    input  wire [NH-1:0] lq_bad,
    output reg           fault
);
    wire rst_i;
    generate if (LOCAL_RST != 0) begin : g_lrst
        wire [0:0] rq;
        ot_rst_pipe #(.REGIONS(1), .STAGES(1)) u_rst (.clk(ck), .rst_n_in(rst_n), .rst_n(rq));
        assign rst_i = rq[0];
    end else begin : g_prst
        assign rst_i = rst_n;
    end endgenerate
    localparam integer IBW  = 3 * NW + 13 * AW + 13;
    localparam integer BW   = AW - 6;
    localparam integer DESC = 2 + AW + 2 * XCW + 4 + NW + 1;
    localparam integer DATA = 2 + BW + 6 + 64 + 1024;
    localparam integer FW   = DESC + DATA;
    localparam integer HW   = 1 + IBW + FW;
    localparam integer CW   = 1 + IBW + 128 + 8;
    localparam integer NR   = 2 * NH;            // rows (tiles) of the column
    localparam integer NE   = NH / 2;            // TDM edges a tuple
    localparam integer QD   = 7 + LEAF_READ_PIN_PIPE + LEAF_BANK_PIPE + REQ_PIPE;      // read issue -> answer usable: lr 1, (relay), leaf 5, answer pin register 1
    // leaf / tile of row r: N station s in N leaf s / 2 (tile s mod 2), S station s in S leaf (NH-1-s) / 2 (tile
    // (NH-1-s) mod 2): a pooled pair (N s, S NH-1-s) sits at the SAME chain depth, and every read at TDM edge e is of
    // a leaf at depth <= e + 2 (the far leaves are read last: a fill reaches depth d d edges after depth 0)
    function automatic integer lf(input integer rw);
        lf = (rw < NH) ? (rw >> 1) : NE + ((NH - 1 - (rw - NH)) >> 1);
    endfunction
    function automatic integer tb(input integer rw);
        tb = (rw < NH) ? (rw & 1) : ((NH - 1 - (rw - NH)) & 1);
    endfunction
    generate if (DX - FILL_LEAD != QD + 1) begin : g_bad_dx
        initial $error("ot_qfd_xhead: DX must be FILL_LEAD + %0d", QD + 1);
    end endgenerate

    // ---- input pin registers = the onward copy (head-row station), ready ----
    // keep: with ONWARD_REG the internal copies must not be folded into the onward pin registers (same D)
    (* keep = "true" *) reg              g_pin;
    (* keep = "true" *) reg  [IBW-1:0]   ib_pin;
    (* keep = "true" *) reg  [FW-1:0]    f_q;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) g_pin <= 1'b0; else g_pin <= a_d[0];
    always @(posedge ck) begin ib_pin <= a_d[1 +: IBW]; f_q <= a_d[1 + IBW +: FW]; end
    generate if (ONWARD_REG >= 2) begin : g_onward2
        // ONWARD_REG 2 (Q-ELEM 2026-10-16, 129.6-um head): the onward copy takes TWO edges, an input pin register at the
        // a_d face and an output pin register at the b_d face, so neither leg crosses the full 129.6 um (w1 gate: one
        // register crossing it put capture at 243.6 ps).  +1 edge per head-row hop; the head's own copies are unchanged.
        wire [HW-1:0] b_mid;
        ot_qfd_onward_reg #(.W(HW)) u_onward_i (.ck(ck), .rst_n(rst_i), .d(a_d), .q(b_mid));
        ot_qfd_onward_reg #(.W(HW)) u_onward_o (.ck(ck), .rst_n(rst_i), .d(b_mid), .q(b_d));
    end else if (ONWARD_REG != 0) begin : g_onward
        // a keep_hierarchy module: wire-level keep did not stop synthesis folding f_q into these (m6s: e_d[454] = fep
        // still drove the fill logic), a hierarchy boundary does
        ot_qfd_onward_reg #(.W(HW)) u_onward (.ck(ck), .rst_n(rst_i), .d(a_d), .q(b_d));
    end else begin : g_shared
        assign b_d = {f_q, ib_pin, g_pin};
    end endgenerate
    reg br_q, nr_q, sr_q, ar_q, fi_q;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) begin br_q <= 1'b0; nr_q <= 1'b0; sr_q <= 1'b0; ar_q <= 1'b0; fi_q <= 1'b0; end
        else begin br_q <= b_r; nr_q <= n_r; sr_q <= s_r; ar_q <= br_q & nr_q & sr_q; fi_q <= fault_i; end
    assign a_r = ar_q;
    reg [16*NR-1:0] tid_q;                         // strap register (a constant tie at the die)
    always @(posedge ck) tid_q <= tids;

    // ---- go: FILL_LEAD edges (a queued attention beat and the far leaf's chain stages), then DX - FILL_LEAD to the
    //      corridors; ib is HELD, not delayed: gos are >= IL - 1 = 7 edges apart (a go while busy and not on the
    //      previous op's last edge faults), so hold registers (ib_q for the check, ib_c + one stage ib_c2 on the way
    //      out, DX - FILL_LEAD = 8 > 7) replace DX x IBW delay flops ----
    wire             g_q, g_dx;
    ot_hdc_delay #(.W(1), .D(FILL_LEAD), .RESET(1)) u_fill_go (.clk(ck), .rst_n(rst_i), .d(g_pin), .q(g_q));
    ot_hdc_delay #(.W(1), .D(DX - FILL_LEAD), .RESET(1)) u_gdx (.clk(ck), .rst_n(rst_i), .d(g_q), .q(g_dx));
    reg  [IBW-1:0]   ib_q, ib_c, ib_c2;            // ib of the go being checked / the go on its way to the corridors
    always @(posedge ck) begin
        if (g_pin) ib_q <= ib_pin;
        if (g_q) ib_c <= ib_q;
        ib_c2 <= ib_c;
    end

    // ---- fill fields ----
    wire              d_v   = f_q[0];
    wire              d_ep  = f_q[1];
    wire [AW-1:0]     d_xb  = f_q[2 +: AW];
    wire [XCW-1:0]    d_xcs = f_q[2 + AW +: XCW];
    wire [XCW-1:0]    d_xks = f_q[2 + AW + XCW +: XCW];
    wire [3:0]        d_sp  = f_q[2 + AW + 2*XCW +: 4];
    wire [NW-1:0]     d_k   = f_q[2 + AW + 2*XCW + 4 +: NW];
    wire              d_rnd = f_q[2 + AW + 2*XCW + 4 + NW];
    wire              fv    = f_q[DESC];
    wire              fep   = f_q[DESC + 1];
    wire [BW-1:0]     fb    = f_q[DESC + 2 +: BW];
    wire [5:0]        foff  = f_q[DESC + 2 + BW +: 6];
    wire [63:0]       fm    = f_q[DESC + 2 + BW + 6 +: 64];
    wire [1023:0]     fd    = f_q[DESC + 2 + BW + 6 + 64 +: 1024];

    // ---- epochs: 0 FREE, 1 FILL, 2 READ ----
    reg  [1:0]        st [0:1];
    reg  [AW-1:0]     e_xb  [0:1];
    reg  [XCW-1:0]    e_xcs [0:1];
    reg  [XCW-1:0]    e_xks [0:1];
    reg  [3:0]        e_sp  [0:1];
    reg  [NW-1:0]     e_k   [0:1];
    reg               e_rnd [0:1];
    reg               e_pool [0:1];
    // tile windows: beat W and start position of the tile's slot, per epoch and row
    reg  [BW-1:0]     wb  [0:1][0:NR-1];
    // {1'b0, W} + 1 and {1'b0, W} - 1 (BW + 1 bits, modulo 2^(BW+1)), precomputed with W in the descriptor's stage C:
    // the data beat's write enable/d then needs three BW-bit equality compares instead of an 19-bit subtraction
    reg  [BW:0]       wbp [0:1][0:NR-1];
    reg  [BW:0]       wbm [0:1][0:NR-1];
    reg  [5:0]        wo  [0:1][0:NR-1];      // write window start (pooled: 0, the slot is one whole beat)
    reg  [5:0]        ro  [0:1][0:NR-1];      // read offset = the footprint's start position (emin mod 64)
    // descriptor pipeline: masked quads + factors (stage A), products + footprint (stage B), windows + pool checks
    // (stage C, written at the end of the descriptor's third edge: the tap puts the first data beat >= 3 edges behind
    // its descriptor on the head row)
    reg               da_v, da_ep, dp_v, dp_ep;
    reg  [AW-1:0]     da_xb, dp_xb;
    reg  [XCW-1:0]    da_xcs, da_xks;
    reg  [NW-1:0]     da_km1;
    reg  [SMAX:0]     da_q [0:NR-1];
    reg  [AW-1:0]     dp_pr [0:NR-1];
    reg [NW-1:0] da_k;reg [5:0] dp_k;
    reg [7:0] first_abs [0:1][0:NR-1][0:3];
    reg [7:0] fa_q [0:NR-1][0:3];
    reg [12:0] go_bad_bits;
    reg  [AW-1:0]     dp_fm;                        // footprint - 1
    integer r, e, i;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) begin da_v <= 1'b0; dp_v <= 1'b0; end else begin da_v <= d_v; dp_v <= da_v; end
    always @(posedge ck) begin
        da_ep <= d_ep; da_xb <= d_xb; da_xcs <= d_xcs; da_xks <= d_xks; da_km1 <= d_k - 1'b1; da_k<=d_k;
        // quad q = (tile id) mod (S / TG)
        for (r = 0; r < NR; r = r + 1)
            da_q[r] <= tid_q[16*r +: 16] & ((({{SMAX{1'b0}}, 1'b1}) << (d_sp - $clog2(TG))) - 1'b1);
        dp_ep <= da_ep; dp_xb <= da_xb;
        dp_k<=da_k[5:0];
        dp_fm <= (NATIVE_AFFINE!=0) ? (TG*da_k-1) : (TG - 1) * {{(AW-XCW){1'b0}}, da_xcs} + {{(AW-NW){1'b0}}, da_km1} * {{(AW-XCW){1'b0}}, da_xks};
        // first chunk TG * q; product TG * q * xcs
        for (r = 0; r < NR; r = r + 1)
            if(NATIVE_AFFINE!=0)case(da_k)
                2:dp_pr[r]<=da_q[r]<<(1+$clog2(TG));
                6:dp_pr[r]<=(da_q[r]<<(2+$clog2(TG)))+(da_q[r]<<(1+$clog2(TG)));
                8:dp_pr[r]<=da_q[r]<<(3+$clog2(TG));
                24:dp_pr[r]<=(da_q[r]<<(4+$clog2(TG)))+(da_q[r]<<(3+$clog2(TG)));
                32:dp_pr[r]<=da_q[r]<<(5+$clog2(TG));
                default:dp_pr[r]<=0;
            endcase else dp_pr[r] <= (da_q[r] * TG) * da_xcs;
    end
    reg [AW-1:0] emin [0:NR-1];
    reg [AW-1:0] sw1 [0:NR-1], sw2 [0:NR-1], swm [0:NR-1];
    reg          c6 [0:NR-1];
    // (a + b + cin) mod 2^BW == k without a carry chain: the carry into bit i must be (a ^ b ^ k)_i, and the carry out
    // of bit i is then (a & b) | ((a | b) & ~k)
    function automatic sumk(input [BW-1:0] a, input [BW-1:0] b, input cin, input [BW-1:0] k);
        reg [BW-1:0] x;
        begin
            x = (a & b) | ((a | b) & ~k);
            sumk = ((a ^ b ^ k) == {x[BW-2:0], cin});
        end
    endfunction
    always @*
        for (r = 0; r < NR; r = r + 1) begin
            sw1[r] = dp_xb + dp_pr[r] + 24'd64;
            sw2[r] = dp_xb + dp_pr[r] + 24'd128;
            swm[r] = dp_xb + dp_pr[r] - 24'd64;
            c6[r]  = ({1'b0, dp_xb[5:0]} + {1'b0, dp_pr[r][5:0]}) >> 6;
        end
    reg          pool_n, pfault_n;
    always @* begin
        for (r = 0; r < NR; r = r + 1) emin[r] = dp_xb + dp_pr[r];
        pool_n = (dp_fm >= 64);
    end
    // pooled: the pair reads the same quad (equal start) and its footprint fits beats W, W + 1 (start + fp <= 128);
    // QW-SLICE7: OR tree of the 8 pair checks instead of a priority chain (same value)
    wire [NH-1:0] pf_t;
    genvar gp;
    generate for (gp = 0; gp < NH; gp = gp + 1) begin : g_pf
        // emin a != emin b  <=>  dp_pr a != dp_pr b (same dp_xb, mod 2^24); the footprint check keeps the original
        // 8-bit context (sum mod 256 >= 128 = bit 7)
        wire [7:0] fsum = {2'b00, emin[gp][5:0]} + dp_fm[7:0];
        assign pf_t[gp] = (dp_pr[gp] != dp_pr[NH + NH - 1 - gp]) || fsum[7];
    end endgenerate
    always @* pfault_n = (dp_fm >= 128) || (pool_n && (|pf_t));
    always @(posedge ck)
        if (dp_v) begin
            e_pool[dp_ep] <= pool_n;
            for (r = 0; r < NR; r = r + 1) begin
                // pooled: the S tile of a pair holds beat W + 1
                // QW-SLICE7 (same values, no chained adders): W = (emin[23:6] + s) mod 2^18 (s = pooled S tile), wbp =
                // {1'b0, W} + 1 = {&W, W + 1}, wbm = {1'b0, W} - 1 = {W == 0, W - 1}; every W + c is one 3-operand sum
                // dp_xb + dp_pr + 64c taken mod 2^24 (bits 23:6), so no adder follows another (was emin, then W +/- 1)
                // the wrap flags &W / W == 0 by the carry-free sum test A + B + c6 == K (no adder in front of them)
                if (pool_n && r >= NH) begin
                    wb[dp_ep][r]  <= sw1[r][AW-1:6];
                    wbp[dp_ep][r] <= {sumk(dp_xb[AW-1:6], dp_pr[r][AW-1:6], c6[r], {{(BW-1){1'b1}}, 1'b0}), sw2[r][AW-1:6]};
                    wbm[dp_ep][r] <= {sumk(dp_xb[AW-1:6], dp_pr[r][AW-1:6], c6[r], {BW{1'b1}}), emin[r][AW-1:6]};
                end else begin
                    wb[dp_ep][r]  <= emin[r][AW-1:6];
                    wbp[dp_ep][r] <= {sumk(dp_xb[AW-1:6], dp_pr[r][AW-1:6], c6[r], {BW{1'b1}}), sw1[r][AW-1:6]};
                    wbm[dp_ep][r] <= {sumk(dp_xb[AW-1:6], dp_pr[r][AW-1:6], c6[r], {BW{1'b0}}), swm[r][AW-1:6]};
                end
                wo[dp_ep][r] <= pool_n ? 6'd0 : emin[r][5:0];
                ro[dp_ep][r] <= emin[r][5:0];
                for(i=0;i<4;i=i+1) first_abs[dp_ep][r][i]<={2'b0,emin[r][5:0]}+i*dp_k;
                for(i=0;i<4;i=i+1) fa_q[r][i]<={2'b0,emin[r][5:0]}+i*dp_k;     // QW-SLICE7: stage-D copy (see pbad_t)
            end
        end

    // ---- stage D (integrity only, one edge after stage C): a pooled read position first_abs + k (k = 0 .. K-1, 8-bit
    //      as the read path forms it) with bit 7 set is a fault.  Every row / element / k of the op is read, so the
    //      check is a static property of the descriptor: flag the epoch here, raise the fault when its go is consumed
    //      (the read path keeps no per-operand overflow adder) ----
    reg          dq_v, dq_ep, dq_pool;
    reg  [5:0]   dq_k;
    reg          e_pbad [0:1];
    reg          pbad_n;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) dq_v <= 1'b0; else dq_v <= dp_v;
    always @(posedge ck) begin dq_ep <= dp_ep; dq_pool <= pool_n; dq_k <= dp_k; end
    // QW-SLICE7: one term per (row, element), OR-reduced as a tree (the original priority if-chain is 64 deep in a
    // generic netlist); x + k - 1 >= 128 with k != 0 is x + k >= 129 (9-bit), same value
    wire [NR*4-1:0] pbad_t;
    genvar gr, gi;
    generate for (gr = 0; gr < NR; gr = gr + 1) begin : g_pb
        for (gi = 0; gi < 4; gi = gi + 1) begin : g_e
            // fa = the value stage C wrote into first_abs[dq_ep] one edge ago (fa_q, a plain register written with it:
            // no epoch mux on this path).  fa + k >= 129 with k <= 63 <=> fa[7] or (fa[6] and fa[5:0] + k >= 65), and the
            // latter implies k != 0: one 7-bit carry ((fa[5:0] + k + 63) >= 128) instead of a 9-bit add + compare
            wire [7:0] fa = fa_q[gr][gi];
            wire [7:0] ksum = {2'b00, fa[5:0]} + {2'b00, dq_k} + 8'd63;
            assign pbad_t[4*gr + gi] = fa[7] || (fa[6] && ksum[7]);
        end
    end endgenerate
    always @* pbad_n = |pbad_t;
    always @(posedge ck) if (dq_v) e_pbad[dq_ep] <= dq_pool && pbad_n;

    // ---- the beat arrives unrotated (lane l = element 64*fb + foff + l): rotate lanes to positions (foff + l) mod 64
    //      in front of the leaf-write registers (f_q is a register; 6 levels of 2:1 per bit) ----
    wire [1023:0] rd_s [0:6];
    wire [63:0]   rm_s [0:6];
    assign rd_s[0] = fd;
    assign rm_s[0] = fm;
    genvar rs;
    generate for (rs = 0; rs < 6; rs = rs + 1) begin : g_rot
        localparam integer K = 1 << rs;
        assign rd_s[rs+1] = foff[rs] ? {rd_s[rs][1023-16*K:0], rd_s[rs][1023 -: 16*K]} : rd_s[rs];
        assign rm_s[rs+1] = foff[rs] ? {rm_s[rs][63-K:0], rm_s[rs][63 -: K]} : rm_s[rs];
    end endgenerate
    wire [1023:0] fd_r = rd_s[6];
    wire [63:0]   fm_r = rm_s[6];

    // ---- data beat -> leaf write control (one edge), to the leaf pins: per tile {en, d, wo} ----
    // d = fb - W in {0, +1, -1} as equality compares against the precomputed W, W + 1, W - 1 (no carry chain between
    // the beat register and the leaf-write control register; HEAD_MUT 7 / 8 / 9 drop the W + 1 / W - 1 / W match)
    reg  d0, dp1, dm1;
    reg  [NH*18-1:0] ctl;
    always @* begin
        ctl = {(NH*18){1'b0}};
        for (r = 0; r < NR; r = r + 1) begin
            d0  = (fb == wb[fep][r]) && (MUT != 9);
            dp1 = ({1'b0, fb} == wbp[fep][r]) && (MUT != 7);
            dm1 = ({1'b0, fb} == wbm[fep][r]) && (MUT != 8);
            ctl[18*lf(r) + 9*tb(r) +: 9] = {
                d0 || dp1 || dm1,                                                       // en
                dm1 ? 2'b10 : dp1 ? 2'b01 : 2'b00,                                      // d = fb - W
                wo[fep][r]};
        end
    end
    // one copy of the write word per chain (N, S): each chain head is driven by its own flops.  With ONWARD_REG the
    // two copies sit in separate keep_hierarchy face registers: as plain regs synthesis merged them (m6t netlist:
    // lw_d 2048 -> 1024 flops, lw_m 128 -> 64, lr0_p 224 -> 168, lr0_ep 8 -> 1), so one flop drove the N AND S face
    // pins (native launch E 245.7 / W 245.5; S-face buses cs_wm/rs_p median ~200 ps vs ~171 N).  Same edge, 0 cycles.
    wire         lwv_d = fv && (st[fep] != 2'd0);
    generate if (ONWARD_REG != 0) begin : g_wface
        genvar cw;
        for (cw = 0; cw < 2; cw = cw + 1) begin : g_c
            ot_qfd_face_reg #(.W(2+1+1+6+64+1024+NE*18), .RB(2)) u_w (.ck(ck), .rst_n(rst_i),
                .d({ctl[18*NE*cw +: 18*NE], fd_r, fm_r, foff, d_ep, fep, d_v, lwv_d}),
                .q({lw_ctl[18*NE*cw +: 18*NE], lw_d[1024*cw +: 1024], lw_m[64*cw +: 64], lw_off[6*cw +: 6], lc_ep[cw],
                    lw_ep[cw], lc_v[cw], lw_v[cw]}));
        end
    end else begin : g_wshared
        reg  [1:0]        lw_v_r, lw_ep_r, lc_v_r, lc_ep_r;
        reg  [2*6-1:0]    lw_off_r;
        reg  [2*64-1:0]   lw_m_r;
        reg  [2*1024-1:0] lw_d_r;
        reg  [NH*18-1:0]  lw_ctl_r;
        always @(posedge ck or negedge rst_i)
            if (!rst_i) begin lw_v_r <= 1'b0; lc_v_r <= 1'b0; end
            else begin
                lw_v_r <= {2{lwv_d}};
                lc_v_r <= {2{d_v}};
            end
        always @(posedge ck) begin
            lw_ep_r <= {2{fep}}; lw_off_r <= {2{foff}}; lw_m_r <= {2{fm_r}}; lw_d_r <= {2{fd_r}}; lw_ctl_r <= ctl;
            lc_ep_r <= {2{d_ep}};
        end
        assign lw_v = lw_v_r; assign lw_ep = lw_ep_r; assign lw_off = lw_off_r; assign lw_m = lw_m_r;
        assign lw_d = lw_d_r; assign lw_ctl = lw_ctl_r; assign lc_v = lc_v_r; assign lc_ep = lc_ep_r;
    end endgenerate

    // ---- the go: verify against the oldest filled epoch, then the TDM read sequencer ----
    wire [NW-1:0] b_tiles = ib_q[IBW - 2*NW +: NW];
    wire [NW-1:0] b_k     = ib_q[IBW - 3*NW +: NW];
    wire          b_wsrc  = ib_q[13*AW + 12];
    wire [AW-1:0] b_xbase = ib_q[8*AW + 12 +: AW];
    wire [AW-1:0] b_xks   = ib_q[7*AW + 12 +: AW];
    wire [AW-1:0] b_xjs   = ib_q[6*AW + 12 +: AW];
    wire [AW-1:0] b_xcs   = ib_q[5*AW + 12 +: AW];
    wire [3:0]    b_split = ib_q[5*AW + 5 +: 4];
    wire          b_round = ib_q[4*AW + 4];
    reg           ep_rd;                    // the next epoch a go consumes
    reg           busy;
    reg           rep;                      // the epoch being read
    reg  [NW-1:0] rnd_left, k_i, k_last;
    reg  [AW-1:0] kx;                       // k * xks
    reg  [XCW-1:0] rxcs, rxks;
    reg  [2:0]    ph;                       // TDM edge within the tuple (0 .. IL-1)
    wire          go_ok = (st[ep_rd] == 2'd1) && !b_wsrc && (b_xjs == 0) && (b_xbase == e_xb[ep_rd]) &&
                          (b_xcs == {{(AW-XCW){1'b0}}, e_xcs[ep_rd]}) && (b_xks == {{(AW-XCW){1'b0}}, e_xks[ep_rd]}) &&
                          (b_split == e_sp[ep_rd]) && (b_k == e_k[ep_rd]) && (b_round == e_rnd[ep_rd]) &&
                          (b_tiles != 0) && (b_k != 0);
    reg           f_pos;
    reg  [AW:0]   rel;
    reg  [5:0]    pos;
    localparam integer ABSW=NATIVE_AFFINE!=0 ? 8 : AW+1;
    reg [ABSW-1:0] ab;
    reg  [NH*28-1:0] rp;
    reg  [NH-1:0] rv;
    reg  [NH-1:0] rt;
    // the read of TDM edge 0 of tuple 0 leaves on the edge after the go's FILL_LEAD delay (positions from the descriptor)
    wire          rd_now = g_q || busy;
    wire [2:0]    ph_now = g_q ? 3'd0 : ph;
    wire          rep_now = g_q ? ((MUT == 4) ? ~ep_rd : ep_rd) : rep;
    wire          pool_now = e_pool[rep_now];
    wire [XCW-1:0] xcs_now = g_q ? e_xcs[ep_rd] : rxcs;
    wire [AW-1:0] kx_now = g_q ? {AW{1'b0}} : kx;
    wire          last = busy && (ph == IL - 1) && (k_i == k_last) && (rnd_left == 0);
    // the TDM edge on which row r is read: N e (line A), N e + NE (B), S NH-1-e (A), S NE-1-e (B)
    function automatic integer row_edge(input integer rw);
        begin
            if (rw < NE) row_edge = rw;
            else if (rw < NH) row_edge = rw - NE;
            else if (rw - NH >= NE) row_edge = NH - 1 - (rw - NH);
            else row_edge = NE - 1 - (rw - NH);
        end
    endfunction
    reg  [AW:0]   rel_i [0:3];
    always @* begin
        rp = {(NH*28){1'b0}}; rv = {NH{1'b0}}; rt = {NH{1'b0}}; f_pos = 1'b0;
        for (i = 0; i < 4; i = i + 1) rel_i[i] = i * xcs_now + kx_now;
        // every index below is static (row r, element i): no runtime part-select
        for (r = 0; r < NR; r = r + 1)
            if (rd_now && ph_now == row_edge(r)) begin
                rv[lf(r)] = 1'b1;
                rt[lf(r)] = tb(r);
                for (i = 0; i < 4; i = i + 1) begin
                    if(NATIVE_AFFINE!=0)begin
                        ab=first_abs[rep_now][r][i]+(g_q ? 6'd0 : k_i[5:0]);
                        if(pool_now)begin
                            rp[28*lf(r)+7*i+:7]={(r<NH)?!ab[6]:ab[6],ab[5:0]};
                        end else rp[28*lf(r)+7*i+:7]={1'b1,ab[5:0]};
                    end else begin
                    if (!pool_now) begin
                        // own slot: position (wo + rel) mod 64; a footprint <= 64 keeps rel < 64
                        if (rel_i[i] >= 64) f_pos = 1'b1;
                        pos = ro[rep_now][r] + rel_i[i][5:0];
                        rp[28*lf(r) + 7*i +: 7] = {1'b1, pos};
                    end else begin
                        // pooled: absolute position ro + rel: 0 .. 63 in the N tile's slot (beat W), 64 .. 127 in
                        // the S tile's (beat W + 1)
                        ab = {{(AW-5){1'b0}}, ro[rep_now][r]} + rel_i[i];
                        if (ab >= 128) f_pos = 1'b1;
                        rp[28*lf(r) + 7*i +: 7] = {(r < NH) ? !ab[6] : ab[6], ab[5:0]};
                    end                    end

                end
            end
    end
    reg  [NH-1:0]    lr0_v, lr0_t, lr0_ep;
    reg  [NH*28-1:0] lr0_p;
    always @(posedge ck) begin lr0_t <= rt; lr0_ep <= {NH{rep_now}}; lr0_p <= rp; end
    // the lr register (the leaf read pins at REQ_PIPE 0): with ONWARD_REG one keep_hierarchy register per face (N leaves
    // 0 .. NE-1, S leaves NE .. NH-1) so the N and S copies are not merged (see g_wface); same edge as lr0_*
    wire [NH-1:0]    lr1_v, lr1_t, lr1_ep;
    wire [NH*28-1:0] lr1_p;
    generate if (ONWARD_REG != 0) begin : g_rface
        genvar cr;
        for (cr = 0; cr < 2; cr = cr + 1) begin : g_c
            ot_qfd_face_reg #(.W(NE*(3+28)), .RB(NE)) u_r (.ck(ck), .rst_n(rst_i),
                .d({rp[28*NE*cr +: 28*NE], rt[NE*cr +: NE], {NE{rep_now}}, rv[NE*cr +: NE]}),
                .q({lr1_p[28*NE*cr +: 28*NE], lr1_t[NE*cr +: NE], lr1_ep[NE*cr +: NE], lr1_v[NE*cr +: NE]}));
        end
    end else begin : g_rshared
        assign lr1_v = lr0_v; assign lr1_t = lr0_t; assign lr1_ep = lr0_ep; assign lr1_p = lr0_p;
    end endgenerate
    // read-request relay (REQ_PIPE stages; 0 = the lr register drives the leaf pins directly)
    ot_hdc_delay #(.W(NH), .D(REQ_PIPE), .RESET(1)) u_lrv (.clk(ck), .rst_n(rst_i), .d(lr1_v), .q(lr_v));
    ot_hdc_delay #(.W(2*NH+NH*28), .D(REQ_PIPE)) u_lrd (.clk(ck), .rst_n(rst_i), .d({lr1_t, lr1_ep, lr1_p}),
        .q({lr_t, lr_ep, lr_p}));

    // ---- answers -> corridor launch (the leaf q pins feed the corridor's output flops through one mux) ----
    // the answer of a read issued at TDM edge e is usable QD edges later: carry the edge and the mode along
    wire [2:0] phd;
    wire       vd, pd;
    ot_hdc_delay #(.W(3), .D(QD)) u_phd (.clk(ck), .rst_n(rst_i), .d(ph_now), .q(phd));
    ot_hdc_delay #(.W(1), .D(QD), .RESET(1)) u_vd (.clk(ck), .rst_n(rst_i), .d(rd_now && ph_now < NE), .q(vd));
    ot_hdc_delay #(.W(1), .D(QD)) u_pd (.clk(ck), .rst_n(rst_i), .d(pool_now), .q(pd));
    // the leaves' answers are registered at this tile's pins (register -> wire -> register: r3 gate boundary)
    reg  [NH*64-1:0] lqp;
    reg  [NH-1:0]    lqvp, lqbp;
    always @(posedge ck) lqp <= lq;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) begin lqvp <= {NH{1'b0}}; lqbp <= {NH{1'b0}}; end else begin lqvp <= lq_v; lqbp <= lq_bad; end
    reg [127:0] xn, xs;
    reg [7:0]   tn, ts;
    reg [2:0]   na, nb, sa, sb;
    reg [63:0]  qna, qnb, qsa, qsb;
    reg         miss;
    always @* begin
        xn = 128'd0; xs = 128'd0; tn = 8'd0; ts = 8'd0; miss = 1'b0;
        qna = 64'd0; qnb = 64'd0; qsa = 64'd0; qsb = 64'd0;
        na = phd; nb = phd + NE; sa = NH - 1 - phd; sb = NE - 1 - phd;
        // static selects: TDM edge e reads N rows e, e + NE and S rows NH + NH-1-e, NH + NE-1-e
        for (e = 0; e < NE; e = e + 1)
            if (phd == e) begin
                qna = lqp[64*lf(e) +: 64];
                qnb = lqp[64*lf(e + NE) +: 64];
                qsa = lqp[64*lf(NH + NH - 1 - e) +: 64];
                qsb = lqp[64*lf(NH + NE - 1 - e) +: 64];
                miss = !lqvp[lf(e)] || !lqvp[lf(e + NE)] || !lqvp[lf(NH + NH - 1 - e)] || !lqvp[lf(NH + NE - 1 - e)];
            end
        if (vd) begin
            if (pd) begin
                xn = (MUT == 6) ? {qnb, qna} : {qnb | qsb, qna | qsa};
                xs = xn;
            end else begin
                xn = {qnb, qna};
                xs = {qsb, qsa};
            end
            if (MUT == 3) begin na = (na + 1'b1) & (NH - 1); nb = (nb + 1'b1) & (NH - 1); sa = (sa + 1'b1) & (NH - 1); sb = (sb + 1'b1) & (NH - 1); end
            tn = {1'b1, nb, 1'b1, na};
            ts = {1'b1, sb, 1'b1, sa};
        end else miss = 1'b0;
    end
    always @(posedge ck or negedge rst_i)
        if(!rst_i)go_bad_bits<=0;
        else go_bad_bits<=g_q ? {
            busy && !last,b_k==0,b_tiles==0,b_round!=e_rnd[ep_rd],b_k!=e_k[ep_rd],
            b_split!=e_sp[ep_rd],b_xks!={{(AW-XCW){1'b0}},e_xks[ep_rd]},
            b_xcs!={{(AW-XCW){1'b0}},e_xcs[ep_rd]},b_xbase!=e_xb[ep_rd],
            b_xjs!=0,b_wsrc,st[ep_rd]!=1,1'b0} : 13'd0;
    reg flt;
    wire flt_set =
        (d_v && NATIVE_AFFINE != 0 && (d_xks != 1 || d_xcs != d_k || !(d_k == 2 || d_k == 6 || d_k == 8 || d_k == 24 || d_k == 32))) ||
        (d_v && st[d_ep] != 2'd0) || (d_v && (d_sp < SMIN || d_sp > SMAX)) || (dp_v && pfault_n) ||
        ((NATIVE_AFFINE != 0 ? (g_q && e_pbad[rep_now]) : f_pos) || (NATIVE_AFFINE != 0 && |go_bad_bits)) ||
        (|lqbp) || miss || (g_q && NATIVE_AFFINE == 0 && (!go_ok || (busy && !last)));
    // FLT_PIPE (with ONWARD_REG 2, Q-LINK-D2D 2026-10-16): every fault condition lands in its own event flop fe[i] and the
    // sticky flt takes |fe one edge later (w2 gate: lqbp -> wide AND/OR cone -> flt -104 ps across the 129.6-um head).
    // The fault is sticky and only reported (fault chain), so +1 edge of fault latency changes no data edge.
    localparam integer FLT_PIPE = (ONWARD_REG >= 2) ? 1 : 0;
    reg [7:0] fe;
    always @(posedge ck or negedge rst_i)
        if (!rst_i) begin
            st[0] <= 2'd0; st[1] <= 2'd0; ep_rd <= 1'b0; busy <= 1'b0; flt <= 1'b0; fe <= 8'd0; lr0_v <= {NH{1'b0}};
            ph <= 3'd0; rep <= 1'b0; fault <= 1'b0;
        end else begin
            lr0_v <= rv;
            fe <= 8'd0;
            if (FLT_PIPE != 0 && |fe) flt <= 1'b1;
            if (FLT_PIPE == 0 && flt_set) flt <= 1'b1;      // QW-SLICE7: the eight set conditions OR-ed (was a priority chain)
            fault <= flt | fi_q;
            // descriptor: claim the epoch
            if (d_v) begin
                if(NATIVE_AFFINE!=0 && (d_xks!=1 || d_xcs!=d_k || !(d_k==2 || d_k==6 || d_k==8 || d_k==24 || d_k==32))) begin if (FLT_PIPE != 0) fe[0] <= 1'b1; end
                if (st[d_ep] != 2'd0) begin if (FLT_PIPE != 0) fe[1] <= 1'b1; end
                st[d_ep] <= 2'd1;
                e_xb[d_ep] <= d_xb; e_xcs[d_ep] <= d_xcs; e_xks[d_ep] <= d_xks; e_sp[d_ep] <= d_sp; e_k[d_ep] <= d_k;
                e_rnd[d_ep] <= d_rnd;
                if (d_sp < SMIN || d_sp > SMAX) begin if (FLT_PIPE != 0) fe[2] <= 1'b1; end
            end
            if (dp_v && pfault_n) begin if (FLT_PIPE != 0) fe[3] <= 1'b1; end
            if ((NATIVE_AFFINE!=0 ? (g_q && e_pbad[rep_now]) : f_pos) || (NATIVE_AFFINE!=0 && |go_bad_bits)) begin if (FLT_PIPE != 0) fe[4] <= 1'b1; end
            if (|lqbp) begin if (FLT_PIPE != 0) fe[5] <= 1'b1; end
            if (miss) begin if (FLT_PIPE != 0) fe[6] <= 1'b1; end                                          // a leaf did not answer its read
            // the go: consume the oldest filled epoch
            if (g_q) begin
                if (busy && last) st[(MUT == 4) ? ~rep : rep] <= 2'd0;     // back to back: the previous op's last edge
                if (NATIVE_AFFINE==0 && (!go_ok || (busy && !last))) begin if (FLT_PIPE != 0) fe[7] <= 1'b1; end
                else begin
                    st[ep_rd] <= 2'd2;
                    rep <= (MUT == 4) ? ~ep_rd : ep_rd;
                    ep_rd <= ~ep_rd;
                    busy <= 1'b1; ph <= 3'd1;
                    rnd_left <= b_tiles - 1'b1; k_i <= {NW{1'b0}}; k_last <= b_k - 1'b1; kx <= {AW{1'b0}};
                    rxcs <= b_xcs[XCW-1:0]; rxks <= b_xks[XCW-1:0];
                end
            end else if (busy) begin
                ph <= ph + 1'b1;
                if (ph == IL - 1) begin
                    if (k_i == k_last) begin
                        k_i <= {NW{1'b0}}; kx <= {AW{1'b0}};
                        if (rnd_left == 0) begin busy <= 1'b0; st[(MUT == 4) ? ~rep : rep] <= 2'd0; end
                        else rnd_left <= rnd_left - 1'b1;
                    end else begin
                        k_i <= k_i + 1'b1; kx <= kx + rxks;
                    end
                end
            end
        end
    function automatic [7:0] retag(input [7:0] t, input integer side_s);
        reg [2:0] a, b;
        begin
            a = t[2:0]; b = t[6:4];
            if (side_s ? !a[2] : a[2]) a = a ^ 3'd3;
            if (side_s ? !b[2] : b[2]) b = b ^ 3'd3;
            retag = {t[7], b, t[3], a};
        end
    endfunction
    (* keep *) reg [CW-1:0] n_q, s_q;
    always @(posedge ck) begin
        n_q <= {retag(tn, (XH_MUT != 0) ? 1 : 0), xn, ib_c2, g_dx};
        s_q <= {retag(ts, 1), xs, ib_c2, g_dx};
    end
    assign n_d = n_q;
    assign s_d = s_q;
endmodule

// qfd_dv_s5_xhead_rt: qfd_dv_s5_xhead with the retag inside the core (every output now leaves a flop directly).
module qfd_dv_s5_xhead_rt #(parameter integer HEAD_MUT = 0, parameter integer XH_MUT = 0, parameter integer IN_PIPE = 1) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [5:0]     cid,
    input  wire           fault_i,
    input  wire [1186:0]  a_f,
    input  wire [379:0]   a_ib,
    output wire [515:0]   n_d,
    output wire [515:0]   s_d,
    output wire           w0_v, w0_ep, c0_v, c0_ep, w1_v, w1_ep, c1_v, c1_ep,
    output wire [5:0]     w0_off, w1_off,
    output wire [63:0]    w0_m, w1_m,
    output wire [1023:0]  w0_d, w1_d,
    output wire [71:0]    w0_ctl, w1_ctl,
    output wire [3:0]     r0_v, r0_t, r0_ep, r1_v, r1_t, r1_ep,
    output wire [111:0]   r0_p, r1_p,
    input  wire [255:0]   q0, q1,
    input  wire [3:0]     q0_v, q1_v,
    input  wire [3:0]     q0_bad, q1_bad,
    output wire           l_rst_n,
    output wire           fault
);
    wire [1566:0]  a_d = {a_f, a_ib};
    wire [1:0]     lw_v, lw_ep, lc_v, lc_ep;
    wire [11:0]    lw_off;
    wire [127:0]   lw_m;
    wire [2047:0]  lw_d;
    wire [143:0]   lw_ctl;
    wire [7:0]     lr_v, lr_t, lr_ep;
    wire [223:0]   lr_p;
    wire [511:0]   lq = {q1, q0};
    wire [7:0]     lq_v = {q1_v, q0_v};
    wire [7:0]     lq_bad = {q1_bad, q0_bad};
    assign {w1_v, w0_v} = lw_v; assign {w1_ep, w0_ep} = lw_ep; assign {c1_v, c0_v} = lc_v; assign {c1_ep, c0_ep} = lc_ep;
    assign {w1_off, w0_off} = lw_off; assign {w1_m, w0_m} = lw_m; assign {w1_d, w0_d} = lw_d; assign {w1_ctl, w0_ctl} = lw_ctl;
    assign {r1_v, r0_v} = lr_v; assign {r1_t, r0_t} = lr_t; assign {r1_ep, r0_ep} = lr_ep; assign {r1_p, r0_p} = lr_p;
    localparam integer AW = 24, NW = 18, XCW = 12, NH = 8, NCOLD = 48;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer CW  = 1 + IBW + 128 + 8;
    wire rst_l;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_l));
    // QW-SLICE7 RST_RELAY 1 (priced: reset assertion +1 AND release +1 edge, boot only, 0 data edges): one UNRESET
    // distribution stage after the 2-stage landing, so the bounded constructor replicates this plain register (not the
    // async landing flops) and raw rst_n keeps 2 loads.  The column's x leaves take the same relayed reset (l_rst_n).
    reg rst_rr;
    always @(posedge ck) rst_rr <= rst_l;
    wire rst = rst_rr;
    assign l_rst_n = rst;
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
    reg [16*2*NH-1:0] tids;
    integer ri;
    always @(posedge ck)
        for (ri = 0; ri < 2 * NH; ri = ri + 1)
            tids[ri * 16 +: 16] <= 16'(tid(int'(cid), ri));
    // IN_PIPE 1 (QW-SLICE7-LEAVES, priced +1 edge): the whole head-row input a_d = {a_f, a_ib} lands in a pin register
    // stage in front of the core's own input registers.  Reason (measured, prep1): the fill rotation select foff (6 bits)
    // needs 6 x 1,088 mux loads; at <= 32 loads per copy every select bit needs >= 34 same-edge copies, i.e. > 32 loads
    // on the raw pin.  One extra stage lets the replica tree grow from a pin register instead (pin <= 32).  Uniform on
    // a_d (go, descriptor, data, ib together), so the head's internal order is unchanged; q / fault_i are not delayed.
    wire [1566:0] a_c;
    generate if (IN_PIPE != 0) begin : g_in_pipe
        reg [1566:1] ad_q;
        reg          ad_g;
        always @(posedge ck) ad_q <= a_d[1566:1];
        always @(posedge ck or negedge rst) if (!rst) ad_g <= 1'b0; else ad_g <= a_d[0];
        assign a_c = {ad_q, ad_g};
    end else begin : g_in_direct
        assign a_c = a_d;
    end endgenerate
    ot_qfd_xhead_rt #(.XH_MUT(XH_MUT), .AW(AW), .NW(NW), .XCW(XCW), .NH(NH), .NATIVE_AFFINE(1), .MUT(HEAD_MUT),
        .LEAF_READ_PIN_PIPE(1), .FILL_LEAD(5), .DX(14)) u_head (
        .ck(ck), .rst_n(rst), .tids(tids), .fault_i(fault_i),
        .a_d(a_c), .a_r(), .b_d(), .b_r(1'b1),
        .n_d(n_d), .n_r(1'b1), .s_d(s_d), .s_r(1'b1),
        .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
        .lc_v(lc_v), .lc_ep(lc_ep), .lr_v(lr_v), .lr_t(lr_t), .lr_ep(lr_ep), .lr_p(lr_p),
        .lq(lq), .lq_v(lq_v), .lq_bad(lq_bad), .fault(fault));
endmodule
