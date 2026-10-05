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
module ot_hdc_vstream #(
    parameter integer SW = 8,
    parameter integer LV = 4,         // the reducer's time levels: segments of up to 2^LV vectors
    parameter integer WR = 64,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer KV_FP8 = 1      // KV cache in FP8 E4M3 (else BF16): hdc_golden.KV_FMT
) (
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
    output reg               fault
);
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
    wire   accept = go && ready;
    wire   emit = active;
    wire [NW-1:0] nvec_in = (i_nin + (SW - 1)) >> LS;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
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
    genvar l;
    generate for (l = 0; l < SW; l = l + 1) begin : g_lane
        wire live = ({1'b0, v} << LS) + l < {1'b0, nin_r};
        ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(l), .KV_FP8(KV_FP8)) u_lane (
            .clk(clk), .rst_n(rst_n), .emit0(emit), .live(live), .i(v), .fin_th(fin_th), .i_last_r(v_last_r),
            .cura0(cura), .curb0(curb), .curc0(curc), .curd0(curd), .rrow(rrow),
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
            .l_raddr(l_raddr[l*AW +: AW]), .l_last(l_last[l]), .retire(l_retire[l]), .l_fault(l_fault[l]));
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd_v <= 1'b0;
        else rd_v <= l_ov[0] && l_red[1:0] != 2'd0;
    end
    always @(posedge clk) begin
        rd_mx <= (l_red[1:0] == 2'd2); rd_sq <= l_redsq[0]; rd_last <= l_last[0]; rd_addr <= l_raddr[0 +: AW];
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= l_ov[li] ? l_out[32*li +: 32] : (l_red[1:0] == 2'd2) ? l_out[31:0] : 32'd0;
    end
    wire f_red;
    ot_hdc_vreduce #(.SW(SW), .LV(LV), .AW(AW)) u_red (.clk(clk), .rst_n(rst_n), .v_in(rd_v), .mx_in(rd_mx),
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(reducer_busy), .fault(f_red));

    // Element chaining in vectors: retirement is in order, so the latest
    // instruction has written (vectors retired - vectors emitted before it).
    reg [15:0] n_emit, n_retire, first_mark;
    wire [15:0] done_n = n_retire - first_mark;
    //: rows: a row's last vector carries l_last; rows retire in order too
    reg [15:0] r_emit, r_retire, r_mark;
    wire [15:0] rdone_n = r_retire - r_mark;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(accept);
    end
    reg fault_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q <= 1'b0; fault <= 1'b0; end
        else begin
            fault_q <= (|l_fault) || f_red;
            fault <= fault_q;
        end
    end
endmodule
