`timescale 1ns/1ps
// Head-rank join of three independently captured input-layer means.
// This is a logical registered stream endpoint: actual protected-link header
// and finite-credit relay binding remain explicit parent obligations.
// Three real SRAM macros retain120 distinct512b frames with SECDED72.
module ot_dsrom_hc_seed_join #(
    parameter integer USER_W=10,POS_W=21,EPOCH_W=4,MAX_CONTEXT=1048576,
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
    localparam [2:0] ARRIVE=0,COMMIT=1,READ=2,RWAIT=3,RCAP=4,HOLD=5;
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
    wire bad=in_capture>2 || in_frame>=40 || in_position>=MAX_CONTEXT ||
        (in_last!=(in_frame==39)) ||
        (owned && (in_user!=user_q || in_position!=position_q || in_epoch!=epoch_q)) ||
        (in_capture<=2 && (complete[in_capture] || in_frame!=next_frame[in_capture]));
    wire fire=in_valid&&in_ready;
    wire [575:0] encoded;
    wire [767:0] memory_q;
    wire [7:0] ce,ue;
    wire [7:0] ra={6'd0,rcapture}*8'd40+{2'd0,rframe};
    genvar l,b;
    generate for(l=0;l<8;l=l+1) begin:g_code
        ot_s81_secded_enc72 e(.d(in_data[64*l+:64]),.c(encoded[72*l+:72]));
        ot_s81_secded_dec72 d(.c(held_code[72*l+:72]^(l==0?READ_INJECT:72'd0)),
            .d(out_data[64*l+:64]),.ce(ce[l]),.ue(ue[l]));
    end
    for(b=0;b<3;b=b+1) begin:g_sram
        wire [767:0] banks={192'd0,wd_q};
        ot_sram_1r1w_256x256_m2_r2c2 m(.clk(clk),
            .r_ce_in(state==READ&&!fault),.r_addr_in(ra),.rd_out(memory_q[256*b+:256]),
            .w_ce_in(state==COMMIT&&!fault),.w_addr_in(wa_q),
            .wd_in(banks[256*b+:256]),.w_mask_in({256{1'b1}}),
            .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end endgenerate
    assign in_ready=state==ARRIVE&&!fault;
    assign out_valid=state==HOLD&&!fault&&!(|ue);
    assign out_user=user_q;assign out_position=position_q;assign out_epoch=epoch_q;
    assign out_capture=rcapture;assign out_frame=rframe;
    assign out_last=rcapture==2&&rframe==39;assign out_corrected=out_valid&&(|ce);
    assign busy=owned;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=ARRIVE;owned<=0;fault<=0;complete<=0;
            user_q<=0;position_q<=0;epoch_q<=0;wa_q<=0;wd_q<=0;held_code<=0;
            rcapture<=0;rframe<=0;for(k=0;k<3;k=k+1) next_frame[k]<=0;
        end else if(!fault) begin
            case(state)
                ARRIVE: if(fire) begin
                    if(bad) fault<=1;
                    else begin
                        owned<=1;user_q<=in_user;position_q<=in_position;epoch_q<=in_epoch;
                        wa_q<={6'd0,in_capture}*8'd40+{2'd0,in_frame};wd_q<=encoded;
                        next_frame[in_capture]<=in_frame+1'b1;
                        if(in_frame==39) complete[in_capture]<=1;
                        state<=COMMIT;
                    end
                end
                COMMIT: if(&complete) begin rcapture<=0;rframe<=0;state<=READ;end
                        else state<=ARRIVE;
                READ: state<=RWAIT;
                RWAIT: state<=RCAP;
                RCAP: begin held_code<=memory_q[575:0];state<=HOLD;end
                HOLD: if(|ue) fault<=1;
                    else if(out_ready) begin
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
