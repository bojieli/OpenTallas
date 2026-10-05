`timescale 1ns/1ps
// Default-off ordered-root terminal reusing the unchanged ROM carried argmax. No ROM provider or core mux
// is substituted here. Reset is legal only with the external owner quiescent.
import ot_rom_coll_pkg::*;
module s81_native_head_carried #(
    parameter integer OPT_NATIVE_HEAD=0,
    parameter integer ROWS=32320,
    parameter integer RANK=0,
    parameter integer OWNER_W=47
)(
    input wire clk,rst_n,start,cancel,
    input wire [OWNER_W-1:0] start_owner,
    input wire [63:0] start_sequence,
    output wire ready,
    input wire in_valid,
    output wire in_ready,
    input wire [OWNER_W-1:0] in_owner,
    input wire [63:0] in_sequence,
    input wire [16:0] in_row,
    input wire [31:0] root4096,root1024,
    output wire logit_valid,
    input wire logit_ready,
    output wire [OWNER_W-1:0] logit_owner,
    output wire [16:0] logit_row,
    output wire [31:0] logit_bits,
    output wire logit_poison,
    input wire up_valid,
    output wire up_ready,
    input wire [511:0] up_data,
    input wire up_last,
    input wire [OWNER_W-1:0] up_owner,
    input wire [63:0] up_sequence,
    output wire dn_valid,
    input wire dn_ready,
    output wire [511:0] dn_data,
    output wire dn_last,
    output wire [OWNER_W-1:0] dn_owner,
    output wire [63:0] dn_sequence,
    output reg fault
);
    reg active,up_owned;
    reg [63:0] request_sequence;
    reg [OWNER_W-1:0] owner;
    reg [14:0] accepted;
    reg [4:0] owned;
    reg [3:0] wp,rp;
    reg [4:0] queued;
    reg [31:0] fbits[0:15];
    reg [16:0] frow[0:15];
    reg fbad[0:15];
    wire match_input=(in_owner==owner && in_sequence==request_sequence && in_row==RANK*ROWS+accepted);
    assign ready=OPT_NATIVE_HEAD!=0 && !active && !fault;
    assign in_ready=OPT_NATIVE_HEAD!=0 && active && !fault && !cancel &&
                    accepted<ROWS && owned<16 && match_input;
    wire fire=in_valid && in_ready;
    wire ack=logit_valid && logit_ready;
    assign logit_valid=(queued!=0) && (fault || native_lg_ready);
    assign logit_owner=owner;
    assign logit_bits=fbits[rp];
    assign logit_row=frow[rp];
    assign logit_poison=fbad[rp];
    wire native_lg_ready,native_dn_valid,native_up_ready,native_fault;
    wire [31:0] native_tokens;
    wire up_match=(up_owner==owner && up_sequence==request_sequence);
    assign up_ready=(RANK!=0) && active && !fault && !up_owned && up_match && native_up_ready;
    wire up_fire=up_valid && up_ready;
    assign dn_valid=active && !fault && accepted==ROWS && owned==0 && native_dn_valid;
    assign dn_owner=owner;assign dn_sequence=request_sequence;
    ot_rom_argmax_reduce #(.LANES(16),.DEPTH(8),.FIRST(RANK==0),.SELF(RANK),.NEXT(RANK+1)) u_argmax (
        .clk(clk),.rst_n(rst_n),
        .lg_valid(logit_valid && logit_ready && !fault),.lg_ready(native_lg_ready),
        .lg_data({480'd0,logit_bits}),.lg_mask(16'd1),.lg_base({15'd0,logit_row}),
        .lg_tag(8'd0),.lg_last(logit_row==RANK*ROWS+ROWS-1),
        .up_valid(up_fire),.up_ready(native_up_ready),.up_data(up_data),.up_last(up_last),
        .dn_valid(native_dn_valid),.dn_ready(dn_valid && dn_ready),.dn_data(dn_data),.dn_last(dn_last),
        .tokens_out(native_tokens),.fault(native_fault));
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
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            active<=0;up_owned<=0;owner<=0;request_sequence<=0;accepted<=0;owned<=0;
            wp<=0;rp<=0;queued<=0;
            fault<=0;
        end else if(start && ready) begin
            active<=1;owner<=start_owner;request_sequence<=start_sequence;accepted<=0;up_owned<=0;fault<=0;
        end else if(active) begin
            if(native_fault || cancel || (up_valid && active && !up_owned && !up_match) || (in_valid && !fault && owned<16 && accepted<ROWS && !match_input)) fault<=1;
            if((v1 && err1!=0)||(v2 && err2!=0)||(v3 && bad3)) fault<=1;
            if(up_fire) up_owned<=1;
            owned<=owned+fire-ack;
            queued<=queued+v3-ack;
            if(fire) accepted<=accepted+1'b1;
            if(ack) rp<=rp+1'b1;
            if(v3) begin
                fbits[wp]<=y3;frow[wp]<=row_delay[8];fbad[wp]<=bad3||fault;
                wp<=wp+1'b1;
            end
            if(dn_valid && dn_ready) begin active<=0;up_owned<=0;end
        end
    end
endmodule
