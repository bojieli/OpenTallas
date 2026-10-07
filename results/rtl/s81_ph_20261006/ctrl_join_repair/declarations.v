module ctrl_NE(
    inout wire [22237:0] phy,
    output wire [8895:0] rd,
    output wire [31:0] rk,
    input wire [10911:0] rq,
    output wire [31:0] wd
); endmodule // DECLARATION ONLY
module ctrl_NW(
    inout wire [22237:0] phy,
    output wire [8895:0] rd,
    output wire [31:0] rk,
    input wire [10911:0] rq,
    output wire [31:0] wd
); endmodule // DECLARATION ONLY
module ctrl_SE(
    inout wire [22237:0] phy,
    output wire [8895:0] rd,
    output wire [31:0] rk,
    input wire [10911:0] rq,
    output wire [31:0] wd
); endmodule // DECLARATION ONLY
module ctrl_SW(
    inout wire [22237:0] phy,
    output wire [8895:0] rd,
    output wire [31:0] rk,
    input wire [10911:0] rq,
    output wire [31:0] wd
); endmodule // DECLARATION ONLY
module phy_NE(
    inout wire [22237:0] dfi
); endmodule // DECLARATION ONLY
module phy_NW(
    inout wire [22237:0] dfi
); endmodule // DECLARATION ONLY
module phy_SE(
    inout wire [22237:0] dfi
); endmodule // DECLARATION ONLY
module phy_SW(
    inout wire [22237:0] dfi
); endmodule // DECLARATION ONLY
module svc_NE(
    input wire [8895:0] rd,
    input wire [31:0] rk,
    output wire [10911:0] rq,
    input wire [31:0] wd
); endmodule // DECLARATION ONLY
module svc_NW(
    input wire [8895:0] rd,
    input wire [31:0] rk,
    output wire [10911:0] rq,
    input wire [31:0] wd
); endmodule // DECLARATION ONLY
module svc_SE(
    input wire [8895:0] rd,
    input wire [31:0] rk,
    output wire [10911:0] rq,
    input wire [31:0] wd
); endmodule // DECLARATION ONLY
module svc_SW(
    input wire [8895:0] rd,
    input wire [31:0] rk,
    output wire [10911:0] rq,
    input wire [31:0] wd
); endmodule // DECLARATION ONLY