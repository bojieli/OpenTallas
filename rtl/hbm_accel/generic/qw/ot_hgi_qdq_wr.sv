`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q WRITE child (q8b four-leaf partition, 2026-10-13; at the cluster N face under the wwq pins): result FIFO
// (one ot_sram_1r1w_64x512_m1_r2c2 macro behind a 2-entry registered prefetch buffer, ESL 128), write issue on the
// 8 slice write lanes, write credits / counts, and the per-record finish detection beside the done pins.
// Every port is a flop at the pin:
//   in : y / vo / qfault / dfault from the decode tiles (+1 cycle: y_f), m (a fired beat's {O sector, sectors, last}
//        from the assembly leaf), wwq_cr / wwq_done / wg_gnt face flops, i_act (core: a record is queued; this pin flop
//        IS the wg_req output flop), i_bad (assembly: lane overrun).
//   out: wwq, wg_req, o_wf (a result was written: result-FIFO space, to the assembly leaf), o_fin (one pulse a finished
//        record, in record order, to the core), sticky fault and idle to the core.
// Finish: at a record's last write the per-lane write counts are pushed into a snapshot FIFO (records are written in
// order); the head record is finished when every lane's done count has passed its snapshot.  The compare takes the
// done pin flops as look-ahead (dcnt + f_wdone), so o_fin is one edge after the last done's pin flop.
module ot_hgi_qdq_wr #(
    parameter integer LQ  = 10,
    parameter integer OD  = 64,
    parameter integer RQ  = 16
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
    input  wire [7:0]        wwq_done,
    output wire              wg_req,
    input  wire              wg_gnt,
    input  wire              i_act,
    output reg               o_wf,
    output reg               o_fin,
    output reg               o_bad,
    output reg               o_idle
);
    localparam integer QW = $clog2(RQ), OW = $clog2(OD), CW = $clog2(LQ + 1);
    reg f_rst, f_wg; reg [7:0] f_wcr, f_wdone; reg [18:0] f_m; reg [511:0] y_f; reg qf_f;
    always @(posedge clk) begin
        f_rst <= rst_n; f_wg <= wg_gnt; f_wcr <= wwq_cr; f_wdone <= wwq_done; f_m <= m; y_f <= y; qf_f <= qfault;
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
    reg [CW-1:0] wcr [0:7]; reg [7:0] wcnt [0:7], dcnt [0:7];
    // head entry in registers (q8b gate, 10-13: the 64:1 head read sat in front of hit -> credit -> fire -> credit update,
    // 15 levels): both candidates (head, head + 1) are read from the registered pointer and the fire selects one.  An
    // entry is written >= 20 cycles (decode latency) before its result can fire, so the one-edge-late copy is always current.
    reg [14:0] mh_o; reg [2:0] mh_n; reg mh_z;
    wire [OW-1:0] mq_h1 = mq_h + 1'b1;
    wire [14:0] w_sec0 = mh_o; wire [2:0] w_n = mh_n;
    reg [7:0] w_hit; reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer b = 0; b < 8; b = b + 1) begin
            w_hit[b] = 3'(b - w_sec0[2:0]) < w_n;
            if (w_hit[b] && wcr[b] == 0) w_cr_ok = 1'b0;
        end
    end
    wire w_fire = wg_ok && !bad && od_hv && w_cr_ok;
    ot_fifo_sram_fwft #(.W(512), .DEPTH(OD), .MACRO(0), .ESL(128)) u_od (.clk(clk), .rst_n(rr_n[1]), .push(vo_f),
        .wdata(y_f), .pop(w_fire), .hv(od_hv), .head(od_head), .ovf(od_ovf));
    // snapshot FIFO: per-lane write count after a record's last write, in record order
    reg [63:0] sq [0:RQ-1]; reg [QW-1:0] sq_t, sq_h; reg [QW:0] sq_n;
    wire sq_push = w_fire && mh_z;
    reg fin;
    always @* begin
        fin = sq_n != 0;
        for (integer b = 0; b < 8; b = b + 1) begin : cmp
            reg [7:0] df; df = 8'(dcnt[b] + 8'(f_wdone[b])) - sq[sq_h][b*8 +: 8];
            if (df[7]) fin = 1'b0;
        end
    end
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            mq_t <= 0; mq_h <= 0; infl <= 0; bad <= 0; wg_ok <= 0; o_wf <= 0; o_fin <= 0; o_bad <= 0; o_idle <= 0;
            sq_t <= 0; sq_h <= 0; sq_n <= 0;
        end else begin
            wg_ok <= f_act && f_wg;
            if (f_m_v) mq_t <= mq_t + 1'b1;
            if (w_fire) mq_h <= mq_h + 1'b1;
            infl <= infl + (OW+1)'(f_m_v) - (OW+1)'(vo_f);
            if ((vo_f && qf_f) || df_f || od_ovf || f_bi) bad <= 1'b1;
            if ((vo_f && qf_f) || df_f || od_ovf) o_bad <= 1'b1;
            o_wf <= w_fire; o_fin <= fin;
            if (sq_push) sq_t <= sq_t + 1'b1;
            if (fin) sq_h <= sq_h + 1'b1;
            sq_n <= sq_n + (QW+1)'(sq_push) - (QW+1)'(fin);
            o_idle <= infl == 0 && !f_m_v;
        end
    end
    always @(posedge clk or negedge rr_n[2]) begin
        if (!rr_n[2]) begin
            for (integer b = 0; b < 8; b = b + 1) begin wwq[b*280 + 279] <= 1'b0; wcr[b] <= LQ[CW-1:0]; wcnt[b] <= 0; dcnt[b] <= 0; end
        end else begin
            for (integer b = 0; b < 8; b = b + 1) begin : lanes
                reg wr; wr = w_fire && w_hit[b];
                wwq[b*280 + 279] <= wr;
                wcr[b] <= wcr[b] + CW'(f_wcr[b]) - CW'(wr);
                wcnt[b] <= wcnt[b] + 8'(wr); dcnt[b] <= dcnt[b] + 8'(f_wdone[b]);
            end
        end
    end
    // Address/payload flops are written separately from resettable valid strobes (no ALDFF feedback on payload bits).
    always @(posedge clk) begin
        if (f_m_v) begin mq_o[mq_t] <= f_m[18:4]; mq_n[mq_t] <= f_m[3:1]; mq_z[mq_t] <= f_m[0]; end
        mh_o <= w_fire ? mq_o[mq_h1] : mq_o[mq_h]; mh_n <= w_fire ? mq_n[mq_h1] : mq_n[mq_h];
        mh_z <= w_fire ? mq_z[mq_h1] : mq_z[mq_h];
        if (sq_push) for (integer q = 0; q < 8; q = q + 1) sq[sq_t][q*8 +: 8] <= wcnt[q] + 8'(w_hit[q]);
        for (integer b = 0; b < 8; b = b + 1) begin
            if (w_fire && w_hit[b]) begin
                reg [255:0] d; reg [1:0] s; reg [127:0] c; s = 2'(3'(b - w_sec0[2:0]));
                // decoded constant-index sector select (one-hot AND-OR, no runtime part-select)
                c = ({128{s == 2'd0}} & od_head[127:0]) | ({128{s == 2'd1}} & od_head[255:128]) |
                    ({128{s == 2'd2}} & od_head[383:256]) | ({128{s == 2'd3}} & od_head[511:384]);
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
