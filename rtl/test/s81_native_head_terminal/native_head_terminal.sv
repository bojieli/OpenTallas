`timescale 1ns/1ps
// Default-off source-owned ordered-root terminal. No ROM provider or core mux
// is substituted here. Reset is legal only with the external owner quiescent.
module s81_native_head_terminal #(
    parameter integer OPT_NATIVE_HEAD=0,
    parameter integer ROWS=32320,
    parameter integer OWNER_W=47
)(
    input wire clk,rst_n,start,cancel,
    input wire [1:0] rank,
    input wire [OWNER_W-1:0] start_owner,
    output wire ready,
    input wire in_valid,
    output wire in_ready,
    input wire [OWNER_W-1:0] in_owner,
    input wire [16:0] in_row,
    input wire [31:0] root4096,root1024,
    output wire logit_valid,
    input wire logit_ready,
    output wire [OWNER_W-1:0] logit_owner,
    output wire [16:0] logit_row,
    output wire [31:0] logit_bits,
    output wire logit_poison,
    output reg done_valid,
    input wire done_ready,
    output wire [OWNER_W-1:0] done_owner,
    output reg [16:0] best_row,
    output reg [31:0] best_bits,
    output wire token_valid,
    output reg fault
);
    reg active,have_best;
    reg [OWNER_W-1:0] owner;
    reg [1:0] rank_r;
    reg [14:0] accepted;
    reg [4:0] owned;
    reg [3:0] wp,rp;
    reg [4:0] queued;
    reg [31:0] fbits[0:15];
    reg [16:0] frow[0:15];
    reg fbad[0:15];
    reg [31:0] best_key;
    wire match_input=(in_owner==owner && in_row==rank_r*ROWS+accepted);
    assign ready=OPT_NATIVE_HEAD!=0 && !active;
    assign in_ready=OPT_NATIVE_HEAD!=0 && active && !fault && !cancel &&
                    !done_valid && accepted<ROWS && owned<16 && match_input;
    wire fire=in_valid && in_ready;
    wire ack=logit_valid && logit_ready;
    assign logit_valid=(queued!=0);
    assign logit_owner=owner;
    assign logit_bits=fbits[rp];
    assign logit_row=frow[rp];
    assign logit_poison=fbad[rp];
    assign done_owner=owner;
    assign token_valid=done_valid && have_best && !fault;
    wire [31:0] y1,y2,y3;
    wire [1:0] err1,err2,err3;
    wire v1,v2,v3;
    reg [31:0] a_delay[0:5];
    reg [16:0] row_delay[0:8];
    integer i;
    // Do not remove either +0: these are the golden padded tree levels.
    ot_hdc_fp32_add_fast u_pad1(clk,rst_n,fire,root1024,32'd0,y1,err1,v1);
    ot_hdc_fp32_add_fast u_pad2(clk,rst_n,v1,y1,32'd0,y2,err2,v2);
    ot_hdc_fp32_add_fast u_join(clk,rst_n,v2,a_delay[5],y2,y3,err3,v3);
    always @(posedge clk) begin
        a_delay[0]<=root4096;
        row_delay[0]<=in_row;
        for(i=1;i<6;i=i+1) a_delay[i]<=a_delay[i-1];
        for(i=1;i<9;i=i+1) row_delay[i]<=row_delay[i-1];
    end
    wire nonfinite=(y3[30:23]==8'hff);
    wire bad3=(err3!=0)||nonfinite;
    wire [31:0] canonical=(y3==32'h80000000)?32'd0:y3;
    wire [31:0] key=canonical[31]?~canonical:{1'b1,canonical[30:0]};
    wire take_best=!have_best || key>best_key || (key==best_key && row_delay[8]<best_row);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            active<=0;have_best<=0;owner<=0;rank_r<=0;accepted<=0;owned<=0;
            wp<=0;rp<=0;queued<=0;best_key<=0;best_bits<=0;best_row<=0;
            fault<=0;done_valid<=0;
        end else if(start && ready) begin
            active<=1;owner<=start_owner;rank_r<=rank;accepted<=0;
            have_best<=0;fault<=0;done_valid<=0;
        end else if(active) begin
            if(cancel || (in_valid && !fault && owned<16 && accepted<ROWS && !match_input)) fault<=1;
            if((v1 && err1!=0)||(v2 && err2!=0)||(v3 && bad3)) fault<=1;
            owned<=owned+fire-ack;
            queued<=queued+v3-ack;
            if(fire) accepted<=accepted+1'b1;
            if(ack) rp<=rp+1'b1;
            if(v3) begin
                fbits[wp]<=y3;frow[wp]<=row_delay[8];fbad[wp]<=bad3||fault;
                wp<=wp+1'b1;
                if(!bad3 && !fault && take_best) begin
                    have_best<=1;best_key<=key;best_bits<=y3;best_row<=row_delay[8];
                end
            end
            if((accepted==ROWS || fault) && owned==0) done_valid<=1;
            if(done_valid && done_ready) begin active<=0;done_valid<=0;end
        end
    end
endmodule
