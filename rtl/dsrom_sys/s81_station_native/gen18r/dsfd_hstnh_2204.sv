module dsfd_hstnh_2204 (
    input wire [0:0] ck,
    input wire [2203:0] di,
    output wire [2203:0] dq
);
    reg [2203:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
