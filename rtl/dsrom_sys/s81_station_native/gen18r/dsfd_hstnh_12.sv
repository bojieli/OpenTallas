module dsfd_hstnh_12 (
    input wire [0:0] ck,
    input wire [11:0] di,
    output wire [11:0] dq
);
    reg [11:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
