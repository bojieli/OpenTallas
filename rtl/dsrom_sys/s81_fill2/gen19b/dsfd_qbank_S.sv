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
    reg rn; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rn <= 1'b0; else rn <= 1'b1; // initialization only: async assert, release +1 edge; no normal data edge
    // S81-KITS-RTLC 10-24 (owner: register every partition pin, in RTL): every input lands in its own pin register
    // (l_*) and every output leaves its own pin register (r_*): 2 flops per bit, +1 cycle per q-bank S station.
    reg [53:0] l_cfg;
    always @(posedge ck[0] or negedge rn) if (!rn) l_cfg <= 54'd0; else l_cfg <= i_cfg;
    reg [53:0] r_cfg;
    always @(posedge ck[0] or negedge rn) if (!rn) r_cfg <= 54'd0; else r_cfg <= l_cfg;
    assign o_cfg = r_cfg;
    reg [0:0] l_go;
    always @(posedge ck[0] or negedge rn) if (!rn) l_go <= 1'd0; else l_go <= i_go;
    reg [0:0] r_go;
    always @(posedge ck[0] or negedge rn) if (!rn) r_go <= 1'd0; else r_go <= l_go;
    assign o_go = r_go;
    reg [282:0] l_x0;
    always @(posedge ck[0] or negedge rn) if (!rn) l_x0 <= 283'd0; else l_x0 <= i_x0;
    reg [282:0] r_x0;
    always @(posedge ck[0] or negedge rn) if (!rn) r_x0 <= 283'd0; else r_x0 <= l_x0;
    assign o_x0 = r_x0;
    reg [265:0] l_x1;
    always @(posedge ck[0] or negedge rn) if (!rn) l_x1 <= 266'd0; else l_x1 <= i_x1;
    reg [265:0] r_x1;
    always @(posedge ck[0] or negedge rn) if (!rn) r_x1 <= 266'd0; else r_x1 <= l_x1;
    assign o_x1 = r_x1;
endmodule
