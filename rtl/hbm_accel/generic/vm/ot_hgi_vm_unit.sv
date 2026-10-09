`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM block body (hgi-takeover 2026-10-09): ot_hgi_vm_core + one die station per packet client.  Die protocol:
// a client keeps at most one request outstanding (it sends the next only after its response), so a request carries
// only a valid bit (the station holds it until the core grants it) and a response needs no back-pressure.  A request
// that arrives while the client's station is still full is a protocol violation: it latches proto_fault.
// status = {proto_fault, mask_fault, ue, ce[15:0]} (19 b) to the command processor (UE / faults halt the CP).
module ot_hgi_vm_unit #(
    parameter integer NC = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,         // per client {v, req 337}
    output reg  [NC*274-1:0] cr,         // per client {v, rsp 273}
    output reg  [18:0]       status
);
    reg  [NC-1:0]     h_v;
    reg  [NC*337-1:0] h_q;
    wire [NC-1:0]     req_r, rsp_v;
    wire [NC*273-1:0] rsp;
    wire [15:0] ce; wire ue, mask_fault;
    reg proto;
    ot_hgi_vm_core #(.NC(NC)) u_core (.clk(clk), .rst_n(rst_n), .req_v(h_v), .req_r(req_r), .req(h_q), .rsp_v(rsp_v),
        .rsp_r({NC{1'b1}}), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault),
        .inj_v(1'b0), .inj_bank(5'd0), .inj_word(3'd0), .inj_mask(39'd0));
    integer c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin h_v <= {NC{1'b0}}; proto <= 1'b0; cr <= {NC*274{1'b0}}; status <= 19'd0; end
        else begin
            for (c = 0; c < NC; c = c + 1) begin
                if (cq[c*338 + 337]) begin
                    if (h_v[c] && !req_r[c]) proto <= 1'b1;
                    h_v[c] <= 1'b1; h_q[c*337 +: 337] <= cq[c*338 +: 337];
                end else if (req_r[c]) h_v[c] <= 1'b0;
                cr[c*274 +: 274] <= {rsp_v[c], rsp[c*273 +: 273]};
            end
            status <= {proto, mask_fault, ue, ce};
        end
endmodule
`default_nettype wire
