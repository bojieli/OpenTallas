`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM block body (hgi-takeover 2026-10-09): ot_hgi_vm_core + one die station per packet client.  Die protocol (VM
// fast path, review ~16:40): a client keeps at most OUT = 4 requests outstanding (request sent, response not yet
// received) and receives the responses IN REQUEST ORDER (tags echoed).  A request carries only a valid bit: the station
// queues up to 4 until the core grants them; a response needs no back-pressure.  A request arriving to a full station is
// a protocol violation (the client exceeded 4 outstanding): it latches proto_fault.  A v1 client (one outstanding) is a
// legal fast-path client.
// status = {proto_fault, mask_fault, ue, ce[15:0]} (19 b) to the command processor (UE / faults halt the CP).
module ot_hgi_vm_unit #(
    parameter integer NC = 1,
    parameter integer WP = 1,            // wide write lanes (the DMA streaming port, 32 B a lane a cycle)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,         // per client {v, req 337}
    output reg  [NC*274-1:0] cr,         // per client {v, rsp 273}
    output reg  [18:0]       status,
    // wide write port, per lane {v, sector 15, wdata 256, word mask 8} (280 b), pin-flopped here; done per lane
    input  wire [WP*280-1:0] wq,
    output wire [WP-1:0]     wq_done
);
    reg [WP*280-1:0] wq_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) wq_r <= {WP*280{1'b0}}; else wq_r <= wq;
    wire [WP-1:0] wl_v; wire [WP*15-1:0] wl_sec; wire [WP*256-1:0] wl_d; wire [WP*8-1:0] wl_m; wire wl_conflict;
    genvar gp;
    for (gp = 0; gp < WP; gp = gp + 1) begin : g_wl
        assign wl_m[gp*8 +: 8] = wq_r[gp*280 +: 8]; assign wl_d[gp*256 +: 256] = wq_r[gp*280 + 8 +: 256];
        assign wl_sec[gp*15 +: 15] = wq_r[gp*280 + 264 +: 15]; assign wl_v[gp] = wq_r[gp*280 + 279];
    end
    reg  [336:0] sq [0:NC-1][0:3];
    reg  [1:0]   sh [0:NC-1];
    reg  [1:0]   stl [0:NC-1];
    reg  [2:0]   sn [0:NC-1];
    reg  [NC-1:0]     h_v;
    reg  [NC*337-1:0] h_q;
    always @* for (integer cc = 0; cc < NC; cc = cc + 1) begin h_v[cc] = sn[cc] != 3'd0; h_q[cc*337 +: 337] = sq[cc][sh[cc]]; end
    wire [NC-1:0]     req_r, rsp_v;
    wire [NC*273-1:0] rsp;
    wire [15:0] ce; wire ue, mask_fault;
    reg proto;
    ot_hgi_vm_core #(.NC(NC), .OUT(4), .WP(WP), .MUT(MUT)) u_core (.clk(clk), .rst_n(rst_n), .req_v(h_v), .req_r(req_r), .req(h_q),
        .rsp_v(rsp_v), .rsp_r({NC{1'b1}}), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault),
        .inj_v(1'b0), .inj_bank(5'd0), .inj_word(3'd0), .inj_mask(39'd0),
        .wl_v(wl_v), .wl_sec(wl_sec), .wl_d(wl_d), .wl_m(wl_m), .wl_done(wq_done), .wl_conflict(wl_conflict));
    integer c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            proto <= 1'b0; cr <= {NC*274{1'b0}}; status <= 19'd0;
            for (c = 0; c < NC; c = c + 1) begin sh[c] <= 2'd0; stl[c] <= 2'd0; sn[c] <= 3'd0; end
        end else begin
            for (c = 0; c < NC; c = c + 1) begin : st
                reg push, pop;
                push = cq[c*338 + 337]; pop = h_v[c] && req_r[c];
                if (push) begin
                    if (sn[c] == 3'd4 && !pop) proto <= 1'b1;
                    else begin sq[c][stl[c]] <= cq[c*338 +: 337]; stl[c] <= stl[c] + 2'd1; end
                end
                if (pop) sh[c] <= sh[c] + 2'd1;
                sn[c] <= sn[c] + {2'd0, push && !(sn[c] == 3'd4 && !pop)} - {2'd0, pop};
                cr[c*274 +: 274] <= {rsp_v[c], rsp[c*273 +: 273]};
            end
            status <= {proto | wl_conflict, mask_fault, ue, ce};
        end
endmodule
`default_nettype wire
