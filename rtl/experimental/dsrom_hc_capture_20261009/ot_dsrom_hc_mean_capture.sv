`timescale 1ns/1ps
// Opt-in mandatory DSpark seed capture. Inputs are the four BF16 residual
// copies BEFORE hc_pre at backbone layers 37,38,39, never post-layer outputs.
// TP4 rank: 1280 dimensions/capture, 160 eight-dimension input beats.
// Actual golden: ((h0+h1)+h2)+h3 in FP32, then FP32 *0.25 and BF16 RNE.
// All three independent captures are retained in protected real SRAM before
// ordered 120-flit delivery. One identity owns the finite buffer until drained.
// Streaming-domain arithmetic uses LAT7; no relaxed serial-domain SDC claim.
module ot_dsrom_hc_mean_capture #(
    parameter integer USER_W=10, POS_W=21, EPOCH_W=4,
    parameter integer ADD_LAT=7, MUL_LAT=7,
    parameter integer MAX_CONTEXT=1048576,
    parameter integer ECC_PIPE=0, // opt-in registered syndrome and correction
    parameter integer SINGLE_CAPTURE=0, // production proximal source=1; combined minimum vehicle=0
    parameter integer MUT_TREE=0, MUT_LAYER_ALIAS=0,
    parameter [71:0] READ_INJECT=72'd0
)(
    input wire clk,rst_n,
    input wire cmd_valid, output wire cmd_ready,
    input wire [1:0] cmd_capture, // 0=L37,1=L38,2=L39, at INPUT of layer
    input wire [USER_W-1:0] cmd_user,
    input wire [POS_W-1:0] cmd_position,
    input wire [EPOCH_W-1:0] cmd_epoch,
    input wire in_valid, output wire in_ready,
    input wire [7:0] in_beat,
    input wire [511:0] in_residuals, // four copies, each eight contiguous BF16
    output wire out_valid, input wire out_ready,
    output wire [511:0] out_data,
    output wire [USER_W-1:0] out_user,
    output wire [POS_W-1:0] out_position,
    output wire [EPOCH_W-1:0] out_epoch,
    output wire [1:0] out_capture,
    output wire [5:0] out_frame,
    output wire out_last, output wire out_corrected,
    output reg capture_done, output wire [1:0] capture_done_capture,
    output wire busy, output reg fault
);
    localparam [3:0] CMD=0,LOAD=1,AISS=2,AWAIT=3,MISS=4,MWAIT=5,
                     STORE=6,WCOMMIT=7,RREQ=8,RWAIT=9,RDECODE=10,RHOLD=11,RECC=12;
    reg [3:0] state;
    reg owned;
    reg [USER_W-1:0] user_q;
    reg [POS_W-1:0] position_q;
    reg [EPOCH_W-1:0] epoch_q;
    reg [2:0] captured;
    reg [1:0] capture_q,add_step,part,read_capture;
    reg [7:0] beat_q;
    reg [5:0] frame_q,read_frame;
    reg [127:0] h1,h2,h3;
    reg [255:0] acc;
    reg [511:0] pack_q;
    reg [575:0] held_code;
    wire [7:0] av,mv;
    wire [255:0] ay,my;
    wire [15:0] ae,me;
    wire [127:0] mean_bf16;
    genvar l,b;
    function automatic [15:0] bf16_rne(input [31:0] x);
        reg [31:0] rounded;
        begin
            rounded=x+32'h00007fff+{31'd0,x[16]};
            bf16_rne=rounded[31:16];
        end
    endfunction
    generate for(l=0;l<8;l=l+1) begin:g_lane
        wire [15:0] next_h=(add_step==0)?h1[16*l+:16]:
                              (add_step==1)?h2[16*l+:16]:h3[16*l+:16];
        // MUT_TREE deliberately changes the accumulation order.
        wire [15:0] operand=(MUT_TREE && add_step==0)?h3[16*l+:16]:
                            (MUT_TREE && add_step==2)?h1[16*l+:16]:next_h;
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add(
            .clk(clk),.rst_n(rst_n),.valid_in(state==AISS&&!fault),
            .a(acc[32*l+:32]),.b({operand,16'd0}),
            .y(ay[32*l+:32]),.err(ae[2*l+:2]),.valid_out(av[l]));
        ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul(
            .clk(clk),.rst_n(rst_n),.valid_in(state==MISS&&!fault),
            .a(acc[32*l+:32]),.b(32'h3e800000),
            .y(my[32*l+:32]),.err(me[2*l+:2]),.valid_out(mv[l]));
        assign mean_bf16[16*l+:16]=bf16_rne(my[32*l+:32]);
    end endgenerate
    wire [575:0] write_code,read_code;
    wire [767:0] bank_data;
    wire [7:0] enc_ce,dec_ue,decode_valid;
    generate for(l=0;l<8;l=l+1) begin:g_ecc
        ot_s81_secded_enc72 u_enc(.d(pack_q[64*l+:64]),.c(write_code[72*l+:72]));
        if(ECC_PIPE) begin:g_pipe
            ot_dsrom_hc_secded_pipe u_dec(.clk(clk),.rst_n(rst_n),
                .valid_in(state==RDECODE&&!fault),
                .c(read_code[72*l+:72]^(l==0?READ_INJECT:72'd0)),
                .valid_out(decode_valid[l]),.d(out_data[64*l+:64]),
                .ce(enc_ce[l]),.ue(dec_ue[l]));
        end else begin:g_comb
            assign decode_valid[l]=1'b0;
            ot_s81_secded_dec72 u_dec(.c(held_code[72*l+:72]^(l==0?READ_INJECT:72'd0)),
                .d(out_data[64*l+:64]),.ce(enc_ce[l]),.ue(dec_ue[l]));
        end
    end endgenerate
    wire [7:0] write_addr=(MUT_LAYER_ALIAS?8'd0:{6'd0,capture_q})*8'd40+{2'd0,frame_q};
    wire [7:0] read_addr={6'd0,read_capture}*8'd40+{2'd0,read_frame};
    wire [767:0] write_banks={192'd0,write_code};
    generate for(b=0;b<3;b=b+1) begin:g_sram
        ot_sram_1r1w_256x256_m2_r2c2 u_mem(
            .clk(clk),.r_ce_in(state==RREQ&&!fault),.r_addr_in(read_addr),
            .rd_out(bank_data[256*b+:256]),
            .w_ce_in(state==STORE&&!fault),.w_addr_in(write_addr),
            .wd_in(write_banks[256*b+:256]),.w_mask_in({256{1'b1}}),
            .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end endgenerate
    assign read_code=bank_data[575:0];
    assign busy=owned;
    assign capture_done_capture=capture_q;
    assign cmd_ready=state==CMD&&!fault;
    assign in_ready=state==LOAD&&!fault;
    assign out_valid=state==RHOLD&&!fault&&!(|dec_ue);
    assign out_user=user_q;
    assign out_position=position_q;
    assign out_epoch=epoch_q;
    assign out_capture=read_capture;
    assign out_frame=read_frame;
    assign out_last=(SINGLE_CAPTURE || read_capture==2)&&read_frame==39;
    assign out_corrected=out_valid&&(|enc_ce);
    integer lane;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=CMD;owned<=0;fault<=0;captured<=0;capture_done<=0;
            user_q<=0;position_q<=0;epoch_q<=0;capture_q<=0;
            beat_q<=0;frame_q<=0;part<=0;add_step<=0;
            read_capture<=0;read_frame<=0;held_code<=0;
            h1<=0;h2<=0;h3<=0;acc<=0;pack_q<=0;
        end else if(!fault) begin
            capture_done<=0;
            case(state)
                CMD: if(cmd_valid) begin
                    if(cmd_capture>2 || cmd_position>=MAX_CONTEXT || (owned &&
                       (cmd_user!=user_q || cmd_position!=position_q || cmd_epoch!=epoch_q ||
                        captured[cmd_capture]))) fault<=1;
                    else begin
                        owned<=1;user_q<=cmd_user;position_q<=cmd_position;epoch_q<=cmd_epoch;
                        capture_q<=cmd_capture;beat_q<=0;frame_q<=0;part<=0;
                        state<=LOAD;
                    end
                end
                LOAD: if(in_valid) begin
                    if(in_beat!=beat_q) fault<=1;
                    else begin
                        for(lane=0;lane<8;lane=lane+1)
                            acc[32*lane+:32]<={in_residuals[16*lane+:16],16'd0};
                        h1<=in_residuals[128+:128];h2<=in_residuals[256+:128];h3<=in_residuals[384+:128];
                        add_step<=0;state<=AISS;
                    end
                end
                AISS: state<=AWAIT;
                AWAIT: if(&av) begin
                    if(|ae) fault<=1;
                    else begin
                        acc<=ay;
                        if(add_step==2) state<=MISS;
                        else begin add_step<=add_step+1'b1;state<=AISS;end
                    end
                end
                MISS: state<=MWAIT;
                MWAIT: if(&mv) begin
                    if(|me) fault<=1;
                    else begin
                        pack_q[128*part+:128]<=mean_bf16;
                        if(part==3) state<=STORE;
                        else begin part<=part+1'b1;beat_q<=beat_q+1'b1;state<=LOAD;end
                    end
                end
                STORE: state<=WCOMMIT;
                WCOMMIT: begin
                    part<=0;
                    if(frame_q==39) begin
                        capture_done<=1;
                        captured[capture_q]<=1;
                        if(SINGLE_CAPTURE || (captured|(3'b001<<capture_q))==3'b111) begin
                            read_capture<=SINGLE_CAPTURE?capture_q:2'd0;read_frame<=0;state<=RREQ;
                        end else state<=CMD;
                    end else begin frame_q<=frame_q+1'b1;beat_q<=beat_q+1'b1;state<=LOAD;end
                end
                RREQ: state<=RWAIT;
                RWAIT: state<=RDECODE;
                RDECODE: begin held_code<=read_code;state<=ECC_PIPE?RECC:RHOLD;end
                RECC: if(&decode_valid) state<=RHOLD;
                RHOLD: begin
                    if(|dec_ue) fault<=1;
                    else if(out_ready) begin
                        if(read_frame==39) begin
                            read_frame<=0;
                            if(SINGLE_CAPTURE || read_capture==2) begin owned<=0;captured<=0;state<=CMD;end
                            else begin read_capture<=read_capture+1'b1;state<=RREQ;end
                        end else begin read_frame<=read_frame+1'b1;state<=RREQ;end
                    end
                end
                default: fault<=1;
            endcase
        end
    end
endmodule
