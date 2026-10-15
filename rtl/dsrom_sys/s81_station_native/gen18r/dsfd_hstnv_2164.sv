module dsfd_hstnv_2164 (
    input wire [0:0] ck,
    input wire [2163:0] di,
    output wire [2163:0] dq
);
    reg [2163:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
