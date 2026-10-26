module dsfd_hstnh_4096 (
    input wire [0:0] ck,
    input wire [4095:0] di,
    output wire [4095:0] dq
);
    reg [4095:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
