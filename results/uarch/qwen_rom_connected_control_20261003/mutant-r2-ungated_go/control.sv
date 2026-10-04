module issue_control #(parameter PART=2,LOCAL_KV_PREP=3)(input clk,rst_n,go,
input wire [17:0]i_nout,
input wire [17:0]i_tiles,
input wire [17:0]i_k,
input wire [0:0]i_wsrc,
input wire [23:0]i_wbase,
input wire [23:0]i_ts,
input wire [23:0]i_ks,
input wire [23:0]i_js,
input wire [23:0]i_xbase,
input wire [23:0]i_xks,
input wire [23:0]i_xjs,
input wire [23:0]i_xcs,
input wire [2:0]i_jsh,
input wire [3:0]i_split,
input wire [23:0]i_wcs,
input wire [0:0]i_round,
input wire [23:0]i_obase,
input wire [23:0]i_ots,
input wire [23:0]i_ojs,
input wire [0:0]i_mmode,
input wire [0:0]i_oen,
input wire [0:0]i_amax,
input wire [0:0]i_rmax,
input wire [23:0]i_mbase,output ready,output wire[6:0]state,output reg wrom_re,kv_re,output reg[23:0]wrom_addr);
localparam W=16,IL=8,AW=24,NW=18,GT=6144,PRUNE=1,SMIN=6,KV_PREP=LOCAL_KV_PREP,INT8_WEIGHT=1,INT8_SCALE_WCS_BASE=1;
    reg              active;
    assign active_o = active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or (G/S)*ts for KV ops
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;           // KV ops: the whole K (elements past it multiply +0)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    //: pruning: an op below the smallest split the pruned tree supports
    reg              split_fault;
    //: KV_PREP > 0: a KV-sourced op waits KV_PREP cycles after its go (ready low) for its per-group KV
    //: offsets, which leave the issue path as a pipelined multiply (see g_kv_addr)
    reg              pend;
    reg [3:0]        pcnt;

assign ready=!active&&!pend;
assign state={active,pend,pcnt,split_fault};
generate begin:g_issue_fast

    //: FAST_ISSUE (1.2 GHz @ SS): the same schedule, cycle for cycle (plus KV_PREP on KV ops).
    //: (1) The per-op products (the round steps ts*(GT/S), ots*(GT/S), (GT/S)*W*IL, (GT/S)*W and the KV
    //:     K-step count ceil(K/S)) are first needed at the first K or round boundary, IL >= 3 cycles after
    //:     the go: they are two register stages computed from the latched fields, not an input-to-register
    //:     multiply; ts*(GT/S) is shifted adds of ts (GT's set bits), not a multiplier.
    //: (2) Every loop add is ot_qwen_w12_kadd: a Kogge-Stone prefix adder whose levels are kept netlist
    //:     boundaries (ABC re-maps a flattened `+` as a MAJ ripple: 22 cells, -656 ps at SS on `cur`).
    localparam integer PRW = $clog2(GT) + 1;
    //: x * (GT >> s), exactly, as the sum of x shifted to each set bit b >= s of the constant GT (two terms at
    //: 6,144): no multiplier
    function automatic [AW+PRW-1:0] mul_gt_shr(input [AW-1:0] x, input [3:0] sh);
        integer b;
        reg [AW+PRW-1:0] acc;
        begin
            acc = 0;
            for (b = 0; b < PRW; b = b + 1)
                if (((GT >> b) & 1) != 0 && b >= sh) acc = acc + ({{PRW{1'b0}}, x} << (b - sh));
            mul_gt_shr = acc;
        end
    endfunction
    reg [PRW-1:0]    pr_a;                 // GT >> split
    reg [AW+PRW-1:0] tsg_a, otsg_a;        // ts*(GT>>S), ots*(GT>>S)
    reg [NW-1:0]     kc_a;
    localparam [NW:0]   WNB = W;
    localparam [NW-1:0] ONE = 1, TWO = 2;
    //: three stages (the first use is IL >= 3 cycles after the go): the shifted terms, their kept sum, the result
    localparam integer NB_GT = PRW;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
        end
        pr_a <= GT >> split_r;
        kpad_a <= {1'b0, ktot_r} + ((1 << split_r) - 1);
    end
    wire [AW+PRW-1:0] tsum, osum;
    wire [NB_GT*(AW+PRW)-1:0] tsh_flat, osh_flat;
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_ts (.rows(tsh_flat), .s(tsum));
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_os (.rows(osh_flat), .s(osum));
    genvar tb;
    for (tb = 0; tb < NB_GT; tb = tb + 1) begin : g_fl
        assign tsh_flat[tb*(AW+PRW) +: AW+PRW] = tsh[tb];
        assign osh_flat[tb*(AW+PRW) +: AW+PRW] = osh[tb];
    end
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        kc_a <= wsrc_r ? kpad_a[NW-1:0] >> split_r : ktot_r;       // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];
        ot_step <= otsg_a[AW-1:0];
        nb_step <= pr_a * (W * IL);
        lb_step <= pr_a * W;
        k_r <= kc_a;
    end
    //: loop adds
    wire [AW-1:0] cur_js, oa_j, xc_j, bk_k, xk_k, bt_t, ot_t;
    wire [NW:0]   nb_j, nbt_t, lb_t;
    wire [NW-1:0] k_1, k_2, t_1, t_2;
    ot_qwen_w12_kadd #(.W(AW)) u_a0 (.a(cur), .b(js_r), .s(cur_js));
    ot_qwen_w12_kadd #(.W(AW)) u_a1 (.a(oa), .b(ojs_r), .s(oa_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a2 (.a(xc), .b(xjs_r), .s(xc_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a3 (.a(base_k), .b(ks_r), .s(bk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a4 (.a(xk), .b(xks_r), .s(xk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a5 (.a(base_t), .b(tstep_r), .s(bt_t));
    ot_qwen_w12_kadd #(.W(AW)) u_a6 (.a(ot), .b(ot_step), .s(ot_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a7 (.a(nb), .b(WNB), .s(nb_j));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a8 (.a(nb_t), .b(nb_step), .s(nbt_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a9 (.a(lb), .b(lb_step), .s(lb_t));
    ot_qwen_w12_kadd #(.W(NW)) u_a10 (.a(k), .b(ONE), .s(k_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a11 (.a(k), .b(TWO), .s(k_2));
    ot_qwen_w12_kadd #(.W(NW)) u_a12 (.a(t), .b(ONE), .s(t_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a13 (.a(t), .b(TWO), .s(t_2));
    //: the go's own first-boundary flags, without the K-step divide: ceil(K/S) == 1 <=> K <= S
    wire kc_is_1 = i_wsrc ? ({{(32-NW){1'b0}}, i_k} <= (32'd1 << i_split)) : (i_k == 1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (pend) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
            else pcnt <= pcnt - 1'b1;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                else active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= kc_is_1;
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
                lb <= 0;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa_j; nb <= nb_j; xc <= xc_j;
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur_js;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k_1; k_last <= (k_2 == k_r);
                    base_k <= bk_k; cur <= bk_k;
                    xk <= xk_k; xc <= xk_k;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t_1; t_last <= (t_2 == tiles_r);
                        base_t <= bt_t; base_k <= bt_t; cur <= bt_t;
                        ot <= ot_t; oa <= ot_t;
                        nb_t <= nbt_t; nb <= nbt_t; lb <= lb_t;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end endgenerate
endmodule
module source_boundary(input clk,rst_n,go,ready,input[127:0]xl,
input wire [17:0] i_nout,
input wire [17:0] i_tiles,
input wire [17:0] i_k,
input wire [0:0] i_wsrc,
input wire [23:0] i_wbase,
input wire [23:0] i_ts,
input wire [23:0] i_ks,
input wire [23:0] i_js,
input wire [23:0] i_xbase,
input wire [23:0] i_xks,
input wire [23:0] i_xjs,
input wire [23:0] i_xcs,
input wire [2:0] i_jsh,
input wire [3:0] i_split,
input wire [23:0] i_wcs,
input wire [0:0] i_round,
input wire [23:0] i_obase,
input wire [23:0] i_ots,
input wire [23:0] i_ojs,
input wire [0:0] i_mmode,
input wire [0:0] i_oen,
input wire [0:0] i_amax,
input wire [0:0] i_rmax,
input wire [23:0] i_mbase,output reg go_q,output reg[378:0]ib_q,output reg[127:0]xl_q);
localparam NW=18,AW=24,IBW=379,BD=1,IREG=1;
wire[378:0]tb;wire tgo;
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go), .q(tgo));

wire ib_go=tgo;
wire[378:0]tile_ib=tb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_q <= 1'b0;
        else go_q <= ib_go;
    end
    always @(posedge clk) begin ib_q <= tile_ib; xl_q <= xl; end

endmodule
module lockstep(input clk,rst_n,go,input[378:0]ib,input[127:0]xl);
wire ready,tre,go_q;wire[378:0]ib_q;wire[127:0]xl_q;
wire[6:0]root_state,tile_state;wire rr,kr,tr,tk;wire[23:0]ra,ta;
issue_control #(.PART(2)) root(.clk(clk),.rst_n(rst_n),.go(go),.i_nout(ib[378 -: 18]),.i_tiles(ib[360 -: 18]),.i_k(ib[342 -: 18]),.i_wsrc(ib[324 -: 1]),.i_wbase(ib[323 -: 24]),.i_ts(ib[299 -: 24]),.i_ks(ib[275 -: 24]),.i_js(ib[251 -: 24]),.i_xbase(ib[227 -: 24]),.i_xks(ib[203 -: 24]),.i_xjs(ib[179 -: 24]),.i_xcs(ib[155 -: 24]),.i_jsh(ib[131 -: 3]),.i_split(ib[128 -: 4]),.i_wcs(ib[124 -: 24]),.i_round(ib[100 -: 1]),.i_obase(ib[99 -: 24]),.i_ots(ib[75 -: 24]),.i_ojs(ib[51 -: 24]),.i_mmode(ib[27 -: 1]),.i_oen(ib[26 -: 1]),.i_amax(ib[25 -: 1]),.i_rmax(ib[24 -: 1]),.i_mbase(ib[23 -: 24]),.ready(ready),.state(root_state),.wrom_re(rr),.kv_re(kr),.wrom_addr(ra));
source_boundary broadcast(.clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.xl(xl),.i_nout(ib[378 -: 18]),.i_tiles(ib[360 -: 18]),.i_k(ib[342 -: 18]),.i_wsrc(ib[324 -: 1]),.i_wbase(ib[323 -: 24]),.i_ts(ib[299 -: 24]),.i_ks(ib[275 -: 24]),.i_js(ib[251 -: 24]),.i_xbase(ib[227 -: 24]),.i_xks(ib[203 -: 24]),.i_xjs(ib[179 -: 24]),.i_xcs(ib[155 -: 24]),.i_jsh(ib[131 -: 3]),.i_split(ib[128 -: 4]),.i_wcs(ib[124 -: 24]),.i_round(ib[100 -: 1]),.i_obase(ib[99 -: 24]),.i_ots(ib[75 -: 24]),.i_ojs(ib[51 -: 24]),.i_mmode(ib[27 -: 1]),.i_oen(ib[26 -: 1]),.i_amax(ib[25 -: 1]),.i_rmax(ib[24 -: 1]),.i_mbase(ib[23 -: 24]),.go_q(go_q),.ib_q(ib_q),.xl_q(xl_q));
issue_control #(.PART(1),.LOCAL_KV_PREP(3)) tile(.clk(clk),.rst_n(rst_n),.go(go_q),.i_nout(ib_q[378 -: 18]),.i_tiles(ib_q[360 -: 18]),.i_k(ib_q[342 -: 18]),.i_wsrc(ib_q[324 -: 1]),.i_wbase(ib_q[323 -: 24]),.i_ts(ib_q[299 -: 24]),.i_ks(ib_q[275 -: 24]),.i_js(ib_q[251 -: 24]),.i_xbase(ib_q[227 -: 24]),.i_xks(ib_q[203 -: 24]),.i_xjs(ib_q[179 -: 24]),.i_xcs(ib_q[155 -: 24]),.i_jsh(ib_q[131 -: 3]),.i_split(ib_q[128 -: 4]),.i_wcs(ib_q[124 -: 24]),.i_round(ib_q[100 -: 1]),.i_obase(ib_q[99 -: 24]),.i_ots(ib_q[75 -: 24]),.i_ojs(ib_q[51 -: 24]),.i_mmode(ib_q[27 -: 1]),.i_oen(ib_q[26 -: 1]),.i_amax(ib_q[25 -: 1]),.i_rmax(ib_q[24 -: 1]),.i_mbase(ib_q[23 -: 24]),.ready(tre),.state(tile_state),.wrom_re(tr),.kv_re(tk),.wrom_addr(ta));
endmodule
