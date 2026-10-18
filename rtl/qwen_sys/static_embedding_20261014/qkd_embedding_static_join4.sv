`timescale 1ns/1ps
// KVJ-C2 2026-10-17 (kv_static_join_plan.md N2): the four per-stack static embedding return trains end here, beside the
// d2d KV end, in front of qkd_embedding_row_tx.  Each train root word up<s> = {record 298, v} (qkd_embedding_static_
// return_hop / _head upo; record = {epoch16, scale, half, word6, token18, data256}) is captured at a pin flop, the
// compiler makes the four trains' delivery edges disjoint, so the four captured words meet in a ONE-HOT select (never an
// arbitration: two valid on one edge latch fault), and the selected beat enters the unchanged qkd_embedding_static_join
// (its beat_slot = the compiled slot, captured on the same edge as the trains).  Added edge: +1 (the pin capture) on the
// train root -> join path; the join's own +1 is unchanged.  No credit, ready or wait.
// Proof: rtl/test/qwen_static_kv/tb_qkd_embedding_static_join4.sv (lock-step vs qkd_embedding_static_join fed the same
// beats one edge earlier).  MUT (bench only): 1 = no conflict fault; 2 = train 3 ignored.
module qkd_embedding_static_join4 #(parameter integer MUT = 0) (
    input wire ck,rst_n,
    input wire [298:0] up0,up1,up2,up3,
    input wire beat_slot,
    output wire word_v,output wire [511:0] word_data,
    output wire [17:0] word_token,output wire [5:0] word_index,
    output wire word_scale,output wire [15:0] word_epoch,
    output reg fault
);
    reg [298:0] u0,u1,u2,u3;
    reg slot_q;
    always @(posedge ck) begin u0[298:1]<=up0[298:1];u1[298:1]<=up1[298:1];u2[298:1]<=up2[298:1];u3[298:1]<=up3[298:1];end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin u0[0]<=0;u1[0]<=0;u2[0]<=0;u3[0]<=0;slot_q<=0;end
        else begin u0[0]<=up0[0];u1[0]<=up1[0];u2[0]<=up2[0];u3[0]<=up3[0];slot_q<=beat_slot;end
    wire v3=(MUT==2)?1'b0:u3[0];
    wire [3:0] hot={v3,u2[0],u1[0],u0[0]};
    wire [297:0] rec=({298{u0[0]}}&u0[298:1])|({298{u1[0]}}&u1[298:1])|({298{u2[0]}}&u2[298:1])|({298{v3}}&u3[298:1]);
    wire bv=|hot;
    wire multi=(MUT==1)?1'b0:((hot&(hot-4'd1))!=4'd0);
    wire jf;
    qkd_embedding_static_join u_join(.ck(ck),.rst_n(rst_n),.beat_slot(slot_q),.beat_v(bv),
        .beat_data(rec[255:0]),.beat_token(rec[273:256]),.beat_word(rec[279:274]),
        .beat_half(rec[280]),.beat_scale(rec[281]),.beat_epoch(rec[297:282]),
        .word_v(word_v),.word_data(word_data),.word_token(word_token),.word_index(word_index),
        .word_scale(word_scale),.word_epoch(word_epoch),.fault(jf));
    reg mf;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin mf<=0;fault<=0;end
        else begin if(multi)mf<=1;fault<=mf|jf|multi;end
endmodule
