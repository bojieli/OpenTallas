`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT LH-P3UNITS/UNIONTILE 10-19: union-dispatch HEAD beside idx_sel (per-quadrant dispatcher build).
// The central factored dispatcher (ot_hnx_union_prefix, UNIONVAR c913ec2b5) paid 23 wire + 4 landing cycles per union
// layer between idx_sel and the farthest quadrant kernel store.  This build keeps ONLY the passive tap at idx_sel and
// broadcasts a compact, registered 50-bit stream word every edge to one dispatcher copy per quadrant
// (ot_hnx_union_qtile = ot_hnx_union_qdisp + ot_hnx_union_kstore beside that quadrant's kernel store) over registered
// <= 405 um relay hops + one landed crossing (fixed latency LQ per quadrant, no ready/credit, no backpressure).
// The c_u stream reaches the quadrants ~100 edges before the union is done, and each copy starts dispatch at the
// COMPILED union-done edge (descriptor field s_off = done edge - go edge, a static IDX timeline property), so the
// link latency is off the critical path; the forwarded union_v / union_count / union_fault verify it LQ edges later.
// Stage E0 (pin capture of the tap fields) is exactly the E0 of ot_hnx_union_prefix.
// Stream word (SW = 50): [0] go [5:1] n_rows [21:6] s_off [22] tv (table slot) [23] td (D sector) [30:24] slot
//   [35:31] c [36] m (word-0 mask valid) [37] cbad [38] uv (union_v) [48:39] union_count [49] ufault.
module ot_hnx_union_tap (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [4:0]    n_rows,
    input  wire [3:0]    k,
    input  wire [17:0]   d_base,
    input  wire [17:0]   r_base,
    input  wire [15:0]   s_off,
    input  wire [337:0]  cq,
    input  wire          union_v,
    input  wire [9:0]    union_count,
    input  wire          union_fault,
    output wire [49:0]   s_out
);
    reg [14:0] rsec_q, dsec_q; reg [7:0] tslots_q; reg [4:0] n_q;
    reg tap_on, rdy_p0, rdy_p1;
    reg t0_v, t0_d, t0_m, t0_cbad; reg [14:0] t0_off; reg [4:0] t0_c;
    reg g_q; reg [4:0] gn_q; reg [15:0] gs_q; reg uv_q, uf_q; reg [9:0] uc_q;
    wire        cq_v    = cq[337];
    wire [14:0] cq_sec  = cq[323:309];
    wire [31:0] cq_w0   = cq[79:48];
    wire [3:0]  cq_m0   = cq[19:16];
    wire [14:0] off     = cq_sec - rsec_q;
    wire in_tab = tap_on && cq_v && off[1:0] == 2'd0 && off[14:2] < {5'd0, tslots_q};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            tap_on <= 1'b0; rdy_p0 <= 1'b0; rdy_p1 <= 1'b0; t0_v <= 1'b0; t0_d <= 1'b0; g_q <= 1'b0; uv_q <= 1'b0;
            uf_q <= 1'b0;
        end else begin
            if (go) tap_on <= 1'b1;
            t0_v <= in_tab; t0_d <= tap_on && cq_v && cq_sec == dsec_q;
            rdy_p0 <= t0_d; rdy_p1 <= rdy_p0;
            if (rdy_p1 || union_fault) tap_on <= 1'b0;
            g_q <= go; uv_q <= union_v; uf_q <= union_fault;
        end
    always @(posedge clk) begin                     // data fields: no reset (qualified by the valids above)
        if (go) begin
            rsec_q <= r_base[17:3]; dsec_q <= d_base[17:3]; tslots_q <= 8'(n_rows) * 8'(k); n_q <= n_rows;
        end
        t0_off <= off; t0_c <= cq_w0[4:0]; t0_m <= cq_m0 == 4'hf;
        t0_cbad <= cq_m0 == 4'hf && (cq_w0 == 32'd0 || cq_w0 > 32'(n_q)) || (cq_m0 != 4'hf && cq_m0 != 4'h0);
        gn_q <= n_rows; gs_q <= s_off; uc_q <= union_count;
    end
    assign s_out = {uf_q, uc_q, uv_q, t0_cbad, t0_m, t0_c, t0_off[8:2], t0_d, t0_v, gs_q, gn_q, g_q};
endmodule

// Fixed-latency broadcast link model: N registered stations (relay hops <= 405 um + the landed crossing's fixed
// latency).  Static: no valid/ready, every stream word advances one station per edge.
module ot_hnx_union_bcast #(
    parameter integer W = 50,
    parameter integer N = 1
)(
    input  wire          clk,
    input  wire [W-1:0]  d,
    output wire [W-1:0]  q
);
    reg [W-1:0] st [0:N-1];
    integer i;
    always @(posedge clk) begin
        st[0] <= d;
        for (i = 1; i < N; i = i + 1) st[i] <= st[i-1];
    end
    assign q = st[N-1];
endmodule
`default_nettype wire
