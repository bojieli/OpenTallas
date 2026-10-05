`timescale 1ns/1ps
import ot_rom_coll_pkg::*;
// Actual already-accepted FP32 ROM writes; no dot, host logits or new VM.
module ot_dsrom_s81_head_amax #(
    parameter integer R=128,AW=30,NW=21,RANK=0
)(
    input wire clk,rst_n,start,
    input wire [46:0] identity,
    input wire [NW-1:0] nout,
    input wire [AW-1:0] obase,
    input wire [R-1:0] write_valid,write_accept,
    input wire [R*AW-1:0] write_address,
    input wire [R*32-1:0] write_bits,
    input wire upstream_valid,
    output wire upstream_ready,
    input wire [511:0] upstream_data,
    input wire upstream_last,
    input wire [46:0] upstream_identity,
    output wire downstream_valid,
    input wire downstream_ready,
    output wire [511:0] downstream_data,
    output wire downstream_last,
    output wire [46:0] downstream_identity,
    input wire final_valid,
    output wire final_ready,
    input wire [511:0] final_data,
    input wire [46:0] final_identity,
    output reg busy,result_seen,
    output reg [NW-1:0] am_idx,
    output reg [31:0] am_val,
    output reg am_any,fault
);
    reg [46:0] owner;
    reg [NW-1:0] expected,seen;
    reg [AW-1:0] base;
    reg up_owned,forwarded;
    assign final_ready=busy && forwarded && !fault && final_identity==owner;
    wire [R-1:0] mask=write_valid & write_accept & {R{busy}};
    wire native_ready,native_fault,up_ready,dn_valid;
    wire [31:0] tokens;
    reg [R*32-1:0] ids;
    integer j,accepted;
    reg range_fault,nonfinite;
    always @* begin
        accepted=0;ids=0;range_fault=0;nonfinite=0;
        for(j=0;j<R;j=j+1) begin
            ids[32*j+:32]=RANK*32320+write_address[AW*j+:AW]-base;
            if(mask[j]) begin
                accepted=accepted+1;
                if(write_address[AW*j+:AW]<base || write_address[AW*j+:AW]>=base+expected) range_fault=1;
                if(write_bits[32*j+23+:8]==8'hff) nonfinite=1;
            end
        end
    end
    wire match_owner=upstream_identity==owner;
    assign upstream_ready=busy && !fault && !up_owned && match_owner && up_ready;
    assign downstream_valid=busy && !fault && seen==expected && dn_valid;
    assign downstream_identity=owner;
    ot_rom_argmax_rows #(.LANES(R),.DEPTH(8),.FIRST(RANK==0),.SELF(RANK),.NEXT(RANK+1)) u_native (
        .clk(clk),.rst_n(rst_n),.lg_valid((|mask) && !fault && !range_fault && !nonfinite),
        .lg_ready(native_ready),.lg_data(write_bits),.lg_mask(mask),.lg_ids(ids),.lg_base(32'd0),
        .lg_tag(8'd0),.lg_last(seen+accepted==expected),
        .up_valid(upstream_valid && upstream_ready),.up_ready(up_ready),
        .up_data(upstream_data),.up_last(upstream_last),
        .dn_valid(dn_valid),.dn_ready(downstream_valid && downstream_ready),
        .dn_data(downstream_data),.dn_last(downstream_last),.tokens_out(tokens),.fault(native_fault));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            busy<=0;result_seen<=0;am_idx<=0;am_val<=0;am_any<=0;fault<=0;
            owner<=0;expected<=0;seen<=0;base<=0;up_owned<=0;forwarded<=0;
        end else begin
            if(start) begin
                if(busy || fault || nout==0 || nout>32320) fault<=1;
                else begin
                    busy<=1;result_seen<=0;owner<=identity;expected<=nout;seen<=0;
                    base<=obase;am_any<=0;up_owned<=0;forwarded<=0;
                end
            end
            if(busy) begin
                if(native_fault || range_fault || nonfinite || seen+accepted>expected || ((|mask)&&!native_ready)) fault<=1;
                if(upstream_valid && !up_owned && !match_owner) fault<=1;
                if(upstream_valid && upstream_ready) up_owned<=1;
                seen<=seen+NW'(accepted);
                if(downstream_valid && downstream_ready) forwarded<=1;
                if(final_valid && final_ready) begin
                    if(final_data[H_KIND+:4]!=K_ARGMAX || !final_data[H_ARG_OK] ||
                       final_data[H_ARG_ID+:32]>=129280 || final_data[H_ARG_VAL+23+:8]==8'hff) fault<=1;
                    else begin
                        am_idx<=NW'(final_data[H_ARG_ID+:32]);am_val<=final_data[H_ARG_VAL+:32];
                        am_any<=1;result_seen<=1;busy<=0;
                    end
                end
            end
        end
    end
endmodule
