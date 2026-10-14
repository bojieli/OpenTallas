`timescale 1ns/1ps
// cont-takeover 2026-10-09 (hbm_continuation NK4): the hardened element of the NK4 scoring array is one full-geometry
// score slice (NK=4 keys x IH=32 heads x NB=4 blocks = 512 FP4 block dots per cycle; Codex hierarchical map 39b818fdd:
// 16 slices = 6.28 M cells).  This wrapper registers every boundary of ot_hdc_v41x_idx_score_slice_l so the slice can be
// hardened and replicated (owner rules: registered block boundaries, relay at the pins): the q-load and key channels and
// the score channel each pass a two-entry skid (ready from a flop, data straight from flops).  The slice's own
// ql_ready <- !i_valid term then sees the skid output, not a pin.  Values and stream order are unchanged; +1 cycle on
// each channel (q load, key, score).
module ot_idx_skid #(parameter integer W=8)(input wire clk,rst_n,input wire i_valid,output wire i_ready,
 input wire[W-1:0]i_data,output wire o_valid,input wire o_ready,output wire[W-1:0]o_data);
 reg v0,v1;reg[W-1:0]d0,d1;
 assign i_ready=!v1;assign o_valid=v0;assign o_data=d0;
 wire push=i_valid&&!v1,pop=v0&&o_ready;
 always@(posedge clk or negedge rst_n)
 if(!rst_n)begin v0<=0;v1<=0;end
 else if(pop)begin if(v1)v1<=0;else v0<=push;end
 else if(push)begin if(!v0)v0<=1;else v1<=1;end
 always@(posedge clk)
 if(pop)begin if(v1)d0<=d1;else if(push)d0<=i_data;end
 else if(push)begin if(!v0)d0<=i_data;else d1<=i_data;end
endmodule

module ot_hdc_v41x_idx_score_slice_reg #(
    parameter integer NK=4, NB=4, IH=32, IW=30, MD=64,
    parameter integer FPL=3, FML=3, QL=3
) (
    input wire clk, rst_n,
    input wire ql_v, output wire ql_ready, input wire [7:0] ql_head,
    input wire [NB*128-1:0] ql_codes, input wire [NB*8-1:0] ql_sc, input wire [15:0] ql_w,
    input wire i_valid, output wire i_ready, input wire i_last, input wire [IW-1:0] i_first_index,
    input wire [NK-1:0] i_kv, input wire [NK-1:0] i_ref, input wire [NK-1:0] i_keep, input wire [NK*NB*136-1:0] i_key,
    output wire o_valid, input wire o_ready, output wire o_last, output wire [NK-1:0] o_kv,
    output wire [NK*16-1:0] o_score, output wire [NK*IW-1:0] o_index, output wire [NK-1:0] o_fault
);
    localparam integer QW=8+NB*128+NB*8+16, KW=1+IW+3*NK+NK*NB*136, OW=1+NK+NK*16+NK*IW+NK;
    wire q_v,q_r,k_v,k_r,s_v,s_r;wire [QW-1:0] q_d;wire [KW-1:0] k_d;wire [OW-1:0] s_d;
    wire [7:0] h;wire [NB*128-1:0] qc;wire [NB*8-1:0] qs;wire [15:0] qw;
    wire kl;wire [IW-1:0] kf;wire [NK-1:0] kv,kr,kk;wire [NK*NB*136-1:0] kd;
    wire sl;wire [NK-1:0] sk,sf;wire [NK*16-1:0] ss;wire [NK*IW-1:0] si;
    // q-load ready is a flop: open only while no key is queued or in the slice and the q skid is empty (one cycle stale,
    // so at most two beats land in the two-entry skid).  Queued keys wait behind queued query beats (the slice loads a
    // query only with no key valid), so queries and keys keep their upstream order.
    reg rq;wire q_skid_unused;
    always @(posedge clk or negedge rst_n) if(!rst_n) rq<=1'b0; else rq<=q_r && !k_v && !q_v;
    assign ql_ready=rq;
    ot_idx_skid #(.W(QW)) u_q(.clk(clk),.rst_n(rst_n),.i_valid(ql_v && rq),.i_ready(q_skid_unused),.i_data({ql_head,ql_codes,ql_sc,ql_w}),
        .o_valid(q_v),.o_ready(q_r),.o_data(q_d));
    assign {h,qc,qs,qw}=q_d;
    ot_idx_skid #(.W(KW)) u_k(.clk(clk),.rst_n(rst_n),.i_valid(i_valid),.i_ready(i_ready),
        .i_data({i_last,i_first_index,i_kv,i_ref,i_keep,i_key}),.o_valid(k_v),.o_ready(k_r),.o_data(k_d));
    assign {kl,kf,kv,kr,kk,kd}=k_d;
    wire k_r_s;assign k_r=k_r_s && !q_v;
    ot_hdc_v41x_idx_score_slice_l #(.NK(NK),.NB(NB),.IH(IH),.IW(IW),.MD(MD),.FPL(FPL),.FML(FML),.QL(QL),.ARRAY_PHASE_GATE(0)) u_slice(
        .clk(clk),.rst_n(rst_n),.ql_v(q_v && q_r),.ql_ready(q_r),.ql_head(h),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),
        .i_valid(k_v && !q_v),.i_ready(k_r_s),.i_last(kl),.i_first_index(kf),.i_kv(kv),.i_ref(kr),.i_keep(kk),.i_key(kd),
        .o_valid(s_v),.o_ready(s_r),.o_last(sl),.o_kv(sk),.o_score(ss),.o_index(si),.o_fault(sf));
    ot_idx_skid #(.W(OW)) u_s(.clk(clk),.rst_n(rst_n),.i_valid(s_v),.i_ready(s_r),.i_data({sl,sk,ss,si,sf}),
        .o_valid(o_valid),.o_ready(o_ready),.o_data({o_last,o_kv,o_score,o_index,o_fault}));
endmodule
