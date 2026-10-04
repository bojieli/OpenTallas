`timescale 1ns/1ps
// Default-off component: same selected native R128 writer argmax, ranks1..3.
// This wrapper adds no registers, arithmetic, winner or ownership state.
// write_ready is the REAL native ingress credit; keep the source/VM request
// held when low. Collective/final ports require the existing real TP4 owner.
module DsromHeadStream #(parameter integer RANK=1, R=128, AW=30, NW=21) (
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
    output wire write_ready,
    output wire [1:0] source_rank,
    output wire busy,result_seen,
    output wire [NW-1:0] am_idx,
    output wire [31:0] am_val,
    output wire am_any,fault
);
    initial if(RANK<1 || RANK>3 || R!=128 || AW!=30 || NW!=21) $fatal(1,"rank0 remains the existing core hook");
    ot_dsrom_s81_head_amax #(.R(R),.AW(AW),.NW(NW),.RANK(RANK)) dut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .identity(identity),
        .nout(nout),
        .obase(obase),
        .write_valid(write_valid),
        .write_accept(write_accept),
        .write_address(write_address),
        .write_bits(write_bits),
        .upstream_valid(upstream_valid),
        .upstream_ready(upstream_ready),
        .upstream_data(upstream_data),
        .upstream_last(upstream_last),
        .upstream_identity(upstream_identity),
        .downstream_valid(downstream_valid),
        .downstream_ready(downstream_ready),
        .downstream_data(downstream_data),
        .downstream_last(downstream_last),
        .downstream_identity(downstream_identity),
        .final_valid(final_valid),
        .final_ready(final_ready),
        .final_data(final_data),
        .final_identity(final_identity),
        .busy(busy),
        .result_seen(result_seen),
        .am_idx(am_idx),
        .am_val(am_val),
        .am_any(am_any),
        .fault(fault)
    );
    assign write_ready=dut.busy && !dut.fault && dut.native_ready;
    assign source_rank=2'(RANK);
endmodule
