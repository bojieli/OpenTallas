`timescale 1ns/1ps
// One endpoint on the persistent controller's *embedding* es288/er261 face.
// A compiler reservation emits the read immediately. Its separately compiled
// return slot must coincide with the actual controller er valid. No credit,
// pending bit or return valid can postpone either operation.
module qkd_embedding_static_pc #(
    parameter integer STACK=0,PC=0,ROW0=24427
)(input wire ck,rst_n,boot_ready,
  input wire issue_v,input wire [17:0] token,input wire [5:0] word_index,
  input wire half,scale,input wire [15:0] epoch,
  input wire return_slot,
  output reg [287:0] es,input wire [260:0] er,
  output reg beat_v,output reg [255:0] beat_data,
  output reg [17:0] beat_token,output reg [5:0] beat_word,
  output reg beat_half,beat_scale,output reg [15:0] beat_epoch,
  output reg corrected,output reg fault,output wire outstanding);
    wire [24:0] sector;
    wire [1:0] stack;
    wire [4:0] pc,bank,col;
    wire [18:0] row;
    wire valid_address;
    qkd_embedding_static_map #(.ROW0(ROW0)) u_map(
        .token(token),.word_index(word_index),.half(half),.scale(scale),
        .logical_sector(sector),.stack(stack),.pc(pc),.bank(bank),.col(col),
        .row(row),.valid_address(valid_address));
    reg pending;
    reg [17:0] token_q;
    reg [5:0] word_q;
    reg half_q,scale_q;
    reg [15:0] epoch_q;
    assign outstanding=pending;
    always @(posedge ck) begin
        es[287:1] <= {1'b0,1'b0,bank,col,row,256'd0};
        if(issue_v) begin token_q<=token;word_q<=word_index;half_q<=half;scale_q<=scale;epoch_q<=epoch;end
        beat_data<=er[256:1];beat_token<=token_q;beat_word<=word_q;
        beat_half<=half_q;beat_scale<=scale_q;beat_epoch<=epoch_q;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin pending<=0;beat_v<=0;corrected<=0;fault<=0;es[0]<=0;end
        else begin
            es[0]<=issue_v;
            beat_v<=return_slot;
            corrected<=return_slot&&er[257];
            if(return_slot) pending<=0;
            if(issue_v) pending<=1;
            if(issue_v&&(!boot_ready||pending||!valid_address||stack!=STACK||pc!=PC)) fault<=1;
            if(return_slot!=er[0] || (return_slot&&!pending) || er[260] || (return_slot&&er[258])) fault<=1;
        end
endmodule
