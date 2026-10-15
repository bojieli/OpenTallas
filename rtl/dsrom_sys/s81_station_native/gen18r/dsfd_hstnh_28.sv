module dsfd_hstnh_28 (
    input wire [0:0] ck,
    input wire [27:0] di,
    output wire [27:0] dq
);
    reg [27:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
