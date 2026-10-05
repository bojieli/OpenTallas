`timescale 1ns/1ps
// Blocking V4.1 collective DMA. Addresses and n here are VM words; the die
// checks the ISA's element alignment and shifts by four before issuing.
// COLL_TOPK_MERGE (topk = 1, TOPK > 0): ONE all-gather of 2n words per rank --
// the n score words at src, then the n local-id words at ibase -- whose
// gathered stream loads ot_coll_topk_merge instead of VM; the unit's k global
// ids (rank * stride + local id, ascending) are then written to dst on every
// rank, ceil(k / LANES) words (GW = 4: dst must be 4-word aligned, one bank a
// lane).
module ot_w15_coll_dma_related_vm #(
    parameter integer VM_RESPONSE_WAIT=0, VISIBLE_COMPLETION=0, TOPK_OUTPUT_QUEUE=0,
    parameter integer WA = 12,
    parameter integer FW = 512,
    parameter integer TAGW = 32,
    parameter integer N = 4,
    parameter integer GW = 1,
    parameter integer VM_ALWAYS_READY = 0,
    parameter integer TOPK = 0,               // 1: COLL_TOPK_MERGE support (ot_coll_topk_merge)
    parameter integer TK_NMAX = 2048,         // candidates per rank (max)
    parameter integer TK_DIG = 8,
    parameter integer RB = (N > 1) ? $clog2(N) : 1
) (
    input wire clk, rst_n,
    input wire vm_req_ready, vm_reply_valid,
    input wire [WA-1:0] vm_reply_cookie,
    output wire [WA-1:0] vm_request_cookie,
    output wire vm_reply_ready,
    input wire vm_write_visible, vm_write_pending,
    input wire go, mode, rnd,
    input wire [TAGW-1:0] tag,
    input wire [WA-1:0] src, n, dst,
    input wire topk,                          // with mode = 1: COLL_TOPK_MERGE
    input wire [WA-1:0] ibase,
    input wire [15:0] tk_k,                   // ids wanted (elements)
    input wire [31:0] tk_stride,
    output reg busy, fault,
    output reg [31:0] words_out, words_in,
    output wire vm_re,
    output wire [WA-1:0] vm_raddr,
    input wire [FW-1:0] vm_rq,
    output wire vm_we,
    output wire [WA-1:0] vm_waddr,
    output wire [FW-1:0] vm_wdata,
    // Four-bank full-shape write port. GW=1 mirrors the scalar port in lane 0.
    input wire vm_ready4,
    output wire [3:0] vm_we4,
    output wire [4*WA-1:0] vm_waddr4,
    output wire [4*FW-1:0] vm_wdata4,
    output wire e_valid,
    input wire e_ready,
    output wire [FW-1:0] e_data,
    output wire e_last,
    output reg e_mode,
    output reg [TAGW-1:0] e_tag,
    input wire o_valid,
    output wire o_ready,
    input wire [GW*FW-1:0] o_data,
    input wire o_last,
    input wire [RB-1:0] o_rank,
    input wire o_err, engine_fault
);
    localparam integer LANES = FW / 32;
    localparam integer TKW = (TOPK != 0) ? GW : 1;
    localparam integer CW = WA + 3;
    localparam [CW-1:0] N_C = CW'(N);
    reg [WA-1:0] rd_k, n_r, src_r, dst_r;
    reg [WA+2:0] wr_k;
    reg rnd_r, rd_q;
    reg [WA-1:0] rd_qk;
    reg [FW-1:0] sk_d [0:1];
    reg sk_l [0:1], sk_h;
    reg [1:0] sk_n;
    reg [1:0] commit_wait;
    reg [WA-1:0] reply_cookie_r;
    reg finish_pending, write_debt;
    wire read_accept = vm_re && (VM_RESPONSE_WAIT == 0 || vm_req_ready);
    assign vm_request_cookie = vm_raddr;
    assign vm_reply_ready = VM_RESPONSE_WAIT != 0 && rst_n && !fault && rd_q &&
                            vm_reply_cookie == reply_cookie_r && sk_n < 2;
    wire read_complete = VM_RESPONSE_WAIT != 0 ? vm_reply_valid && vm_reply_ready : rd_q;
    wire native_write_accept = rst_n && (|vm_we4) && vm_ready4;
    // Reserve the entire retained legal K=N*TK_NMAX, even when K512 uses8 packets.
    localparam integer TQ_DEPTH = (N*TK_NMAX + TKW*LANES-1)/(TKW*LANES);
    localparam integer TQP = TQ_DEPTH > 1 ? $clog2(TQ_DEPTH) : 1;
    localparam integer TQC = $clog2(TQ_DEPTH+1);
    localparam integer TQB = 4+4*WA+4*FW;
    reg [TQB-1:0] topk_packet [0:TQ_DEPTH-1];
    reg [TQP-1:0] tq_head,tq_tail;
    reg [TQC-1:0] tq_count;
    wire tq_pop = TOPK_OUTPUT_QUEUE != 0 && tq_count != 0 && vm_ready4 && !fault && rst_n;
    wire [TQB-1:0] tq_front = topk_packet[tq_head];
    wire [3:0] tq_we = tq_count != 0 ? tq_front[TQB-1 -: 4] : 4'b0;
    wire [4*WA-1:0] tq_addr = tq_front[4*FW +: 4*WA];
    wire [4*FW-1:0] tq_data = tq_front[0+:4*FW];
    wire pop = e_valid && e_ready;
    wire [2:0] held = {1'b0, sk_n} + {2'b0, rd_q} - {2'b0, pop};
    wire [CW-1:0] limit = (CW'(1) << WA);
    wire [CW-1:0] src_start = CW'(src), dst_start = CW'(dst), n_ext = CW'(n);
    wire [CW-1:0] src_end = src_start + n_ext;
    wire [CW-1:0] dst_end = dst_start + (mode ? (n_ext * N_C) : n_ext);
    wire [CW-1:0] tk_words = CW'((32'(tk_k) + LANES - 1) / LANES);
    wire [CW-1:0] ib_start = CW'(ibase), ib_end = ib_start + n_ext;
    wire tk_bad = (TOPK == 0) || !mode || (tk_k == 0) || (32'(tk_k) > 32'(n) * LANES * N) ||
                  (32'(n) * LANES > TK_NMAX) || ((GW == 4) && (dst[1:0] != 0)) || (ib_end > limit) ||
                  (dst_start + tk_words > limit) ||
                  ((ib_start < dst_start + tk_words) && (dst_start < ib_end));
    wire bad_command = topk ? ((n == 0) || (src_end > limit) || tk_bad ||
                               ((src_start < dst_start + tk_words) && (dst_start < src_end)))
                            : ((n == 0) || (src_end > limit) || (dst_end > limit) ||
                               ((src_start < dst_end) && (dst_start < src_end)));
    reg tk_r, tk_go, tk_sel;
    reg [WA-1:0] ib_r, nh_r;
    reg [15:0] tk_k_r;
    reg [31:0] tk_stride_r;
    reg [CW-1:0] tk_oidx;
    assign vm_re = busy && !fault && !tk_sel && rd_k != n_r && held < 3'd2 && (VM_RESPONSE_WAIT == 0 || !rd_q) && rst_n;
    assign vm_raddr = (tk_r && rd_k >= nh_r) ? ib_r + (rd_k - nh_r) : src_r + rd_k;
    assign e_valid = sk_n != 0 && !fault;
    assign e_data = sk_d[sk_h];
    assign e_last = sk_l[sk_h];
    wire [CW-1:0] gather_addr = CW'(dst_r) + (CW'(n_r) * CW'(o_rank)) + (wr_k / N_C);
    wire tk_ov, tk_ol, tk_done, tk_fault;
    wire [$clog2(TKW+1)-1:0] tk_nw;
    wire [TKW*FW-1:0] tk_od;
    wire gvm_we = busy && !tk_r && o_valid && (!e_mode || GW == 1) &&
                  !fault && !o_err && !engine_fault;
    wire tk_ld = busy && tk_r && !tk_sel && o_valid && !fault && !o_err && !engine_fault;
    assign vm_we = gvm_we || (GW == 1 && (TOPK_OUTPUT_QUEUE != 0 ? tq_we[0] : tk_ov));
    assign vm_waddr = tk_r ? (TOPK_OUTPUT_QUEUE != 0 ? tq_addr[0+:WA] : dst_r + tk_oidx[WA-1:0]) : (e_mode ? gather_addr[WA-1:0] : dst_r + wr_k[WA-1:0]);

    function automatic [31:0] bf16_rne(input [31:0] x);
        reg [32:0] tmp;
        begin
            tmp = {1'b0, x} + 33'h000007fff + 33'(x[16]);
            bf16_rne = {tmp[31:16], 16'h0000};
            if (x[30:0] == 0) bf16_rne = 32'h00000000;
        end
    endfunction
    genvar lane;
    generate for (lane = 0; lane < LANES; lane = lane + 1) begin : g_round
        assign vm_wdata[32*lane +: 32] =
            tk_r ? (TOPK_OUTPUT_QUEUE != 0 ? tq_data[32*lane +: 32] : tk_od[32*lane +: 32]) :
            (!e_mode && rnd_r) ? bf16_rne(o_data[32*lane +: 32]) :
                                 o_data[32*lane +: 32];
    end endgenerate

    wire tr_ready, tr_done, tr_fault;
    wire [3:0] tr_we;
    wire [4*WA-1:0] tr_addr;
    wire [4*FW-1:0] tr_data;
    wire tr_valid, tr_last;
    generate if (GW == 4) begin : g_transpose
        ot_chip_v41x_coll_transpose_related_vm #(.WA(WA), .FW(FW), .OUT_PIPE(VM_ALWAYS_READY), .ELASTIC_PIPE(VISIBLE_COMPLETION)) u_tr (
            .clk(clk), .rst_n(rst_n),
            .start(go && !busy && mode && !topk && !bad_command && !fault),
            .dst(dst), .n(n),
            .in_ready(tr_ready), .in_valid(busy && e_mode && o_valid && !fault && !o_err && !engine_fault),
            .in_data(o_data), .in_last(o_last),
            .out_ready(vm_ready4), .out_valid(tr_valid), .out_we(tr_we),
            .out_addr(tr_addr), .out_data(tr_data), .out_last(tr_last),
            .done(tr_done), .fault(tr_fault));
    end else begin : g_scalar
        assign tr_ready = 1'b1;
        assign tr_done = 1'b0;
        assign tr_fault = 1'b0;
        assign tr_we = 4'b0;
        assign tr_addr = {4*WA{1'b0}};
        assign tr_data = {4*FW{1'b0}};
        assign tr_valid = 1'b0;
        assign tr_last = 1'b0;
    end endgenerate
    // ---- COLL_TOPK_MERGE select unit -------------------------------------------------------------------
    wire [CW-1:0] tk_wi = wr_k / N_C;                    // gathered word index (the same for every rank)
    generate if (TOPK != 0) begin : g_topk
        localparam integer TCB = $clog2(N * TK_NMAX + 1);
        ot_coll_topk_merge #(.N(N), .NMAX(TK_NMAX), .LW(LANES), .LDW(GW == 4 ? N : 1), .P(TKW * LANES),
                             .DIG(TK_DIG)) u_tk (
            .clk(clk), .rst_n(rst_n),
            .ld_valid(tk_ld), .ld_id(tk_wi >= CW'(nh_r)), .ld_rank(o_rank),
            .ld_word($clog2(N * TK_NMAX / LANES)'(tk_wi >= CW'(nh_r) ? tk_wi - CW'(nh_r) : tk_wi)),
            .ld_data(o_data[(GW == 4 ? N : 1)*FW-1:0]),
            .go(tk_go), .n(TCB'(32'(nh_r) * LANES)), .k(TCB'(tk_k_r)), .stride(tk_stride_r),
            .busy(), .done(tk_done), .fault(tk_fault),
            .out_valid(tk_ov), .out_nw(tk_nw), .out_data(tk_od), .out_last(tk_ol), .stat_cycles());
    end else begin : g_notopk
        assign tk_ov = 1'b0; assign tk_ol = 1'b0; assign tk_done = 1'b0; assign tk_fault = 1'b0;
        assign tk_nw = 0; assign tk_od = {TKW*FW{1'b0}};
    end endgenerate
    reg [3:0] tk_we;
    reg [4*WA-1:0] tk_wa;
    integer tj;
    always @(*) begin
        tk_we = 4'b0; tk_wa = {4*WA{1'b0}};
        for (tj = 0; tj < 4; tj = tj + 1) begin
            tk_we[tj] = (GW == 4) && tk_ov && (tj < tk_nw);
            tk_wa[tj*WA +: WA] = dst_r + tk_oidx[WA-1:0] + WA'(tj);
        end
    end
    assign o_ready = (GW == 4 && e_mode && !tk_r) ? tr_ready :
                     (VISIBLE_COMPLETION != 0 && !tk_r ? vm_ready4 : 1'b1);
    assign vm_we4 = (GW == 4 && tk_r) ? (TOPK_OUTPUT_QUEUE != 0 ? tq_we : tk_we) : (GW == 4 && e_mode) ? tr_we : {3'b000, vm_we};
    assign vm_waddr4 = (GW == 4 && tk_r) ? (TOPK_OUTPUT_QUEUE != 0 ? tq_addr : tk_wa) : (GW == 4 && e_mode) ? tr_addr : {{3*WA{1'b0}}, vm_waddr};
    assign vm_wdata4 = (GW == 4 && tk_r) ? (TOPK_OUTPUT_QUEUE != 0 ? tq_data : {{(4-TKW)*FW{1'b0}}, tk_od}) :
                       (GW == 4 && e_mode) ? tr_data : {{3*FW{1'b0}}, vm_wdata};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; fault <= 0; rd_k <= 0; n_r <= 0; src_r <= 0;
            dst_r <= 0; wr_k <= 0; rnd_r <= 0; rd_q <= 0; rd_qk <= 0;
            sk_n <= 0; sk_h <= 0; e_mode <= 0; e_tag <= 0;
            commit_wait <= 0; reply_cookie_r<=0; finish_pending<=0; write_debt<=0;
            tq_head<=0;tq_tail<=0;tq_count<=0;
            words_out <= 0; words_in <= 0;
            tk_r <= 0; tk_go <= 0; tk_sel <= 0; ib_r <= 0; nh_r <= 0; tk_k_r <= 0; tk_stride_r <= 0; tk_oidx <= 0;
            sk_d[0] <= 0; sk_d[1] <= 0; sk_l[0] <= 0; sk_l[1] <= 0;
        end else begin
            tk_go <= 0;
            if (native_write_accept) write_debt<=1;
            if (vm_write_visible && VISIBLE_COMPLETION != 0) begin
                if (!write_debt) fault<=1;
                else write_debt<=0;
            end
            if (VM_RESPONSE_WAIT != 0 && vm_reply_valid && rd_q && vm_reply_cookie!=reply_cookie_r) fault<=1;
            if (TOPK_OUTPUT_QUEUE != 0) begin
                if (tk_ov) begin
                    if (tq_count==TQC'(TQ_DEPTH) && !tq_pop) fault<=1;
                    else begin
                        topk_packet[tq_tail]<={GW==4 ? tk_we : {3'b0,tk_ov},
                            GW==4 ? tk_wa : {{3*WA{1'b0}},dst_r+tk_oidx[WA-1:0]},
                            {{(4-TKW)*FW{1'b0}},tk_od}};
                        tq_tail<=tq_tail==TQP'(TQ_DEPTH-1) ? 0 : tq_tail+1'b1;
                    end
                end
                if (tq_pop)tq_head<=tq_head==TQP'(TQ_DEPTH-1) ? 0 : tq_head+1'b1;
                case ({tk_ov,tq_pop})
                    2'b10:if(tq_count!=TQC'(TQ_DEPTH))tq_count<=tq_count+1'b1;
                    2'b01:tq_count<=tq_count-1'b1;
                    default:;
                endcase
            end
            if (VISIBLE_COMPLETION != 0 && busy && finish_pending && !fault &&
                !write_debt && !vm_write_pending && !(|vm_we4) && tq_count==0 &&
                !rd_q && sk_n==0 && rd_k==n_r) begin
                busy<=0;tk_r<=0;tk_sel<=0;finish_pending<=0;
            end
            if (o_err || engine_fault || tr_fault || tk_fault || (go && busy)) fault <= 1;
            if (go && !busy) begin
                if (bad_command || fault) fault <= 1;
                else begin
                    busy <= 1; rd_k <= 0; n_r <= topk ? n << 1 : n; src_r <= src;
                    tk_r <= topk; tk_sel <= 0; ib_r <= ibase; nh_r <= n; tk_k_r <= tk_k;
                    tk_stride_r <= tk_stride; tk_oidx <= 0;
                    dst_r <= dst; wr_k <= 0; rnd_r <= rnd;
                    rd_q <= 0; sk_n <= 0; sk_h <= 0;
                    e_mode <= mode; e_tag <= tag;
                    commit_wait <= 0; finish_pending<=0; write_debt<=0;
                    tq_head<=0;tq_tail<=0;tq_count<=0;
                end
            end else if (busy) begin
                if (VM_RESPONSE_WAIT == 0) begin rd_q<=vm_re;rd_qk<=rd_k;end
                else begin
                    if(read_accept)begin rd_q<=1;rd_qk<=rd_k;reply_cookie_r<=vm_raddr;end
                    if(read_complete)rd_q<=0;
                end
                if (read_accept) rd_k <= rd_k + 1'b1;
                if (read_complete) begin
                    sk_d[sk_h ^ sk_n[0]] <= vm_rq;
                    sk_l[sk_h ^ sk_n[0]] <= (rd_qk == n_r - 1'b1);
                end
                if (pop) begin sk_h <= ~sk_h; words_out <= words_out + 1; end
                sk_n <= sk_n + {1'b0, read_complete} - {1'b0, pop};
                commit_wait <= {commit_wait[0], tr_done};
                if (GW == 4 && e_mode && commit_wait[1]) begin
                    if(VISIBLE_COMPLETION != 0)finish_pending<=1;else busy<=0;end
                // COLL_TOPK_MERGE: the gather's last word starts the select; its words go to dst; done ends
                if (tk_r) begin
                    if (GW == 1 && tk_ld) begin
                        wr_k <= wr_k + 1'b1; words_in <= words_in + 1;
                        if (integer'(o_rank) >= N) fault <= 1;
                        if (o_last && wr_k != CW'(n_r) * N_C - CW'(1)) fault <= 1;
                    end
                    if (tk_ld && o_last) begin tk_sel <= 1; tk_go <= 1; end
                    if (tk_ov) tk_oidx <= tk_oidx + CW'(tk_nw);
                    if (tk_done) begin
                        if(VISIBLE_COMPLETION != 0)finish_pending<=1;
                        else begin busy<=0;tk_r<=0;tk_sel<=0;end
                    end
                end
                if (GW == 4 && e_mode && o_valid && o_ready && !fault && !o_err && !engine_fault) begin
                    wr_k <= wr_k + CW'(N);
                    words_in <= words_in + 32'(N);
                    if (o_rank != 0) fault <= 1;
                    if (o_last && wr_k != CW'(n_r) * N_C - N_C) fault <= 1;
                end
                if (vm_we && !tk_r && (VISIBLE_COMPLETION == 0 || vm_ready4)) begin
                    wr_k <= wr_k + 1'b1;
                    words_in <= words_in + 1;
                    if (e_mode && integer'(o_rank) >= N) fault <= 1;
                    if (o_last) begin
                        if (wr_k != (e_mode ? (CW'(n_r) * N_C - CW'(1)) : (CW'(n_r) - CW'(1))))
                            fault <= 1;
                        if(VISIBLE_COMPLETION != 0)finish_pending<=1;else busy<=0;
                    end
                end
            end
        end
    end
endmodule
