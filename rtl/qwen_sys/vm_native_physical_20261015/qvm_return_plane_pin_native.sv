`timescale 1ns/1ps
// Actual source pin stage, followed by the original three return stages.
// All controls/data take the same one edge. There is no ready/credit path.
module qvm_return_plane_pin_native #(
    parameter integer ELEMS=177808, AW=24, SW=64, NRBS=16, MUT=0
)(
    input wire ck,v5,v6,v7,
    input wire [AW-1:0] a5,a6,a7,
    input wire stride1,
    input wire [NRBS*16-1:0] d,
    output wire [SW-1:0] q
);
    localparam integer PIN_W=3+3*AW+1+NRBS*16;
    // Preserve sampled unused address bits as real input-pin flops as well.
    (* keep="true", dont_touch="true" *) reg [PIN_W-1:0] pin_q;
    always @(posedge ck) pin_q <= {v5,v6,v7,a5,a6,a7,stride1,d};
    wire pv5,pv6,pv7,psi;
    wire [AW-1:0] pa5,pa6,pa7;
    wire [NRBS*16-1:0] pd;
    assign {pv5,pv6,pv7,pa5,pa6,pa7,psi,pd}=pin_q;
    ot_qfd_vm_su_return_plane #(.ELEMS(ELEMS),.AW(AW),.SW(SW),.NRBS(NRBS),.MUT(MUT)) u_core(
        .ck(ck),.v5(pv5),.v6(pv6),.v7(pv7),.a5(pa5),.a6(pa6),.a7(pa7),.stride1(psi),.d(pd),.q(q));
endmodule
