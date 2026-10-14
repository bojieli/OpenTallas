`timescale 1ns/1ps
`default_nettype none
// B2 partition: request/record+I-list, sector mover, serial mover, KV core, two16-lane hold leaves.
// Every parent connection is wiring; the VM receiver expands compact wl into its bank.
// Read-group32-lane format remains the current contract while the local8-lane die interface is unresolved.
// BACK1 belongs to its separate CLOSED NS1/NB8 engine beside each VM slice; integration is still owed.
// No physical qualification until child views, assigned pins, slot/hop gates and measured CTS have passed.
module ot_hgi_b2_dma_q #(
    parameter integer MUT_CORE_PIN = 0,
    parameter integer HARD_CLOCKS = 0, // physical parent: ten independent die-compensated clock entries
    parameter integer FRONT = 0,
    parameter integer VR2 = 1,
    parameter integer KVW = 1,
    parameter integer SBIT = 35,
    parameter [35:0] STACK_BYTES = 36'd22500000000,
    parameter integer MUT_SEAM = 0,
    parameter integer MUT_B2 = 0
) (
    input  wire          clk,
    input wire [9:0] leaf_clk, // rq,mv,kc,h0,h1,serial,dp,kface,vmface,groupface; functional wrapper shares clk only when HARD_CLOCKS=0
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
    output wire [279:0] wl,
    output wire [4:0] wl_bank,
    input wire wl_done
);
    wire [9:0] q5_clock = HARD_CLOCKS != 0 ? leaf_clk : {10{clk}};
    wire [264:0] land_write;wire [63:0] land_read;wire [6:0] source_format;wire [306:0] decoded;
    wire mover_v, mover_rdy, mover_done, mover_fault, mover_src, mover_fv, mover_frdy, mover_fdone, mover_wld;
    wire [226:0] mover_cmd; wire [337:0] mover_vmq; wire [273:0] mover_vmr; wire il_active; wire [337:0] il_vmq; wire [279:0] mover_wl;
    wire kc_v, kc_rdy, kc_idle, kc_creq, kc_src, kc_done, kc_gnt;
    wire [14:0] kc_vs, kc_vst; wire [31:0] kc_ds, kc_dst; wire [17:0] kc_ns; wire [19:0] kc_m;
    wire [191:0] kc_cr,credit_source; wire [511:0] kc_kq; wire [3:0] kc_wv, kc_wo, kc_wrdy, kc_rv, kc_rwe;
    wire [147:0] kc_wa; wire [1023:0] kc_wd;
    wire [31:0] hv; wire [1023:0] hd; wire [63:0] hs0, hs1; wire ha;
    wire [3:0] rv, rwe, rrr; wire [147:0] ra; wire [15:0] rl; wire [63:0] rt; wire [1023:0] rwd; wire [127:0] rws;
    wire ser_mv_v;
    wire [226:0] ser_mv;
    wire ser_mv_rdy;
    wire ser_mv_done;
    wire ser_mv_fault;
    wire ser_fence_rdy;
    wire ser_k_req_v;
    wire ser_k_req_rdy;
    wire ser_k_req_we;
    wire [36:0] ser_k_req_addr;
    wire [255:0] ser_k_req_wdata;
    wire [31:0] ser_k_req_wstrb;
    wire [15:0] ser_k_req_tag;
    wire ser_k_rsp_v;
    wire ser_k_rsp_rdy;
    wire ser_k_rsp_we;
    wire [255:0] ser_k_rsp_data;
    wire ser_k_fault;
    wire [337:0] ser_vmq;
    wire [273:0] ser_vmr;
    wire [36:0] ka;
    wire [31:0] kc_req_valid;
    for(genvar kr=0;kr<32;kr=kr+1)assign kc_req_valid[kr]=kc_kq[kr*16+15];
    wire [512:0] group_request;
    wire [342:0] mv_k_request; wire mv_k_ready; wire [257:0] mv_k_response;
    wire [337:0] fast_packet; wire packet_serial_owner; wire [273:0] packet_mover_return;
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_b2_dma_rq #(.SBIT(SBIT), .MUT_B2(MUT_B2), .MUT_SEAM(MUT_SEAM))
`else
    ot_hgi_b2_dma_rq
`endif
    u_rq(
      .clk(q5_clock[0]), .rst_n(rst_n), .qid(qid), .dma_rec(dma_rec), .dma_ret(dma_ret),
      .mover_v(mover_v), .mover_cmd(mover_cmd), .pin_m_rdy(mover_rdy), .pin_m_done(mover_done), .pin_m_fault(mover_fault), .pin_m_src(mover_src),
      .mover_fv(mover_fv), .pin_m_fence_rdy(mover_frdy), .pin_m_fence_done(mover_fdone),
      .il_vmq(il_vmq), .il_active(il_active), .vmr(mover_vmr));
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_b2_dma_mv #(.VR2(VR2), .KVW(KVW), .SVR2(0), .MUT_SEAM(MUT_SEAM), .PX(2), .B2(1), .QID(0), .MUT_B2(MUT_B2))
`else
    ot_hgi_b2_dma_mv
`endif
    u_mv(
      .land_write(land_write),.land_read(land_read),.source_format(source_format),.decoded(decoded),
      .ser_mv_v(ser_mv_v),
      .ser_mv(ser_mv),
      .ser_mv_rdy(ser_mv_rdy),
      .ser_mv_done(ser_mv_done),
      .ser_mv_fault(ser_mv_fault),
      .ser_fence_rdy(ser_fence_rdy),
      .ser_k_req_v(ser_k_req_v),
      .ser_k_req_rdy(ser_k_req_rdy),
      .ser_k_req_we(ser_k_req_we),
      .ser_k_req_addr(ser_k_req_addr),
      .ser_k_req_wdata(ser_k_req_wdata),
      .ser_k_req_wstrb(ser_k_req_wstrb),
      .ser_k_req_tag(ser_k_req_tag),
      .ser_k_rsp_v(ser_k_rsp_v),
      .ser_k_rsp_rdy(ser_k_rsp_rdy),
      .ser_k_rsp_we(ser_k_rsp_we),
      .ser_k_rsp_data(ser_k_rsp_data),
      .ser_k_fault(ser_k_fault),
      .ser_vmr(ser_vmr),
      .clk(q5_clock[1]), .rst_n(rst_n), .qid(qid), .vm_serial_owner(packet_serial_owner), .mv_v(mover_v), .mv(mover_cmd), .mv_rdy(mover_rdy), .mv_done(mover_done), .mv_fault(mover_fault), .mv_src(mover_src),
      .fence_v(mover_fv), .fence_rdy(mover_frdy), .fence_done(mover_fdone),
      .k_req_v(mv_k_request[342]), .k_req_rdy(mv_k_ready), .k_req_we(mv_k_request[341]), .k_req_addr(mv_k_request[340:304]), .k_req_wdata(mv_k_request[303:48]),
      .k_req_wstrb(mv_k_request[47:16]), .k_req_tag(mv_k_request[15:0]), .k_rsp_v(mv_k_response[257]), .k_rsp_rdy(), .k_rsp_we(mv_k_response[256]), .k_rsp_data(mv_k_response[255:0]), .k_fault(1'b0),
      .r_req_v(rv), .r_req_rdy({3'd0,r_req_rdy}), .r_req_addr(ra), .r_req_len(rl), .r_req_tag(rt), .r_req_we(rwe), .r_req_wdata(rwd), .r_req_wstrb(rws),
      .r_rsp_v({3'd0,r_rsp_v}), .r_rsp_we({3'd0,r_rsp_we}), .r_rsp_rdy(rrr), .r_rsp_tag({48'd0,r_rsp_tag}), .r_rsp_last({3'd0,r_rsp_last}), .r_rsp_data({768'd0,r_rsp_data}),
      .vr2q(group_request), .vr2r_ctrl(vr2r[8256:8224]), .vmq(fast_packet), .vmr(packet_mover_return), .wl(wl), .wl_done(wl_done),
      .kv_c_rdy(kc_rdy), .kv_idle_w(kc_idle), .kv_creq(kc_creq), .kv_src(kc_src), .kv_done(kc_done), .kv_req_v(kc_req_valid),
      .kv_wv(kc_wv), .kv_wo(kc_wo), .kv_wa(kc_wa), .kv_wd(kc_wd), .kc_v(kc_v), .kc_vs(kc_vs), .kc_vst(kc_vst), .kc_ds(kc_ds),
      .kc_dst(kc_dst), .kc_ns(kc_ns), .kc_m(kc_m), .kc_gnt(kc_gnt), .credit_source(credit_source), .kc_wrdy(kc_wrdy));
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_dma_kvw_core_reg_kq #(.OWN_B0(1),.MUT_KQ_ZERO(MUT_CORE_PIN))
`else
    ot_hgi_dma_kvw_core_reg_kq
`endif
    u_kc(.clk(q5_clock[2]), .rn(rst_n), .c_v(kc_v), .c_rdy(kc_rdy), .c_vs(kc_vs), .c_vst(kc_vst),
      .c_ds(kc_ds), .c_dst(kc_dst), .c_ns(kc_ns), .c_m(kc_m), .g_gnt(kc_gnt), .g_cr(kc_cr), .kq(kc_kq), .kq_creq(kc_creq),
      .h_v(hv), .h_d(hd), .h_sel0(hs0), .h_sel1(hs1), .h_act(ha), .b0_we(), .b0_wa(), .b0_wd(), .b0_re(), .b0_ra(), .b0_rd(256'd0),
      .kw_v(kc_wv), .kw_rdy(kc_wrdy), .kw_addr(kc_wa), .kw_wdata(kc_wd), .r_rsp_v({3'd0,r_rsp_v}), .r_rsp_we({3'd0,r_rsp_we}), .kw_wo(kc_wo), .src(kc_src), .done(kc_done), .idle(kc_idle));
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_dma_kvw_hold #(.NL(16))
`else
    ot_hgi_dma_kvw_hold
`endif
    u_h0(.clk(q5_clock[3]), .rst_n(rst_n), .rsp(vr2r[4111:0]), .act(ha), .sel0(hs0[31:0]), .sel1(hs1[31:0]), .hv(hv[15:0]), .d0(hd[255:0]), .d1(hd[511:256]));
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_dma_kvw_hold #(.NL(16))
`else
    ot_hgi_dma_kvw_hold
`endif
    u_h1(.clk(q5_clock[4]), .rst_n(rst_n), .rsp(vr2r[8223:4112]), .act(ha), .sel0(hs0[63:32]), .sel1(hs1[63:32]), .hv(hv[31:16]), .d0(hd[767:512]), .d1(hd[1023:768]));
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_b2_dma_serial #(.MUT_RNE(0),.MUT_SEAM(MUT_SEAM))
`else
    ot_hgi_b2_dma_serial
`endif
    u_ser(.clk(q5_clock[5]),.rst_n(rst_n),
      .mv_v(ser_mv_v),
      .mv(ser_mv),
      .mv_rdy(ser_mv_rdy),
      .mv_done(ser_mv_done),
      .mv_fault(ser_mv_fault),
      .fence_rdy(ser_fence_rdy),
      .k_req_v(ser_k_req_v),
      .k_req_rdy(ser_k_req_rdy),
      .k_req_we(ser_k_req_we),
      .k_req_addr(ser_k_req_addr),
      .k_req_wdata(ser_k_req_wdata),
      .k_req_wstrb(ser_k_req_wstrb),
      .k_req_tag(ser_k_req_tag),
      .k_rsp_v(ser_k_rsp_v),
      .k_rsp_rdy(ser_k_rsp_rdy),
      .k_rsp_we(ser_k_rsp_we),
      .k_rsp_data(ser_k_rsp_data),
      .k_fault(ser_k_fault),
      .vmq(ser_vmq),
      .vmr(ser_vmr));
    ot_hgi_b2_dma_land_dp u_dp(.clk(q5_clock[6]),.rst_n(rst_n),
      .land_write(land_write),.land_read(land_read),.source_format(source_format),.decoded(decoded));
    ot_hgi_b2_dma_kface u_kface(.clk(q5_clock[7]),.rst_n(rst_n),.credit_source(credit_source),.kc_cr(kc_cr),
      .request(mv_k_request),.request_ready(mv_k_ready),
      .k_req_v(k_req_v),.k_req_rdy(k_req_rdy),.k_req_we(k_req_we),.k_req_addr(k_req_addr),
      .k_req_wdata(k_req_wdata),.k_req_wstrb(k_req_wstrb),.k_req_tag(k_req_tag),
      .k_rsp_v(k_rsp_v),.k_rsp_we(k_rsp_we),.k_rsp_data(k_rsp_data),.response(mv_k_response));
    assign k_rsp_rdy=1'b1;
`ifndef OT_B2_DMA_Q5_HARD
    ot_hgi_b2_dma_vmface #(.MUT_SEAM(MUT_SEAM))
`else
    ot_hgi_b2_dma_vmface
`endif
    u_vmface(.clk(q5_clock[8]),.rst_n(rst_n),.serial_owner(packet_serial_owner),.il_owner(il_active),
      .fast_request(fast_packet),.serial_request(ser_vmq),.il_request(il_vmq),.vmq(vmq),.vmr(vmr),
      .mover_response(packet_mover_return),.il_response(mover_vmr));
    assign r_req_addr = ra[36:0];
    assign wl_bank = wl[268:264];
    assign r_req_v=rv[0]; assign r_req_len=rl[3:0]; assign r_req_tag=rt[15:0]; assign r_req_we=rwe[0];
    assign r_req_wdata=rwd[255:0]; assign r_req_wstrb=rws[31:0]; assign r_rsp_rdy=rrr[0];
    ot_hgi_b2_dma_groupface #(.MUT_SEAM(MUT_SEAM)) u_groupface(.clk(q5_clock[9]),.rst_n(rst_n),.request(group_request),.kv_request(kc_kq),.vr2q(vr2q));
endmodule
`default_nettype wire
