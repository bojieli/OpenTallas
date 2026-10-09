`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09: the KV merge of one KV landing (die master qkd_land: one slice per row engine of its stack).
// The KV die's sequencer posts the new position's four K / V rows (kvw_*: {v, g}, t = T-1, layer, 128 FP8 bytes) to
// the HBM write queue; the landing snoops that stream and keeps the rows.  Every row request an engine issues is
// recorded in order (the controllers answer an engine in request order); a response to a request for t = T-1 (the
// position the posted write may not have reached in HBM yet) is replaced by the kept row.  Exact by construction: the
// replaced bytes ARE the crossed K / V (the golden attends over the stored FP8 values, which these are).
// Timing guarantee (CONTRACT.md): the rows reach the landing (seq -> land relays) before any engine's request for T-1
// can be answered (seq -> aggregator -> engine -> landing -> HBM latency is longer by construction); a T-1 response
// that finds no row for this layer is a sticky fault (fail closed), never a silent wrong value.
// MUT = 1 (bench only): no merge.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_merge #(
    parameter integer HD  = 128,
    parameter integer E   = 8,                 // row engines served
    parameter integer PD  = 64,                // outstanding requests per engine
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              kvw_v,
    input  wire [1:0]        kvw_vg,
    input  wire [13:0]       kvw_t,
    input  wire [HD*8-1:0]   kvw_d,
    input  wire [E-1:0]      e_req_valid,
    input  wire [E-1:0]      e_req_v,
    input  wire [E-1:0]      e_req_g,
    input  wire [13*E-1:0]   e_req_t,
    input  wire [E-1:0]      h_rsp_valid,
    input  wire [E*HD*8-1:0] h_rsp_data,
    output reg  [E-1:0]      e_rsp_valid,
    output reg  [E*HD*8-1:0] e_rsp_data,
    output reg               fault
);
    reg          kv_q;
    reg [1:0]    vg_q;
    reg [13:0]   t_q;
    reg [HD*8-1:0] d_q;
    always @(posedge clk) begin vg_q <= kvw_vg; t_q <= kvw_t; d_q <= kvw_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) kv_q <= 1'b0; else kv_q <= kvw_v;
    reg [HD*8-1:0] row [0:3];
    reg [3:0]      have;
    reg [13:0]     tn;                          // T-1 of the rows kept
    always @(posedge clk) if (kv_q) row[vg_q] <= d_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin have <= 4'd0; tn <= 14'h3fff; end
        else if (kv_q) begin
            if (t_q != tn) begin have <= 4'd1 << vg_q; tn <= t_q; end
            else have <= have | (4'd1 << vg_q);
        end
    wire [E-1:0] m_hv, m_pe, m_rqv, m_pf, m_miss;
    genvar e;
    generate for (e = 0; e < E; e = e + 1) begin : g_m
        reg        rq_v, rq_vv, rq_g, hv;
        reg [12:0] rq_t;
        reg [HD*8-1:0] hd;
        always @(posedge clk) begin rq_vv <= e_req_v[e]; rq_g <= e_req_g[e]; rq_t <= e_req_t[13*e +: 13]; hd <= h_rsp_data[HD*8*e +: HD*8]; end
        always @(posedge clk or negedge rst_n) if (!rst_n) begin rq_v <= 1'b0; hv <= 1'b0; end
                                               else begin rq_v <= e_req_valid[e]; hv <= h_rsp_valid[e]; end
        wire [2:0] ph;
        wire pe, pf;
        ot_qkvd_fifo #(.W(3), .D(PD)) u_p (.clk(clk), .rst_n(rst_n), .push(rq_v), .din({({1'b0, rq_t} == tn), rq_vv, rq_g}),
            .pop(hv), .dout(ph), .empty(pe), .full(pf), .count());
        always @(posedge clk) if (hv) e_rsp_data[HD*8*e +: HD*8] <= (ph[2] && MUT != 1) ? row[ph[1:0]] : hd;
        always @(posedge clk or negedge rst_n) if (!rst_n) e_rsp_valid[e] <= 1'b0; else e_rsp_valid[e] <= hv;
        assign m_hv[e] = hv; assign m_pe[e] = pe; assign m_rqv[e] = rq_v; assign m_pf[e] = pf;
        assign m_miss[e] = hv && ph[2] && !have[ph[1:0]];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (|(m_hv & m_pe) || |(m_rqv & m_pf & ~m_hv) || (|m_miss && MUT != 1)) fault <= 1'b1;
endmodule
