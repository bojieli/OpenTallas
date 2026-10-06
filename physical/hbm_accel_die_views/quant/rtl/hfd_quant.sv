// hfd_quant: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  Quant view: ot_hfd_actquant_m (make_actquant_m.py: margin-first port of the 1.2 GHz ot_dsrom_actquant_f12, lever su_swiglu 1d4ea2dc2; exact vs ot_hdc_actquant and f12 on 87,475 blocks, tb_aq_equiv.sv; LATENCY 22 = original 13 + 9, f12 + 4) behind the die ports: x = f_vm[1023:0] (32 FP32 a block); the dequantised BF16 block y[511:0] is broadcast to the four SU quarters (t_su_*). The die interface carries no valid / format bit (v tied 1, II = 1) and fp4 alternates from a wrapper toggle so both formats stay live; q / e / vo / fault have no die net (generator-side width defect): they end in kept sink flops.
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
    reg [1023:0] i0_f_vm; always @(posedge clk) i0_f_vm <= f_vm;
    reg [1023:0] i_f_vm; always @(posedge clk) i_f_vm <= i0_f_vm;
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
    ot_hfd_actquant_m #(.MLAT(5)) u_aq (.clk(w_aq_clk), .rst_n(w_aq_rst_n), .v(w_aq_v), .fp4(w_aq_fp4), .x(w_aq_x), .vo(w_aq_vo), .q(w_aq_q), .e(w_aq_e), .y(w_aq_y), .fault(w_aq_fault));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_aq_vo
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_aq_vo[k]), .q());
    end
    for (genvar k = 0; k < 256; k = k + 1) begin : g_sink_w_aq_q
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_aq_q[k]), .q());
    end
    for (genvar k = 0; k < 10; k = k + 1) begin : g_sink_w_aq_e
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_aq_e[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_aq_fault
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_aq_fault[k]), .q());
    end
    wire [511:0] od_t_su_NE = {w_aq_y[511:0]};
    wire [511:0] o_t_su_NE;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_NE
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_su_NE[k]), .q(o_t_su_NE[k]));
    end
    assign t_su_NE[511:0] = o_t_su_NE[511:0];
    wire [511:0] od_t_su_NW = {w_aq_y[511:0]};
    wire [511:0] o_t_su_NW;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_NW
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_NW[k]), .q(o_t_su_NW[k]));
    end
    assign t_su_NW[511:0] = o_t_su_NW[511:0];
    wire [511:0] od_t_su_SE = {w_aq_y[511:0]};
    wire [511:0] o_t_su_SE;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_SE
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_su_SE[k]), .q(o_t_su_SE[k]));
    end
    assign t_su_SE[511:0] = o_t_su_SE[511:0];
    wire [511:0] od_t_su_SW = {w_aq_y[511:0]};
    wire [511:0] o_t_su_SW;
    for (genvar k = 0; k < 512; k = k + 1) begin : g_o_t_su_SW
        ot_hfd_oreg4 u (.clk(clk), .d(od_t_su_SW[k]), .q(o_t_su_SW[k]));
    end
    assign t_su_SW[511:0] = o_t_su_SW[511:0];
endmodule
