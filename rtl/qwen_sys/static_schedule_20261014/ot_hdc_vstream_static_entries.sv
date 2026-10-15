// Static actual-RTL successor; original engine SHA256 6a2aa7a96fdc5dc1271d24fbe15bcfed5e11bf51049297e361b41a6d75b96a4d
// Distinct physical-clock candidate; actual phases/RC/roots remain unqualified.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Vector stream unit of the hardwired decode core: SW lanes (a multiple of 8).
//
// The instruction is the scalar stream unit's (rtl/hdc/ot_hdc_stream.sv): a
// 2-D loop (outer o, inner i) over elements, each through the fixed element
// pipeline.  Here the inner loop advances a VECTOR of SW elements a cycle:
// lane l of vector v takes element v*SW + l of the current outer iteration
// (VI mode), a lane past the inner count stays idle, and a new outer
// iteration starts a new vector.  Every lane is the scalar datapath
// (ot_hdc_vstream_lane, generated from ot_hdc_stream.sv); lanes run in
// lockstep, so every element of a vector retires in the same cycle and a new
// op of another class waits for the unit to drain, as before.
//
// Reductions (one segment per outer iteration) go to ot_hdc_vreduce, which
// implements the arithmetic contract R-ARITH: chunks of 8 contiguous elements
// summed sequentially from +0, the chunk sums added by a pairwise tree padded
// with +0 (tools/hdc_golden.py reduce_chunked) -- independent of SW.  An idle
// lane contributes +0 to a SUM and lane 0's element to a MAX.
//
// `progress` counts the VECTORS the latest instruction has written (element
// chaining in vector units: tools/hdc_program.py chase_threshold).
// ---------------------------------------------------------------------------
module ot_hdc_vstream_static_entries #(
    parameter integer SW = 8,
    parameter integer LV = 4,         // the reducer's time levels: segments of up to 2^LV vectors
    parameter integer WR = 64,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer KV_FP8 = 1,     // KV cache in FP8 E4M3 (else BF16): hdc_golden.KV_FMT
    parameter integer ML = 0,         // lane memory-read latency (ot_hdc_vstream_lane ML): memories answer 1 + ML edges late
    parameter integer LOFF = 0,       // 1: the per-lane address offsets (cur + l x stride) are formed here and every lane is
                                      // instantiated with LANE 0, so all SW lanes are ONE module (one synthesis, kept
                                      // hierarchy); the same AW-bit sums, 0 cycles.  0 = the original per-lane paramods.
    parameter integer RTREE = 0,      // 1: replicated reset registers -- one for the stream control/reducer and one per lane
                                      // (each async-assert / registered-deassert from rst_n), so no reset net spans the SW
                                      // lanes (64 x ~12k flops); every flop's reset deasserts exactly one edge later.
    parameter integer LT = 0,         // 1: each lane is the hardened tile ot_hdc_vstream_lane_t (pin flops in/out, own reset
                                      // register and clock tree) behind RD relay stages each way (broadcast fields: one
                                      // kept relay copy per group of 8 lanes first); requires LOFF = 1.  Lanes see the
                                      // memories 2 + 2*RD edges later (their ML grows by that); outputs leave 1 + RD later.
    parameter integer RD = 2,         // LT: relay stages each way between the vstream ports / control and each lane tile
    parameter integer RED_ENTRIES = 0 // opt-in functional regional64 reducer; physical top supplies nine distinct clocks
) (
    input wire[SW-1:0]ck_head,ck_exp,ck_rcp,ck_rsq,
    input  wire [SW-1:0] ck_lane, input wire[8:0]ck_red,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_nin,
    input  wire              i_asrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi,
    input  wire              i_bsrc,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_csrc,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire [1:0]        i_ma,
    input  wire [1:0]        i_mb,
    input  wire [2:0]        i_ad,
    input  wire [2:0]        i_sfu,
    input  wire              i_mc,
    input  wire              i_md,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire [1:0]        i_red,
    input  wire              i_redsq,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2,
    // reads: one port per lane and operand
    output wire [SW-1:0]     va_re,
    output wire [SW*AW-1:0]  va_addr,
    input  wire [SW*32-1:0]  va_q,
    output wire [SW-1:0]     vb_re,
    output wire [SW*AW-1:0]  vb_addr,
    input  wire [SW*32-1:0]  vb_q,
    output wire [SW-1:0]     vc_re,
    output wire [SW*AW-1:0]  vc_addr,
    input  wire [SW*32-1:0]  vc_q,
    // weight ROM (embedding rows): one word a vector, lane 0's address
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output wire [SW-1:0]     crom_re,
    output wire [SW*AW-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    // writes: one port per lane
    output wire [SW-1:0]     vm_we,
    output wire [SW*AW-1:0]  vm_waddr,
    output wire [SW*32-1:0]  vm_wdata,
    output wire [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    output reg  [15:0]       progress,
    output reg  [15:0]       progress_rows,  // outer iterations (rows) the latest instruction has written
    output reg               fault,
    // observation (qwen-rtl-finish 2026-10-07: the split controller's issue shell rebuilds ready from these)
    output wire              obs_active,
    output wire [7:0]        obs_inflight
);
    // ---- reset: the control/reducer copy (RTREE: its own register; each lane registers its own copy below) ----
    wire rst_c;
    generate if (RTREE != 0) begin : g_rc
        reg rc;
        always @(posedge clk or negedge rst_n) if (!rst_n) rc <= 1'b0; else rc <= 1'b1;
        assign rst_c = rc;
    end else begin : g_rcw
        assign rst_c = rst_n;
    end endgenerate
    localparam integer LS = $clog2(SW);

    // -- issue loop: vectors --------------------------------------------------------
    reg              active;
    reg [2:0]        cls;
    reg [7:0]        inflight;             // vectors emitted, not yet retired
    reg [NW-1:0]     o, v, nout_r, nin_r, nvec_r;
    reg              v_last_r, o_last_r;
    reg [NW:0]       fin_th;
    reg [AW-1:0]     rowa, rowb, rowc, rowd, cura, curb, curc, curd, rrow;
    reg [AW-1:0]     aso, asi, bso, bsi, cso, csi, dso, dsi, rso;
    reg              asrc, bsrc, csrc, mc, md, redsq;
    reg [1:0]        ma, mb, dst, red;
    reg [2:0]        ad;
    reg [31:0]       imm1, imm2;
    wire             reducer_busy;
    wire [SW-1:0]    l_retire;
    wire             retire = l_retire[0];  // lane 0 carries every vector

    assign ready = !active && ((i_sfu == cls) || (inflight == 0));
    // The compiler owns issue. ready is diagnostic only; illegal overlap faults.
    wire   accept = go;
    wire   emit = active;
    wire [NW-1:0] nvec_in = (i_nin + (SW - 1)) >> LS;

    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin
            active <= 1'b0; cls <= 3'd0; inflight <= 0;
        end else begin
            inflight <= inflight + (emit ? 8'd1 : 8'd0) - (retire ? 8'd1 : 8'd0);
            if (accept) begin
                active <= 1'b1; cls <= i_sfu;
            end else if (active && v_last_r && o_last_r) begin
                active <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (accept) begin
            o <= 0; v <= 0; nout_r <= i_nout; nin_r <= i_nin; nvec_r <= nvec_in;
            v_last_r <= (nvec_in == 1); o_last_r <= (i_nout == 1);
            fin_th <= {1'b0, nvec_in} - 17'd8;
            rowa <= i_abase; cura <= i_abase; rowb <= i_bbase; curb <= i_bbase;
            rowc <= i_cbase; curc <= i_cbase; rowd <= i_dbase; curd <= i_dbase; rrow <= i_rbase;
            aso <= i_aso; asi <= i_asi; bso <= i_bso; bsi <= i_bsi; cso <= i_cso; csi <= i_csi;
            dso <= i_dso; dsi <= i_dsi; rso <= i_rso;
            asrc <= i_asrc; bsrc <= i_bsrc; csrc <= i_csrc; mc <= i_mc; md <= i_md;
            ma <= i_ma; mb <= i_mb; ad <= i_ad; dst <= i_dst; red <= i_red; redsq <= i_redsq;
            imm1 <= i_imm1; imm2 <= i_imm2;
        end else if (active) begin
            if (!v_last_r) begin
                v <= v + 1'b1; v_last_r <= (v + 2 == nvec_r);
                cura <= cura + (asi << LS); curb <= curb + (bsi << LS);
                curc <= curc + (csi << LS); curd <= curd + (dsi << LS);
            end else begin
                v <= 0; v_last_r <= (nvec_r == 1);
                o <= o + 1'b1; o_last_r <= (o + 2 == nout_r);
                rowa <= rowa + aso; cura <= rowa + aso; rowb <= rowb + bso; curb <= rowb + bso;
                rowc <= rowc + cso; curc <= rowc + cso; rowd <= rowd + dso; curd <= rowd + dso;
                rrow <= rrow + rso;
            end
        end
    end

    // -- lanes --------------------------------------------------------------------------
    wire [SW-1:0]    l_ov, l_redsq, l_last, l_fault, l_wrom_re;
    wire [SW*32-1:0] l_out;
    wire [SW*2-1:0]  l_red;
    wire [SW*AW-1:0] l_raddr, l_wrom_addr;
    wire [NW:0]      i_first = {1'b0, v} << LS;       // the vector's first element
    // ---- LT: the broadcast fields' group relay (stage 1 of RD): one kept copy per group of 8 lanes ----
    localparam integer GBW = NW + (NW + 1) + 5*AW + 6 + 8 + 9 + 64 + WR*16;
    localparam integer NG = (SW + 7) / 8;
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        if (LT != 0) begin : g_on
            (* keep *) reg [GBW-1:0] gb;
            (* keep *) reg [2:0]     gv;
            reg rg;                                   // the group's reset relay
            always @(posedge clk or negedge rst_n) if (!rst_n) rg <= 1'b0; else rg <= 1'b1;
            always @(posedge clk or negedge rg) if (!rg) gv <= 3'd0; else gv <= {emit, accept, v_last_r};
            always @(posedge clk) gb <= {v, fin_th, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                                         ma, mb, dst, red, ad, cls, i_sfu, imm1, imm2, wrom_q};
        end
    end endgenerate
    genvar l;
    generate for (l = 0; l < SW; l = l + 1) begin : g_lane
        wire live = ({1'b0, v} << LS) + l < {1'b0, nin_r};
        wire rst_l;                                   // this lane's reset (RTREE: its own register)
        if (RTREE != 0) begin : g_rl
            reg rl;
            always @(posedge ck_lane[l] or negedge rst_n) if (!rst_n) rl <= 1'b0; else rl <= 1'b1;
            assign rst_l = rl;
        end else begin : g_rw
            assign rst_l = rst_n;
        end
`ifdef OT_LOFF_MUT
        localparam integer LMUT = 1;   // bench mutant: the offset applied twice (must FAIL)
`else
        localparam integer LMUT = 0;
`endif
        wire [AW-1:0] lcura = (LOFF != 0) ? cura + l * asi : cura;
        wire [AW-1:0] lcurb = (LOFF != 0) ? curb + l * bsi : curb;
        wire [AW-1:0] lcurc = (LOFF != 0) ? curc + l * csi : curc;
        wire [AW-1:0] lcurd = (LOFF != 0) ? curd + l * dsi : curd;
        if (LT == 0) begin : g_flat
            ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE((LOFF != 0) ? LMUT * l : l), .KV_FP8(KV_FP8), .ML(ML)) u_lane (
                .clk(ck_lane[l]), .rst_n(rst_l), .emit0(emit), .live(live), .i(v), .fin_th(fin_th), .i_last_r(v_last_r),
                .cura0(lcura), .curb0(lcurb), .curc0(lcurc), .curd0(lcurd), .rrow(rrow),
                .asi(asi), .bsi(bsi), .csi(csi), .dsi(dsi),
                .asrc(asrc), .bsrc(bsrc), .csrc(csrc), .mc(mc), .md(md), .redsq(redsq),
                .ma(ma), .mb(mb), .dst(dst), .red(red), .ad(ad), .imm1(imm1), .imm2(imm2),
                .cls(cls), .accept(accept), .i_sfu(i_sfu),
                .va_re(va_re[l]), .va_addr(va_addr[l*AW +: AW]), .va_q(va_q[32*l +: 32]),
                .vb_re(vb_re[l]), .vb_addr(vb_addr[l*AW +: AW]), .vb_q(vb_q[32*l +: 32]),
                .vc_re(vc_re[l]), .vc_addr(vc_addr[l*AW +: AW]), .vc_q(vc_q[32*l +: 32]),
                .wrom_re(l_wrom_re[l]), .wrom_addr(l_wrom_addr[l*AW +: AW]), .wrom_q(wrom_q),
                .crom_re(crom_re[l]), .crom_addr(crom_addr[l*AW +: AW]), .crom_q(crom_q[64*l +: 64]),
                .vm_we(vm_we[l]), .vm_waddr(vm_waddr[l*AW +: AW]), .vm_wdata(vm_wdata[32*l +: 32]),
                .kv_we(kv_we[l]), .kv_waddr(kv_waddr[l*AW +: AW]), .kv_wdata(kv_wdata[32*l +: 32]),
                .l_ov(l_ov[l]), .l_out(l_out[32*l +: 32]), .l_red(l_red[2*l +: 2]), .l_redsq(l_redsq[l]),
                .l_raddr(l_raddr[l*AW +: AW]), .l_last(l_last[l]), .retire(l_retire[l]), .l_fault(l_fault[l]),
                //: SFH = 0: the special-function pipelines are inside the lane (the external-tile ports are unused)
                .sx_exp_v(), .sx_exp_x(), .sy_exp_y(32'd0), .sy_exp_vo(1'b0), .sy_exp_f(1'b0),
                .sx_rcp_v(), .sx_rcp_x(), .sy_rcp_y(32'd0), .sy_rcp_f(1'b0),
                .sx_rsq_v(), .sx_rsq_x(), .sy_rsq_y(32'd0), .sy_rsq_f(1'b0));
        end else begin : g_tile
            //: inbound -- broadcast fields from this lane's group relay (stage 1), then RD - 1 per-lane stages; per-lane
            //: fields (live, offsets, memory answers) RD per-lane stages; the tile adds its pin flop.
            localparam integer PDW = 4*AW + 3*32 + 64;
            //: OT_LOFF_MUT (bench mutant): the lane offset applied twice, as LANE = l does on the flat lanes (must FAIL)
            wire [AW-1:0] tcura = lcura + LMUT * l * asi, tcurb = lcurb + LMUT * l * bsi;
            wire [AW-1:0] tcurc = lcurc + LMUT * l * csi, tcurd = lcurd + LMUT * l * dsi;
            wire [GBW-1:0] b_d = g_grp[l / 8].g_on.gb;
            wire [2:0]     b_v = g_grp[l / 8].g_on.gv;
            wire [GBW-1:0] b_q;
            wire [2:0]     bv_q;
            wire           lv_q;
            wire [PDW-1:0] p_q;
            ot_hdc_delay #(.W(GBW), .D(RD - 1)) u_bd (.clk(ck_lane[l]), .rst_n(rst_l), .d(b_d), .q(b_q));
            ot_hdc_delay #(.W(3), .D(RD - 1), .RESET(1)) u_bv (.clk(ck_lane[l]), .rst_n(rst_l), .d(b_v), .q(bv_q));
            ot_hdc_delay #(.W(1), .D(RD), .RESET(1)) u_lv (.clk(ck_lane[l]), .rst_n(rst_l), .d(live), .q(lv_q));
            ot_hdc_delay #(.W(PDW), .D(RD)) u_pd (.clk(ck_lane[l]), .rst_n(rst_l),
                .d({tcura, tcurb, tcurc, tcurd, va_q[32*l +: 32], vb_q[32*l +: 32], vc_q[32*l +: 32], crom_q[64*l +: 64]}),
                .q(p_q));
            wire [NW-1:0] t_i; wire [NW:0] t_fin; wire [AW-1:0] t_rrow, t_asi, t_bsi, t_csi, t_dsi;
            wire t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq; wire [1:0] t_ma, t_mb, t_dst, t_red;
            wire [2:0] t_ad, t_cls, t_isfu; wire [31:0] t_imm1, t_imm2; wire [WR*16-1:0] t_wrom;
            assign {t_i, t_fin, t_rrow, t_asi, t_bsi, t_csi, t_dsi, t_asrc, t_bsrc, t_csrc, t_mc, t_md, t_redsq,
                    t_ma, t_mb, t_dst, t_red, t_ad, t_cls, t_isfu, t_imm1, t_imm2, t_wrom} = b_q;
            //: outbound -- the tile's out flops, then RD per-lane stages
            localparam integer OVW = 11;
            localparam integer ODW = 7*AW + 2*32 + 32 + 2 + 1 + AW;
            wire [OVW-1:0] o_v, o_vq;
            wire [ODW-1:0] o_d, o_dq;
            ot_hdc_vstream_lane_clock_entries_candidate #(.WR(WR), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML(ML), .RD(RD)) u_tile (
                .ck_head(ck_head[l]),.ck_exp(ck_exp[l]),.ck_rcp(ck_rcp[l]),.ck_rsq(ck_rsq[l]), .rst_n(rst_l), .emit0(bv_q[2]), .live(lv_q), .i(t_i), .fin_th(t_fin), .i_last_r(bv_q[0]),
                .cura0(p_q[PDW-1 -: AW]), .curb0(p_q[PDW-1-AW -: AW]), .curc0(p_q[PDW-1-2*AW -: AW]),
                .curd0(p_q[PDW-1-3*AW -: AW]), .rrow(t_rrow),
                .asi(t_asi), .bsi(t_bsi), .csi(t_csi), .dsi(t_dsi),
                .asrc(t_asrc), .bsrc(t_bsrc), .csrc(t_csrc), .mc(t_mc), .md(t_md), .redsq(t_redsq),
                .ma(t_ma), .mb(t_mb), .dst(t_dst), .red(t_red), .ad(t_ad), .imm1(t_imm1), .imm2(t_imm2),
                .cls(t_cls), .accept(bv_q[1]), .i_sfu(t_isfu),
                .va_re(o_v[10]), .va_addr(o_d[ODW-1 -: AW]), .va_q(p_q[64+64 +: 32]),
                .vb_re(o_v[9]), .vb_addr(o_d[ODW-1-AW -: AW]), .vb_q(p_q[64+32 +: 32]),
                .vc_re(o_v[8]), .vc_addr(o_d[ODW-1-2*AW -: AW]), .vc_q(p_q[64 +: 32]),
                .wrom_re(o_v[7]), .wrom_addr(o_d[ODW-1-3*AW -: AW]), .wrom_q(t_wrom),
                .crom_re(o_v[6]), .crom_addr(o_d[ODW-1-4*AW -: AW]), .crom_q(p_q[0 +: 64]),
                .vm_we(o_v[5]), .vm_waddr(o_d[ODW-1-5*AW -: AW]), .vm_wdata(o_d[ODW-1-6*AW -: 32]),
                .kv_we(o_v[4]), .kv_waddr(o_d[ODW-1-6*AW-32 -: AW]), .kv_wdata(o_d[ODW-1-7*AW-32 -: 32]),
                .l_ov(o_v[3]), .l_out(o_d[AW+3 +: 32]), .l_red(o_d[AW+1 +: 2]), .l_redsq(o_d[AW]),
                .l_raddr(o_d[0 +: AW]), .l_last(o_v[2]), .retire(o_v[1]), .l_fault(o_v[0]));
            ot_hdc_delay #(.W(OVW), .D(RD), .RESET(1)) u_ov (.clk(ck_lane[l]), .rst_n(rst_l), .d(o_v), .q(o_vq));
            ot_hdc_delay #(.W(ODW), .D(RD)) u_od (.clk(ck_lane[l]), .rst_n(rst_l), .d(o_d), .q(o_dq));
            assign {va_re[l], vb_re[l], vc_re[l], l_wrom_re[l], crom_re[l], vm_we[l], kv_we[l], l_ov[l], l_last[l],
                    l_retire[l], l_fault[l]} = o_vq;
            assign {va_addr[l*AW +: AW], vb_addr[l*AW +: AW], vc_addr[l*AW +: AW], l_wrom_addr[l*AW +: AW],
                    crom_addr[l*AW +: AW], vm_waddr[l*AW +: AW], vm_wdata[32*l +: 32], kv_waddr[l*AW +: AW],
                    kv_wdata[32*l +: 32], l_out[32*l +: 32], l_red[2*l +: 2], l_redsq[l], l_raddr[l*AW +: AW]} = o_dq;
        end
    end endgenerate
    //: the embedding row: SW consecutive BF16 elements in one weight-ROM word
    //: (the program aligns the row), read at lane 0's address
    assign wrom_re = l_wrom_re[0];
    assign wrom_addr = l_wrom_addr[0 +: AW];

    // -- reducer ------------------------------------------------------------------------
    reg              rd_v, rd_mx, rd_sq, rd_last;
    reg [AW-1:0]     rd_addr;
    reg [SW*32-1:0]  rd_x;
    integer li;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) rd_v <= 1'b0;
        else rd_v <= l_ov[0] && l_red[1:0] != 2'd0;
    end
    always @(posedge clk) begin
        rd_mx <= (l_red[1:0] == 2'd2); rd_sq <= l_redsq[0]; rd_last <= l_last[0]; rd_addr <= l_raddr[0 +: AW];
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= l_ov[li] ? l_out[32*li +: 32] : (l_red[1:0] == 2'd2) ? l_out[31:0] : 32'd0;
    end
    wire f_red;
    generate if (RED_ENTRIES == 0) begin : g_red_original
    ot_hdc_vreduce #(.SW(SW), .LV(LV), .AW(AW)) u_red (.clk(clk), .rst_n(rst_c), .v_in(rd_v), .mx_in(rd_mx),
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(reducer_busy), .fault(f_red));
    end else begin : g_red_entries
        if (SW != 64 || LV != 7 || AW != 24) begin : g_bad_shape
            OT_VRED_ENTRIES_REQUIRE_SW64_LV7_AW24 u_trap ();
        end
        wire tail_busy, tail_fault, guard_fault;
        // Functional composition ties the physical parent's nine scalar entries. No physical-parent qualification.
        qfd_su_vred_entries64 u_red (.ck_region0(ck_red[0]),.ck_region1(ck_red[1]),.ck_region2(ck_red[2]),.ck_region3(ck_red[3]),
            .ck_region4(ck_red[4]),.ck_region5(ck_red[5]),.ck_region6(ck_red[6]),.ck_region7(ck_red[7]),.ck_tail(ck_red[8]),.rst_n(rst_c),
            .v_in(rd_v),.mx_in(rd_mx),.sq_in(rd_sq),.last_in(rd_last),.addr_in(rd_addr),.x_in(rd_x),
            .o_we(red_we),.o_addr(red_addr),.o_data(red_data),.busy(tail_busy),.fault(tail_fault));
        ot_hdc_vred_pending_guard #(.CW(NW+1)) u_pending (.clk(clk),.rst_n(rst_c),
            .vector_v(rd_v),.vector_last(rd_last),.output_v(red_we),.tail_busy(tail_busy),
            .busy(reducer_busy),.fault(guard_fault));
        assign f_red=tail_fault||guard_fault;
    end endgenerate

    // Element chaining in vectors: retirement is in order, so the latest
    // instruction has written (vectors retired - vectors emitted before it).
    reg [15:0] n_emit, n_retire, first_mark;
    wire [15:0] done_n = n_retire - first_mark;
    //: rows: a row's last vector carries l_last; rows retire in order too
    reg [15:0] r_emit, r_retire, r_mark;
    wire [15:0] rdone_n = r_retire - r_mark;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin
            n_emit <= 0; n_retire <= 0; first_mark <= 0; progress <= 0;
            r_emit <= 0; r_retire <= 0; r_mark <= 0; progress_rows <= 0;
        end else begin
            n_emit <= n_emit + (emit ? 16'd1 : 16'd0);
            n_retire <= n_retire + (retire ? 16'd1 : 16'd0);
            r_emit <= r_emit + ((emit && v_last_r) ? 16'd1 : 16'd0);
            r_retire <= r_retire + ((retire && l_last[0]) ? 16'd1 : 16'd0);
            if (accept) begin
                first_mark <= n_emit; progress <= 0;
                r_mark <= r_emit; progress_rows <= 0;
            end else begin
                progress <= done_n[15] ? 16'd0 : done_n;
                progress_rows <= rdone_n[15] ? 16'd0 : rdone_n;
            end
        end
    end

    wire idle_c = !active && inflight == 0 && !(|vm_we) && !(|kv_we) && !rd_v && !reducer_busy;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) idle <= 1'b1;
        else idle <= idle_c && !(accept);
    end
    reg fault_q;
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin fault_q <= 1'b0; fault <= 1'b0; end
        else begin
            fault_q <= fault_q || (go && !ready) || (|l_fault) || f_red;
            fault <= fault_q;
        end
    end
    assign obs_active = active;
    assign obs_inflight = inflight;
endmodule