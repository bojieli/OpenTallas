`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hgi-1010/d (2026-10-10): an HBM read lane for a record unit that is not beside the loader (the HC unit's weight
// window fetch), carried over two die nets to one ot_hfd_loader_kport lane in the loader block:
//   xq  {addr 37 (kport byte address = sector << 5), v}       unit block -> loader     38 b
//   xr  {data 256, v}                                         loader -> unit block     257 b
// ONE sector in flight (the kport lane holds one transaction): the client splits a request of len sectors into len
// single-sector reads and returns {tag, beat, data} per sector in order.  Every die pin is registered on both sides, so
// a request and a response are one-edge pulses; with one sector in flight no back-pressure crosses the die (the
// server's one-entry buffer always has room).  Exact: the bytes are the kport lane's (the same path as the loader's
// own reads); rate: one sector per kport round trip (the boot-path rate, priced by hgi_loader_kport_model).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hbm_rd_client #(
    parameter integer HAW = 35,
    parameter integer TG = 7
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           hq_v,
    output wire           hq_rdy,
    input  wire [HAW-1:0] hq_addr,              // sector address
    input  wire [2:0]     hq_len,               // sectors (1..7)
    input  wire [TG-1:0]  hq_tag,
    output reg            hr_v,
    output reg  [TG-1:0]  hr_tag,
    output reg  [1:0]     hr_beat,
    output reg  [255:0]   hr_data,
    output reg  [37:0]    xq,
    input  wire [256:0]   xr
);
    reg busy, wait_r; reg [HAW-1:0] a; reg [2:0] n, b; reg [TG-1:0] tg;
    assign hq_rdy = !busy;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; wait_r <= 1'b0; xq <= 38'd0; hr_v <= 1'b0; end
        else begin
            xq[0] <= 1'b0; hr_v <= 1'b0;
            if (!busy) begin
                if (hq_v) begin
                    busy <= 1'b1; a <= hq_addr; n <= (hq_len == 3'd0) ? 3'd1 : hq_len; b <= 3'd0; tg <= hq_tag;
                    xq <= {hq_addr[31:0], 5'd0, 1'b1}; wait_r <= 1'b1;
                end
            end else if (wait_r && xr[0]) begin
                hr_v <= 1'b1; hr_tag <= tg; hr_beat <= b[1:0]; hr_data <= xr[256:1];
                if (b + 3'd1 == n) begin busy <= 1'b0; wait_r <= 1'b0; end
                else begin b <= b + 3'd1; xq <= {a[31:0] + {29'd0, b + 3'd1}, 5'd0, 1'b1}; end
            end
        end
    end
endmodule

module ot_hgi_hbm_rd_server (
    input  wire           clk,
    input  wire           rst_n,
    input  wire [37:0]    xq,
    output reg  [256:0]   xr,
    // one ot_hfd_loader_kport lane
    output reg            req_v,
    input  wire           req_rdy,
    output reg  [36:0]    req_addr,
    input  wire           rsp_v,
    input  wire [255:0]   rsp_data,
    output reg            fault                 // a request while one is held (the client never does: fail closed)
);
    reg held;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin req_v <= 1'b0; held <= 1'b0; xr <= 257'd0; fault <= 1'b0; end
        else begin
            xr[0] <= 1'b0;
            if (req_v && req_rdy) req_v <= 1'b0;
            if (xq[0]) begin
                if (held) fault <= 1'b1;
                req_v <= 1'b1; req_addr <= xq[37:1]; held <= 1'b1;
            end
            if (rsp_v && held) begin xr <= {rsp_data, 1'b1}; held <= 1'b0; end
        end
    end
endmodule

// the HC unit as it sits in the HGI unit slot: ot_hgi_hc_unit + its HBM read lane client
module ot_hgi_hc_die #(
    parameter integer W = 32,
    parameter integer RMAX = 128,
    parameter [31:0]  HC_EPS = 32'h358637BD,
    parameter integer WMACRO = 1,
    parameter integer XMACRO = 1,
    parameter integer PMAX = 8,
    parameter integer MUT_MP = 0,
    parameter integer WVM = 1,             // x staging over the W-group wide VM read lanes (client 2)
    parameter integer WLQ = 24,
    parameter integer WD = 8,
    parameter integer MUT_WV = 0,
    parameter integer SPL = 4,             // striped weight fetch: sub-windows a bank (HL = 8 SPL HBM read lanes, window i
                                           //   on lane i), each lane its own client -> its own svc / loader lane
    parameter integer HL = 8 * SPL
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_o,
    input  wire [20:0]   rec_n_a, rec_n_o,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    output wire [HL*38-1:0]  xq,
    input  wire [HL*257-1:0] xr,
    // the W-group wide VM read lanes (ot_hgi_vm_lanearb client): burst ownership + 32 lanes
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr
);
    localparam integer TG = 4 + $clog2(RMAX) + ((W > 32) ? $clog2(W / 32) : 0);   // = the unit's tag width
    wire [HL-1:0] hq_v, hq_rdy, hr_v; wire [HL*35-1:0] hq_addr; wire [HL*3-1:0] hq_len; wire [HL*TG-1:0] hq_tag, hr_tag;
    wire [HL*2-1:0] hr_beat; wire [HL*256-1:0] hr_data;
    ot_hgi_hc_unit #(.W(W), .RMAX(RMAX), .WMACRO(WMACRO), .XMACRO(XMACRO), .PMAX(PMAX), .MUT_MP(MUT_MP), .WVM(WVM), .WLQ(WLQ), .WD(WD), .MUT_WV(MUT_WV), .HL(HL), .SPL(SPL)) u_hc (.clk(clk), .rst_n(rst_n), .cfg_norm_eps(HC_EPS), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_a(rec_a), .rec_b(rec_b), .rec_o(rec_o), .rec_n_a(rec_n_a),
        .rec_n_o(rec_n_o), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag), .hr_v(hr_v), .hr_tag(hr_tag),
        .hr_beat(hr_beat), .hr_data(hr_data), .rg_req(rg_req), .rg_gnt(rg_gnt), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr));
    for (genvar l = 0; l < HL; l = l + 1) begin : g_cl
        ot_hgi_hbm_rd_client #(.HAW(35), .TG(TG)) u_cl (.clk(clk), .rst_n(rst_n), .hq_v(hq_v[l]), .hq_rdy(hq_rdy[l]),
            .hq_addr(hq_addr[l*35 +: 35]), .hq_len(hq_len[l*3 +: 3]), .hq_tag(hq_tag[l*TG +: TG]), .hr_v(hr_v[l]),
            .hr_tag(hr_tag[l*TG +: TG]), .hr_beat(hr_beat[l*2 +: 2]), .hr_data(hr_data[l*256 +: 256]),
            .xq(xq[l*38 +: 38]), .xr(xr[l*257 +: 257]));
    end
endmodule
// hgi-1010/c 2026-10-10 (hardware ROW_GATHER sink, HBM-space O): the write twin of ot_hgi_hbm_rd_server.
// The loader side of an HBM write lane: one sector in flight on an ot_hfd_loader_kport lane (we = 1); the acknowledgement
// returns as a one-edge pulse.  xw {data 256, strb 32, addr 37 (kport byte address), v}.
module ot_hgi_hbm_wr_server (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [325:0]  xw,
    output reg           xa,
    output reg           req_v,
    input  wire          req_rdy,
    output reg  [36:0]   req_addr,
    output reg  [255:0]  req_wdata,
    output reg  [31:0]   req_wstrb,
    input  wire          rsp_v,
    output reg           fault
);
    reg pend;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin req_v <= 1'b0; xa <= 1'b0; pend <= 1'b0; fault <= 1'b0; end
        else begin
            xa <= 1'b0;
            if (req_v && req_rdy) req_v <= 1'b0;
            if (xw[0]) begin
                if (req_v || pend) fault <= 1'b1;
                req_v <= 1'b1; req_addr <= xw[37:1]; req_wstrb <= xw[69:38]; req_wdata <= xw[325:70]; pend <= 1'b1;
            end
            if (pend && rsp_v) begin pend <= 1'b0; xa <= 1'b1; end
        end
    end
endmodule
`default_nettype wire
