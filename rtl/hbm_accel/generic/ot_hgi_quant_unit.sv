`timescale 1ns/1ps
`default_nettype none
// HGI-1 quant unit (FUSED.QDQ_*) as one die block body (hgi-takeover 2026-10-09): the normative record bus
// (ot_hgi_quant_record) -> the qualified VM transport (ot_hgi_quant_vm_transport, which owns the 23-edge decode core)
// -> the VM packet client.  Die-side protocol: one VM request outstanding (the transport issues its next request only
// after the response of the previous one), so the request needs no ready (the VM station holds it) and the response
// needs no back-pressure.  Return = {fault, done, ready}.
module ot_hgi_quant_unit (
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
    // the die station accepts one request; the transport keeps req_v until req_r: hand it a one-cycle accept
    reg sent;
    wire take = req_v && !sent;
    ot_hgi_quant_vm_transport #(.ENABLE(1)) u_tr (.clk(clk), .rst_n(rst_n), .cmd(cmd), .ready(ready), .done(done),
        .fault(fault), .drained(drained), .req_v(req_v), .req_r(take), .req(req), .rsp_v(vmr[273]), .rsp_r(rsp_r),
        .rsp(vmr[272:0]), .provider_fault(1'b0));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sent <= 1'b0; vmq <= 338'd0; ret <= 3'd0; end
        else begin
            if (take) sent <= 1'b1; else if (vmr[273]) sent <= 1'b0;
            vmq <= {take, req};
            ret <= {fault | nfault, done, ready & drained};
        end
endmodule
`default_nettype wire
