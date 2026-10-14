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

// The FUSED mover's HBM side over ONE remote read lane (hbmdie-1011/bind): main's ot_hgi_dma_mover issues HBM loads as
// bursts on four per-stack lanes (r_req_*, len 1..8, tag, answered in order with rsp_last) plus single sectors on k_req
// (the serial engine).  This adapter serves the five sources round robin, one burst at a time, as single-sector reads on
// the ot_hgi_hbm_rdq_client (stack bits travel in the address; the loader's kport lane routes them).  Every issued sector
// first allocates a slot of a D-deep in-order landing FIFO {k, lane, tag, last | data}, so the client's responses (no
// ready) always land and the mover's per-lane landing grant (r_rsp_rdy) can stall the head without loss.  Read only: a
// write on any source faults (fail closed; the FUSED mover only LOADs from HBM).
module ot_hgi_rlane_rdq #(parameter integer D = 32) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [3:0]        r_req_v,
    output wire [3:0]        r_req_rdy,
    input  wire [4*37-1:0]   r_req_addr,
    input  wire [4*4-1:0]    r_req_len,
    input  wire [4*16-1:0]   r_req_tag,
    input  wire [3:0]        r_req_we,
    output wire [3:0]        r_rsp_v,
    input  wire [3:0]        r_rsp_rdy,
    output wire [4*16-1:0]   r_rsp_tag,
    output wire [3:0]        r_rsp_last,
    output wire [4*256-1:0]  r_rsp_data,
    input  wire              k_req_v,
    output wire              k_req_rdy,
    input  wire              k_req_we,
    input  wire [36:0]       k_req_addr,
    output reg               k_rsp_v,
    output reg  [255:0]      k_rsp_data,
    output wire              c_req_v,
    input  wire              c_req_rdy,
    output wire              c_req_we,
    output wire [36:0]       c_req_addr,
    input  wire              c_rsp_v,
    input  wire [255:0]      c_rsp_data,
    output reg               fault
);
    localparam integer AW = $clog2(D);
    // ---- source select (round robin over {k, r3..r0}) and the burst engine
    wire [4:0] src_v = {k_req_v, r_req_v};
    reg [2:0] rr; reg busy; reg bk; reg [1:0] bl; reg [36:0] ba; reg [3:0] bn; reg [15:0] bt;
    reg [2:0] pick; reg pv;
    integer i;
    always @* begin
        pv = 1'b0; pick = 3'd0;
        for (i = 0; i < 5; i = i + 1)
            if (!pv && src_v[(rr + i) % 5]) begin pv = 1'b1; pick = 3'((rr + i) % 5); end
    end
    wire take = !busy && pv;
    for (genvar l = 0; l < 4; l = l + 1) begin : g_rdy
        assign r_req_rdy[l] = rst_n && !busy && pv && pick == 3'(l);
    end
    assign k_req_rdy = rst_n && !busy && pv && pick == 3'd4;
    // ---- landing FIFO: slots allocated at issue (it), filled by responses (rt), presented / freed at the head (hd)
    reg [AW:0] it, rt, hd;
    reg [255:0] fd [0:D-1]; reg fk [0:D-1]; reg [1:0] fl [0:D-1]; reg [15:0] ft [0:D-1]; reg fz [0:D-1]; reg [D-1:0] fv;
    wire room = (it - hd) != (AW + 1)'(D);
    assign c_req_v = busy && room;
    assign c_req_we = 1'b0;
    assign c_req_addr = ba;
    wire iss = c_req_v && c_req_rdy;
    wire [AW-1:0] h = hd[AW-1:0];
    wire hv = fv[h];
    wire hk = fk[h]; wire [1:0] hl = fl[h];
    wire pop = hv && (hk || r_rsp_rdy[hl]);
    for (genvar l = 0; l < 4; l = l + 1) begin : g_rsp
        assign r_rsp_v[l] = hv && !hk && hl == 2'(l);
        assign r_rsp_tag[l*16 +: 16] = ft[h];
        assign r_rsp_last[l] = fz[h];
        assign r_rsp_data[l*256 +: 256] = fd[h];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr <= 3'd0; busy <= 1'b0; bk <= 1'b0; bl <= 2'd0; ba <= '0; bn <= 4'd0; bt <= 16'd0;
            it <= '0; rt <= '0; hd <= '0; fv <= '0; k_rsp_v <= 1'b0; k_rsp_data <= '0; fault <= 1'b0;
        end else begin
            if (take) begin
                busy <= 1'b1; rr <= (pick == 3'd4) ? 3'd0 : pick + 3'd1;
                if (pick == 3'd4) begin
                    bk <= 1'b1; bl <= 2'd0; ba <= k_req_addr; bn <= 4'd1; bt <= 16'd0;
                    if (k_req_we) fault <= 1'b1;
                end else begin
                    bk <= 1'b0; bl <= pick[1:0]; ba <= r_req_addr[pick[1:0]*37 +: 37];
                    bn <= r_req_len[pick[1:0]*4 +: 4]; bt <= r_req_tag[pick[1:0]*16 +: 16];
                    if (r_req_we[pick[1:0]] || r_req_len[pick[1:0]*4 +: 4] == 4'd0) fault <= 1'b1;
                end
            end
            if (iss) begin
                fk[it[AW-1:0]] <= bk; fl[it[AW-1:0]] <= bl; ft[it[AW-1:0]] <= bt; fz[it[AW-1:0]] <= bn == 4'd1;
                it <= it + 1'd1; ba <= ba + 37'd32; bn <= bn - 4'd1;
                if (bn == 4'd1) busy <= 1'b0;
            end
            if (c_rsp_v) begin
                fd[rt[AW-1:0]] <= c_rsp_data; rt <= rt + 1'd1;
                if (rt == it) fault <= 1'b1;                     // a response with no slot (never: the client answers its own)
            end
            k_rsp_v <= pop && hk;
            if (pop && hk) k_rsp_data <= fd[h];
            if (pop) hd <= hd + 1'd1;
            // valid bits: set on fill, cleared on pop (distinct slots: a slot fills only between its issue and its pop)
            fv <= (fv | (c_rsp_v ? (D)'(1) << rt[AW-1:0] : '0)) & ~(pop ? (D)'(1) << h : '0);
        end
    end
endmodule

`default_nettype wire
