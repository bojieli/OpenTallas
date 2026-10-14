`timescale 1ns/1ps
`default_nettype none
// Concrete native interfaces. The parent contains wiring only. Legacy global
// descriptors keep their meaning through real bank routing/reorder leaves.
// Four BACK engines remain separate from the B2 engines. Physical assignment,
// exclusive native read-group allocation and successor views remain requested.
module ot_hgi_b2_dma_native #(parameter integer HARD_CLOCKS=0,MUT=0)(
    input  wire          clk,
    input wire [86:0] leaf_clk, // rq,mv,kc,h0,h1,serial; functional wrapper shares clk only when HARD_CLOCKS=0
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
    output wire [543:0] native_rq,
    input wire [31:0] native_rq_cr, input wire [8223:0] native_rr,
    output wire [8991:0] native_wq,
    input wire [31:0] native_wq_cr,native_wq_done,
    input wire [3:0] back_mv_v, output wire [3:0] back_mv_ready,
    input wire [907:0] back_mv,
    output wire [3:0] back_src,back_done,back_fault,back_quiet,
    output wire [543:0] back_native_rq,
    input wire [31:0] back_native_rq_cr,input wire [8223:0] back_native_rr,
    output wire [9247:0] back_wd,input wire [31:0] back_wd_cr,input wire [15:0] back_wa,
    output wire [72:0] adapter_fault
);
 wire [86:0] clocks=HARD_CLOCKS!=0?leaf_clk:{87{clk}};
 wire [512:0] vr2q;wire [8256:0] vr2r;wire [279:0] wl;wire [4:0] wl_bank;
 wire wl_done;wire [31:0] wl_native_ready,commit_done;
 ot_hgi_b2_dma_q #(.HARD_CLOCKS(1),.NATIVE_WL(1)) u_dma(
 .clk(clk),
 .rst_n(rst_n),
 .qid(qid),
 .dma_rec(dma_rec),
 .dma_ret(dma_ret),
 .k_req_v(k_req_v),
 .k_req_rdy(k_req_rdy),
 .k_req_we(k_req_we),
 .k_req_addr(k_req_addr),
 .k_req_wdata(k_req_wdata),
 .k_req_wstrb(k_req_wstrb),
 .k_req_tag(k_req_tag),
 .k_rsp_v(k_rsp_v),
 .k_rsp_rdy(k_rsp_rdy),
 .k_rsp_we(k_rsp_we),
 .k_rsp_data(k_rsp_data),
 .r_req_v(r_req_v),
 .r_req_rdy(r_req_rdy),
 .r_req_addr(r_req_addr),
 .r_req_len(r_req_len),
 .r_req_tag(r_req_tag),
 .r_req_we(r_req_we),
 .r_req_wdata(r_req_wdata),
 .r_req_wstrb(r_req_wstrb),
 .r_rsp_v(r_rsp_v),
 .r_rsp_we(r_rsp_we),
 .r_rsp_rdy(r_rsp_rdy),
 .r_rsp_tag(r_rsp_tag),
 .r_rsp_last(r_rsp_last),
 .r_rsp_data(r_rsp_data),
 .vmq(vmq),
 .vmr(vmr),
 .leaf_clk(clocks[5:0]),.vr2q(vr2q),.vr2r(vr2r),.wl(wl),.wl_bank(wl_bank),
 .wl_done(wl_done),.wl_native_ready(wl_native_ready));
 ot_hgi_dma_native_read_fabric #(.HARD_CLOCKS(1),.MUT(MUT)) u_read(
 .clk(clk),.rst_n(rst_n),.leaf_clk(clocks[45:6]),.legacy_q(vr2q),.legacy_r(vr2r),
 .native_rq(native_rq),.native_cr(native_rq_cr),.native_rr(native_rr),.fault(adapter_fault[39:0]));
 ot_hgi_dma_native_write_fabric #(.HARD_CLOCKS(1),.MUT(MUT)) u_write(
 .clk(clk),.rst_n(rst_n),.leaf_clk(clocks[77:46]),.compact(wl),.producer_ready(wl_native_ready),
 .native_wq(native_wq),.native_cr(native_wq_cr),.native_done(native_wq_done),
 .commit_done(commit_done),.fault(adapter_fault[71:40]));
 ot_hgi_dma_native_write_commit u_commit(.clk(clocks[78]),.rst_n(rst_n),.committed(commit_done),.done(wl_done),.fault(adapter_fault[72]));
 for(genvar s=0;s<4;s=s+1)begin:back
  wire [128:0] local_q;wire [2064:0] local_r;
  wire e_mv_v,e_mv_ready,e_src,e_done,e_fault,e_quiet;wire [226:0] e_mv;
  ot_hgi_dma_native_back_pin #(.SID(s)) u_pin(
   .clk(clocks[83+s]),.rst_n(rst_n),.mv_v(back_mv_v[s]),.mv(back_mv[s*227 +:227]),.mv_ready(back_mv_ready[s]),
   .engine_mv_v(e_mv_v),.engine_mv(e_mv),.engine_mv_ready(e_mv_ready),
   .engine_src(e_src),.engine_done(e_done),.engine_fault(e_fault),.engine_quiet(e_quiet),
   .src(back_src[s]),.done(back_done[s]),.fault(back_fault[s]),.quiet(back_quiet[s]),
   .local_q(local_q),.local_r(local_r),.native_rq(back_native_rq[s*136 +:136]),
   .native_cr(back_native_rq_cr[s*8 +:8]),.native_rr(back_native_rr[s*2056 +:2056]));
  ot_hgi_dma_back #(.NS(1),.NB(8),.STK(s),.VCR(8)) u_back(
   .clk(clocks[79+s]),.rst_n(rst_n),.mv_v(e_mv_v),.mv_rdy(e_mv_ready),
   .mv(e_mv),.mv_src(e_src),.mv_done(e_done),.mv_fault(e_fault),.quiet(e_quiet),
   .vr2q(local_q),.vr2r(local_r),.wd(back_wd[s*2312 +:2312]),
   .wd_cr(back_wd_cr[s*8 +:8]),.wa(back_wa[s*4 +:4]));
 end
endmodule
`default_nettype wire
