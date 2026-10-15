// hfd_hc_eng: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 FUSED HC engine view (el1011-hbm-fused 10-12): ot_hgi_hc_eng_station = pin flops + one-entry job hold + the lane-local one-pass engine ot_hgi_hc_eng LL 1 (d 5120 HC_POST / HC_PRE_NORM; hbm-hcvm lane tiles) on its own lgE slot (KE 3, tap packing as ot_hgi_fused_station); jobs from the FUSED record in hb_quant (HCE 2) over fused_ne {g_rdy, job_v, job 149}, return fused_ne_r {job_rdy, fault, done}. Bench rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv (run_hgi_die_masters.sh fused_hce).
module hfd_hc_eng (
    input wire [0:0] ck,
    input wire [150:0] f_fused_ne,
    input wire [8256:0] f_lgE_rdn,
    input wire [64:0] f_lgE_wdn,
    input wire [0:0] rst,
    output wire [2:0] t_fused_ne,
    output wire [512:0] t_lgE_rup,
    output wire [8960:0] t_lgE_wup
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [150:0] i0_f_fused_ne; always @(posedge clk) i0_f_fused_ne <= f_fused_ne;
    reg [150:0] i1_f_fused_ne; always @(posedge clk) i1_f_fused_ne <= i0_f_fused_ne;
    reg [150:0] i2_f_fused_ne; always @(posedge clk) i2_f_fused_ne <= i1_f_fused_ne;
    reg [150:0] i3_f_fused_ne; always @(posedge clk) i3_f_fused_ne <= i2_f_fused_ne;
    reg [150:0] i_f_fused_ne; always @(posedge clk) i_f_fused_ne <= i3_f_fused_ne;
    reg [8256:0] i0_f_lgE_rdn; always @(posedge clk) i0_f_lgE_rdn <= f_lgE_rdn;
    reg [8256:0] i1_f_lgE_rdn; always @(posedge clk) i1_f_lgE_rdn <= i0_f_lgE_rdn;
    reg [8256:0] i2_f_lgE_rdn; always @(posedge clk) i2_f_lgE_rdn <= i1_f_lgE_rdn;
    reg [8256:0] i3_f_lgE_rdn; always @(posedge clk) i3_f_lgE_rdn <= i2_f_lgE_rdn;
    reg [8256:0] i_f_lgE_rdn; always @(posedge clk) i_f_lgE_rdn <= i3_f_lgE_rdn;
    reg [64:0] i0_f_lgE_wdn; always @(posedge clk) i0_f_lgE_wdn <= f_lgE_wdn;
    reg [64:0] i1_f_lgE_wdn; always @(posedge clk) i1_f_lgE_wdn <= i0_f_lgE_wdn;
    reg [64:0] i2_f_lgE_wdn; always @(posedge clk) i2_f_lgE_wdn <= i1_f_lgE_wdn;
    reg [64:0] i3_f_lgE_wdn; always @(posedge clk) i3_f_lgE_wdn <= i2_f_lgE_wdn;
    reg [64:0] i_f_lgE_wdn; always @(posedge clk) i_f_lgE_wdn <= i3_f_lgE_wdn;
    wire [0:0] w_he_clk;
    wire [0:0] w_he_rst_n;
    wire [150:0] w_he_ne_i;
    wire [2:0] w_he_ne_o;
    wire [512:0] w_he_lg_rup;
    wire [8256:0] w_he_lg_rdn;
    wire [8960:0] w_he_lg_wup;
    wire [64:0] w_he_lg_wdn;
    assign w_he_clk = {1{clk}};
    assign w_he_rst_n = {1{rst_n}};
    assign w_he_ne_i = {i_f_fused_ne[150:0]};
    assign w_he_lg_rdn = {i_f_lgE_rdn[8256:0]};
    assign w_he_lg_wdn = {i_f_lgE_wdn[64:0]};
    ot_hgi_hc_eng_station #(.D(5120), .LQ(32), .RL(10)) u_he (.clk(w_he_clk), .rst_n(w_he_rst_n), .ne_i(w_he_ne_i), .ne_o(w_he_ne_o), .lg_rup(w_he_lg_rup), .lg_rdn(w_he_lg_rdn), .lg_wup(w_he_lg_wup), .lg_wdn(w_he_lg_wdn));
    wire [2:0] od_t_fused_ne = {w_he_ne_o[2:0]};
    wire [2:0] o_t_fused_ne;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_fused_ne
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_fused_ne[k]), .q(o_t_fused_ne[k]));
    end
    assign t_fused_ne[2:0] = o_t_fused_ne[2:0];
    wire [512:0] od_t_lgE_rup = {w_he_lg_rup[512:0]};
    wire [512:0] o_t_lgE_rup;
    for (genvar k = 0; k < 513; k = k + 1) begin : g_o_t_lgE_rup
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_lgE_rup[k]), .q(o_t_lgE_rup[k]));
    end
    assign t_lgE_rup[512:0] = o_t_lgE_rup[512:0];
    wire [8960:0] od_t_lgE_wup = {w_he_lg_wup[8960:0]};
    wire [8960:0] o_t_lgE_wup;
    for (genvar k = 0; k < 8961; k = k + 1) begin : g_o_t_lgE_wup
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_lgE_wup[k]), .q(o_t_lgE_wup[k]));
    end
    assign t_lgE_wup[8960:0] = o_t_lgE_wup[8960:0];
endmodule
