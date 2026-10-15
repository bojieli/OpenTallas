module dsfd_hstnh_1024 (
    input wire [0:0] ck,
    input wire [1023:0] di,
    output wire [1023:0] dq
);
    reg [1023:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
