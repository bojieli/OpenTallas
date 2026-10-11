`timescale 1ns/1ps
`default_nettype none
// The quant-side end of a REMOTE kport read lane (hgi-1010/c2): a unit that is not beside the loader issues up to Q sector
// reads in flight over two registered die nets; the loader's ot_hgi_hbm_rdq_server queues them (Q deep) onto one
// ot_hfd_loader_kport lane, which answers in order.  The in-flight count is the credit: the server queue can never
// overflow and no ready crosses the die.  Read only: a write request faults (fail closed; the FUSED mover only LOADs).
module ot_hgi_hbm_rdq_client #(parameter integer Q = 32) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          req_v,
    output wire          req_rdy,
    input  wire          req_we,
    input  wire [36:0]   req_addr,
    output reg           rsp_v,
    output reg  [255:0]  rsp_data,
    output reg           fault,
    output reg  [37:0]   xq,                  // {addr 37, v}
    input  wire [256:0]  xr                   // {data 256, v}
);
    reg [$clog2(Q + 1)-1:0] inf;
    assign req_rdy = rst_n && (inf != Q[$clog2(Q + 1)-1:0]);
    wire iss = req_v && req_rdy && !req_we;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin inf <= '0; rsp_v <= 1'b0; xq <= 38'd0; fault <= 1'b0; end
        else begin
            xq <= iss ? {req_addr, 1'b1} : 38'd0;
            rsp_v <= xr[0]; rsp_data <= xr[256:1];
            inf <= inf + (iss ? 1'd1 : 1'd0) - (xr[0] ? 1'd1 : 1'd0);
            if (req_v && req_rdy && req_we) fault <= 1'b1;
        end
endmodule

// The loader-side end (one ot_hfd_loader_kport lane, read only): a Q-deep request queue, responses forwarded as
// registered pulses (the client always accepts).  fault: a request beyond Q (the client never sends one).
module ot_hgi_hbm_rdq_server #(parameter integer Q = 32) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [37:0]   xq,
    output reg  [256:0]  xr,
    output wire          req_v,
    input  wire          req_rdy,
    output wire [36:0]   req_addr,
    input  wire          rsp_v,
    input  wire [255:0]  rsp_data,
    output reg           fault
);
    localparam integer QW = $clog2(Q);
    reg [36:0] qa [0:Q-1]; reg [QW:0] n; reg [QW-1:0] h, t;
    assign req_v = n != '0;
    assign req_addr = qa[h];
    wire pop = req_v && req_rdy;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin n <= '0; h <= '0; t <= '0; xr <= 257'd0; fault <= 1'b0; end
        else begin
            if (xq[0]) begin
                qa[t] <= xq[37:1]; t <= t + 1'd1;
                if (n == Q[QW:0] && !pop) fault <= 1'b1;
            end
            n <= n + (xq[0] ? 1'd1 : 1'd0) - (pop ? 1'd1 : 1'd0);
            if (pop) h <= h + 1'd1;
            xr <= {rsp_data, rsp_v};
        end
endmodule
`default_nettype wire
