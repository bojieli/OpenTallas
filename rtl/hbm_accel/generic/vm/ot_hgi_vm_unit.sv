`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM block body (hgi-takeover 2026-10-09): ot_hgi_vm_core + one die station per packet client.  Die protocol (VM
// fast path, review ~16:40): a client keeps at most OUT = 4 requests outstanding (request sent, response not yet
// received) and receives the responses IN REQUEST ORDER (tags echoed).  A request carries only a valid bit: the station
// queues up to 4 until the core grants them; a response needs no back-pressure.  A request arriving to a full station is
// a protocol violation (the client exceeded 4 outstanding): it latches proto_fault.  A v1 client (one outstanding) is a
// legal fast-path client.
// status = {proto_fault, mask_fault, ue, ce[15:0]} (19 b) to the command processor (UE / faults halt the CP).
//
// WIDE LANES (hgi-1010/f, coordinator 2026-10-10 budget audit item 1; b's SU/SFU lane contract, generalised to NRL
// read and NWL write clients: SU, SFU, SM x-load, ATT, HC, FUSED).  Every port is pin-flopped here.
//   lrq  client c lane b {v, sector 15}: read one sector of bank b (sector[4:0] must be b: a misrouted request is
//        dropped and latches proto_fault).  The client holds LQ credits a lane; lrq_cr returns one when the request
//        is accepted by its bank.
//   lrr  lane b {v, cid CIDW, data 256}: ONE response bus shared by the read clients (a bank serves one read a cycle);
//        client c takes lane b when cid == c.  Responses of one client lane come back in request order, RLAT edges after
//        acceptance; no back-pressure (the client always accepts).
//   lwq  client c lane b {v, sector 15, wdata 256, word mask 8} (the DMA wq layout), LQW credits a lane; lwq_cr returns
//        one when the write is accepted; lwq_done pulses when it is in the macro (the record retires on its last done).
//   Bank arbitration (ot_hgi_vm_core): reads: packet clients, then the lane clients in round robin; writes: the DMA
//   wide group, then packet clients, then the lane clients in round robin.  Back-pressure lands on the lane queues only.
module ot_hgi_vm_unit #(
    parameter integer NC = 1,
    parameter integer WP = 1,            // wide write lanes (the DMA streaming port, 32 B a lane a cycle)
    parameter integer WDIRECT = 0,       // lane b -> bank b only (WP 32 with the DMA front)
    parameter integer NRL = 0,           // wide lane read clients
    parameter integer NWL = 0,           // wide lane write clients
    parameter integer CIDW = 3,
    parameter integer LQ = 8,            // read credits a client lane (power of two)
    parameter integer LQW = 4,           // write credits a client lane (power of two)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,         // per client {v, req 337}
    output reg  [NC*274-1:0] cr,         // per client {v, rsp 273}
    output reg  [18:0]       status,
    // wide write port, per lane {v, sector 15, wdata 256, word mask 8} (280 b), pin-flopped here; done per lane
    input  wire [WP*280-1:0] wq,
    output wire [WP-1:0]     wq_done,
    input  wire [(NRL>0?NRL:1)*32*16-1:0]  lrq,
    output reg  [(NRL>0?NRL:1)*32-1:0]     lrq_cr,
    output reg  [32*(1+CIDW+256)-1:0]      lrr,
    input  wire [(NWL>0?NWL:1)*32*280-1:0] lwq,
    output reg  [(NWL>0?NWL:1)*32-1:0]     lwq_cr,
    output reg  [(NWL>0?NWL:1)*32-1:0]     lwq_done
);
    localparam integer NRLL = NRL > 0 ? NRL : 1, NWLL = NWL > 0 ? NWL : 1;
    localparam integer QB = LQ > 1 ? $clog2(LQ) : 1, QBW = LQW > 1 ? $clog2(LQW) : 1;
    reg [WP*280-1:0] wq_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) wq_r <= {WP*280{1'b0}}; else wq_r <= wq;
    wire [WP-1:0] wl_v; wire [WP*15-1:0] wl_sec; wire [WP*256-1:0] wl_d; wire [WP*8-1:0] wl_m; wire wl_conflict;
    genvar gp;
    for (gp = 0; gp < WP; gp = gp + 1) begin : g_wl
        assign wl_m[gp*8 +: 8] = wq_r[gp*280 +: 8]; assign wl_d[gp*256 +: 256] = wq_r[gp*280 + 8 +: 256];
        assign wl_sec[gp*15 +: 15] = wq_r[gp*280 + 264 +: 15]; assign wl_v[gp] = wq_r[gp*280 + 279];
    end
    // per-client station: a 4-entry FIFO with one explicit write enable per entry (generate per client and entry: the
    // pin data reaches each entry's D through one 2:1 mux; hgi-1010/c: the old for-loop over clients writing a 2-D array
    // elaborated as a 24-deep procmux chain from cq to sq)
    wire [NC-1:0]     h_v;
    wire [NC*337-1:0] h_q;
    wire [NC-1:0]     req_r, rsp_v;
    wire [NC*273-1:0] rsp;
    wire [15:0] ce; wire ue, mask_fault;
    wire [NC-1:0] ovf;                    // a push into a full station that does not pop this cycle
    reg proto;
    // ---- wide lane queues
    reg [NRLL*32*16-1:0]  lrq_p;
    reg [NWLL*32*280-1:0] lwq_p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lrq_p <= '0; lwq_p <= '0; end
        else begin lrq_p <= (NRL > 0) ? lrq : '0; lwq_p <= (NWL > 0) ? lwq : '0; end
    wire [NRLL*32-1:0] lr_v, lr_acc; wire [NRLL*32*15-1:0] lr_sec;
    wire [NWLL*32-1:0] lw_v, lw_acc, lw_done; wire [NWLL*32*15-1:0] lw_sec; wire [NWLL*32*256-1:0] lw_d;
    wire [NWLL*32*8-1:0] lw_m;
    wire [32*(1+CIDW+256)-1:0] lr_rsp;
    wire [NRLL*32-1:0] lr_bad; wire [NWLL*32-1:0] lw_bad;
    genvar gl, ge;
    for (gl = 0; gl < NRLL * 32; gl = gl + 1) begin : g_lrq
        reg [14:0] e [0:LQ-1];
        reg [QB-1:0] h, t; reg [QB:0] n;
        wire [15:0] q = lrq_p[gl*16 +: 16];
        wire push = (NRL > 0) && q[15];
        wire mis = q[4:0] != 5'(gl % 32);
        wire full = n == (QB+1)'(LQ) && !lr_acc[gl];
        assign lr_bad[gl] = push && (mis || full);
        wire wr = push && !mis && !full;
        assign lr_v[gl] = n != '0;
        assign lr_sec[gl*15 +: 15] = e[h];
        for (ge = 0; ge < LQ; ge = ge + 1) begin : g_e
            always @(posedge clk) if (wr && t == QB'(ge)) e[ge] <= q[14:0];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin h <= '0; t <= '0; n <= '0; end
            else begin
                if (wr) t <= t + 1'b1;
                if (lr_acc[gl]) h <= h + 1'b1;
                n <= n + {{QB{1'b0}}, wr} - {{QB{1'b0}}, lr_acc[gl]};
            end
    end
    for (gl = 0; gl < NWLL * 32; gl = gl + 1) begin : g_lwq
        reg [278:0] e [0:LQW-1];
        reg [QBW-1:0] h, t; reg [QBW:0] n;
        wire [279:0] q = lwq_p[gl*280 +: 280];
        wire push = (NWL > 0) && q[279];
        wire mis = q[264 +: 5] != 5'(gl % 32);
        wire full = n == (QBW+1)'(LQW) && !lw_acc[gl];
        assign lw_bad[gl] = push && (mis || full);
        wire wr = push && !mis && !full;
        assign lw_v[gl] = n != '0;
        assign lw_sec[gl*15 +: 15] = e[h][278:264];
        assign lw_d[gl*256 +: 256] = e[h][263:8];
        assign lw_m[gl*8 +: 8] = e[h][7:0];
        for (ge = 0; ge < LQW; ge = ge + 1) begin : g_e
            always @(posedge clk) if (wr && t == QBW'(ge)) e[ge] <= q[278:0];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin h <= '0; t <= '0; n <= '0; end
            else begin
                if (wr) t <= t + 1'b1;
                if (lw_acc[gl]) h <= h + 1'b1;
                n <= n + {{QBW{1'b0}}, wr} - {{QBW{1'b0}}, lw_acc[gl]};
            end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lrq_cr <= '0; lwq_cr <= '0; lwq_done <= '0; lrr <= '0; end
        else begin lrq_cr <= lr_acc; lwq_cr <= lw_acc; lwq_done <= lw_done; lrr <= lr_rsp; end
    ot_hgi_vm_core #(.NC(NC), .OUT(4), .WP(WP), .WDIRECT(WDIRECT), .NRL(NRL), .NWL(NWL), .CIDW(CIDW), .MUT(MUT)) u_core (
        .clk(clk), .rst_n(rst_n), .req_v(h_v), .req_r(req_r), .req(h_q),
        .rsp_v(rsp_v), .rsp_r({NC{1'b1}}), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault),
        .inj_v(1'b0), .inj_bank(5'd0), .inj_word(3'd0), .inj_mask(39'd0),
        .wl_v(wl_v), .wl_sec(wl_sec), .wl_d(wl_d), .wl_m(wl_m), .wl_done(wq_done), .wl_conflict(wl_conflict),
        .lr_v(lr_v), .lr_sec(lr_sec), .lr_acc(lr_acc), .lr_rsp(lr_rsp),
        .lw_v(lw_v), .lw_sec(lw_sec), .lw_d(lw_d), .lw_m(lw_m), .lw_acc(lw_acc), .lw_done(lw_done));
    genvar gc;
    for (gc = 0; gc < NC; gc = gc + 1) begin : g_st
        reg [336:0] e0, e1, e2, e3;
        reg [1:0] sh, stl; reg [2:0] sn;
        wire push = cq[gc*338 + 337];
        wire pop  = h_v[gc] && req_r[gc];
        assign ovf[gc] = push && sn == 3'd4 && !pop;
        wire wr = push && !ovf[gc];
        assign h_v[gc] = sn != 3'd0;
        assign h_q[gc*337 +: 337] = (sh == 2'd0) ? e0 : (sh == 2'd1) ? e1 : (sh == 2'd2) ? e2 : e3;
        always @(posedge clk) begin
            if (wr && stl == 2'd0) e0 <= cq[gc*338 +: 337];
            if (wr && stl == 2'd1) e1 <= cq[gc*338 +: 337];
            if (wr && stl == 2'd2) e2 <= cq[gc*338 +: 337];
            if (wr && stl == 2'd3) e3 <= cq[gc*338 +: 337];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sh <= 2'd0; stl <= 2'd0; sn <= 3'd0; cr[gc*274 +: 274] <= 274'd0; end
            else begin
                if (wr) stl <= stl + 2'd1;
                if (pop) sh <= sh + 2'd1;
                sn <= sn + {2'd0, wr} - {2'd0, pop};
                cr[gc*274 +: 274] <= {rsp_v[gc], rsp[gc*273 +: 273]};
            end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin proto <= 1'b0; status <= 19'd0; end
        else begin
            if (|ovf || |lr_bad || |lw_bad) proto <= 1'b1;
            status <= {proto | wl_conflict, mask_fault, ue, ce};
        end
endmodule
`default_nettype wire
