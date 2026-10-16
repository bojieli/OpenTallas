`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_coll_rgx_hbm (hgi-1010/c 2026-10-10): the die-side memory adapters of the hardware COLL.ROW_GATHER (RGXHW = 1) in
// hfd_coll, between ot_hgi_coll_ep's rg_* ports and die nets:
//   ROW SOURCE  rg_hq / rg_hr (2 sector read lanes, 8-bit tags)  -> one ot_hgi_hbm_rd_client a lane (one sector in flight)
//               die nets  t_hgi_rgxq{0,1} {addr 37, v} 38 b  /  f_hgi_rgxr{0,1} {data 256, v} 257 b  (the loader serves each
//               on its own ot_hfd_loader_kport lane through ot_hgi_hbm_rd_server)
//   LIST FETCH  rg_lq / rg_lr (512-bit list words, VM 512-bit word address)  -> a VM packet client (two sector reads a word,
//               in order, at most 2 words = 4 sectors in flight: the VM fast-path limit)
//               die nets  t_hgi_vmq {v, req 337} 338 b / f_hgi_vmr {v, rsp 273} 274 b  (VM client 'coll')
// Every die output leaves a flop (the clients' xq, vmq here); die inputs are flopped by the view wrapper.
// MUT_LF (bench): the list word's halves swapped: must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_coll_rgx_hbm #(
    parameter integer MUT_LF = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // ot_hgi_coll_ep row source
    input  wire [1:0]    rg_hq_v,
    output wire [1:0]    rg_hq_rdy,
    input  wire [69:0]   rg_hq_addr,      // 2 x sector address 35
    input  wire [15:0]   rg_hq_tag,
    output wire [1:0]    rg_hr_v,
    output wire [15:0]   rg_hr_tag,
    output wire [511:0]  rg_hr_data,
    // ot_hgi_coll_ep list fetch
    input  wire          rg_lq_v,
    output wire          rg_lq_rdy,
    input  wire [31:0]   rg_lq_addr,      // VM 512-bit word address
    output reg           rg_lr_v,
    output reg  [511:0]  rg_lr_data,
    // die
    output wire [75:0]   xq,              // {lane 1 {addr 37, v}, lane 0}
    input  wire [513:0]  xr,              // {lane 1 {data 256, v}, lane 0}
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    genvar l;
    for (l = 0; l < 2; l = l + 1) begin : g_ln
        wire [1:0] beat_unused;
        ot_hgi_hbm_rd_client #(.HAW(35), .TG(8)) u_c (.clk(clk), .rst_n(rst_n), .hq_v(rg_hq_v[l]), .hq_rdy(rg_hq_rdy[l]),
            .hq_addr(rg_hq_addr[l*35 +: 35]), .hq_len(3'd1), .hq_tag(rg_hq_tag[l*8 +: 8]), .hr_v(rg_hr_v[l]),
            .hr_tag(rg_hr_tag[l*8 +: 8]), .hr_beat(beat_unused), .hr_data(rg_hr_data[l*256 +: 256]),
            .xq(xq[l*38 +: 38]), .xr(xr[l*257 +: 257]));
    end
    // ---- list fetch: word w = sectors 2w (ids 0..7, bits 255:0) and 2w + 1 (ids 8..15)
    reg [1:0] wq_n;                 // words requested and not yet returned
    reg       hi_pend; reg [26:0] hi_sec;
    reg [1:0] rx_n;                 // halves of the head word received
    reg [255:0] lo_d;
    assign rg_lq_rdy = !hi_pend && wq_n < 2'd2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vmq <= 338'd0; wq_n <= 2'd0; hi_pend <= 1'b0; rx_n <= 2'd0; rg_lr_v <= 1'b0;
        end else begin : lf
            reg take, done;
            vmq[337] <= 1'b0; rg_lr_v <= 1'b0;
            take = rg_lq_v && rg_lq_rdy; done = 1'b0;
            if (take) begin
                vmq <= {1'b1, 1'b0, rg_lq_addr[25:0], 1'b0, 5'd0, 256'd0, 32'd0, 16'h5247};
                hi_pend <= 1'b1; hi_sec <= {rg_lq_addr[25:0], 1'b1};
            end else if (hi_pend) begin
                vmq <= {1'b1, 1'b0, hi_sec, 5'd0, 256'd0, 32'd0, 16'h5248};
                hi_pend <= 1'b0;
            end
            if (vmr[273]) begin
                if (rx_n == 2'd0) begin lo_d <= vmr[255:0]; rx_n <= 2'd1; end
                else begin
                    rg_lr_v <= 1'b1; rx_n <= 2'd0; done = 1'b1;
                    rg_lr_data <= (MUT_LF != 0) ? {lo_d, vmr[255:0]} : {vmr[255:0], lo_d};
                end
            end
            wq_n <= wq_n + {1'b0, take} - {1'b0, done};
        end
    end
endmodule
`default_nettype wire
