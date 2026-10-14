`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// el1011-hbm-b2 (2026-10-12): the DMA unit of B2 cluster QID (QID = the qid STRAP pin: one hardened unit for all four clusters, core = cluster 0 behind ot_hgi_b2_qrot) (HBM die B2: four clusters, one per HBM stack, each with a
// LOCAL VM slice).  = ot_hgi_dma_record (B2: fail-closed on a record of another stack) + ot_hgi_dma_engines (B2: the mover /
// front / back serve only stack QID; STRIPE4 and indexed-stream rows of other stacks are skipped -- the B2 dispatcher sends
// those two forms to all four clusters, every other record to onehot(stack of its HBM-side descriptor)).
// Ports: the cluster station's legacy DMA record bus (704 b) + return {wr_quiet, fault, done, ready}; ONE HBM read/write
// burst lane (stack QID's kport lane) + the mover's single-sector kport lane (stack QID addresses only); the local VM
// slice's packet client (vmq / vmr), DMA wide-read group (vr2q / vr2r) and wide write port (wl / wl_done), today's formats
// (the b2-vm stream's slice-port spec replaces them when it lands).  Die configuration: FRONT 0 (the svc DMA stream is not
// adopted; every move on the mover), VR2 1, KVW 1, BACK 0.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_dma_q_flat #(
    parameter integer FRONT = 0,
    parameter integer VR2 = 1,
    parameter integer KVW = 1,
    parameter integer SBIT = 35,
    parameter [35:0] STACK_BYTES = 36'd22500000000,
    parameter integer MUT_B2 = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    qid,            // strap: this cluster's HBM stack (0..3); ONE hardened unit for all four
    input  wire [703:0]  dma_rec,        // {pos1, n_O, n_A, O, A, header, valid}; A[255:239,7] = the I-list address
    output wire [3:0]    dma_ret,        // {wr_quiet, fault, done, ready}
    // the mover's single-sector kport lane (stack QID)
    output wire          k_req_v,
    input  wire          k_req_rdy,
    output wire          k_req_we,
    output wire [36:0]   k_req_addr,
    output wire [255:0]  k_req_wdata,
    output wire [31:0]   k_req_wstrb,
    output wire [15:0]   k_req_tag,
    input  wire          k_rsp_v,
    output wire          k_rsp_rdy,
    input  wire          k_rsp_we,
    input  wire [255:0]  k_rsp_data,
    // stack QID's burst lane
    output wire          r_req_v,
    input  wire          r_req_rdy,
    output wire [36:0]   r_req_addr,
    output wire [3:0]    r_req_len,
    output wire [15:0]   r_req_tag,
    output wire          r_req_we,
    output wire [255:0]  r_req_wdata,
    output wire [31:0]   r_req_wstrb,
    input  wire          r_rsp_v,
    input  wire          r_rsp_we,
    output wire          r_rsp_rdy,
    input  wire [15:0]   r_rsp_tag,
    input  wire          r_rsp_last,
    input  wire [255:0]  r_rsp_data,
    // the local VM slice
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    output wire [512:0]  vr2q,
    input  wire [8256:0] vr2r,
    output wire [32*280-1:0] wl,
    input  wire [31:0]   wl_done
);
    wire d_mv_src, d_mv_pdone, d_mv_fdone, d_wq, d_is_v, d_is_rdy; wire [207:0] d_is_cmd;
    wire d_mv_v, d_mv_rdy, d_mv_done, d_mv_fault, d_fv, d_frdy, d_fdone, d_rdy, d_done, d_fault;
    wire [226:0] d_mv;
    // the core is cluster 0: HBM descriptors rotated by -qid on the way in, request addresses +qid on the way out
    wire [255:0] ra_r, ro_r;
    ot_hgi_b2_qrot_d #(.SBIT(SBIT)) u_rqa (.qid(qid), .d(dma_rec[384:129]), .r(ra_r));
    ot_hgi_b2_qrot_d #(.SBIT(SBIT)) u_rqo (.qid(qid), .d(dma_rec[640:385]), .r(ro_r));
    ot_hgi_dma_record #(.LEGACY(0), .B2(1), .QID(0), .SBIT(SBIT)) u_dma (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1),
        .rec_v(dma_rec[0]), .rec_rdy(d_rdy), .rec_hdr(dma_rec[128:1]), .rec_a(ra_r), .rec_o(ro_r),
        .rec_n_a(dma_rec[661:641]), .rec_n_o(dma_rec[682:662]), .rec_pos1(dma_rec[703:683]),
        .rec_ilist({14'd0, dma_rec[129 + 255 -: 17], dma_rec[129 + 7]}), .rec_done(d_done), .rec_fault(d_fault), .halted(),
        .wr_quiet(d_wq), .lg_mv_v(1'b0), .lg_mv_rdy(), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(),
        .mv_v(d_mv_v), .mv_rdy(d_mv_rdy), .mv(d_mv), .mv_done(d_mv_done), .mv_fault(d_mv_fault),
        .mv_src(d_mv_src), .mv_pdone(d_mv_pdone), .mv_fdone(d_mv_fdone),
        .is_v(d_is_v), .is_rdy(d_is_rdy), .is_cmd(d_is_cmd), .fence_v(d_fv), .fence_rdy(d_frdy), .fence_done(d_fdone));
    // the engines' four-lane vectors: only core lane 0 (= stack qid) is live (the others are constant 0 inside at B2 = 1)
    wire [3:0] rv, rwe, rrr; wire [4*37-1:0] ra; wire [15:0] rl; wire [63:0] rt; wire [1023:0] rwd; wire [127:0] rws;
    wire [3:0] rsv = {3'd0, r_rsp_v}, rswe = {3'd0, r_rsp_we}, rsl = {3'd0, r_rsp_last}, rqr = {3'd0, r_req_rdy};
    wire [63:0] rst_t = {48'd0, r_rsp_tag}; wire [1023:0] rsd = {768'd0, r_rsp_data};
    wire [36:0] k_a0;
    ot_hgi_b2_qrot_a #(.SBIT(SBIT)) u_rqr (.qid(qid), .a(ra[36:0]), .r(r_req_addr));
    ot_hgi_b2_qrot_a #(.SBIT(SBIT)) u_rqk (.qid(qid), .a(k_a0), .r(k_req_addr));
    assign r_req_v = rv[0]; assign r_req_len = rl[3:0];
    assign r_req_tag = rt[15:0]; assign r_req_we = rwe[0]; assign r_req_wdata = rwd[255:0];
    assign r_req_wstrb = rws[31:0]; assign r_rsp_rdy = rrr[0];
    ot_hgi_dma_engines #(.FRONT(FRONT), .VR2(VR2), .KVW(KVW), .SBIT(SBIT), .STACK_BYTES(STACK_BYTES), .B2(1), .QID(0),
                         .MUT_B2(MUT_B2)) u_eng (.clk(clk), .rst_n(rst_n), .mv_v(d_mv_v), .mv_rdy(d_mv_rdy),
        .mv(d_mv), .mv_done(d_mv_done), .mv_fault(d_mv_fault), .mv_src(d_mv_src), .mv_pdone(d_mv_pdone), .mv_fdone(d_mv_fdone),
        .is_v(d_is_v), .is_rdy(d_is_rdy), .is_cmd(d_is_cmd), .fence_v(d_fv), .fence_rdy(d_frdy), .fence_done(d_fdone),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_a0), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data),
        .r_req_v(rv), .r_req_rdy(rqr), .r_req_addr(ra), .r_req_len(rl), .r_req_tag(rt), .r_req_we(rwe), .r_req_wdata(rwd),
        .r_req_wstrb(rws), .r_rsp_v(rsv), .r_rsp_we(rswe), .r_rsp_rdy(rrr), .r_rsp_tag(rst_t), .r_rsp_last(rsl), .r_rsp_data(rsd),
        .vr2q(vr2q), .vr2r(vr2r), .vmq(vmq), .vmr(vmr), .dq(), .dq_rdy(4'd0), .dd({32*270{1'b0}}), .dd_cr(),
        .wl(wl), .wl_done(wl_done), .wd(), .wd_cr(32'd0), .wa(16'd0));
    assign dma_ret = {d_wq, d_fault, d_done, d_rdy};
endmodule
`default_nettype wire
