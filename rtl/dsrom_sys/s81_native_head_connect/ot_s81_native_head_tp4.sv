`timescale 1ns/1ps
import ot_rom_coll_pkg::*;

// Same-clock minimum component connection for the existing carried native
// head. Roots are supplied by the actual native dot producer, never host FP.
// No registers, owner allocation, token mapping or extra execution engine.
// This direct connection is not a model of physical inter-die wire/CDC delay.
module ot_s81_native_head_tp4 #(
    parameter integer OPT_NATIVE_HEAD=0,
    parameter integer ROWS=32320
) (
    input wire clk,rst_n,
    input wire [3:0] start,cancel,
    input wire [4*47-1:0] start_owner,
    input wire [4*64-1:0] start_sequence,
    output wire [3:0] ready,
    input wire [3:0] in_valid,
    output wire [3:0] in_ready,
    input wire [4*47-1:0] in_owner,
    input wire [4*64-1:0] in_sequence,
    input wire [4*17-1:0] in_row,
    input wire [4*32-1:0] root4096,root1024,
    output wire [3:0] logit_valid,
    input wire [3:0] logit_ready,
    output wire [4*47-1:0] logit_owner,
    output wire [4*17-1:0] logit_row,
    output wire [4*32-1:0] logit_bits,
    output wire [3:0] logit_poison,
    output wire result_valid,
    input wire result_ready,
    output wire [31:0] result_global_id,result_bits,
    output wire [46:0] result_owner,
    output wire [63:0] result_sequence,
    output wire [3:0] rank_fault,
    output wire fault
);
    wire [3:0] dn_valid,dn_ready,dn_last;
    wire [4*512-1:0] dn_data;
    wire [4*47-1:0] dn_owner;
    wire [4*64-1:0] dn_sequence;
    wire [511:0] final_record=dn_data[3*512 +: 512];
    wire final_ok=dn_last[3] && final_record[H_KIND +: 4]==K_ARGMAX &&
                  final_record[H_ARG_OK] &&
                  final_record[H_ARG_ID +: 32] < 4*ROWS;
    assign fault=(|rank_fault) || (dn_valid[3] && !final_ok);
    assign result_valid=OPT_NATIVE_HEAD!=0 && dn_valid[3] && final_ok && !fault;
    assign result_global_id=final_record[H_ARG_ID +: 32];
    assign result_bits=final_record[H_ARG_VAL +: 32];
    assign result_owner=dn_owner[3*47 +: 47];
    assign result_sequence=dn_sequence[3*64 +: 64];
    // The final terminal retains its native output until the actual consumer
    // accepts it. A fault does not retire that frame or its accepted debt.
    assign dn_ready[3]=result_valid && result_ready;

    genvar r;
    generate for(r=0;r<4;r=r+1) begin: g_rank
        wire up_valid,up_ready,up_last;
        wire [511:0] up_data;
        wire [46:0] up_owner;
        wire [63:0] up_sequence;
        if(r==0) begin: g_first
            assign up_valid=1'b0;
            assign up_last=1'b0;
            assign up_data=512'd0;
            assign up_owner=47'd0;
            assign up_sequence=64'd0;
        end else begin: g_link
            // Ascending vocabulary IDs/ranks preserve low-ID ties. Forward
            // the complete existing envelope; native tag8 is never an owner.
            assign up_valid=dn_valid[r-1];
            assign up_last=dn_last[r-1];
            assign up_data=dn_data[(r-1)*512 +: 512];
            assign up_owner=dn_owner[(r-1)*47 +: 47];
            assign up_sequence=dn_sequence[(r-1)*64 +: 64];
            assign dn_ready[r-1]=up_ready;
        end
        s81_native_head_carried #(
            .OPT_NATIVE_HEAD(OPT_NATIVE_HEAD),.ROWS(ROWS),.RANK(r),.OWNER_W(47)
        ) u_head (
            .clk(clk),.rst_n(rst_n),.start(start[r]),.cancel(cancel[r]),
            .start_owner(start_owner[r*47 +: 47]),
            .start_sequence(start_sequence[r*64 +: 64]),.ready(ready[r]),
            .in_valid(in_valid[r]),.in_ready(in_ready[r]),
            .in_owner(in_owner[r*47 +: 47]),.in_sequence(in_sequence[r*64 +: 64]),
            .in_row(in_row[r*17 +: 17]),
            .root4096(root4096[r*32 +: 32]),.root1024(root1024[r*32 +: 32]),
            .logit_valid(logit_valid[r]),.logit_ready(logit_ready[r]),
            .logit_owner(logit_owner[r*47 +: 47]),.logit_row(logit_row[r*17 +: 17]),
            .logit_bits(logit_bits[r*32 +: 32]),.logit_poison(logit_poison[r]),
            .up_valid(up_valid),.up_ready(up_ready),.up_data(up_data),.up_last(up_last),
            .up_owner(up_owner),.up_sequence(up_sequence),
            .dn_valid(dn_valid[r]),.dn_ready(dn_ready[r]),
            .dn_data(dn_data[r*512 +: 512]),.dn_last(dn_last[r]),
            .dn_owner(dn_owner[r*47 +: 47]),.dn_sequence(dn_sequence[r*64 +: 64]),
            .fault(rank_fault[r])
        );
    end endgenerate
endmodule
