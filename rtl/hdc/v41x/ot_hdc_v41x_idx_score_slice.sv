`timescale 1ns/1ps
// Full-shape V4.1 index score slice: NK keys/cycle, 32 heads x 128 FP4 dims.
// Reuses the exact chunk8 q4dot/head-sum arithmetic in ot_hdc_v41x_idx_engine.
// The output is a ready/valid BF16 score beat with global position metadata,
// suitable for one quarter's selector ingress. No scalar VM score writes.
// Four NK=4 slices per quarter form its 16 score lanes; four quarters need
// sixteen slices. The slice's arithmetic is fully pipelined (II=1 when ready),
// with a finite metadata queue and the engine's own finite output credit.
module ot_hdc_v41x_idx_score_slice #(
    parameter integer NK=4, NB=4, IH=32, IW=30, MD=64
) (
    input wire clk, rst_n,
    input wire ql_v,
    output wire ql_ready,
    input wire [7:0] ql_head,
    input wire [NB*128-1:0] ql_codes,
    input wire [NB*8-1:0] ql_sc,
    input wire [15:0] ql_w,
    input wire i_valid,
    output wire i_ready,
    input wire i_last,
    input wire [IW-1:0] i_first_index,
    input wire [NK-1:0] i_kv,
    input wire [NK-1:0] i_ref,
    input wire [NK-1:0] i_keep,
    input wire [NK*NB*136-1:0] i_key,
    output wire o_valid,
    input wire o_ready,
    output wire o_last,
    output wire [NK-1:0] o_kv,
    output wire [NK*16-1:0] o_score,
    output wire [NK*IW-1:0] o_index,
    output wire [NK-1:0] o_fault
);
    localparam integer PW=$clog2(MD), CW=$clog2(MD+1);
    reg [IW+NK:0] meta [0:MD-1]; // {last, first_index, refused mask}
    reg [PW-1:0] wr,rd;
    reg [CW-1:0] count;
    wire ev,er;
    wire [NK-1:0] ekv,ef;
    wire [NK*16-1:0] es;
    wire take=i_valid && i_ready;
    wire pop=o_valid && o_ready;
    // Query SRAM is single-buffered. A new query may overwrite it only after
    // all earlier score beats leave both the engine and metadata queue.
    assign ql_ready=(count==0) && !ev && !i_valid;
    assign i_ready=er && count<MD;
    assign o_valid=ev && count!=0;
    assign o_last=meta[rd][IW+NK];
    assign o_kv=ekv;
    assign o_fault=ef | meta[rd][NK-1:0];
    wire [IW-1:0] first_index=meta[rd][IW+NK-1:NK];
    genvar g;
    generate for(g=0;g<NK;g=g+1) begin:g_idx
        localparam [IW-1:0] OFFSET=g;
        assign o_index[g*IW +: IW]=first_index+OFFSET;
        assign o_score[g*16 +: 16]=meta[rd][g] ? 16'd0 : es[g*16 +: 16];
    end endgenerate
    ot_hdc_v41x_idx_engine #(.NK(NK),.IH(IH),.NB(NB),.FD(MD)) engine (
        .clk(clk),.rst_n(rst_n),.ql_v(ql_v && ql_ready),.ql_head(ql_head),
        .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
        .k_valid(take),.k_ready(er),.k_kv(i_kv),.k_keep(i_keep),.k_key(i_key),
        .o_valid(ev),.o_ready(pop),.o_kv(ekv),.o_score(es),.o_fault(ef),
        .cnt_keys_scored(),.cnt_headsums_fused(),.cnt_faults());
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin wr<=0;rd<=0;count<=0;end
        else begin
            if(take) begin
                meta[wr]<={i_last,i_first_index,i_ref};
                wr<=wr+1'b1;
            end
            if(pop) rd<=rd+1'b1;
            case({take,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:count<=count;
            endcase
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_n && ql_v && !ql_ready)
        $fatal(1,"index score query overwrite while prior scores are in flight");
`endif
endmodule
