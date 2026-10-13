`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX wide adapter, TILED form (ot_hgi_idx_index_wt): BEAT leaf.
// Selector to / co pin capture, the two beat FIFOs (8 deep, the selector's credits), the top-k half-beat compaction
// (T1 one-hot prefix select -> T2) and the candidate beat compaction (D1).  SPEC "Tiled redesign".
// Free-flowing: a half beat / candidate beat leaves its FIFO only against an S3 credit of WR (one credit a WR queue
// slot, W = 6 covers the registered round trip), so T1 / T2 / D1 load every cycle and never stall.
// FIFO write and read pointers are registered copies, one a 64-bit slice; the half selector hb has one copy a lane.
// MUT 2 (inherited): R taken from the next lane.
module ot_hgi_idxw_beat #(
    parameter integer MUT = 0,
    parameter integer W   = 6       // S3 credits a stream (= WR input queue depth)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [611:0]  to_i,
    output reg           toc_o,
    input  wire [71:0]   co_i,
    output reg           coc_o,
    // S4 (QCORE)
    input  wire          bstart_i,
    input  wire          cand_en_i,
    output reg           b_idle_o,
    output reg           b_bad_o,
    // S3 (WR)
    output reg           t2_v_o,
    output reg  [3:0]    t2_n_o,
    output reg  [255:0]  t2_o_o, t2_r_o,
    input  wire          t2_cr_i,
    output reg           d1_v_o,
    output reg  [3:0]    d1_n_o,
    output reg  [63:0]   d1_i_o, d1_x_o,
    input  wire          d1_cr_i
);
    localparam integer TD = 611, NS = 10, CD = 71;
    integer i, l;
    genvar gc, ge, gl, gr;
    // ---- reset
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    wire [2:0] rnc;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rn
        reg r;
        (* keep = "true" *) always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rn;
        assign rnc[gr] = r;
    end endgenerate
    // ---- pin flops
    reg to_v, co_v, bstart_q, t2cr_q, d1cr_q, cand_en; reg [611:1] to_d; reg [71:1] co_d;
    always @(posedge clk or negedge rnc[0])
        if (!rnc[0]) begin to_v <= 1'b0; co_v <= 1'b0; bstart_q <= 1'b0; t2cr_q <= 1'b0; d1cr_q <= 1'b0; end
        else begin to_v <= to_i[0]; co_v <= co_i[0]; bstart_q <= bstart_i; t2cr_q <= t2_cr_i; d1cr_q <= d1_cr_i; end
    always @(posedge clk) begin to_d <= to_i[611:1]; co_d <= co_i[71:1]; cand_en <= cand_en_i; end
    // ---- control
    reg [3:0] tfn, cfn; reg hb; reg [2:0] tcred, dcred; reg to_last, co_last, t1_v;
    wire t_ld = tfn != 4'd0 && (tcred != 3'd0 || t2cr_q);
    wire t_pop = t_ld && hb;
    wire c_pop = cfn != 4'd0 && (dcred != 3'd0 || d1cr_q);
    // ---- top-k beat FIFO: slice c has its own valid / start pin flops and its own write and read pointer
    wire [611:0] th;
    assign th[0] = 1'b1;
    generate for (gc = 0; gc < NS; gc = gc + 1) begin : g_tf
        localparam integer SW = (gc == NS - 1) ? TD - 64*(NS-1) : 64;
        reg v, s; reg [2:0] wpc, rpc; reg [SW-1:0] rv; integer e;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) v <= 1'b0; else v <= to_i[0];
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) s <= 1'b0; else s <= bstart_i;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) wpc <= 3'd0; else if (v) wpc <= wpc + 3'd1;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) rpc <= 3'd0; else if (t_pop) rpc <= rpc + 3'd1;
        wire [8*SW-1:0] ef;
        for (ge = 0; ge < 8; ge = ge + 1) begin : g_e
            reg [SW-1:0] m;
            always @(posedge clk) if (v && wpc == 3'(ge)) m <= to_d[1 + gc*64 +: SW];
            assign ef[ge*SW +: SW] = m;
        end
        always @* begin rv = '0; for (e = 0; e < 8; e = e + 1) if (rpc == 3'(e)) rv = rv | ef[e*SW +: SW]; end
        assign th[1 + gc*64 +: SW] = rv;
    end endgenerate
    // ---- candidate beat FIFO (71 bits: two slices)
    wire [71:0] ch;
    assign ch[0] = 1'b1;
    generate for (gc = 0; gc < 2; gc = gc + 1) begin : g_cf
        localparam integer SW = (gc == 1) ? CD - 64 : 64;
        reg v, s; reg [2:0] wpc, rpc; reg [SW-1:0] rv; integer e;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) v <= 1'b0; else v <= co_i[0];
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) s <= 1'b0; else s <= bstart_i;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) wpc <= 3'd0; else if (v) wpc <= wpc + 3'd1;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) rpc <= 3'd0; else if (c_pop) rpc <= rpc + 3'd1;
        wire [8*SW-1:0] ef;
        for (ge = 0; ge < 8; ge = ge + 1) begin : g_e
            reg [SW-1:0] m;
            always @(posedge clk) if (v && wpc == 3'(ge)) m <= co_d[1 + gc*64 +: SW];
            assign ef[ge*SW +: SW] = m;
        end
        always @* begin rv = '0; for (e = 0; e < 8; e = e + 1) if (rpc == 3'(e)) rv = rv | ef[e*SW +: SW]; end
        assign ch[1 + gc*64 +: SW] = rv;
    end endgenerate
    // ---- T1: the half beat's 8 lanes (hb copy a lane) and the one-hot output-word select of each lane
    wire [7:0] t1_lv; wire [8*20-1:0] t1_o; wire [8*32-1:0] t1_r; wire [63:0] t1_s;   // t1_s[i*8 + l]: word i <- lane l
    reg [3:0] t1_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_t1
        reg hc; reg lv; reg [19:0] o; reg [31:0] r; reg [7:0] s; reg [3:0] cv, pr; integer x, pp;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || bstart_q) hc <= 1'b0; else if (t_ld) hc <= !hc;
        always @* begin
            pp = hc ? gl + 8 : gl;
            pr = (MUT == 2) ? 4'(pp + 1) : 4'(pp);
            cv = 4'd0;
            for (x = 0; x < gl; x = x + 1) cv = cv + 4'(th[4 + (hc ? x + 8 : x)]);
        end
        always @(posedge clk) begin
            lv <= th[4 + pp];
            o <= th[292 + 20*pp +: 20];
            r <= th[20 + pr] ? 32'hFF80_0000 : {th[36 + 16*pr +: 16], 16'd0};
            for (x = 0; x < 8; x = x + 1) s[x] <= th[4 + pp] && cv == 4'(x);
        end
        assign t1_lv[gl] = lv; assign t1_o[gl*20 +: 20] = o; assign t1_r[gl*32 +: 32] = r;
        for (ge = 0; ge < 8; ge = ge + 1) begin : g_s
            assign t1_s[ge*8 + gl] = s[ge];
        end
    end endgenerate
    reg [3:0] cntv; reg [255:0] o_acc, r_acc;
    always @(posedge clk) begin
        cntv = 4'd0;
        for (i = 0; i < 8; i = i + 1) cntv = cntv + 4'(th[4 + (hb ? i + 8 : i)]);
        t1_n <= cntv;
        // T2 (S3 beat): output word i = the lane selected for it
        o_acc = 256'd0; r_acc = 256'd0;
        for (i = 0; i < 8; i = i + 1)
            for (l = 0; l < 8; l = l + 1)
                if (t1_s[i*8 + l]) begin
                    o_acc[i*32 +: 32] = o_acc[i*32 +: 32] | {12'd0, t1_o[l*20 +: 20]};
                    r_acc[i*32 +: 32] = r_acc[i*32 +: 32] | t1_r[l*32 +: 32];
                end
        t2_n_o <= t1_n; t2_o_o <= o_acc; t2_r_o <= r_acc;
        // D1 (S3 beat): 2 lanes compacted
        d1_n_o <= 4'(ch[4]) + 4'(ch[5]);
        d1_i_o <= {32'(ch[55 +: 17]), ch[4] ? 32'(ch[38 +: 17]) : 32'(ch[55 +: 17])};
        d1_x_o <= {{ch[22 +: 16], 16'd0}, ch[4] ? {ch[6 +: 16], 16'd0} : {ch[22 +: 16], 16'd0}};
    end
    always @(posedge clk) begin
        if (!rnc[2]) begin
            tfn <= 4'd0; cfn <= 4'd0; hb <= 1'b0; tcred <= 3'(W); dcred <= 3'(W); to_last <= 1'b0; co_last <= 1'b0;
            t1_v <= 1'b0; t2_v_o <= 1'b0; d1_v_o <= 1'b0; toc_o <= 1'b0; coc_o <= 1'b0; b_idle_o <= 1'b0; b_bad_o <= 1'b0;
        end else begin
            tfn <= tfn + {3'd0, to_v} - {3'd0, t_pop};
            cfn <= cfn + {3'd0, co_v} - {3'd0, c_pop};
            b_bad_o <= (to_v && tfn == 4'd8 && !t_pop) || (co_v && cfn == 4'd8 && !c_pop);
            tcred <= tcred + 3'(t2cr_q) - 3'(t_ld);
            dcred <= dcred + 3'(d1cr_q) - 3'(c_pop);
            if (t_ld) hb <= !hb;
            t1_v <= t_ld; t2_v_o <= t1_v; d1_v_o <= c_pop;
            toc_o <= t_pop; coc_o <= c_pop;
            if (t_pop && th[1]) to_last <= 1'b1;
            if (c_pop && ch[1]) co_last <= 1'b1;
            b_idle_o <= to_last && co_last && tfn == 4'd0 && cfn == 4'd0 && !t1_v && !t2_v_o && !d1_v_o;
            if (bstart_q) begin
                tfn <= 4'd0; cfn <= 4'd0; hb <= 1'b0; tcred <= 3'(W); dcred <= 3'(W); to_last <= 1'b0; co_last <= !cand_en;
                b_idle_o <= 1'b0;
            end
        end
    end
endmodule
`default_nettype wire
