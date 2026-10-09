`timescale 1ns/1ps
// Head-rank join of three independently captured input-layer means.
// This is a logical registered stream endpoint: actual protected-link header
// and finite-credit relay binding remain explicit parent obligations.
// Three real SRAM macros retain120 distinct512b frames with SECDED72.
module ot_dsrom_hc_seed_join #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,MAX_CONTEXT=1048576,
    parameter integer ECC_PIPE=0,
    // MACRO_CAP (cont-takeover 2026-10-09, default off, needs ECC_PIPE): the SECDED pipe decodes the REGISTERED macro
    // capture (held_code, taken at RCAP) instead of the raw SRAM rd_out: no logic between a macro output and its
    // first flop (owner rule; eccpipe join r2 TT -42.7 ps = rd_out -> overall-parity XOR tree).  +1 cycle per frame read.
    parameter integer MACRO_CAP=0,
    // IN_SKID (cont-takeover 2026-10-09, default off): registered input boundary via ot_dsrom_hc_skid, +1 cycle per frame
    // arrival; the arrival checks (45 gate levels from the pins) then start at flops.
    parameter integer IN_SKID=0,
    // OUT_SKID (cont-takeover 2026-10-09, default off): registered output boundary, +1 cycle per output frame.
    parameter integer OUT_SKID=0,
    // LINK_CREDIT (cont-takeover 2026-10-09, REVIEW ~11:30, default off): every stream boundary is the die-link credit
    // relay (rtl/common/ot_link_credit.sv): {valid,data} pins from/into flops, and the opposite-direction ready pin
    // carries one credit pulse per freed landing slot (receiver) / per credit returned (sender).  Supersedes IN_SKID /
    // OUT_SKID.  LINK_DEPTH = landing depth = sender credits (>= the link round trip for full rate).  Landing overflow
    // is a fault.
    parameter integer LINK_CREDIT=0, LINK_DEPTH=8,
    parameter [71:0] READ_INJECT=72'd0
)(
    input wire clk,rst_n,
    input wire in_valid,output wire in_ready,input wire [511:0] in_data,
    input wire [USER_W-1:0] in_user,input wire [POS_W-1:0] in_position,
    input wire [EPOCH_W-1:0] in_epoch,input wire [1:0] in_capture,
    input wire [5:0] in_frame,input wire in_last,
    output wire out_valid,input wire out_ready,output wire [511:0] out_data,
    output wire [USER_W-1:0] out_user,output wire [POS_W-1:0] out_position,
    output wire [EPOCH_W-1:0] out_epoch,output wire [1:0] out_capture,
    output wire [5:0] out_frame,output wire out_last,output wire out_corrected,
    output wire busy,output reg fault
);
    // OUT_SKID: registered output boundary (ot_dsrom_hc_skid): outputs straight from flops, out_ready lands in a flop.
    wire y_out_valid,y_out_ready,y_out_last,y_out_corrected;wire [511:0] y_out_data;wire [USER_W-1:0] y_out_user;
    wire [POS_W-1:0] y_out_position;wire [EPOCH_W-1:0] y_out_epoch;wire [1:0] y_out_capture;wire [5:0] y_out_frame;
    wire [0:0] lf;wire link_fault=LINK_CREDIT!=0 && (|lf);
    generate if(LINK_CREDIT) begin:g_oskid_link
        ot_link_credit_tx #(.W(512+USER_W+POS_W+EPOCH_W+2+6+2),.CRED(LINK_DEPTH)) u_out_l(.clk(clk),.rst_n(rst_n),.i_valid(y_out_valid),.i_ready(y_out_ready),.i_data({y_out_data,y_out_user,y_out_position,y_out_epoch,y_out_capture,y_out_frame,y_out_last,y_out_corrected}),.l_valid(out_valid),.l_data({out_data,out_user,out_position,out_epoch,out_capture,out_frame,out_last,out_corrected}),.l_credit(out_ready));
    end else if(OUT_SKID) begin:g_oskid
        ot_dsrom_hc_skid #(.W(512+USER_W+POS_W+EPOCH_W+2+6+2)) u_out(.clk(clk),.rst_n(rst_n),
            .i_valid(y_out_valid),.i_ready(y_out_ready),
            .i_data({y_out_data,y_out_user,y_out_position,y_out_epoch,y_out_capture,y_out_frame,y_out_last,y_out_corrected}),
            .o_valid(out_valid),.o_ready(out_ready),
            .o_data({out_data,out_user,out_position,out_epoch,out_capture,out_frame,out_last,out_corrected}));
    end else begin:g_odirect
        assign out_valid=y_out_valid;assign y_out_ready=out_ready;assign out_data=y_out_data;assign out_user=y_out_user;
        assign out_position=y_out_position;assign out_epoch=y_out_epoch;assign out_capture=y_out_capture;
        assign out_frame=y_out_frame;assign out_last=y_out_last;assign out_corrected=y_out_corrected;
    end endgenerate
    wire x_in_valid,x_in_ready,x_in_last;wire [511:0] x_in_data;wire [USER_W-1:0] x_in_user;
    wire [POS_W-1:0] x_in_position;wire [EPOCH_W-1:0] x_in_epoch;wire [1:0] x_in_capture;wire [5:0] x_in_frame;
    generate if(LINK_CREDIT) begin:g_skid_link
        ot_link_credit_rx #(.W(512+USER_W+POS_W+EPOCH_W+2+6+1),.DEPTH(LINK_DEPTH)) u_in_l(.clk(clk),.rst_n(rst_n),.l_valid(in_valid),.l_data({in_data,in_user,in_position,in_epoch,in_capture,in_frame,in_last}),.l_credit(in_ready),.o_valid(x_in_valid),.o_ready(x_in_ready),.o_data({x_in_data,x_in_user,x_in_position,x_in_epoch,x_in_capture,x_in_frame,x_in_last}),.fault(lf[0]));
    end else if(IN_SKID) begin:g_skid
        assign lf=1'b0;
        ot_dsrom_hc_skid #(.W(512+USER_W+POS_W+EPOCH_W+2+6+1)) u_in(.clk(clk),.rst_n(rst_n),.i_valid(in_valid),.i_ready(in_ready),
            .i_data({in_data,in_user,in_position,in_epoch,in_capture,in_frame,in_last}),
            .o_valid(x_in_valid),.o_ready(x_in_ready),
            .o_data({x_in_data,x_in_user,x_in_position,x_in_epoch,x_in_capture,x_in_frame,x_in_last}));
    end else begin:g_direct
        assign lf=1'b0;
        assign x_in_valid=in_valid;assign in_ready=x_in_ready;assign x_in_data=in_data;assign x_in_user=in_user;
        assign x_in_position=in_position;assign x_in_epoch=in_epoch;assign x_in_capture=in_capture;
        assign x_in_frame=in_frame;assign x_in_last=in_last;
    end endgenerate
    localparam [2:0] ARRIVE=0,COMMIT=1,READ=2,RWAIT=3,RCAP=4,HOLD=5,RECC=6;
    reg [2:0] state;
    reg owned;
    reg [USER_W-1:0] user_q;
    reg [POS_W-1:0] position_q;
    reg [EPOCH_W-1:0] epoch_q;
    reg [5:0] next_frame[0:2];
    reg [2:0] complete;
    reg [7:0] wa_q;
    reg [575:0] wd_q,held_code;
    reg [1:0] rcapture;
    reg [5:0] rframe;
    reg mc_go;
    wire bad=x_in_capture>2 || x_in_frame>=40 || x_in_position>=MAX_CONTEXT ||
        (x_in_last!=(x_in_frame==39)) ||
        (owned && (x_in_user!=user_q || x_in_position!=position_q || x_in_epoch!=epoch_q)) ||
        (x_in_capture<=2 && (complete[x_in_capture] || x_in_frame!=next_frame[x_in_capture]));
    wire fire=x_in_valid&&x_in_ready;
    wire [575:0] encoded;
    wire [767:0] memory_q;
    wire [7:0] ce,ue,decode_valid;
    wire [7:0] ra={6'd0,rcapture}*8'd40+{2'd0,rframe};
    genvar l,b;
    generate for(l=0;l<8;l=l+1) begin:g_code
        ot_s81_secded_enc72 e(.d(x_in_data[64*l+:64]),.c(encoded[72*l+:72]));
        if(ECC_PIPE) begin:g_pipe
            ot_dsrom_hc_secded_pipe d(.clk(clk),.rst_n(rst_n),
                .valid_in(MACRO_CAP?mc_go:(state==RCAP&&!fault)),
                .c((MACRO_CAP?held_code[72*l+:72]:memory_q[72*l+:72])^(l==0?READ_INJECT:72'd0)),
                .valid_out(decode_valid[l]),.d(y_out_data[64*l+:64]),.ce(ce[l]),.ue(ue[l]));
        end else begin:g_comb
            assign decode_valid[l]=1'b0;
            ot_s81_secded_dec72 d(.c(held_code[72*l+:72]^(l==0?READ_INJECT:72'd0)),
                .d(y_out_data[64*l+:64]),.ce(ce[l]),.ue(ue[l]));
        end
    end
    for(b=0;b<3;b=b+1) begin:g_sram
        wire [767:0] banks={192'd0,wd_q};
        ot_sram_1r1w_256x256_m2_r2c2 m(.clk(clk),
            .r_ce_in(state==READ&&!fault),.r_addr_in(ra),.rd_out(memory_q[256*b+:256]),
            .w_ce_in(state==COMMIT&&!fault),.w_addr_in(wa_q),
            .wd_in(banks[256*b+:256]),.w_mask_in({256{1'b1}}),
            .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end endgenerate
    assign x_in_ready=state==ARRIVE&&!fault;
    assign y_out_valid=state==HOLD&&!fault&&!(|ue);
    assign y_out_user=user_q;assign y_out_position=position_q;assign y_out_epoch=epoch_q;
    assign y_out_capture=rcapture;assign y_out_frame=rframe;
    assign y_out_last=rcapture==2&&rframe==39;assign y_out_corrected=y_out_valid&&(|ce);
    assign busy=owned;
    integer k;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) mc_go<=1'b0; else mc_go<=MACRO_CAP!=0 && state==RCAP && !fault;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=ARRIVE;owned<=0;fault<=0;complete<=0;
            user_q<=0;position_q<=0;epoch_q<=0;wa_q<=0;wd_q<=0;held_code<=0;
            rcapture<=0;rframe<=0;for(k=0;k<3;k=k+1) next_frame[k]<=0;
        end else if(link_fault) fault<=1;
        else if(!fault) begin
            case(state)
                ARRIVE: if(fire) begin
                    if(bad) fault<=1;
                    else begin
                        owned<=1;user_q<=x_in_user;position_q<=x_in_position;epoch_q<=x_in_epoch;
                        wa_q<={6'd0,x_in_capture}*8'd40+{2'd0,x_in_frame};wd_q<=encoded;
                        next_frame[x_in_capture]<=x_in_frame+1'b1;
                        if(x_in_frame==39) complete[x_in_capture]<=1;
                        state<=COMMIT;
                    end
                end
                COMMIT: if(&complete) begin rcapture<=0;rframe<=0;state<=READ;end
                        else state<=ARRIVE;
                READ: state<=RWAIT;
                RWAIT: state<=RCAP;
                RCAP: begin held_code<=memory_q[575:0];state<=ECC_PIPE?RECC:HOLD;end
                RECC: if(&decode_valid) state<=HOLD;
                HOLD: if(|ue) fault<=1;
                    else if(y_out_ready) begin
                        if(rframe==39) begin
                            rframe<=0;
                            if(rcapture==2) begin
                                state<=ARRIVE;owned<=0;complete<=0;
                                for(k=0;k<3;k=k+1) next_frame[k]<=0;
                            end else begin rcapture<=rcapture+1'b1;state<=READ;end
                        end else begin rframe<=rframe+1'b1;state<=READ;end
                    end
                default: fault<=1;
            endcase
        end
    end
endmodule
