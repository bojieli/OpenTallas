`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09 (review-0528 KV4: write-then-read FENCE): the KV merge of one KV landing (die master qkd_land: one
// slice per row engine of its stack), on the row REQUEST and RESPONSE paths between the engines and the controllers.
//   * The KV-die sequencer posts the new position's four K / V rows (kvw_*: {v, g}, t = T-1, layer, 128 FP8 bytes) to
//     the landings; a landing keeps them, tagged {t, layer}, and its HBM write queue stores them.
//   * The layer start reaches the landing with the layer's T and index (lay_*: from the stack aggregator, the same
//     wavefront that starts the engines, so it always precedes the layer's first row request).
//   * FENCE: a row request for t = T-1 waits at the head of its engine's in-order request queue until the row {v, g}
//     of THIS layer {T-1, layer} has been merged (row_ok); the requests behind it wait too (order is preserved).  No
//     timing assumption: the rows may arrive at any time (a link-credit stall, a slow kvn path) -- the read waits.
//   * The response to that request (read in request order) is replaced by the kept row: the HBM write may not have
//     landed, the crossed K / V are the values the golden attends over.
// A response with no request outstanding, a request-queue overrun or a malformed row raise a sticky fault.
// MUT (bench only): 1 = no merge (the HBM row is used as is); 2 = no fence (the T-1 request is not held).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_merge #(
    parameter integer HD  = 128,
    parameter integer E   = 8,                 // row engines served
    parameter integer PD  = 64,                // queued requests per engine (>= the engine's outstanding-request credit)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // layer start (T, layer index) from the stack aggregator
    input  wire              lay_start,
    input  wire [13:0]       lay_T,
    input  wire [5:0]        lay_idx,
    // the posted rows of the new position
    input  wire              kvw_v,
    input  wire [1:0]        kvw_vg,
    input  wire [13:0]       kvw_t,
    input  wire [5:0]        kvw_layer,
    input  wire [HD*8-1:0]   kvw_d,
    // engine requests in, controller requests out (in order per engine)
    input  wire [E-1:0]      e_req_valid,
    input  wire [E-1:0]      e_req_v,
    input  wire [E-1:0]      e_req_g,
    input  wire [13*E-1:0]   e_req_t,
    output reg  [E-1:0]      h_req_valid,
    output reg  [E-1:0]      h_req_v,
    output reg  [E-1:0]      h_req_g,
    output reg  [13*E-1:0]   h_req_t,
    // controller responses in, merged responses out
    input  wire [E-1:0]      h_rsp_valid,
    input  wire [E*HD*8-1:0] h_rsp_data,
    output reg  [E-1:0]      e_rsp_valid,
    output reg  [E*HD*8-1:0] e_rsp_data,
    output reg               fault
);
    // ---- layer context ----
    reg          ls_q;
    reg [13:0]   T_q, T_cur;
    reg [5:0]    L_q, L_cur;
    always @(posedge clk) begin T_q <= lay_T; L_q <= lay_idx; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ls_q <= 1'b0; T_cur <= 14'd0; L_cur <= 6'd0; end
        else begin ls_q <= lay_start; if (ls_q) begin T_cur <= T_q; L_cur <= L_q; end end
    wire [13:0] tn = T_cur - 14'd1;
    // ---- kept rows, tagged {t, layer} ----
    reg          kv_q;
    reg [1:0]    vg_q;
    reg [13:0]   t_q;
    reg [5:0]    l_q;
    reg [HD*8-1:0] d_q;
    always @(posedge clk) begin vg_q <= kvw_vg; t_q <= kvw_t; l_q <= kvw_layer; d_q <= kvw_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) kv_q <= 1'b0; else kv_q <= kvw_v;
    reg [HD*8-1:0] row [0:3];
    reg [13:0]     row_t [0:3];
    reg [5:0]      row_l [0:3];
    reg [3:0]      row_v;
    always @(posedge clk) if (kv_q) begin row[vg_q] <= d_q; row_t[vg_q] <= t_q; row_l[vg_q] <= l_q; end
    always @(posedge clk or negedge rst_n) if (!rst_n) row_v <= 4'd0; else if (kv_q) row_v[vg_q] <= 1'b1;
    wire [3:0] row_ok;
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_ok
        assign row_ok[k] = row_v[k] && row_t[k] == tn && row_l[k] == L_cur;
    end endgenerate
    // ---- per engine: request queue (fence), pending-response tags, merged response ----
    wire [E-1:0] m_hv, m_pe, m_qf, m_qv;
    genvar e;
    generate for (e = 0; e < E; e = e + 1) begin : g_m
        reg        rq_v;
        reg [14:0] rq_d;                         // {v, g, t[12:0]}
        always @(posedge clk) rq_d <= {e_req_v[e], e_req_g[e], e_req_t[13*e +: 13]};
        always @(posedge clk or negedge rst_n) if (!rst_n) rq_v <= 1'b0; else rq_v <= e_req_valid[e];
        wire [14:0] qh;
        wire        qe, qf;
        wire        head_last = ({1'b0, qh[12:0]} == tn);
        wire        go = !qe && (!head_last || row_ok[qh[14:13]] || MUT == 2);
        ot_qkvd_fifo #(.W(15), .D(PD)) u_q (.clk(clk), .rst_n(rst_n), .push(rq_v), .din(rq_d), .pop(go), .dout(qh),
            .empty(qe), .full(qf), .count());
        always @(posedge clk) if (go) begin h_req_v[e] <= qh[14]; h_req_g[e] <= qh[13]; h_req_t[13*e +: 13] <= qh[12:0]; end
        always @(posedge clk or negedge rst_n) if (!rst_n) h_req_valid[e] <= 1'b0; else h_req_valid[e] <= go;
        // pending tags {last, v, g} in request order (the controllers answer an engine in order)
        reg        hv;
        reg [HD*8-1:0] hd;
        always @(posedge clk) hd <= h_rsp_data[HD*8*e +: HD*8];
        always @(posedge clk or negedge rst_n) if (!rst_n) hv <= 1'b0; else hv <= h_rsp_valid[e];
        wire [2:0] ph;
        wire pe, pf;
        ot_qkvd_fifo #(.W(3), .D(PD)) u_p (.clk(clk), .rst_n(rst_n), .push(go), .din({head_last, qh[14:13]}),
            .pop(hv), .dout(ph), .empty(pe), .full(pf), .count());
        always @(posedge clk) if (hv) e_rsp_data[HD*8*e +: HD*8] <= (ph[2] && MUT != 1) ? row[ph[1:0]] : hd;
        always @(posedge clk or negedge rst_n) if (!rst_n) e_rsp_valid[e] <= 1'b0; else e_rsp_valid[e] <= hv;
        assign m_hv[e] = hv; assign m_pe[e] = pe; assign m_qf[e] = qf; assign m_qv[e] = rq_v;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (|(m_hv & m_pe) || |(m_qv & m_qf)) fault <= 1'b1;
endmodule
