`timescale 1ns/1ps
`default_nettype none
// Static VM edge services. Q/G STREAM commands retain the fixed x43 row schedule.
// Collective ABI: four compiler-addressed {tag8,data512,mask16,row14,valid} writes,
// and f_crq={row14,valid} / t_crs={data512,valid} reads. Collective pins connect
// directly to the core auxiliary request/return ports: the core's L12 pin latency
// is unchanged. No legacy CPUSH/CCFG records, queue credits, or runtime pacing.
// Codes 5/7 and LARM group7 are unsupported legacy operations and raise fault.
// Q/G STREAM: code4, dest cd[27:26] (0=query,1=gather), base cd[25:12],
// count-minus-one cd[11:7]. Each unit reserves row[1:0] of aux4..7; a simultaneous
// collective request on the same lane is a compiler schedule fault.
// Q/G return timing retains the existing RLAT13 issue metadata pipeline.
// Collective write tags pass unchanged to the core write/commit pipeline.
module dsfd_vm_static_xio #(parameter integer RLAT = 13) (
    input wire ck_control_t, ck_control_s,
    input wire [1:0] ck_x43_t, ck_x43_s, // [0]query, [1]gather
    input wire rss_control_t, rst_control_s,
    input wire [1:0] rss_x43_t, rst_x43_s, // per-root active-low epoch resets
    // engine 12 native forward
    input  wire          n_v, input wire [83:0] n_d,
    // aux ports 4..7 to / from dsfd_vm_static_core
    output reg  [3:0]    a_v, output reg [55:0] a_row,
    input  wire [3:0]    e_v, input wire [2047:0] e_d,
    // collective
    input  wire [2203:0] f_collective,
    input  wire [14:0]   f_crq,
    output wire [512:0]  t_crs,
    output reg  [3:0]    w_v, output reg [55:0] w_row, output reg [2047:0] w_d, output reg [63:0] w_m, output reg [31:0] w_t,
    // gather
    output wire [511:0]  t_gather,             // serial
    input  wire [10:0]   f_xgo,                // stream
    // scan query
    output wire [512:0]  qSW,                  // serial
    input  wire [2:0]    qSWs,                 // serial
    output wire          fault
);
    // Each CDC half and each control domain owns its actual clock entry.
    // All roots retain the related3:4 common epoch; measured phi-R delivery
    // must preserve these logical sample edges. No child root is scalar-tied.
    reg [1:0] rq;
    always @(posedge ck_control_t or negedge rss_control_t) if (!rss_control_t) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // epoch sample index of the current edge (same convention as ot_s81_vm_x43: first edge after release = 0)
    reg [1:0] tp;
    always @(posedge ck_control_t or negedge rss_control_t) if (!rss_control_t) tp <= 2'd3; else tp <= tp + 2'd1;
    wire [1:0] tn = tp + 2'd1;
    reg [2:0] f_iss; reg f3, f9, f10; reg [1:0] f_s;
    wire [7:0] flt = {f_s, f10, f9, f3, f_iss};

    // ---------------------------------------------------------------- command decode
    wire [2:0] code = n_d[30:28];
    wire is_st = n_v && code == 3'd4, is_cp = n_v && code == 3'd5, is_cf = n_v && code == 3'd7;
    wire is_cl = n_v && code == 3'd6 && n_d[27:24] == 4'd7;
    // Unit 0 names the direct collective lane; state is used only for Q/G (1/2).
    reg [2:0] act; reg [13:0] u_row [0:2]; reg [4:0] u_n [0:2];
    reg [3:0] stream_av; reg [55:0] stream_ar;
    // ---------------------------------------------------------------- issue (edge I)
    reg [2:0] go; reg [1:0] gl [0:2];
    always @* begin : p_go integer u;
        for (u = 0; u < 3; u = u + 1) begin
            go[u] = (u == 0) ? f_crq[0] : (act[u] && tn != 2'd2);
            gl[u] = (u == 0) ? f_crq[2:1] : u_row[u][1:0];
        end
    end
    reg lane_bad;
    reg [2:0] go_ok;
    always @* begin
        lane_bad = 1'b0; go_ok = go;
        if (go[2] && go_ok[1] && gl[2] == gl[1]) begin lane_bad = 1'b1; go_ok[2] = 1'b0; end
    end
    // The direct collective lane is merged with the registered Q/G requests.
    // A collision faults and collective retains its reserved lane; nothing waits.
    always @* begin
        a_v = stream_av; a_row = stream_ar;
        if (f_crq[0]) begin
            a_v[f_crq[2:1]] = 1'b1;
            a_row[14*f_crq[2:1] +: 14] = f_crq[14:1];
        end
    end
    reg [RLAT-1:0] dC; reg [1:0] dlC [0:RLAT-1];
    reg [RLAT:0] dQ, dG; reg [1:0] dlQ [0:RLAT]; reg [1:0] dlG [0:RLAT];
    always @(posedge ck_control_t) begin : p_iss integer u, k; reg [3:0] av;
        if (!rn) begin
            act <= 3'd0; stream_av <= 4'd0; dC <= '0; dQ <= '0; dG <= '0;
            f_iss <= 3'd0;
        end else begin
            av = 4'd0;
            for (u = 1; u < 3; u = u + 1) if (go_ok[u]) av[gl[u]] = 1'b1;
            stream_av <= av;
            for (u = 1; u < 3; u = u + 1) if (go[u]) begin
                u_row[u] <= u_row[u] + 14'd1;
                if (u_n[u] == 5'd0) act[u] <= 1'b0; else u_n[u] <= u_n[u] - 5'd1;
            end
            if (lane_bad) f_iss[1] <= 1'b1;
            dC <= {dC[RLAT-2:0], f_crq[0]};
            dQ <= {dQ[RLAT-1:0], go_ok[1]}; dG <= {dG[RLAT-1:0], go_ok[2]};
            if (f_crq[0] && stream_av[f_crq[2:1]]) f_iss[1] <= 1'b1;
            if (is_cp || is_cf || is_cl) f_iss[2] <= 1'b1;
            if (is_st) begin
                if (n_d[27]) f_iss[2] <= 1'b1;
                else begin
                    if (act[1 + n_d[26]] && !(go[1 + n_d[26]] && u_n[1 + n_d[26]] == 5'd0)) f_iss[0] <= 1'b1;
                    act[1 + n_d[26]] <= 1'b1; u_row[1 + n_d[26]] <= n_d[25:12]; u_n[1 + n_d[26]] <= n_d[11:7];
                end
            end

        end
        for (k = 0; k < 4; k = k + 1)
            stream_ar[14*k +: 14] <= (go_ok[1] && gl[1] == k[1:0]) ? u_row[1] : u_row[2];
        dlC[0] <= f_crq[2:1]; dlQ[0] <= gl[1]; dlG[0] <= gl[2];
        for (k = 1; k <= RLAT; k = k + 1) begin
            dlQ[k] <= dlQ[k-1]; dlG[k] <= dlG[k-1];
        end
        for (k = 1; k < RLAT; k = k + 1) dlC[k] <= dlC[k-1];
    end
    // ---------------------------------------------------------------- return register (edge I + 14)
    wire rC = dC[RLAT-1], rQ = dQ[RLAT], rG = dG[RLAT];
    wire [1:0] lC = dlC[RLAT-1], lQ = dlQ[RLAT], lG = dlG[RLAT];
    wire [3:0] e_exp = (rC ? (4'd1 << lC) : 4'd0) | (rQ ? (4'd1 << lQ) : 4'd0) | (rG ? (4'd1 << lG) : 4'd0);
    wire [511:0] dCw = e_d[512*lC +: 512], dQw = e_d[512*lQ +: 512], dGw = e_d[512*lG +: 512];
    reg q_v; reg [511:0] q_d; reg g_v; reg [510:0] g_d;
    assign t_crs = {dCw, rC};
    reg [2:0] gn; reg [9:0] gph [0:3]; reg [1:0] gw, gr;
    reg [10:0] xq; always @(posedge ck_control_t) xq <= rn ? f_xgo : 11'd0;
    always @(posedge ck_control_t) begin : p_ret reg push, pop;
        if (!rn) begin
            q_v <= 1'b0; g_v <= 1'b0; gn <= 3'd0; gw <= 2'd0; gr <= 2'd0;
            f3 <= 1'b0; f9 <= 1'b0; f10 <= 1'b0;
        end else begin
            if (e_v != e_exp) f3 <= 1'b1;
            q_v <= rQ; q_d <= dQw;
            g_v <= rG; g_d <= dGw[510:0];
            // gather phase mirror (assertion only)
            push = rG && dGw[1:0] == 2'd0; pop = xq[10];
            if (push) begin gph[gw] <= dGw[58:49]; gw <= gw + 2'd1; end
            if (pop) begin
                if (gn == 3'd0 && !push) f9 <= 1'b1;
                else if (gph[gr] != xq[9:0]) f9 <= 1'b1;
                gr <= gr + 2'd1;
            end
            gn <= gn + (push ? 3'd1 : 3'd0) - ((pop && (gn != 3'd0 || push)) ? 3'd1 : 3'd0);
            if (push && !pop && gn == 3'd4) f10 <= 1'b1;
        end
    end
    // Compiler rows and masks are passed to the core without a landing pointer
    // or extra pin stage. Each lane's 8-bit tag remains part of f_collective ABI;
    // the wrapper/core associates these writes with fixed sources 44..47.
    always @* begin : p_land integer k;
        w_v = 4'd0; w_row = 56'd0; w_d = 2048'd0; w_m = 64'd0; w_t = 32'd0;
        for (k = 0; k < 4; k = k + 1) begin
            w_v[k] = f_collective[551*k];
            w_row[14*k +: 14] = f_collective[551*k+1 +: 14];
            w_m[16*k +: 16] = f_collective[551*k+15 +: 16];
            w_d[512*k +: 512] = f_collective[551*k+31 +: 512];
            `ifdef OT_VM_XIO_MUT_TAG
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8] ^ 8'd1;
`else
            w_t[8*k +: 8] = f_collective[551*k+543 +: 8];
`endif
        end
    end
    // ---------------------------------------------------------------- serial-bound streams
    wire qo_v, go_v; wire [511:0] qo_d; wire [510:0] go_d; wire qf, gf;
    ot_s81_vm_x43 #(.W(512)) u_xq (.t_ck(ck_x43_t[0]), .t_rst_n(rss_x43_t[0]), .s_v(q_v), .s_d(q_d), .s_ck(ck_x43_s[0]), .s_rst_n(rst_x43_s[0]),
        .o_v(qo_v), .o_d(qo_d), .fault(qf));
    ot_s81_vm_x43 #(.W(511)) u_xg (.t_ck(ck_x43_t[1]), .t_rst_n(rss_x43_t[1]), .s_v(g_v), .s_d(g_d), .s_ck(ck_x43_s[1]), .s_rst_n(rst_x43_s[1]),
        .o_v(go_v), .o_d(go_d), .fault(gf));
    assign qSW = {qo_d, qo_v};
    assign t_gather = {go_d, go_v};
    reg [1:0] sq; always @(posedge ck_control_s or negedge rst_control_s) if (!rst_control_s) sq <= 2'b00; else sq <= {sq[0], 1'b1};
    reg [2:0] qs_q; reg qs_bad;
    always @(posedge ck_control_s) begin
        qs_q <= qSWs;
        if (!sq[1]) qs_bad <= 1'b0; else if (qo_v && !(qs_q[0] && qs_q[1])) qs_bad <= 1'b1;
    end
    always @(posedge ck_control_t) if (!rn) f_s <= 2'd0; else begin if (qs_bad) f_s[0] <= 1'b1; if (qf | gf) f_s[1] <= 1'b1; end
    assign fault = |flt;
endmodule
`default_nettype wire
