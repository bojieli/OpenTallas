module dsfd_qbank_N (
    input wire [0:0] ck,
    output wire [62:0] d_r0,
    output wire [62:0] d_r1,
    output wire [1:0] d_st,
    input wire [62:0] e_r0,
    input wire [62:0] e_r1,
    input wire [1:0] e_st,
    input wire [0:0] rs
);
    reg [62:0] r_r0;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_r0 <= 63'd0; else r_r0 <= e_r0;
    assign d_r0 = r_r0;
    reg [62:0] r_r1;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_r1 <= 63'd0; else r_r1 <= e_r1;
    assign d_r1 = r_r1;
    reg [1:0] r_st;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_st <= 2'd0; else r_st <= e_st;
    assign d_st = r_st;
endmodule
