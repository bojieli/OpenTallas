module dsfd_rly_1_EW (
    input wire [0:0] ck,
    input wire [0:0] i,
    output wire [0:0] o,
    input wire [0:0] rs
);
    reg [0:0] r; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r <= 1'd0; else r <= i;
    assign o = r;
endmodule
module dsfd_rly_1_WE (
    input wire [0:0] ck,
    input wire [0:0] i,
    output wire [0:0] o,
    input wire [0:0] rs
);
    reg [0:0] r; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r <= 1'd0; else r <= i;
    assign o = r;
endmodule
module dsfd_rly_1_WN (
    input wire [0:0] ck,
    input wire [0:0] i,
    output wire [0:0] o,
    input wire [0:0] rs
);
    reg [0:0] r; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r <= 1'd0; else r <= i;
    assign o = r;
endmodule
