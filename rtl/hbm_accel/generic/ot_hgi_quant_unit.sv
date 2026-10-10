`timescale 1ns/1ps
`default_nettype none
// HGI-1 quant unit (FUSED.QDQ_*) as one die block body (hgi-takeover 2026-10-09): the normative record bus
// (ot_hgi_quant_record) -> the qualified VM transport (ot_hgi_quant_vm_transport, which owns the 23-edge decode core)
// -> the VM packet client.  Die-side protocol: the VM fast path -- up to 4 requests outstanding (the transport counts
// them), in-order responses; the request needs no ready (the VM station queues 4) and the response no back-pressure.
// Return = {fault, done, ready}.
module ot_hgi_quant_unit #(
    parameter integer SERIAL_SHAPE = 0,
    parameter integer MUT = 0          // bench: transport MUTANT (4 = responses paired with the newest request)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,           // {n_O, n_A, desc_O, desc_A, header, valid}
    output reg  [2:0]    ret,           // {fault, done, ready}
    output reg  [337:0]  vmq,           // {v, req 337}
    input  wire [273:0]  vmr            // {v, rsp 273}
);
    wire [1408:0] cmd;
    wire nfault, ready, done, fault, drained, req_v, rsp_r;
    wire [336:0] req;
    ot_hgi_quant_record u_rec (.clk(clk), .rst_n(rst_n), .rec(rec), .cmd(cmd), .nfault(nfault));
    // the die station queues the request: every staged request is taken the next cycle
    wire take = req_v;
    ot_hgi_quant_vm_transport #(.ENABLE(1), .MUTANT(MUT), .SERIAL_SHAPE(SERIAL_SHAPE)) u_tr (.clk(clk), .rst_n(rst_n), .cmd(cmd), .ready(ready), .done(done),
        .fault(fault), .drained(drained), .req_v(req_v), .req_r(take), .req(req), .rsp_v(vmr[273]), .rsp_r(rsp_r),
        .rsp(vmr[272:0]), .provider_fault(1'b0));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vmq <= 338'd0; ret <= 3'd0; end
        else begin
            vmq <= {take, req};
            ret <= {fault | nfault, done, ready & drained};
        end
endmodule
`default_nettype wire
