module dsfd_hstnh_560 (
    input wire [0:0] ck,
    input wire [559:0] di,
    output wire [559:0] dq
);
    reg [559:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
