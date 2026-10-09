`timescale 1ns/1ps
// Explicit reserved/shared native VM read-client facade. NO added hard-master
// port is claimed: req/rsp must bind through the actual owner arbiter.
// Actual ShapeLayout(tp_exact=True) keeps H=4x5120 expanded BF16/FP32
// words on each rank. Read only this rank's contiguous1280 dimensions:
// Hbase + copy*320 rows + rank*80 rows + localrow (16 words/512b row).
// One outstanding read owns its response; real rsp_valid governs progress.
// Four protected row registers are reused for two eight-dimension beats.
module ot_dsrom_hc_input_reader #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,
    parameter integer MAX_CONTEXT=1048576, ECC_PIPE=0,
    // PLAIN_ROWS (cont-takeover 2026-10-09, default off): the four row registers hold the VM response as plain flops,
    // with no SECDED re-encode / decode.  They are ordinary pipeline flops, not SRAM: REVIEW_20261009 S4 (binding) keeps
    // SECDED on SRAM/HBM payloads only, and the encode->flop->decode loop was the reader's TT -554 ps path
    // (rows -> overall-parity tree -> mean_residuals).  Values, order and protocol unchanged; fewer cycles (no DECODE).
    parameter integer PLAIN_ROWS=0,
    // REG_IO (cont-takeover 2026-10-09, default off): registered boundaries.  cmd_* through ot_dsrom_hc_skid (+1 cycle per
    // command); the VM response (valid/data/fault, no ready) lands in flops before the BF16-zero check (+1 cycle per
    // response); req_row comes from a flop loaded in a new REQ0 state (+1 cycle per request).  Values/order unchanged.
    parameter integer REG_IO=0,
    parameter [71:0] HOLD_INJECT=72'd0
)(
    input wire clk,rst_n,
    input wire cmd_valid, output wire cmd_ready,
    input wire [1:0] cmd_capture,
    input wire [USER_W-1:0] cmd_user,
    input wire [POS_W-1:0] cmd_position,
    input wire [EPOCH_W-1:0] cmd_epoch,
    input wire [13:0] cmd_h_row,
    input wire [1:0] cmd_rank,
    input wire [14:0] cmd_region_rows,
    output wire mean_cmd_valid,input wire mean_cmd_ready,
    output wire [1:0] mean_cmd_capture,
    output wire [USER_W-1:0] mean_cmd_user,
    output wire [POS_W-1:0] mean_cmd_position,
    output wire [EPOCH_W-1:0] mean_cmd_epoch,
    output wire req_valid,input wire req_ready,output wire [13:0] req_row,
    input wire rsp_valid,input wire [511:0] rsp_data,input wire rsp_fault,
    output wire mean_valid,input wire mean_ready,
    output wire [7:0] mean_beat,output wire [511:0] mean_residuals,
    output wire busy,output reg fault
);
    wire x_cmd_valid,x_cmd_ready;wire [1:0] x_cmd_capture;wire [USER_W-1:0] x_cmd_user;wire [POS_W-1:0] x_cmd_position;
    wire [EPOCH_W-1:0] x_cmd_epoch;wire [13:0] x_cmd_h_row;wire [1:0] x_cmd_rank;wire [14:0] x_cmd_region_rows;
    wire x_rsp_valid,x_rsp_fault;wire [511:0] x_rsp_data;wire [13:0] x_req_row;
    reg [13:0] req_row_q;
    generate if(REG_IO) begin:g_regio
        ot_dsrom_hc_skid #(.W(2+USER_W+POS_W+EPOCH_W+14+2+15)) u_cmd(.clk(clk),.rst_n(rst_n),.i_valid(cmd_valid),.i_ready(cmd_ready),
            .i_data({cmd_capture,cmd_user,cmd_position,cmd_epoch,cmd_h_row,cmd_rank,cmd_region_rows}),
            .o_valid(x_cmd_valid),.o_ready(x_cmd_ready),
            .o_data({x_cmd_capture,x_cmd_user,x_cmd_position,x_cmd_epoch,x_cmd_h_row,x_cmd_rank,x_cmd_region_rows}));
        reg rv_q,rf_q;reg [511:0] rd_q;
        always @(posedge clk or negedge rst_n) if(!rst_n) begin rv_q<=1'b0;rf_q<=1'b0;end else begin rv_q<=rsp_valid;rf_q<=rsp_fault;end
        always @(posedge clk) rd_q<=rsp_data;
        assign x_rsp_valid=rv_q;assign x_rsp_fault=rf_q;assign x_rsp_data=rd_q;
        assign req_row=req_row_q;
    end else begin:g_direct
        assign x_cmd_valid=cmd_valid;assign cmd_ready=x_cmd_ready;assign x_cmd_capture=cmd_capture;assign x_cmd_user=cmd_user;
        assign x_cmd_position=cmd_position;assign x_cmd_epoch=cmd_epoch;assign x_cmd_h_row=cmd_h_row;assign x_cmd_rank=cmd_rank;
        assign x_cmd_region_rows=cmd_region_rows;
        assign x_rsp_valid=rsp_valid;assign x_rsp_fault=rsp_fault;assign x_rsp_data=rsp_data;assign req_row=x_req_row;
    end endgenerate
    localparam [3:0] IDLE=0,MCMD=1,REQ=2,WAIT=3,SEND=4,DECODE=5,DWAIT=6,EWAIT=7,REQ0=8;
    reg [3:0] state;
    reg [1:0] capture_q,copy_q;
    reg [USER_W-1:0] user_q;
    reg [POS_W-1:0] position_q;
    reg [EPOCH_W-1:0] epoch_q;
    reg [13:0] base_q;
    reg [1:0] rank_q;
    reg [6:0] row_q;
    reg half_q;
    reg [575:0] rows[0:3];
    wire [575:0] rsp_encoded;
    wire [7:0] encode_valid;
    wire [511:0] decoded[0:3];
    wire [31:0] ue,decode_valid;
    wire [31:0] ce_unused;
    reg bad_bf16;
    wire [575:0] row_in=PLAIN_ROWS?{64'd0,x_rsp_data}:rsp_encoded;
    localparam integer EP=(ECC_PIPE!=0)&&(PLAIN_ROWS==0);
    genvar c,l;
    generate for(l=0;l<8;l=l+1) begin:g_encode
        if(EP) begin:g_pipe
            ot_dsrom_hc_secded_encode_pipe e(.clk(clk),.rst_n(rst_n),
                .valid_in(state==WAIT&&x_rsp_valid&&!x_rsp_fault&&!bad_bf16&&!fault),
                .d(x_rsp_data[64*l+:64]),.c(rsp_encoded[72*l+:72]),.valid_out(encode_valid[l]));
        end else if(PLAIN_ROWS) begin:g_plain
            assign encode_valid[l]=1'b0;
            assign rsp_encoded[72*l+:72]=72'd0;
        end else begin:g_comb
            assign encode_valid[l]=1'b0;
            ot_s81_secded_enc72 e(.d(x_rsp_data[64*l+:64]),.c(rsp_encoded[72*l+:72]));
        end
    end
    for(c=0;c<4;c=c+1) begin:g_copy
        for(l=0;l<8;l=l+1) begin:g_decode
            if(PLAIN_ROWS) begin:g_plain
                assign decode_valid[8*c+l]=1'b1;
                assign decoded[c][64*l+:64]=rows[c][64*l+:64];
                assign ce_unused[8*c+l]=1'b0;
                assign ue[8*c+l]=1'b0;
            end else if(EP) begin:g_pipe
                ot_dsrom_hc_secded_pipe d(.clk(clk),.rst_n(rst_n),
                    .valid_in(state==DECODE&&!fault),
                    .c(rows[c][72*l+:72]^(c==0&&l==0?HOLD_INJECT:72'd0)),
                    .valid_out(decode_valid[8*c+l]),.d(decoded[c][64*l+:64]),
                    .ce(ce_unused[8*c+l]),.ue(ue[8*c+l]));
            end else begin:g_comb
                assign decode_valid[8*c+l]=1'b0;
                ot_s81_secded_dec72 d(.c(rows[c][72*l+:72]^(c==0&&l==0?HOLD_INJECT:72'd0)),
                    .d(decoded[c][64*l+:64]),.ce(ce_unused[8*c+l]),.ue(ue[8*c+l]));
            end
        end
        for(l=0;l<8;l=l+1) begin:g_select
            assign mean_residuals[128*c+16*l+:16]=half_q?decoded[c][256+32*l+16+:16]:decoded[c][32*l+16+:16];  // explicit 2:1 (was a variable part-select)
        end
    end endgenerate
    wire [14:0] end_row={1'b0,x_cmd_h_row}+15'd1280;
    wire [14:0] requested_row={1'b0,base_q}+{13'd0,copy_q}*15'd320+
                              {13'd0,rank_q}*15'd80+{8'd0,row_q};
    assign x_cmd_ready=state==IDLE&&!fault;
    assign mean_cmd_valid=state==MCMD&&!fault;
    assign mean_cmd_capture=capture_q;assign mean_cmd_user=user_q;
    assign mean_cmd_position=position_q;assign mean_cmd_epoch=epoch_q;
    assign req_valid=state==REQ&&!fault;
    assign x_req_row=requested_row[13:0];
    assign mean_valid=state==SEND&&!fault&&!(|ue);
    assign mean_beat={row_q,half_q};
    assign busy=state!=IDLE;
    always @(posedge clk) req_row_q<=requested_row[13:0];
    integer k;
    always_comb begin
        bad_bf16=0;
        for(integer w=0;w<16;w=w+1)
            if(x_rsp_data[32*w+:16]!=16'd0) bad_bf16=1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;fault<=0;capture_q<=0;copy_q<=0;user_q<=0;
            position_q<=0;epoch_q<=0;base_q<=0;rank_q<=0;row_q<=0;half_q<=0;
            for(k=0;k<4;k=k+1) rows[k]<=0;
        end else if(!fault) begin
            if(x_rsp_fault || (x_rsp_valid&&state!=WAIT)) fault<=1;
            else case(state)
                IDLE: if(x_cmd_valid) begin
                    if(x_cmd_capture>2 || x_cmd_position>=MAX_CONTEXT || x_cmd_region_rows<1280 || end_row>16384) fault<=1;
                    else begin capture_q<=x_cmd_capture;user_q<=x_cmd_user;
                        position_q<=x_cmd_position;epoch_q<=x_cmd_epoch;base_q<=x_cmd_h_row;rank_q<=x_cmd_rank;
                        row_q<=0;copy_q<=0;half_q<=0;state<=MCMD;end
                end
                MCMD: if(mean_cmd_ready) state<=(REG_IO?REQ0:REQ);
                REQ0: state<=REQ;
                REQ: if(req_ready) state<=WAIT;
                WAIT: if(x_rsp_valid) begin
                    if(bad_bf16) fault<=1;
                    else if(EP) state<=EWAIT;
                    else begin
                        rows[copy_q]<=row_in;
                        if(copy_q==3) begin copy_q<=0;half_q<=0;state<=EP?DECODE:SEND;end
                        else begin copy_q<=copy_q+1'b1;state<=(REG_IO?REQ0:REQ);end
                    end
                end
                EWAIT: if(&encode_valid) begin
                    rows[copy_q]<=rsp_encoded;
                    if(copy_q==3) begin copy_q<=0;half_q<=0;state<=DECODE;end
                    else begin copy_q<=copy_q+1'b1;state<=(REG_IO?REQ0:REQ);end
                end
                DECODE: state<=DWAIT;
                DWAIT: if(&decode_valid) state<=SEND;
                SEND: if(|ue) fault<=1;
                    else if(mean_ready) begin
                        if(!half_q) half_q<=1;
                        else if(row_q==79) state<=IDLE;
                        else begin row_q<=row_q+1'b1;half_q<=0;state<=(REG_IO?REQ0:REQ);end
                    end
                default: fault<=1;
            endcase
        end
    end
endmodule
