module dsfd_hstnh_6 (
    input wire [0:0] ck,
    input wire [5:0] di,
    output wire [5:0] dq
);
    reg [5:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
