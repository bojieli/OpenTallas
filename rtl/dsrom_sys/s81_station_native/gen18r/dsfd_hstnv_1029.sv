module dsfd_hstnv_1029 (
    input wire [0:0] ck,
    input wire [1028:0] di,
    output wire [1028:0] dq
);
    reg [1028:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
