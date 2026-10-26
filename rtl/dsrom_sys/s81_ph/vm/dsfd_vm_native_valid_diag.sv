`timescale 1ns/1ps
`default_nettype none
// Diagnostic cone of dsfd_vm_static_suhc_return_map, with real boundary capture.
// No data mux, execution gating, or normal-data latency is added. The sequence
// tile observes a sticky fault two stream edges after the old combinational cone.
module dsfd_vm_native_valid_diag (
    input wire ck, rst_n,
    input wire [31:0] i_v,
    input wire [17:0] expected_v,
    input wire [89:0] release_slot,
    input wire [15:0] i_fault,
    output reg fault
);
    reg [15:0] fault_q;
    reg [31:0] valid_q;
    reg [17:0] expected_q;
    reg [89:0] slot_q;
    wire [17:0] bad;
    genvar p;
    generate for (p = 0; p < 18; p = p + 1) begin : check_port
        wire [4:0] sel = slot_q[5*p+:5];
        wire legal = (p == 0) ? (sel < 4) :
                     (p == 1) ? (sel < 8) :
                     (p < 16) ? (sel == p) : (sel >= 16 && sel < 20);
`ifdef S81_NATIVE_DIAG_MUT_VALID
        wire present = 1'b1;
`else
        wire present = valid_q[sel];
`endif
`ifdef S81_NATIVE_DIAG_MUT_SLOT
        wire accepted = 1'b1;
`else
        wire accepted = legal;
`endif
`ifdef S81_NATIVE_DIAG_MUT_DROP
        assign bad[p] = (p == 17) ? 1'b0 : expected_q[p] && (!accepted || !present);
`else
        assign bad[p] = expected_q[p] && (!accepted || !present);
`endif
    end endgenerate
    always @(posedge ck) begin
        fault_q <= i_fault;
        valid_q <= i_v;
        expected_q <= expected_v;
        slot_q <= release_slot;
        if (!rst_n) fault <= 1'b0;
        `ifdef S81_NATIVE_DIAG_MUT_EXTRA
        else fault <= fault | (|bad);
`else
        else fault <= fault | (|bad) | (|fault_q);
`endif
    end
endmodule
`default_nettype wire
