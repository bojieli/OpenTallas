`timescale 1ns/1ps
`default_nettype none
// ix2 result beats (hbm-redesign-idx 2026-10-13): the selector's top-k beats (to, 16 lanes) and candidate beats
// (co, 2 lanes) land in pin flops and 8-deep beat FIFOs (one credit a beat back: toc / coc).  A top-k beat is
// compacted in two half beats of 8 lanes: T1 registers the lane fields and the prefix counts of the valid lanes,
// T2 (the link register) places the lane whose prefix count is i at word i.  The compacted halves {n, 8 ids, 8
// {ninf, score}} and the candidate beats leave on two credited links to the write tile (4 credits each).
module ot_hgi_idx_ix2_pk #(
    parameter integer MUT = 0       // 2: R taken from the wrong lane
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire          run,
    input  wire          cand_en_i,
    input  wire [611:0]  to,
    output reg           toc,
    input  wire [71:0]   co,
    output reg           coc,
    output reg           t_v,
    output reg  [3:0]    t_n,
    output reg  [159:0]  t_o,
    output reg  [135:0]  t_r,
    input  wire          t_cr,
    output reg           d_v,
    output reg  [1:0]    d_n,
    output reg  [65:0]   d_p,           // {val1 16, val0 16, id1 17, id0 17} compacted
    input  wire          d_cr,
    output reg           pk_done,
    output reg           pk_bad
);
    integer l, i, p;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg st_q, run_q, cand_en, to_v, co_v, tcr_q, dcr_q; reg [611:1] to_d; reg [71:1] co_d;
    always @(posedge clk or negedge rn)
        if (!rn) begin st_q <= 1'b0; run_q <= 1'b0; to_v <= 1'b0; co_v <= 1'b0; tcr_q <= 1'b0; dcr_q <= 1'b0; end
        else begin st_q <= start; run_q <= run; to_v <= to[0]; co_v <= co[0]; tcr_q <= t_cr; dcr_q <= d_cr; end
    always @(posedge clk) begin cand_en <= cand_en_i; to_d <= to[611:1]; co_d <= co[71:1]; end
    reg [611:1] tf [0:7]; reg [2:0] tfh, tft; reg [3:0] tfn;
    // four kept copies of the head pointer, one a quarter of the 611-b head word (10-13: one copy drove 4,874 loads)
    (* keep = 1 *) reg [2:0] tfh_a, tfh_b, tfh_c, tfh_d;
    reg [71:1]  cf [0:7]; reg [2:0] cfh, cft; reg [3:0] cfn;
    reg hb, t1_v, to_last, co_last;
    reg [7:0] t1_lv; reg [19:0] t1_o [0:7]; reg [16:0] t1_r [0:7]; reg [2:0] t1_pf [0:7]; reg [3:0] t1_n;
    reg [2:0] tcred, dcred;
    wire [611:1] th_a = tf[tfh_a], th_b = tf[tfh_b], th_c = tf[tfh_c], th_d = tf[tfh_d];
    wire [611:1] th = {th_d[611:459], th_c[458:306], th_b[305:153], th_a[152:1]}; wire [71:1] ch = cf[cfh];
    wire t2_ld = t1_v && (tcred != 3'd0 || tcr_q);
    wire t1_free = !t1_v || t2_ld;
    wire t_ld = run_q && tfn != 4'd0 && t1_free;
    wire t_pop = t_ld && hb;
    wire c_pop = run_q && cfn != 4'd0 && (dcred != 3'd0 || dcr_q);
    reg [3:0] cntv, pref; reg [159:0] o_acc; reg [135:0] r_acc;
    always @(posedge clk) begin
        if (to_v) tf[tft] <= to_d;
        if (co_v) cf[cft] <= co_d;
        if (t_ld) begin
            for (l = 0; l < 8; l = l + 1) begin
                p = hb ? l + 8 : l;
                t1_lv[l] <= th[4 + p];
                t1_o[l] <= th[292 + 20*p +: 20];
                pref = (MUT == 2) ? 4'(p + 1) : 4'(p);
                t1_r[l] <= {th[20 + {28'd0, pref}], th[36 + 16*{28'd0, pref} +: 16]};
                cntv = 4'd0;
                for (i = 0; i < 8; i = i + 1) if (i < l) cntv = cntv + 4'(th[4 + (hb ? i + 8 : i)]);
                t1_pf[l] <= cntv[2:0];
            end
            cntv = 4'd0;
            for (i = 0; i < 8; i = i + 1) cntv = cntv + 4'(th[4 + (hb ? i + 8 : i)]);
            t1_n <= cntv;
        end
        if (t2_ld) begin
            o_acc = 160'd0; r_acc = 136'd0;
            for (i = 0; i < 8; i = i + 1)
                for (l = 0; l < 8; l = l + 1)
                    if (t1_lv[l] && t1_pf[l] == 3'(i)) begin o_acc[i*20 +: 20] = o_acc[i*20 +: 20] | t1_o[l];
                                                             r_acc[i*17 +: 17] = r_acc[i*17 +: 17] | t1_r[l]; end
            t_n <= t1_n; t_o <= o_acc; t_r <= r_acc;
        end
        if (c_pop) begin
            d_n <= 2'(ch[4]) + 2'(ch[5]);
            d_p <= {ch[22 +: 16], ch[4] ? ch[6 +: 16] : ch[22 +: 16], ch[55 +: 17], ch[4] ? ch[38 +: 17] : ch[55 +: 17]};
        end
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin
            tfh <= 3'd0; tfh_a <= 3'd0; tfh_b <= 3'd0; tfh_c <= 3'd0; tfh_d <= 3'd0; tft <= 3'd0; tfn <= 4'd0; cfh <= 3'd0; cft <= 3'd0; cfn <= 4'd0; hb <= 1'b0; t1_v <= 1'b0;
            to_last <= 1'b0; co_last <= 1'b0; tcred <= 3'd4; dcred <= 3'd4; toc <= 1'b0; coc <= 1'b0; t_v <= 1'b0; d_v <= 1'b0;
            pk_done <= 1'b0; pk_bad <= 1'b0;
        end else begin
            toc <= t_pop; coc <= c_pop; t_v <= t2_ld; d_v <= c_pop;
            if (to_v) tft <= tft + 3'd1;
            if (co_v) cft <= cft + 3'd1;
            tfn <= tfn + {3'd0, to_v} - {3'd0, t_pop};
            cfn <= cfn + {3'd0, co_v} - {3'd0, c_pop};
            if (run_q && ((to_v && tfn == 4'd8 && !t_pop) || (co_v && cfn == 4'd8 && !c_pop))) pk_bad <= 1'b1;
            if (t1_free) t1_v <= t_ld;
            if (t_ld) begin hb <= !hb; if (hb) begin tfh <= tfh + 3'd1; tfh_a <= tfh_a + 3'd1; tfh_b <= tfh_b + 3'd1; tfh_c <= tfh_c + 3'd1; tfh_d <= tfh_d + 3'd1; if (th[1]) to_last <= 1'b1; end end
            if (c_pop) begin cfh <= cfh + 3'd1; if (ch[1]) co_last <= 1'b1; end
            tcred <= tcred + 3'(tcr_q) - 3'(t2_ld);
            dcred <= dcred + 3'(dcr_q) - 3'(c_pop);
            pk_done <= run_q && to_last && co_last && tfn == 4'd0 && cfn == 4'd0 && !t1_v && tcred == 3'd4 && dcred == 3'd4 &&
                       !to_v && !co_v;
            if (st_q) begin
                tfh <= 3'd0; tfh_a <= 3'd0; tfh_b <= 3'd0; tfh_c <= 3'd0; tfh_d <= 3'd0; tft <= 3'd0; tfn <= 4'd0; cfh <= 3'd0; cft <= 3'd0; cfn <= 4'd0; hb <= 1'b0; t1_v <= 1'b0;
                to_last <= 1'b0; co_last <= !cand_en; tcred <= 3'd4; dcred <= 3'd4; pk_done <= 1'b0; pk_bad <= 1'b0;
            end
        end
endmodule
`default_nettype wire
