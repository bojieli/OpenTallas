module dsfd_hstnh_77 (
    input wire [0:0] ck,
    input wire [76:0] di,
    output wire [76:0] dq
);
    reg [76:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
