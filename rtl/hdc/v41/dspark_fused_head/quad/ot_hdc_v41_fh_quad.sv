`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_hdc_v41_fh_quad: one hardened QUADRANT of the margin-first fused head (redesign pass 2026-10-06). Four identical
// instances (gid strap 0..3) plus ot_hdc_v41_fh_head_top form ot_hdc_v41_fh_head_q, which is cycle-identical to
// ot_hdc_v41_fh_macro_ctx MARGIN=1 HARD_LANE=1 (CAPTURE, ALAT 7, RETURN_EXTRA 5, PROTECT_SPLIT 1). Nothing is added:
// the group's registers of fh_ctx / fh_add / sram_return_hardened are only regrouped into the quadrant:
//   in : the write mask / data ADDR_PIPE stage-1 registers (s_wmask, s_wdata), res_u, mask_q, o_mask1, o_addr1, the leaf-row / argmax-index / index-address group replicas, the group
//        copies of the return valid (u_rvg), fused select (u_selg) and index-write go (u_iwgg), the per-lane
//        request registers (ADDR_PIPE stage 2) - every input pin lands on one of these flops;
//   core: 16 hardened SRAM lane leaves (bank_id = {gid, lane}), the res_h delay line, 16 capture + FP32 add LAT 7
//        lanes, the fused/plain result select, the o_*1 / index-write port, the argmax leaves;
//   out: leaf, o_data, o_mask, o_addr, poison, group_fault - all flops.
// Index writes belong to group 0 (gid strap); o_addr takes the index address from its group replica iw_e_x, equal
// to the top's iaddr_r whenever an index write is selected (iaddr_r is held from go_fus acceptance to the write).
// ---------------------------------------------------------------------------------------------------------------
module ot_hdc_v41_fh_quad #(
    parameter integer W = 16, AW = 24, NW = 16, ALAT = 7, RETURN_EXTRA = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        gid,
    input  wire              rok,
    input  wire [8:0]        rrow,
    input  wire              wok,
    input  wire [8:0]        wrow,
    input  wire [W-1:0]      wr_mask_in,
    input  wire [W*32-1:0]   wr_data_in,
    input  wire [W*32-1:0]   res_in,
    input  wire [W-1:0]      o_mask1_in,
    input  wire [AW-1:0]     o_addr1_in,
    input  wire [W-1:0]      leaf_mask_in,
    input  wire [NW-1:0]     leaf_row_in,
    input  wire [NW-1:0]     am_idx_in,
    input  wire              rv_mid,
    input  wire              fsel_m,
    input  wire              iwg_m,
    input  wire [AW-1:0]     iw_e,
    output wire [(1+32+NW)*W-1:0] leaf,
    output reg  [W*32-1:0]   o_data,
    output reg  [W-1:0]      o_mask,
    output reg  [AW-1:0]     o_addr,
    output wire [W-1:0]      poison,
    output reg               group_fault
);
    localparam integer LW = $clog2(W);
    localparam integer CW = 1 + 32 + NW;
    // ---- input flops ---------------------------------------------------------------------------------------
    reg [W*32-1:0] res_u;
    reg [W-1:0] mask_q, o_mask1;
    reg [AW-1:0] o_addr1;
    always @(posedge clk) begin res_u <= res_in; mask_q <= leaf_mask_in; o_mask1 <= o_mask1_in; o_addr1 <= o_addr1_in; end
    wire [NW-1:0] row_qg, am_idx_x;
    wire [AW-1:0] iw_e_x;
    ot_hdc_v41_fh_kvec #(.N(NW)) u_rowq (.clk(clk), .d(leaf_row_in), .q(row_qg));
    ot_hdc_v41_fh_kvec #(.N(NW)) u_amg (.clk(clk), .d(am_idx_in), .q(am_idx_x));
    ot_hdc_v41_fh_kvec #(.N(AW)) u_iag (.clk(clk), .d(iw_e), .q(iw_e_x));
    wire protected_vg, fsel_g, iwg_g;
    ot_hdc_v41_fh_kreg u_rvg (.clk(clk), .rst_n(rst_n), .d(rv_mid), .q(protected_vg));
    ot_hdc_v41_fh_kreg u_selg (.clk(clk), .rst_n(rst_n), .d(fsel_m), .q(fsel_g));
    ot_hdc_v41_fh_kreg u_iwgg (.clk(clk), .rst_n(rst_n), .d(iwg_m), .q(iwg_g));
    // ---- SRAM lanes: ADDR_PIPE stage 2 (kept per-lane request register) + hardened lane leaf -----------------
    wire [W*32-1:0] ra_q;
    reg [W-1:0] s_wmask;
    reg [W*32-1:0] s_wdata;
    always @(posedge clk) begin s_wmask <= wr_mask_in; s_wdata <= wr_data_in; end
    genvar l;
    generate for (l = 0; l < W; l = l + 1) begin : g_bank
        wire r_ok, w_ok;
        wire [8:0] r_row, w_row;
        wire [31:0] w_d;
        ot_hdc_v41_fh_quad_lane_req u_req (.clk(clk), .rst_n(rst_n),
            .read_ok_d(rok), .read_row_d(rrow), .write_ok_d(wok && s_wmask[l]), .write_row_d(wrow), .wr_data_d(s_wdata[32*l+:32]),
            .read_ok(r_ok), .read_row(r_row), .write_ok(w_ok), .write_row(w_row), .wr_data(w_d));
        ot_hdc_v41_fh_sram_lane_hardened u_lane (
            .bank_id({gid, 4'(l)}),
            .clk(clk), .rst_n(rst_n), .read_ok(r_ok), .read_row(r_row),
            .write_ok(w_ok), .write_row(w_row), .wr_data(w_d),
            .rd_data(ra_q[32*l+:32]), .rd_valid(), .corrected(),
            .poisoned(poison[l]), .wr_committed());
    end endgenerate
    // ---- fused add lanes (ot_hdc_v41_fh_add CAPTURE + TREE, one group) --------------------------------------
    wire [W*32-1:0] res_h;
    ot_hdc_delay #(.W(W*32), .D(2 + RETURN_EXTRA)) u_rh (.clk(clk), .rst_n(rst_n), .d(res_u), .q(res_h));
    wire [W*32-1:0] fsum;
    wire [W-1:0] ffault, fused_lane_v, iwg;
    generate for (l = 0; l < W; l = l + 1) begin : g_fadd
        reg [31:0] addend_r, result_r;
        wire valid_in;
        always @(posedge clk) begin addend_r <= ra_q[32*l+:32]; result_r <= res_h[32*l+:32]; end
        ot_hdc_v41_fh_kreg u_v (.clk(clk), .rst_n(rst_n), .d(protected_vg), .q(valid_in));
        wire [1:0] err;
        wire vo;
        ot_hdc_fp32_add_lat #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(addend_r),
                                                 .b(result_r), .y(fsum[32*l +: 32]), .err(err), .valid_out(vo));
        assign ffault[l] = vo && (err != 2'd0);
        ot_hdc_v41_fh_kreg u_sel (.clk(clk), .rst_n(rst_n), .d(fsel_g), .q(fused_lane_v[l]));
        ot_hdc_v41_fh_kreg u_iwg (.clk(clk), .rst_n(rst_n), .d(iwg_g), .q(iwg[l]));
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) group_fault <= 1'b0; else group_fault <= |ffault;
    wire [W*32-1:0] res;
    generate for (l = 0; l < W; l = l + 1) begin : g_res
        assign res[32*l+:32] = fused_lane_v[l] ? fsum[32*l+:32] : res_u[32*l+:32];
    end endgenerate
    // ---- result port: o_*1 stage, the argmax-index write (group 0) ------------------------------------------
    reg [W*32-1:0] o_data1;
    always @(posedge clk) o_data1 <= res;
    wire idx_group = gid == 2'd0;
    wire [NW-1:0] index_local [0:W-1];
    wire [W-1:0] index_mask_local;
    generate for (l = 0; l < W; l = l + 1) begin : g_index_prepare
        ot_hdc_v41_fh_indexreg #(.NW(NW), .LW(LW), .LANE(l)) u_index (
            .clk(clk), .index_in(am_idx_x), .lane_in(iw_e_x[LW-1:0]),
            .index_q(index_local[l]), .mask_q(index_mask_local[l]));
    end endgenerate
    integer il;
    always @(posedge clk) begin
        for (il = 0; il < W; il = il + 1) begin
            o_data[32*il +: 32] <= iwg[il] ? ((idx_group && index_mask_local[il]) ? {{(32-NW){1'b0}}, index_local[il]} : 32'b0)
                                           : o_data1[32*il +: 32];
            o_mask[il] <= iwg[il] ? (idx_group && index_mask_local[il]) : o_mask1[il];
        end
        o_addr <= iwg[0] ? (idx_group ? (iw_e_x >> LW) : {AW{1'b0}}) : o_addr1;
    end
    // ---- argmax leaves ----------------------------------------------------------------------------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    generate for (l = 0; l < W; l = l + 1) begin : g_leaf
        reg [CW-1:0] c;
        always @(posedge clk) c <= {mask_q[l], okey(res[32*l +: 32]), row_qg};
        assign leaf[CW*l +: CW] = c;
    end endgenerate
endmodule

// Kept per-lane request register (ADDR_PIPE stage 2), the quadrant's own copy of ot_hdc_v41_fh_lane_req (same logic): the
// quadrant view is synthesised against the hardened lane LEAF (liberty), so it cannot read the lane RTL file.
(* keep_hierarchy *)
module ot_hdc_v41_fh_quad_lane_req(
    input wire clk,rst_n,read_ok_d,write_ok_d,
    input wire [8:0] read_row_d,write_row_d,
    input wire [31:0] wr_data_d,
    output reg read_ok,write_ok,
    output reg [8:0] read_row,write_row,
    output reg [31:0] wr_data
);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin read_ok<=0; write_ok<=0; end
        else begin read_ok<=read_ok_d; write_ok<=write_ok_d; end
    always @(posedge clk) begin read_row<=read_row_d; write_row<=write_row_d; wr_data<=wr_data_d; end
endmodule
