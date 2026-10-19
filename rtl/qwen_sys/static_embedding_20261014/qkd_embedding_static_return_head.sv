`timescale 1ns/1ps
// KVJ-C2 2026-10-17: the HEAD station of a per-stack static embedding return train (physical slot 0, the far end of the
// strip).  It is qkd_embedding_static_return_hop with no upstream: the train starts here, so the station has no upi face
// (a hop's upi at the train head would otherwise be a tied die-top input).  Same capture slot, retained beat, transfer
// slot, the same two sampled edges and the same fault terms with upi = 0 (an upstream beat can never collide).
// upo = {record 298, v}; record = {epoch16 [297:282], scale [281], half [280], word6 [279:274], token18 [273:256],
// data256 [255:0]} (the layout qkd_embedding_static_join4 unpacks).
// Proof: rtl/test/qwen_static_kv/tb_qkd_embedding_return_head.sv (lock-step vs the hop with upi = 0).
// MUT (bench only): 1 = transfer without an occupied beat does not fault.
module qkd_embedding_static_return_head #(parameter integer MUT = 0) (
    input wire ck,rst_n,
    input wire capture_slot,capture_v,input wire [297:0] capture_record,
    input wire transfer_slot,
    output reg [298:0] upo,
    output reg fault
);
    reg cs_q,cv_q,ts_q;
    reg [297:0] record_q,retained;
    reg occupied;
    always @(posedge ck) begin
        record_q<=capture_record;
        if(cs_q&&cv_q)retained<=record_q;
        upo[298:1]<=ts_q?retained:298'd0;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin cs_q<=0;cv_q<=0;ts_q<=0;upo[0]<=0;occupied<=0;fault<=0;end
        else begin
            cs_q<=capture_slot;cv_q<=capture_v;ts_q<=transfer_slot;
            upo[0]<=ts_q;
            if(ts_q)occupied<=0;
            if(cs_q&&cv_q)occupied<=1;
            if(cs_q!=cv_q||(ts_q&&!occupied&&MUT!=1)||(cs_q&&occupied)||(cs_q&&ts_q))fault<=1;
        end
endmodule
