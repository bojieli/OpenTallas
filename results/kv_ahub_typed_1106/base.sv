module qkd_ahub_static_dw #(parameter [63:0] AP_OFS=0, parameter integer FR_OFS=0,Z_IN_STRIDE=0) (input ck,input[42:0]ap0,ap1,ap2,ap3,output reg[35:0]am0,am1,am2,am3);
always @(posedge ck) begin am0<=ap0[35:0];am1<=ap1[35:0];am2<=ap2[35:0];am3<=ap3[35:0];end
endmodule
module qkd_ahub(input[6:0]ck,input[42:0]ap0,ap1,ap2,ap3,output reg[34:0]am0,am1,am2,am3);
always @(posedge ck[0]) am0<={ap0[35:2],ap0[0]};
always @(posedge ck[1]) am1<={ap1[35:2],ap1[0]};
always @(posedge ck[2]) am2<={ap2[35:2],ap2[0]};
always @(posedge ck[3]) am3<={ap3[35:2],ap3[0]};
endmodule
module gold (
    input wire ck,
    input wire [42:0] ap0,ap1,ap2,ap3,
    output wire [34:0] o0,o1,o2,o3
);
    wire [35:0] a0,a1,a2,a3;
    qkd_ahub_static_dw #(.AP_OFS(64'hffddffdcffdfffdf), .FR_OFS(-7), .Z_IN_STRIDE(4)) u_ahub (
        .ck(ck),
        .am0(a0), .am1(a1), .am2(a2), .am3(a3),
        .ap0(ap0), .ap1(ap1), .ap2(ap2), .ap3(ap3)
    );
    assign o0={a0[35:2],a0[0]}; assign o1={a1[35:2],a1[0]};
    assign o2={a2[35:2],a2[0]}; assign o3={a3[35:2],a3[0]};
endmodule
module gate (
    input wire ck,
    input wire [42:0] ap0,ap1,ap2,ap3,
    output wire [34:0] o0,o1,o2,o3
);
    wire [35:0] a0,a1,a2,a3;
    qkd_ahub u_ahub (
        .ck({7{ck}}),
        .am0({a0[35:2], a0[0]}), .am1({a1[35:2], a1[0]}), .am2({a2[35:2], a2[0]}), .am3({a3[35:2], a3[0]}),
        .ap0(ap0), .ap1(ap1), .ap2(ap2), .ap3(ap3)
    );
    assign o0={a0[35:2],a0[0]}; assign o1={a1[35:2],a1[0]};
    assign o2={a2[35:2],a2[0]}; assign o3={a3[35:2],a3[0]};
endmodule
