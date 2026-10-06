`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41_fh_ctx: HARDENING CONTEXT (not a production block) of the fused DSpark draft head of
// ot_hdc_v41_matvec (rtl/hdc/v41/dspark_fused_head), one position copy (G = 4 groups x W = 16 lanes: 64 FP32
// adds).  It holds every register-to-register path the fused head adds to the engine, each bounded by the
// engine's own registers, which start / end here as flops:
//   start  the early result tag a_tag_p and the result valid line (vline), the split tree's result word res_u
//          (its last level's output register), the issue / S1..S3 valid bits, the argmax index am_idx and the
//          as-built result-port stage o_*1 (address, mask, enable: computed from r_tag by as-built logic);
//   port   ra_q, the vector memory's addend read data (the I/O budget models the SRAM);
//   end    r_tag / r_v (the registered tag select whose fields feed the as-built lane-mask, address and
//          argmax-row logic exactly as the as-built a_tag did), the argmax leaf registers (key of the
//          selected result), the result-port registers o_* (with the argmax-index write), ra_re / ra_addr.
// ot_hdc_v41_fh_add is the production unit as is; every other line is copied from ot_hdc_v41_matvec.  The
// as-built engine's own paths (lane mask / address arithmetic from r_tag, the argmax compare tree) are not
// part of the fused head and are not in this context.
// ---------------------------------------------------------------------------
module ot_hdc_v41_fh_ctx #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer ALAT = 0,
    parameter integer CAPTURE = 0,
    parameter integer RETURN_EXTRA = 0,
    parameter integer RETIRE = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire retire_busy,retire_warm_ack,
    output reg warm_emit,
    input  wire              s3_v_in,          // the S3 valid that enters the engine's result valid line
    input  wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] a_tag_p_in,
    input  wire [G*W*32-1:0] res_in,
    input  wire [G*W*32-1:0] ra_q,
    output wire [G-1:0]      ra_re,
    output wire [G*AW-1:0]   ra_addr,
    input  wire              go_fus,           // a fused op with i_iwe accepted (sets iw_pend)
    input  wire [AW-1:0]     i_iaddr,
    input  wire [4:0]        busy_in,          // active, e_v, s1_v, s1b_v, s2_v (s3_v is s3_v_in)
    input  wire [G-1:0]      o_we1_in,
    input  wire [G*AW-1:0]   o_addr1_in,
    input  wire [G*W-1:0]    o_mask1_in,
    input  wire [G*W-1:0]    leaf_mask_in,
    input  wire [NW-1:0]     leaf_row_in,
    input  wire              tv_in,            // tv[0] input (r_v && r_last && r_amax, as-built)
    input  wire              ov1_in,
    input  wire [NW-1:0]     am_idx_in,
    output reg  [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] r_tag,
    output reg               r_v,
    output wire [(1+32+NW)*G*W-1:0] leaf,
    output reg  [G-1:0]      o_we,
    output reg  [G*AW-1:0]   o_addr,
    output reg  [G*W-1:0]    o_mask,
    output reg  [G*W*32-1:0] o_data,
    output reg               fault
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer OD = 6 * LG;
    localparam integer LV = $clog2(G * W);
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 2 + AW + AW + 3 * (NW + 1) + 2 + AW + 3 + AW + 1;
    localparam integer MPI = 0;
    localparam integer DF = 2 + RETURN_EXTRA + CAPTURE + ((ALAT == 0) ? 5 : ALAT);
    // -- engine registers the paths start at -------------------------------------------------------
    reg [TW-1:0]     a_tag_p;
    reg [G*W*32-1:0] res_u;
    reg [4:0]        busy_q;
    reg              s3_v;
    reg [G-1:0]      o_we1;
    reg [G*AW-1:0]   o_addr1;
    reg [G*W-1:0]    o_mask1, mask_q;
    reg [NW-1:0]     row_q, am_idx;
    reg [LV:0]       tv;
    reg              ov1, ov;
    always @(posedge clk) begin
        a_tag_p <= a_tag_p_in; res_u <= res_in; o_addr1 <= o_addr1_in; o_mask1 <= o_mask1_in;
        mask_q <= leaf_mask_in; row_q <= leaf_row_in; am_idx <= am_idx_in;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy_q <= 0; s3_v <= 0; o_we1 <= 0; tv <= 0; ov1 <= 0; ov <= 0; end
        else begin
            busy_q <= busy_in; s3_v <= s3_v_in; o_we1 <= o_we1_in; tv <= {tv[LV-1:0], tv_in}; ov1 <= ov1_in;
            ov <= ov1;
        end
    end
    wire [10+OD:0] vline;
    ot_hdc_vline #(.D(10 + OD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));

    // -- copied from ot_hdc_v41_matvec -------------------------------------------------------------
    reg  [TW-1:0] a_tag;
    always @(posedge clk) a_tag <= a_tag_p;
    wire          t_v = vline[10 + OD];
    wire          u_fus = a_tag[0];
    wire          t_v_p = vline[10 + OD - 1];
    wire          p_last, p_oen, p_amax, p_wsrc, p_mmode, p_fus;
    wire [1:0]    p_split, p_hg;
    wire [AW-1:0] p_ogs, p_oa, p_ots, p_ops;
    wire [2:0]    p_m;
    wire [NW:0]   p_nb, p_lb, p_nout;
    assign {p_last, p_oen, p_amax, p_wsrc, p_mmode, p_split, p_oa, p_ots, p_nb, p_lb, p_nout, p_hg, p_ogs, p_m,
            p_ops, p_fus} = a_tag_p;
    wire [LG:0]   p_tq = (G >> p_hg) - 1;
    wire [LG:0]   p_ports = G >> p_split;
    wire [TW-1:0] f_tag_p;
    ot_hdc_delay #(.W(TW), .D(DF - 1)) u_ftag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(f_tag_p));
    wire [DF:0] fline;
    ot_hdc_vline #(.D(DF)) u_fv (.clk(clk), .rst_n(rst_n), .v(t_v && u_fus), .vd(fline));
    wire          f_v = fline[DF];
    always @(posedge clk) r_tag <= fline[DF - 1] ? f_tag_p : a_tag_p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_v <= 1'b0;
        else r_v <= fline[DF - 1] || (t_v_p && !p_fus);
    end

    wire [G*W*32-1:0] fsum;
    wire [G*W-1:0]    ffault;
    ot_hdc_v41_fh_add #(.W(W), .G(G), .AW(AW), .MPI(MPI), .ALAT(ALAT),.CAPTURE(CAPTURE),.RETURN_EXTRA(RETURN_EXTRA)) u_fh (
        .clk(clk), .rst_n(rst_n), .t_v_p(t_v_p), .p_fus(p_fus), .p_last(p_last), .p_ports(p_ports), .p_m(p_m),
        .p_tq(p_tq), .p_hg(p_hg), .p_oa(p_oa), .p_ots(p_ots), .p_ogs(p_ogs), .p_ops(p_ops), .res_u(res_u),
        .ra_re(ra_re), .ra_addr(ra_addr), .ra_q(ra_q), .fsum(fsum), .ffault(ffault));
    wire [G*W-1:0] fused_lane_v;
    for (genvar fl=0; fl<G*W; fl=fl+1) begin : g_fused_select
        if (CAPTURE) begin : g_local
            ot_hdc_v41_fh_kreg u_sel (.clk(clk),.rst_n(rst_n),.d(fline[DF-1]),.q(fused_lane_v[fl]));
        end else assign fused_lane_v[fl]=f_v;
    end
    wire [G*W*32-1:0] res;
    for (genvar rl=0; rl<G*W; rl=rl+1) begin : g_result_local
        assign res[32*rl+:32]=fused_lane_v[rl]?fsum[32*rl+:32]:res_u[32*rl+:32];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= |ffault;
    end

    // result port: the as-built o_*1 stage (o_data1 takes the selected result), then the argmax-index write
    reg  [G*W*32-1:0] o_data1;
    always @(posedge clk) o_data1 <= res;
    reg iw_pend;
    reg iw_issued;
    reg iw_go;
    reg iw_go2;
    wire iw_write_go=CAPTURE?iw_go2:iw_go;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) iw_go2<=0; else iw_go2<=iw_go;
    reg [AW-1:0] iaddr_r;
    wire drained_nx = (!RETIRE || !retire_busy) && !(|busy_q) && !s3_v && !(|vline) && !(|tv[LV-1:0]) && !ov1 && !ov && !(|fline);
    wire iw_go_n = iw_pend && !iw_go && !(CAPTURE && iw_go2) && drained_nx && (!RETIRE || !iw_issued);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iw_pend <= 1'b0; iw_issued<=0; warm_emit<=0; iaddr_r <= 0; iw_go <= 1'b0; end
        else begin
            iw_go <= iw_go_n;warm_emit<=iw_write_go;
            if (go_fus && (!RETIRE || (!iw_pend&&!retire_busy))) begin
                iw_pend <= 1'b1;iw_issued<=0;iaddr_r <= i_iaddr;
            end else if(RETIRE&&iw_write_go) iw_issued<=1;
            else if(RETIRE?retire_warm_ack:iw_write_go) begin iw_pend<=0;iw_issued<=0;end
        end
    end
    wire [AW-1:0] iw_e = iaddr_r + MPI;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we <= 0;
        else if (iw_write_go) o_we <= {{(G-1){1'b0}}, 1'b1};
        else o_we <= o_we1;
    end
    localparam integer IWG_LANES=CAPTURE?1:4;
    localparam integer NIW=(G*W+IWG_LANES-1)/IWG_LANES;
    wire [NIW-1:0] iwg;
    genvar ic;
    generate for (ic = 0; ic < NIW; ic = ic + 1) begin : g_iwg
        ot_hdc_v41_fh_kreg u_iwg (.clk(clk), .rst_n(rst_n), .d(CAPTURE?iw_go:iw_go_n), .q(iwg[ic]));
    end endgenerate
    wire [G*W*32-1:0] iw_data_old = {{(G*W-1){32'd0}}, {{(32-NW){1'b0}}, am_idx}} << (32 * iw_e[LW-1:0]);
    wire [G*W-1:0]    iw_mask_old = {{(G*W-1){1'b0}}, 1'b1} << iw_e[LW-1:0];
    wire [NW-1:0] index_local [0:W-1];
    wire [W-1:0] index_mask_local;
    for (genvar ix=0; ix<W; ix=ix+1) begin : g_index_prepare
        ot_hdc_v41_fh_indexreg #(.NW(NW),.LW(LW),.LANE(ix)) u_index (
            .clk(clk), .index_in(am_idx), .lane_in(iw_e[LW-1:0]),
            .index_q(index_local[ix]), .mask_q(index_mask_local[ix]));
    end
    wire [G*W*32-1:0] iw_data;
    wire [G*W-1:0] iw_mask;
    for (genvar ix=0; ix<G*W; ix=ix+1) begin : g_index_word
        if (CAPTURE && ix<W) begin
            assign iw_data[32*ix+:32] = index_mask_local[ix] ? {{(32-NW){1'b0}}, index_local[ix]} : 32'b0;
            assign iw_mask[ix] = index_mask_local[ix];
        end else if (CAPTURE) begin
            assign iw_data[32*ix+:32] = 32'b0;
            assign iw_mask[ix] = 1'b0;
        end else begin
            assign iw_data[32*ix+:32] = iw_data_old[32*ix+:32];
            assign iw_mask[ix] = iw_mask_old[ix];
        end
    end
    integer il, ia;
    always @(posedge clk) begin
        for (il = 0; il < G * W; il = il + 1) begin
            o_data[32*il +: 32] <= iwg[il / IWG_LANES] ? iw_data[32*il +: 32] : o_data1[32*il +: 32];
            o_mask[il] <= iwg[il / IWG_LANES] ? iw_mask[il] : o_mask1[il];
        end
        for (ia = 0; ia < G; ia = ia + 1)
            o_addr[ia*AW +: AW] <= iwg[ia * W / IWG_LANES] ? ((ia == 0) ? (iw_e >> LW) : {AW{1'b0}}) : o_addr1[ia*AW +: AW];
    end

    // argmax leaves: the key of the selected result (mask and row are as-built, registered here)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer CW = 1 + 32 + NW;
    genvar e;
    generate for (e = 0; e < G * W; e = e + 1) begin : g_leaf
        reg [CW-1:0] c;
        always @(posedge clk) c <= {mask_q[e], okey(res[32*e +: 32]), row_q};
        assign leaf[CW*e +: CW] = c;
    end endgenerate
endmodule
