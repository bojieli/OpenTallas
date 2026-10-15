module dsfd_hstnv_4 (
    input wire [0:0] ck,
    input wire [3:0] di,
    output wire [3:0] dq
);
    reg [3:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
