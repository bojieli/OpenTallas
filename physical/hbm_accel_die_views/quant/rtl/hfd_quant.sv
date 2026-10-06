// hfd_quant: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  INTERIM: ot_hdc_actquant (unchanged; routed at 0.9 GHz only, results/physical_abi3/asap7/hdc/v41/ot_hdc_actquant) behind the die ports: x = f_vm[1023:0] (32 FP32 a block); the dequantised BF16 block y[511:0] is broadcast to the four SU quarters (t_su_*). The die interface carries no valid / format bit (v is tied 1: one block a cycle, II = 1) and fp4 alternates from a wrapper toggle so both formats stay live; q / e / vo / fault have no die net (generator-side width defect).
module hfd_quant (
    input wire [0:0] ck,
    input wire [1023:0] f_vm,
    input wire [0:0] rst,
    output wire [511:0] t_su_NE,
    output wire [511:0] t_su_NW,
    output wire [511:0] t_su_SE,
    output wire [511:0] t_su_SW
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [1023:0] i_f_vm; always @(posedge clk) i_f_vm <= f_vm;
    wire [0:0] w_aq_clk;
    wire [0:0] w_aq_rst_n;
    wire [0:0] w_aq_v;
    wire [0:0] w_aq_fp4;
    wire [1023:0] w_aq_x;
    wire [0:0] w_aq_vo;
    wire [255:0] w_aq_q;
    wire [9:0] w_aq_e;
    wire [511:0] w_aq_y;
    wire [0:0] w_aq_fault;
    reg tgl; always @(posedge clk) tgl <= rst_n ? ~tgl : 1'b0;
    assign w_aq_clk = {1{clk}};
    assign w_aq_rst_n = {1{rst_n}};
    assign w_aq_v = 1'd1;
    assign w_aq_fp4 = tgl;
    assign w_aq_x = {i_f_vm[1023:0]};
    ot_hdc_actquant u_aq (.clk(w_aq_clk), .rst_n(w_aq_rst_n), .v(w_aq_v), .fp4(w_aq_fp4), .x(w_aq_x), .vo(w_aq_vo), .q(w_aq_q), .e(w_aq_e), .y(w_aq_y), .fault(w_aq_fault));
    wire [511:0] od_t_su_NE = {w_aq_y[511:0]};
    wire [511:0] o_t_su_NE;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[511:0] = o_t_su_NE[511:0];
    wire [511:0] od_t_su_NW = {w_aq_y[511:0]};
    wire [511:0] o_t_su_NW;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[511:0] = o_t_su_NW[511:0];
    wire [511:0] od_t_su_SE = {w_aq_y[511:0]};
    wire [511:0] o_t_su_SE;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[511:0] = o_t_su_SE[511:0];
    wire [511:0] od_t_su_SW = {w_aq_y[511:0]};
    wire [511:0] o_t_su_SW;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg1 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[511:0] = o_t_su_SW[511:0];
endmodule
