module dsfd_hstnv_690 (
    input wire [0:0] ck,
    input wire [689:0] di,
    output wire [689:0] dq
);
    reg [689:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
