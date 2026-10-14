`timescale 1ns/1ps
`default_nettype none
// Distinct opt-in leaf: unchanged real SRAM/write path, no completion feedback.
module ot_hgi_qdq_wr_pay #(
    parameter integer LQ  = 10,
    parameter integer OD  = 64,
    parameter integer RQ  = 16,
    parameter integer EMPTY_BYPASS = 0 // opt-in registered input result bypass
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              m_v,
    input  wire [18:0]       m,           // {O sector 15, sectors 3, last}
    input  wire              i_bad,
    input  wire              vo,
    input  wire              qfault,
    input  wire              dfault,
    input  wire [511:0]      y,
    output reg  [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    output wire              wg_req,
    input  wire              wg_gnt,
    input  wire              i_act,
    output reg               o_wf,
    output reg               snapshot_v,
    output reg [63:0]        snapshot,
    output reg               o_bad,
    output reg               o_idle
);
    localparam integer QW = $clog2(RQ), OW = $clog2(OD), CW = $clog2(LQ + 1);
    reg f_rst, f_wg; reg [7:0] f_wcr; reg [18:0] f_m; reg [511:0] y_f; reg qf_f;
    always @(posedge clk) begin
        f_rst <= rst_n; f_wg <= wg_gnt; f_wcr <= wwq_cr; f_m <= m; y_f <= y; qf_f <= qfault;
    end
    wire [2:0] rr_n;                                  // 0 control, 1 result FIFO, 2 lanes
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    reg f_m_v, vo_f, df_f, f_act, f_bi;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin f_m_v <= 0; vo_f <= 0; df_f <= 0; f_act <= 0; f_bi <= 0; end
        else begin f_m_v <= m_v; vo_f <= vo; df_f <= dfault; f_act <= i_act; f_bi <= i_bad; end
    assign wg_req = f_act;
    // fired-beat queue (one entry a beat in the decode or the result FIFO)
    reg [14:0] mq_o [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg mq_z [0:OD-1];
    reg [OW-1:0] mq_t, mq_h; reg [OW:0] infl;         // infl: fired beats not yet out of the decode
    wire od_hv, od_ovf; wire [511:0] od_head;
    reg bad, wg_ok;
    reg [CW-1:0] wcr [0:7]; reg [7:0] wcnt [0:7];
    // head entry in registers (q8b gate, 10-13: the 64:1 head read sat in front of hit -> credit -> fire -> credit update,
    // 15 levels): both candidates (head, head + 1) are read from the registered pointer and the fire selects one.  An
    // entry is written >= 20 cycles (decode latency) before its result can fire, so the one-edge-late copy is always current.
    reg [14:0] mh_o; reg [2:0] mh_n; reg mh_z;
    wire [OW-1:0] mq_h1 = mq_h + 1'b1;
    // q8e: independent head reads stay in parallel with the fire cone. Keeping the
    // read outputs prevents synthesis from moving fire in front of the 64:1 mux.
    (* keep = 1 *) wire [18:0] mq_head0 = {mq_o[mq_h], mq_n[mq_h], mq_z[mq_h]};
    (* keep = 1 *) wire [18:0] mq_head1 = {mq_o[mq_h1], mq_n[mq_h1], mq_z[mq_h1]};
    wire [14:0] w_sec0 = mh_o; wire [2:0] w_n = mh_n;
    reg [7:0] w_hit; reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            w_hit[b] = 3'(b - w_sec0[2:0]) < w_n;
            if (w_hit[b] && wcr[b] == 0) w_cr_ok = 1'b0;
        end
    end
    wire result_empty,tracker_bad;
    wire bypass_eligible=(EMPTY_BYPASS!=0)&&result_empty&&!od_hv&&vo_f&&!qf_f&&!df_f&&!f_bi&&!od_ovf;
    wire w_fire = wg_ok && !bad && !tracker_bad && (od_hv||bypass_eligible) && w_cr_ok;
    wire bypass_fire=w_fire&&!od_hv&&bypass_eligible;
    wire [511:0] result_head=(EMPTY_BYPASS!=0)&&!od_hv?y_f:od_head;
    generate if(EMPTY_BYPASS!=0)begin:g_result_tracker
        // Accepted registered VO minus actual WWQ launches counts every SRAM,
        // prefetch-head and read-pending obligation. Complement rails refuse a
        // shortcut if mutable tracking state disagrees; no raw VO/Y bypass.
        (* keep="true",dont_touch="true" *) reg [OW:0] outstanding,outstanding_n;
        wire [OW:0] next_outstanding=outstanding+(OW+1)'(vo_f)-(OW+1)'(w_fire);
        assign tracker_bad=outstanding!=~outstanding_n;
        assign result_empty=(outstanding==0)&&!tracker_bad;
        always @(posedge clk or negedge rr_n[0])
            if(!rr_n[0])begin outstanding<=0;outstanding_n<='1;end
            else begin outstanding<=next_outstanding;outstanding_n<=~next_outstanding;end
`ifndef SYNTHESIS
        always @(negedge clk)if(rr_n[0]&&rr_n[1]&&!tracker_bad)begin
            if(outstanding !== u_od.in_arr+u_od.oc+u_od.inflight)
                $fatal(1,"PAY outstanding tracker does not equal real SRAM/head/read-pending obligations");
            if(bypass_fire&&(u_od.in_arr!=0||u_od.oc!=0||u_od.inflight))
                $fatal(1,"PAY bypass with stored result obligation");
        end
`endif
    end else begin:g_no_result_tracker
        assign result_empty=1'b0;assign tracker_bad=1'b0;
    end endgenerate
    ot_fifo_sram_fwft #(.W(512), .DEPTH(OD), .MACRO(0), .ESL(128)) u_od (.clk(clk), .rst_n(rr_n[1]), .push(vo_f&&!bypass_fire),
        .wdata(y_f), .pop(w_fire), .hv(od_hv), .head(od_head), .ovf(od_ovf));
    wire snapshot_push = w_fire && mh_z;
    wire [63:0] snapshot_counts;
    for(genvar q=0;q<8;q=q+1)begin:g_snapshot
        assign snapshot_counts[q*8+:8]=wcnt[q]+8'(w_hit[q]);
    end
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            mq_t <= 0; mq_h <= 0; infl <= 0; bad <= 0; wg_ok <= 0; o_wf <= 0; snapshot_v <= 0; o_bad <= 0; o_idle <= 0;
        end else begin
            wg_ok <= f_act && f_wg;
            if (f_m_v) mq_t <= mq_t + 1'b1;
            if (w_fire) mq_h <= mq_h + 1'b1;
            infl <= infl + (OW+1)'(f_m_v) - (OW+1)'(vo_f);
            if ((vo_f && qf_f) || df_f || od_ovf || f_bi || tracker_bad) bad <= 1'b1;
            if ((vo_f && qf_f) || df_f || od_ovf || tracker_bad) o_bad <= 1'b1;
            o_wf <= w_fire; snapshot_v <= snapshot_push;
            o_idle <= infl == 0 && !f_m_v;
        end
    end
    always @(posedge clk or negedge rr_n[2]) begin
        if (!rr_n[2]) begin
            for (integer b = 0; b < 8; b = b + 1) begin wwq[b*280 + 279] <= 1'b0; wcr[b] <= LQ[CW-1:0]; wcnt[b] <= 0; end
        end else begin
            for (integer b = 0; b < 8; b = b + 1) begin : lanes
                reg wr; wr = w_fire && w_hit[b];
                wwq[b*280 + 279] <= wr;
                wcr[b] <= wcr[b] + CW'(f_wcr[b]) - CW'(wr);
                wcnt[b] <= wcnt[b] + 8'(wr);
            end
        end
    end
    // Address/payload flops are written separately from resettable valid strobes (no ALDFF feedback on payload bits).
    always @(posedge clk) begin
        if (f_m_v) begin mq_o[mq_t] <= f_m[18:4]; mq_n[mq_t] <= f_m[3:1]; mq_z[mq_t] <= f_m[0]; end
        {mh_o, mh_n, mh_z} <= ({19{!w_fire}} & mq_head0) | ({19{w_fire}} & mq_head1);
        snapshot <= snapshot_counts; // first registered launch, same edge as WWQ
        for (integer b = 0; b < 8; b = b + 1) begin
            if (w_fire && w_hit[b]) begin
                reg [255:0] d; reg [1:0] s; reg [127:0] c; s = 2'(3'(b - w_sec0[2:0]));
                // decoded constant-index sector select (one-hot AND-OR, no runtime part-select)
                c = ({128{s == 2'd0}} & result_head[127:0]) | ({128{s == 2'd1}} & result_head[255:128]) |
                    ({128{s == 2'd2}} & result_head[383:256]) | ({128{s == 2'd3}} & result_head[511:384]);
                for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {c[k*16 +: 16], 16'd0};
                wwq[b*280 +: 279] <= {15'(w_sec0 + 15'(s)), d, 8'hff};
            end
        end
    end
    initial begin
        if ((OD & (OD - 1)) != 0 || (RQ & (RQ - 1)) != 0) $fatal(1, "ot_hgi_qdq_wr: OD / RQ powers of two");
        if (OD < 32) $fatal(1, "ot_hgi_qdq_wr: OD >= 32 (decode latency 26)");
    end
endmodule
`default_nettype wire
