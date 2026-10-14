module smpub_parent_reference #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MUT_PAR = 0,
    parameter integer NSS = 4,
    parameter integer SD = 8,
    parameter integer AD = 32              // per-SM arrival entries in every slice (= the slice default; row credits)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               pub_v,
    output wire               pub_rdy,
    input  wire [39:0]        pub_base,
    input  wire [31:0]        pub_stride,
    input  wire [1:0]         pub_space,
    input  wire [19:0]        pub_m,
    input  wire [12:0]        pub_q,
    input  wire [3:0]         pub_p,
    input  wire               pub_bf16,
    output reg                pub_done,
    output reg                pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output reg                s0_v,
    output reg  [19:0]        s0_idx,
    output reg  [31:0]        s0_data,
    output reg  [NSM-1:0]     sm_cr          // row credits to ot_hgi_sm_record: slice pulses, one output flop
);
    localparam integer NSL = (NSM + NSS - 1) / NSS;            // slices
    localparam integer NCOL = (NSL + 1) / 2;                   // columns (slice k: column k % NCOL; N row k < NCOL)
    localparam integer NIN = (NSL + NPC - 1) / NPC;            // slices a VM client (slice k -> client k % NPC)
    localparam integer LV = (NSL <= 2) ? 1 : $clog2(NSL);      // STREAM tree levels
    localparam integer NLF = 1 << LV;                          // tree leaves (leaf 2c = slice c, 2c + 1 = slice c + NCOL)
    localparam integer W = 52, CW = 76;
    localparam integer NSMP = NSL * NSS;
    integer k, j;
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---- command: pin flops, accept processed one edge after the handshake
    reg rel, busy, acc_q; reg [39:0] pf_b; reg [31:0] pf_s; reg [1:0] pf_sp; reg [19:0] pf_m; reg [12:0] pf_q;
    reg [3:0] pf_p; reg pf_bf;
    assign pub_rdy = rel && !busy && !acc_q;
    always @(posedge clk) begin pf_b <= pub_base; pf_s <= pub_stride; pf_sp <= pub_space; pf_m <= pub_m; pf_q <= pub_q;
                                pf_p <= pub_p; pf_bf <= pub_bf16; end
    // command chain: cp[0] at the command port, one relay a column
    // {sm, bf, ob 18, ost 18, mm 20, qq 13, pp 4} fields (no reset) and the go pulse (reset), one stage a column
    reg [NCOL*(CW-1)-1:0] cfd; reg [NCOL-1:0] cgo;
    reg r1_v; reg [W-1:0] r1_d; reg agg_r;
    always @(posedge clk) begin
        if (acc_q) cfd[0 +: CW-1] <= {pf_sp == 2'd2, pf_bf, pf_b[17:0], pf_s[17:0], pf_m, pf_q, pf_p};
        for (j = 1; j < NCOL; j = j + 1) cfd[j*(CW-1) +: CW-1] <= cfd[(j-1)*(CW-1) +: CW-1];
    end
    // ---- slices
    wire [NSMP-1:0] rv_p = NSMP'(sm_rv);
    wire [NSMP*12-1:0] rr_p = (NSMP*12)'(sm_rrow);
    wire [NSMP*NC*32-1:0] rd_p = (NSMP*NC*32)'(sm_rdata);
    wire [NSL-1:0] s_wv, s_sov, s_dn, s_ft; wire [NSL*279-1:0] s_wp; wire [NSL*W-1:0] s_sod;
    wire [NSL-1:0] s_cr; wire [NSMP-1:0] s_smcr;
    always @(posedge clk or negedge rn) if (!rn) sm_cr <= '0; else sm_cr <= NSM'(s_smcr);
    genvar gk, gl, gn, gc, gj;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_s
        localparam integer COL = gk % NCOL;
        localparam integer NE_ = (NSM - gk * NSS >= NSS) ? NSS : NSM - gk * NSS;
        localparam [NSS-1:0] EN = NSS'((1 << NE_) - 1);
        wire [CW-1:0] ci = {cgo[COL], cfd[COL*(CW-1) +: CW-1]};
`ifdef SYNTHESIS
        ot_hgi_sm_pub_slice u (
`else
        ot_hgi_sm_pub_slice #(.NSS(NSS), .NC(NC), .SD(SD), .AD(AD), .MUT_ROW(MUT_ROW), .MUT_PAR(MUT_PAR)) u (
`endif
            .clk(clk), .rst_n(rst_n), .sid(3'(gk)), .sm_en(EN), .c_go(ci[CW-1]), .c_sm(ci[CW-2]), .c_bf(ci[CW-3]),
            .c_ob(ci[72:55]), .c_ost(ci[54:37]), .c_mm(ci[36:17]), .c_qq(ci[16:4]), .c_pp(ci[3:0]),
            .sm_rv(rv_p[gk*NSS +: NSS]), .sm_rrow(rr_p[gk*NSS*12 +: NSS*12]), .sm_rdata(rd_p[gk*NSS*NC*32 +: NSS*NC*32]),
            .w_v(s_wv[gk]), .w_pkt(s_wp[gk*279 +: 279]), .w_ack(s_ack[gk]),
            .so_v(s_sov[gk]), .so_idx(s_sod[gk*W+32 +: 20]), .so_data(s_sod[gk*W +: 32]), .so_cr(s_cr[gk]),
            .s_done(s_dn[gk]), .s_fault(s_ft[gk]), .sm_cr(s_smcr[gk*NSS +: NSS]));
    end endgenerate
    // ---- done / fault return: col + 1 relays a slice
    wire [NSL-1:0] dn_l, ft_l;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_ret
        localparam integer DL = gk % NCOL + 1;
        reg [DL:0] dq, fq;
        always @(posedge clk or negedge rn)
            if (!rn) begin dq <= '0; fq <= '0; end
            else begin dq <= {dq[DL-1:0], s_dn[gk]}; fq <= {fq[DL-1:0], s_ft[gk]}; end
        assign dn_l[gk] = dq[DL-1]; assign ft_l[gk] = fq[DL-1];
    end endgenerate
    // ---- VM: one merge node a client (its slices' held packets; one write out a client, as MEM 1)
    wire [NPC-1:0] vq_vw; wire [NSL-1:0] s_ack;
    localparam integer OWW = (NIN > 1) ? $clog2(NIN) : 1;
    generate for (gc = 0; gc < NPC; gc = gc + 1) begin : g_c
        reg [NIN-1:0] pend, ak; reg bsy, n_v, va_q, vq_v; reg [278:0] n_p, vq_p; reg [OWW-1:0] own, rr;
        assign vq_vw[gc] = vq_v;
        assign vmq[gc*338 +: 338] = {vq_v, 1'b1, 12'd0, vq_p[278:264], 5'd0, vq_p[263:8],
            {{4{vq_p[7]}}, {4{vq_p[6]}}, {4{vq_p[5]}}, {4{vq_p[4]}}, {4{vq_p[3]}}, {4{vq_p[2]}}, {4{vq_p[1]}}, {4{vq_p[0]}}},
            16'h5042};
        always @(posedge clk) if (n_v) vq_p <= n_p;
        always @(posedge clk or negedge rn) begin
            if (!rn) begin pend <= '0; ak <= '0; bsy <= 1'b0; n_v <= 1'b0; va_q <= 1'b0; vq_v <= 1'b0; own <= '0; rr <= '0; end
            else begin : nd
                reg f; integer q_, jj; reg [NIN-1:0] pn;
                va_q <= vmr[gc*274 + 273] && vmr[gc*274 + 256];           // port pin flop (MEM 1: vr[273] && vr[256])
                vq_v <= n_v; n_v <= 1'b0; ak <= '0;
                pn = pend;
                for (q_ = 0; q_ < NIN; q_ = q_ + 1) if (gc + q_ * NPC < NSL) if (s_wv[gc + q_ * NPC]) pn[q_] = 1'b1;
                f = 1'b0;
                if (!bsy) for (jj = 0; jj < NIN; jj = jj + 1) begin q_ = (rr + 1 + jj) % NIN;
                    if (!f && pend[q_]) begin
                        f = 1'b1; pn[q_] = 1'b0; own <= OWW'(q_); rr <= OWW'(q_); bsy <= 1'b1; n_v <= 1'b1;
                        n_p <= s_wp[(gc + q_ * NPC) * 279 +: 279];
                    end
                end
                if (bsy && va_q) begin bsy <= 1'b0; ak[own] <= 1'b1; end    // acknowledged: back to the owning slice
                pend <= pn;
            end
        end
        for (gj = 0; gj < NIN; gj = gj + 1) begin : g_a
            if (gc + gj * NPC < NSL) begin : g_ae assign s_ack[gc + gj * NPC] = ak[gj]; end
        end
    end endgenerate
    // ---- STREAM: credit tree of 2:1 nodes (level 0 = the slices)
    wire [(LV+1)*NLF-1:0] t_v, t_cr, t_a; wire [(LV+1)*NLF*W-1:0] t_d;
    generate
        for (gn = 0; gn < NLF; gn = gn + 1) begin : g_lf
            localparam integer SK = (gn % 2 == 0) ? gn / 2 : gn / 2 + NCOL;
            if (gn / 2 < NCOL && SK < NSL) begin : g_e
                assign t_v[gn] = s_sov[SK]; assign t_d[gn*W +: W] = s_sod[SK*W +: W]; assign s_cr[SK] = t_cr[gn];
            end else begin : g_z
                assign t_v[gn] = 1'b0; assign t_d[gn*W +: W] = '0;
            end
            assign t_a[gn] = 1'b0;
        end
        for (gl = 1; gl <= LV; gl = gl + 1) begin : g_l
            for (gn = 0; gn < (NLF >> gl); gn = gn + 1) begin : g_n
                localparam integer B = gl * NLF + gn, C0 = (gl - 1) * NLF + 2 * gn;
                ot_hgi_sm_pub_smrg #(.D(SD), .W(W), .ROOT(gl == LV), .LVL(gl)) u (
                    .clk(clk), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
            end
            for (gn = (NLF >> gl); gn < NLF; gn = gn + 1) begin : g_u
                assign t_v[gl*NLF + gn] = 1'b0; assign t_d[(gl*NLF + gn)*W +: W] = '0; assign t_a[gl*NLF + gn] = 1'b0;
                if (gl < LV) begin : g_uc assign t_cr[gl*NLF + gn] = 1'b0; end
            end
        end
        for (gn = 0; gn < NLF; gn = gn + 1) begin : g_tc
            assign t_cr[LV*NLF + gn] = 1'b0;
        end
    endgenerate
    // root -> relay -> s0 (the port register); the root's busy snapshot relayed to the collector
    always @(posedge clk) begin if (t_v[LV*NLF]) r1_d <= t_d[LV*NLF*W +: W]; if (r1_v) begin s0_idx <= r1_d[51:32]; s0_data <= r1_d[31:0]; end end
    // ---- control
    reg [NSL-1:0] sdn; reg [7:0] allc;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            rel <= 1'b0; busy <= 1'b0; acc_q <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0; s0_v <= 1'b0; r1_v <= 1'b0;
            agg_r <= 1'b0; sdn <= '0; allc <= 8'd0; cgo <= '0;
        end else begin
            rel <= 1'b1;
            acc_q <= pub_v && pub_rdy;
            pub_done <= 1'b0; cgo <= {cgo, 1'b0};
            r1_v <= t_v[LV*NLF]; s0_v <= r1_v; agg_r <= t_a[LV*NLF];
            if (|ft_l) pub_fault <= 1'b1;                                   // a slice overrun: fail closed
            if (acc_q) begin
                if (!(pf_sp == 2'd1 || pf_sp == 2'd2) || pf_p == 4'd0 || pf_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sdn <= '0; allc <= 8'd0;
                    cgo[0] <= 1'b1;
                end
            end else if (busy) begin
                sdn <= sdn | dn_l;
                if (&sdn && allc != 8'hFF) allc <= allc + 8'd1;
                if (&sdn && allc >= 8'(LV + 1) && !agg_r && vq_vw == 0) begin busy <= 1'b0; pub_done <= 1'b1; end
            end
        end
    end
endmodule