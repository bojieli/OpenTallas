`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA engines (hgi-takeover 2026-10-10): the DMA unit's move port (ot_hgi_dma_record, one move outstanding)
// dispatched to
//   ot_hgi_dma_front  every HBM -> VM LOAD with element strides 1, 32 B aligned source rows of whole sectors, VM rows of
//                     whole sectors (base / stride multiples of 8 words), formats FP32 / U32 / BF16 / FP8E4M3 / INT8:
//                     the svc DMA stream (per-stack requests, 4 x 8 data lanes) -> the 32 VM wide write lanes;
//   ot_hgi_dma_mover  the rest (STORE, VM -> VM, strided, unaligned, KV ops) on its kport lane + VM client; its one
//                     VM wide lane goes out on its bank's lane (the engines never run together: one move outstanding).
// FRONT = 0 sends every move to the mover (the comparison point).  Fence: the mover's (the front is idle at a fence).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_engines #(
    parameter integer FRONT = 1,
    parameter integer SBIT = 35,
    parameter [35:0] STACK_BYTES = 36'd22500000000
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                mv_v,
    output wire                mv_rdy,
    input  wire [226:0]        mv,
    output wire                mv_done,
    output wire                mv_fault,
    input  wire                fence_v,
    output wire                fence_rdy,
    output wire                fence_done,
    // the mover's kport lane
    output wire                k_req_v,
    input  wire                k_req_rdy,
    output wire                k_req_we,
    output wire [36:0]         k_req_addr,
    output wire [255:0]        k_req_wdata,
    output wire [31:0]         k_req_wstrb,
    output wire [15:0]         k_req_tag,
    input  wire                k_rsp_v,
    output wire                k_rsp_rdy,
    input  wire                k_rsp_we,
    input  wire [255:0]        k_rsp_data,
    // the mover's VM packet client
    output wire [337:0]        vmq,
    input  wire [273:0]        vmr,
    // the svc DMA stream (hgi-takeover.log "SPEC for hbm-forks")
    output wire [4*51-1:0]     dq,
    input  wire [3:0]          dq_rdy,
    input  wire [32*270-1:0]   dd,
    output wire [31:0]         dd_cr,
    // the VM wide write port
    output wire [32*280-1:0]   wl,
    input  wire [31:0]         wl_done
);
    wire [2:0] sf = mv[4:2];
    wire elig = mv[1:0] == 2'd0 && mv[94:93] == 2'd1 && mv[92:77] == 16'd1 && mv[185:170] == 16'd1 &&
                (sf == 3'd0 || sf == 3'd1 || sf == 3'd2 || sf == 3'd4 || sf == 3'd5) &&
                mv[9:5] == 5'd0 && mv[49:45] == 5'd0 && mv[100:98] == 3'd0 && mv[140:138] == 3'd0 &&
                ((sf == 3'd0 || sf == 3'd5) ? mv[208:206] == 3'd0 : (sf == 3'd1) ? mv[209:206] == 4'd0 : mv[210:206] == 5'd0) &&
                mv[205:186] != 20'd0 && mv[226:206] != 21'd0;
    wire to_f = (FRONT != 0) && elig;
    wire f_rdy, f_done, f_fault, m_rdy, m_done, m_fault; wire [279:0] m_wl; wire [32*280-1:0] f_wl;
    assign mv_rdy = to_f ? f_rdy : m_rdy;
    assign mv_done = f_done | m_done;
    assign mv_fault = f_fault | m_fault;
    generate if (FRONT != 0) begin : g_front
        ot_hgi_dma_front #(.SBIT(SBIT), .STACK_BYTES(STACK_BYTES)) u_front (.clk(clk), .rst_n(rst_n), .mv_v(mv_v && to_f),
            .mv_rdy(f_rdy), .mv(mv), .mv_done(f_done), .mv_fault(f_fault), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
            .wl(f_wl), .wl_done(wl_done));
    end else begin : g_nofront
        assign f_rdy = 1'b0; assign f_done = 1'b0; assign f_fault = 1'b0; assign dq = '0; assign dd_cr = '0; assign f_wl = '0;
    end endgenerate
    // the mover's lane goes out on the lane of its sector's bank (the VM takes lane b into bank b); its done pulses come
    // one a cycle at most, so any lane's done is the mover's while the front is idle
    reg [32*280-1:0] m_wlx;
    always @* begin m_wlx = '0; if (m_wl[279]) m_wlx[m_wl[268:264]*280 +: 280] = m_wl; end
    // per lane: the front's lane when it is valid (its data bits are not cleared between writes), else the mover's
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_wl
        assign wl[gl*280 +: 280] = f_wl[gl*280 + 279] ? f_wl[gl*280 +: 280] : m_wlx[gl*280 +: 280];
    end endgenerate
    ot_hgi_dma_mover u_mover (.clk(clk), .rst_n(rst_n), .mv_v(mv_v && !to_f), .mv_rdy(m_rdy), .mv(mv), .mv_done(m_done),
        .mv_fault(m_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_req_addr), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data), .k_fault(1'b0), .vmq(vmq), .vmr(vmr), .wl(m_wl), .wl_done(|wl_done));
`ifndef SYNTHESIS
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    always @(posedge clk) if (trc && rst_n && mv_v && mv_rdy)
        $display("ENGINES move -> %s ssp %0d sf %0d src %h sst %0d sis %0d dsp %0d df %0d dst %h dstr %0d dis %0d m %0d n %0d",
                 to_f ? "front" : "mover", mv[1:0], mv[4:2], mv[44:5], mv[76:45], mv[92:77], mv[94:93], mv[97:95], mv[137:98],
                 mv[169:138], mv[185:170], mv[205:186], mv[226:206]);
`endif
endmodule
`default_nettype wire
