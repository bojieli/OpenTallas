module \$dff (CLK, D, Q);
    parameter WIDTH = 1;
    parameter CLK_POLARITY = 1'b1;
    input CLK;
    input [WIDTH-1:0] D;
    output [WIDTH-1:0] Q;
    assign Q = D;
endmodule

module \$_DFF_P_ (C, D, Q);
    input C, D;
    output Q;
    assign Q = D;
endmodule

module \$_DFF_N_ (C, D, Q);
    input C, D;
    output Q;
    assign Q = D;
endmodule
