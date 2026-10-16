module dsfd_qbank_S (
    input wire [0:0] ck,
    input wire [53:0] i_cfg,
    input wire [0:0] i_go,
    input wire [282:0] i_x0,
    input wire [265:0] i_x1,
    output wire [53:0] o_cfg,
    output wire [0:0] o_go,
    output wire [282:0] o_x0,
    output wire [265:0] o_x1,
    input wire [0:0] rs
);
    reg [53:0] r_cfg;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_cfg <= 54'd0; else r_cfg <= i_cfg;
    assign o_cfg = r_cfg;
    reg [0:0] r_go;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_go <= 1'd0; else r_go <= i_go;
    assign o_go = r_go;
    reg [282:0] r_x0;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_x0 <= 283'd0; else r_x0 <= i_x0;
    assign o_x0 = r_x0;
    reg [265:0] r_x1;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) r_x1 <= 266'd0; else r_x1 <= i_x1;
    assign o_x1 = r_x1;
endmodule
