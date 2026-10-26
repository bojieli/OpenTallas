module dsfd_hstnv_759 (
    input wire [0:0] ck,
    input wire [758:0] di,
    output wire [758:0] dq
);
    reg [758:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
