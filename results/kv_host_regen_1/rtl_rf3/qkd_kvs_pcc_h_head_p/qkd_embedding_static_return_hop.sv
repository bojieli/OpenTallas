`timescale 1ns/1ps
// Static successor of the embedding-return portion of qkd_land_pc. One retained
// actual beat, pin capture plus output station (two sampled edges per hop).
// Compiler injects each local beat before its reserved through train arrives.
// A conflict/missing/late beat faults; there is no POP queue, priority or wait.
module qkd_embedding_static_return_hop(
    input wire ck,rst_n,
    input wire capture_slot,capture_v,input wire [297:0] capture_record,
    input wire transfer_slot,
    input wire [298:0] upi,output reg [298:0] upo,
    output reg fault
);
    reg cs_q,cv_q,ts_q;
    reg [297:0] record_q,retained;
    reg [298:0] up_q;
    reg occupied;
    always @(posedge ck) begin
        record_q<=capture_record;up_q[298:1]<=upi[298:1];
        if(cs_q&&cv_q)retained<=record_q;
        upo[298:1]<=ts_q?retained:up_q[298:1];
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin cs_q<=0;cv_q<=0;ts_q<=0;up_q[0]<=0;upo[0]<=0;occupied<=0;fault<=0;end
        else begin
            cs_q<=capture_slot;cv_q<=capture_v;ts_q<=transfer_slot;up_q[0]<=upi[0];
            upo[0]<=up_q[0]||ts_q;
            if(ts_q)occupied<=0;
            if(cs_q&&cv_q)occupied<=1;
            if(cs_q!=cv_q||(ts_q&&up_q[0])||(ts_q&&!occupied)||
               (cs_q&&occupied)||(cs_q&&ts_q))fault<=1;
        end
endmodule
