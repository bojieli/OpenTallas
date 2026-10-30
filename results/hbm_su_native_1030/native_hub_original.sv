
// ---------------------------------------------------------------------------------------------------------------------
// hub (hardened once: hnx_fused_hub_1019, the 432 x 432 fus_hub slot on the strip centre line).  ot_hnx_fused_top's own
// logic: job decode + checks (ph = 0 added), the scalar prologue with scb in a 1R1W 128x256 SRAM (registered read: the
// command bus gets one pipeline edge so the WGT beat takes the macro's data), the ROW-PIPELINED padded heap, / D, + eps,
// rsqrt, r broadcast; plus tree levels 4 and 5 (three ot_hnx_fused_tnode) and the 4 quadrant down buses.
// job word: as ot_hnx_fused_top.  Straps (die binder): wsc = last SCRD -> its scalar in scb (from the tree's round trip),
// pk*/pb* = the hub nodes' pads.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_fused_hub #(
    parameter integer D    = 5120,
    parameter integer RR   = 10,
    parameter integer NMAX = 8,
    parameter integer MUT  = 0,
    parameter integer UW   = 271,
    parameter integer DW   = 173,
    // N4EXT (HBM-MU-QUAD-3 n4, opt-in, default 0 = unchanged): 1 = levels 4 sit OUTSIDE the hub (one per die hub
    // partition: NW n4 = (Q0, Q1) = global lanes 0..15, NE n4 = (Q2, Q3) = 16..31); the hub receives ONE input per die hub
    // on uq0 (NW n4) / uq2 (NE n4) and does only level 5 t5 = (NW, NE); uq1 / uq3 unused, dq0 / dq2 drive the n4 nodes.
    parameter integer N4EXT = 0,
    parameter integer DELIVERED_RESET = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          job_v,
    input  wire [216:0]  job,
    output reg           done,
    output reg           fault,
    output wire          busy,
    input  wire [7:0]    wsc,
    input  wire [5:0]    pk4a,
    input  wire [5:0]    pk4b,
    input  wire [5:0]    pk5,
    input  wire          pb4a,
    input  wire          pb4b,
    input  wire          pb5,
    input  wire [UW-1:0] uq0,
    input  wire [UW-1:0] uq1,
    input  wire [UW-1:0] uq2,
    input  wire [UW-1:0] uq3,
    output wire [DW-1:0] dq0,
    output wire [DW-1:0] dq1,
    output wire [DW-1:0] dq2,
    output wire [DW-1:0] dq3
);
    localparam integer SD = D / 8, NM = D / 256, NB = NM;
    localparam integer NBP = (NB <= 1) ? 1 : (1 << $clog2(NB));
    localparam integer LG = $clog2(NBP);
    localparam integer LM = 5, LA = 6;
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D), DF = D >> DK;
    generate if (D % 256 != 0 || NM > 31 || NMAX > 16) begin : g_bad
        ot_hnx_fused_D_must_be_a_multiple_of_256 u_trap ();
    end endgenerate
    wire [3:0] rl;
    generate if (DELIVERED_RESET != 0) begin : g_delivered_reset
        ot_hnx_fused_delivered_reset #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    end else begin : g_legacy_reset
        ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    end endgenerate
    wire rs = rl[0];

    // ---- tree levels 4 / 5 and the down fan-out
    wire [UW-1:0] u4a, u4b, ur; wire [DW-1:0] d5a, d5b, dtop;
    generate if (N4EXT == 0) begin : g_t4
    ot_hnx_fused_tnode #(.DELIVERED_RESET(DELIVERED_RESET)) u_t4a (.clk(clk), .rst_n(rl[3]), .pad_k(pk4a), .pad_b(pb4a), .ua(uq0), .ub(uq1), .uo(u4a),
        .dn(d5a), .da(dq0), .db(dq1));
    ot_hnx_fused_tnode #(.DELIVERED_RESET(DELIVERED_RESET)) u_t4b (.clk(clk), .rst_n(rl[3]), .pad_k(pk4b), .pad_b(pb4b), .ua(uq2), .ub(uq3), .uo(u4b),
        .dn(d5b), .da(dq2), .db(dq3));
    end else begin : g_n4ext
        assign u4a = uq0; assign u4b = uq2;                // per-hub n4 outputs (NW, NE)
        assign dq0 = d5a; assign dq2 = d5b; assign dq1 = '0; assign dq3 = '0;
    end endgenerate
    ot_hnx_fused_tnode #(.DELIVERED_RESET(DELIVERED_RESET)) u_t5 (.clk(clk), .rst_n(rl[3]), .pad_k(pk5), .pad_b(pb5), .ua(u4a), .ub(u4b), .uo(ur),
        .dn(dtop), .da(d5a), .db(d5b));
    wire r_v = ur[270], r_t = ur[269], r_fa = ur[258], r_fo = ur[257], r_fl = ur[256];
    wire [9:0] r_x = ur[268:259]; wire [255:0] r_d = ur[255:0];
    wire sc_in = r_v && !r_t, vsum_v = r_v && r_t; wire [31:0] vsum = r_d[31:0];

    // ---- job decode
    reg [216:0] jq;
    wire j_post = jq[0]; wire [3:0] j_nm1 = jq[4:1];
    wire [18:0] ja = jq[23:5], jb = jq[42:24], jc = jq[61:43], jo = jq[80:62];
    wire [23:0] rsA = jq[104:81], rsB = jq[128:105], rsC = jq[152:129], rsO = jq[176:153];
    wire [5:0] nsc_j = j_post ? 6'(3 * (32'(j_nm1) + 1)) : 6'(32'(j_nm1) + 1);
    wire job_ok = (ja[2:0] == 3'd0) && (jb[2:0] == 3'd0) && (jc[2:0] == 3'd0) && (jo[2:0] == 3'd0) &&
                  (ja[7:3] == jb[7:3]) && (ja[7:3] == jo[7:3]) &&                    // lane-local: one bank phase
                  (MUT == 7 || j_post || ja[7:3] == 5'd0) &&                         // PRE csum tree: ph = 0
                  (rsA[7:0] == 8'd0) && (rsB[7:0] == 8'd0) && (rsO[7:0] == 8'd0) && (rsC[2:0] == 3'd0) &&
                  (j_post || rsB == 24'd0) &&                                        // PRE: the gain is a broadcast
                  (32'(j_nm1) < NMAX);

    // ---- scalars (prologue): scb[x] = scalar sector x, a 1R1W SRAM (48 of 128 rows)
    reg cv, cw, ch; reg [2:0] cop; reg [7:0] cx; reg [127:0] cd;
    reg rbv; reg [31:0] rb;
    reg [5:0] scl;
    wire [255:0] scb_rd; wire [5:0] wsx;
    ot_sram_1r1w_128x256_m1_r2c2 u_scb (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, wsx}), .rd_out(scb_rd),
        .w_ce_in(sc_in), .w_addr_in({1'b0, r_x[5:0]}), .wd_in(r_d), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // command pipeline edge: a WGT beat takes the macro's registered read of the address set on its issue edge
    reg pv; reg [2:0] pop; reg [7:0] px; reg [127:0] pd; reg prv; reg [31:0] prb;
    always @(posedge clk or negedge rs) if (!rs) begin pv <= 1'b0; prv <= 1'b0; end else begin pv <= cv; prv <= rbv; end
    always @(posedge clk) begin
        pop <= cop; px <= cx; pd <= cw ? (ch ? scb_rd[255:128] : scb_rd[127:0]) : cd; prb <= rb;
    end
    assign dtop = {pv, pop, px, pd, prv, prb};

    // ROW-PIPELINED padded heap (ot_hnx_fused_top's, unchanged): leaves NBP + b, block b = the b-th tree sum of a row
    reg [5:0] bi;
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer hgt(input integer x);
        integer h, y;
        begin h = LG; y = x; while (y > 1) begin y = y >> 1; h = h - 1; end hgt = h; end
    endfunction
    function automatic integer is_add(input integer x);
        is_add = (x >= 1 && x < NBP && ((((2 * x + 1) << (hgt(x) - 1)) - NBP) < NB)) ? 1 : 0;
    endfunction
    wire [31:0] nv [1:2*NBP-1]; wire nd [1:2*NBP-1]; wire cons [1:2*NBP-1]; wire fire [1:2*NBP-1];
    wire [2*NBP-1:0] ncol;
    assign ncol[0] = 1'b0;
    genvar n;
    generate
        for (n = NBP; n < 2 * NBP; n = n + 1) begin : g_leaf
            assign fire[n] = 1'b0;
            if (n - NBP < NB) begin : g_r
                reg [31:0] val; reg vld;
                wire hit = vsum_v && bi == 6'(n - NBP);
                always @(posedge clk or negedge rl[1])
                    if (!rl[1]) vld <= 1'b0;
                    else if (hit) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (hit) val <= vsum;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = hit && vld && !cons[n] && MUT != 4;
            end else begin : g_p
                assign nd[n] = 1'b0; assign nv[n] = 32'd0; assign ncol[n] = 1'b0;
            end
        end
        for (n = 1; n < NBP; n = n + 1) begin : g_vn
            if (is_add(n)) begin : g_add
                reg vld; reg [31:0] val; wire [LAV:0] av; wire [31:0] s; wire af;
                assign fire[n] = nd[2 * n] && nd[2 * n + 1];
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rl[1]), .v(fire[n]), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rl[1], fire[n], nv[2 * n], nv[2 * n + 1], s, af);
                always @(posedge clk or negedge rl[1])
                    if (!rl[1]) vld <= 1'b0;
                    else if (av[LAV]) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (av[LAV]) val <= s;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = (av[LAV] && vld && !cons[n] && MUT != 4) || af;
            end else begin : g_pass
                assign fire[n] = 1'b0; assign nd[n] = nd[2 * n]; assign nv[n] = nv[2 * n]; assign ncol[n] = 1'b0;
            end
        end
        assign cons[1] = nd[1];
        for (n = 2; n < 2 * NBP; n = n + 1) begin : g_cons
            if (is_add(n >> 1)) begin : g_ca assign cons[n] = fire[n >> 1]; end
            else if ((n & 1) == 0) begin : g_cp assign cons[n] = cons[n >> 1]; end
            else begin : g_cz assign cons[n] = 1'b0; end
        end
    endgenerate
    wire ss_v = nd[1]; wire [31:0] ss = nv[1];
    // scalar tail: / D, + eps, rsqrt
    reg [31:0] eps_r;
    reg ssv_q; reg [31:0] ss_q;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) ssv_q <= 1'b0; else ssv_q <= ss_v;
    always @(posedge clk) ss_q <= ss;
    wire [31:0] mq, me, rr; wire mq_v, rr_v2, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rl[2]), .v(ssv_q), .x(ss_q), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rl[2]), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rl[2], mq_v, mq, eps_r, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rl[2]), .v(ve[LA]), .x(me), .y(rr), .vo(rr_v2), .fault(f_rsq));

    // ---- sequencer (static calendar; ot_hnx_fused_top's, with the scb read issued on the beat's edge)
    localparam [2:0] S_IDLE = 0, S_SC = 1, S_SCW = 2, S_WG = 3, S_RUN = 4;
    reg [2:0] st; reg post; reg [3:0] nm1; reg [5:0] nsc, scs; reg [7:0] wt; reg sfault;
    reg [15:0] cs_r; reg [1:0] cj; reg [15:0] rsc_s;
    reg [3:0] wrow; reg [2:0] wb; reg [15:0] tg; reg [15:0] tw_next; reg [15:0] per; reg [4:0] gofs;
    reg [3:0] hr; reg dec; reg busy_q;
    assign busy = busy_q;                                        // registered output (1 edge after the state)
    always @(posedge clk or negedge rs) if (!rs) busy_q <= 1'b0; else busy_q <= (st != S_IDLE);
    wire [2:0] nbt = post ? 3'd5 : 3'd1;                         // WGT beats a row
    assign wsx = post ? 6'(3 * wrow + wb / 2) : 6'(wrow);       // scalar sector of beat wb of row wrow
    wire beat_wg = (st == S_WG) && wrow <= nm1 && wrow < 4'd2;
    wire beat_run = (st == S_RUN) && wrow <= nm1 && tg >= tw_next;
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; cv <= 1'b0; cw <= 1'b0; ch <= 1'b0; cop <= '0; cx <= '0;
            cd <= '0; rbv <= 1'b0; rb <= '0; jq <= '0; post <= 1'b0; nm1 <= '0; nsc <= '0; scs <= '0; scl <= '0;
            wt <= '0; sfault <= 1'b0; cs_r <= '0; cj <= '0; rsc_s <= '0; wrow <= '0; wb <= '0; tg <= '0;
            tw_next <= '0; per <= '0; gofs <= '0; bi <= '0; hr <= '0; eps_r <= '0; dec <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cv <= 1'b0; cw <= 1'b0; rbv <= 1'b0;
            if (sc_in) scl <= scl + 6'd1;
            if (vsum_v) bi <= (bi == 6'(NB - 1)) ? 6'd0 : bi + 6'd1;
            if (r_fl) sfault <= 1'b1;                                  // lane / tree-node faults
            if (|ncol) sfault <= 1'b1;
            if (f_div || f_eps || f_rsq) sfault <= 1'b1;
            if (rr_v2) begin rbv <= 1'b1; rb <= rr; hr <= hr + 4'd1; end
            if (r_fo && !r_fa) sfault <= 1'b1;                        // fins of one record on one edge
            if (job_v && st != S_IDLE) sfault <= 1'b1;                  // launch collision
            case (st)
                S_IDLE: if (job_v) begin
                    jq <= job; st <= S_SC; dec <= 1'b1;
                    scs <= '0; scl <= '0; sfault <= 1'b0; hr <= '0; bi <= '0;
                end
                S_SC: if (dec) begin
                    dec <= 1'b0;
                    if (!job_ok) begin fault <= 1'b1; st <= S_IDLE; end
                    else begin
                        post <= j_post; nm1 <= j_nm1; nsc <= nsc_j; eps_r <= jq[216:185];
                        cs_r <= jc[18:3]; cj <= '0; rsc_s <= rsC[18:3];
                        per <= j_post ? 16'(5 * NM) + 16'(jq[184:177]) : 16'(4 * NM) + 16'(jq[184:177]);
                        gofs <= j_post ? 5'd0 : 5'(NM);
                        cv <= 1'b1; cop <= 3'd0; cx <= '0;
                        cd <= {19'd0, jq[184:177], rsO[18:3], rsB[18:3], rsA[18:3], jo[18:3], jb[18:3], ja[18:3], j_nm1, j_post};
                    end
                end else begin                                          // one SCRD a cycle
                    cv <= 1'b1; cop <= 3'd2; cx <= 8'(scs); cd <= {112'd0, cs_r + 16'(cj)};
                    if (cj == (post ? 2'd2 : 2'd0)) begin cj <= '0; cs_r <= cs_r + rsc_s; end else cj <= cj + 2'd1;
                    scs <= scs + 6'd1;
                    if (scs + 6'd1 == nsc) begin st <= S_SCW; wt <= wsc; end
                end
                S_SCW: if (wt != 8'd0) wt <= wt - 8'd1;
                       else begin
                           if (scl != nsc) sfault <= 1'b1;               // a scalar missed its fixed return
                           st <= S_WG; wrow <= '0; wb <= '0;
                       end
                S_WG: begin                                             // rows 0 and 1 into slots 0 / 1, then GO
                    if (beat_wg) begin
                        cv <= 1'b1; cw <= 1'b1; ch <= wb[0]; cop <= 3'd1; cx <= {wrow, wrow[0], wb};
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; end else wb <= wb + 3'd1;
                    end else begin
                        cv <= 1'b1; cop <= 3'd3; st <= S_RUN; tg <= '0; wb <= '0;
                        tw_next <= 16'(gofs) + per + 16'(RR + 8);         // row p >= 2 beats RR + 8 after row p - 1 starts
                    end
                end
                S_RUN: begin
                    tg <= tg + 16'd1;
                    if (beat_run) begin
                        cv <= 1'b1; cw <= 1'b1; ch <= wb[0]; cop <= 3'd1; cx <= {wrow, wrow[0], wb};
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; tw_next <= tw_next + per; end
                        else wb <= wb + 3'd1;
                    end
                    if (r_fa) begin
                        st <= S_IDLE;
                        if (sfault || r_fl || (!post && hr != nm1 + 4'd1)) fault <= 1'b1; else done <= 1'b1;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
