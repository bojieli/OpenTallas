`timescale 1ps/1ps
module tb;
localparam integer MUT = 0;
reg ck = 0, hck = 0;
always #417 ck = ~ck;
always #512 hck = ~hck;
integer e, checks = 0, mut = 0, seed = 1019;
reg rst_n = 0, hrst_n = 0;
// the tile landing, modelled in the bench for the oracle: async assert, release on the 2nd own-clock edge
reg c1 = 0, c2 = 0, h1 = 0, h2 = 0;
always @(posedge ck or negedge rst_n) if (!rst_n) begin c1 <= 0; c2 <= 0; end else begin c1 <= 1; c2 <= c1; end
always @(posedge hck or negedge hrst_n) if (!hrst_n) begin h1 <= 0; h2 <= 0; end else begin h1 <= 1; h2 <= h1; end
reg [0:0] g_afk = 0;
reg [0:0] g_afv = 0;
reg [0:0] g_afu = 0;
reg [1:0] g_slg__cfg_stack = 0;
reg [2:0] g_slg__cfg_group = 0;
reg [37:0] g_kreq = 0;
reg [14:0] g_vreq = 0;
reg [12:0] g_x__est = 0;
reg [12:0] g_x__est_d = 0; always @(posedge ck) g_x__est_d <= g_x__est;
reg [17:0] g_x__tok = 0;
reg [15:0] g_x__tep = 0;
wire [1055:0] g_r_rsp;
wire [1061:0] g_r_krsp;
wire [0:0] g_r_af__fault;
wire [0:0] g_r_y__est__0_1;
wire [17:0] g_r_y__tok;
wire [15:0] g_r_y__tep;
reg [270:0] g_i_ctl = 0;
reg [270:0] g_i_ctl_d = 0; always @(posedge ck) g_i_ctl_d <= g_i_ctl;
reg [294:0] g_i_pc0 = 0;
reg [9:0] g_i_pc0_h = 0;
reg [294:0] g_i_pc1 = 0;
reg [9:0] g_i_pc1_h = 0;
reg [294:0] g_i_pc2 = 0;
reg [9:0] g_i_pc2_h = 0;
reg [294:0] g_i_pc3 = 0;
reg [9:0] g_i_pc3_h = 0;
wire [32:0] g_r_o_pc0;
wire [94:0] g_r_o_pc0_h;
wire [32:0] g_r_o_pc1;
wire [94:0] g_r_o_pc1_h;
wire [32:0] g_r_o_pc2;
wire [94:0] g_r_o_pc2_h;
wire [32:0] g_r_o_pc3;
wire [94:0] g_r_o_pc3_h;
wire [270:0] g_r_o_dn_raw; reg [270:0] g_r_o_dn = 0; always @(posedge ck) g_r_o_dn <= g_r_o_dn_raw;
reg [143:0] g_i_up = 0;
reg [143:0] g_i_up_d = 0; always @(posedge ck) g_i_up_d <= g_i_up;
wire [143:0] g_r_o_ctl_raw; reg [143:0] g_r_o_ctl = 0; always @(posedge ck) g_r_o_ctl <= g_r_o_ctl_raw;
wire [1055:0] g_d_rsp;
wire [1061:0] g_d_krsp;
wire [0:0] g_d_af__fault;
wire [0:0] g_d_y__est__0_1;
wire [32:0] g_d_o_pc0;
wire [94:0] g_d_o_pc0_h;
wire [32:0] g_d_o_pc1;
wire [94:0] g_d_o_pc1_h;
wire [32:0] g_d_o_pc2;
wire [94:0] g_d_o_pc2_h;
wire [32:0] g_d_o_pc3;
wire [94:0] g_d_o_pc3_h;
wire [270:0] g_d_o_dn;
wire [143:0] g_d_o_ctl;
qkd_kvs_grp_ref ref_g (.ck(ck), .rst_n(c2), .afk(g_afk), .afv(g_afv), .afu(g_afu), .hck(hck), .hrst_n(h2), .slg__cfg_stack(g_slg__cfg_stack), .slg__cfg_group(g_slg__cfg_group), .kreq(g_kreq), .vreq(g_vreq), .x__est(g_x__est_d), .x__tok(g_x__tok), .x__tep(g_x__tep), .rsp(g_r_rsp), .krsp(g_r_krsp), .af__fault(g_r_af__fault), .y__est__0_1(g_r_y__est__0_1), .y__tok(g_r_y__tok), .y__tep(g_r_y__tep), .i_ctl(g_i_ctl_d), .i_pc0(g_i_pc0), .i_pc0_h(g_i_pc0_h), .i_pc1(g_i_pc1), .i_pc1_h(g_i_pc1_h), .i_pc2(g_i_pc2), .i_pc2_h(g_i_pc2_h), .i_pc3(g_i_pc3), .i_pc3_h(g_i_pc3_h), .o_pc0(g_r_o_pc0), .o_pc0_h(g_r_o_pc0_h), .o_pc1(g_r_o_pc1), .o_pc1_h(g_r_o_pc1_h), .o_pc2(g_r_o_pc2), .o_pc2_h(g_r_o_pc2_h), .o_pc3(g_r_o_pc3), .o_pc3_h(g_r_o_pc3_h), .o_dn(g_r_o_dn_raw), .i_up(g_i_up_d), .o_ctl(g_r_o_ctl_raw));
qkd_kvs_grp_s5_bench #(.MUT(MUT)) dut_g (.ck(ck), .rst_n(rst_n), .afk(g_afk), .afv(g_afv), .afu(g_afu), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(g_slg__cfg_stack), .slg__cfg_group(g_slg__cfg_group), .kreq(g_kreq), .vreq(g_vreq), .x__est(g_x__est[0:0]), .rsp(g_d_rsp), .krsp(g_d_krsp), .af__fault(g_d_af__fault), .y__est__0_1(g_d_y__est__0_1), .i_ctl(g_i_ctl), .i_pc0(g_i_pc0), .i_pc0_h(g_i_pc0_h), .i_pc1(g_i_pc1), .i_pc1_h(g_i_pc1_h), .i_pc2(g_i_pc2), .i_pc2_h(g_i_pc2_h), .i_pc3(g_i_pc3), .i_pc3_h(g_i_pc3_h), .o_pc0(g_d_o_pc0), .o_pc0_h(g_d_o_pc0_h), .o_pc1(g_d_o_pc1), .o_pc1_h(g_d_o_pc1_h), .o_pc2(g_d_o_pc2), .o_pc2_h(g_d_o_pc2_h), .o_pc3(g_d_o_pc3), .o_pc3_h(g_d_o_pc3_h), .o_dn(g_d_o_dn), .i_up(g_i_up), .o_ctl(g_d_o_ctl));
task stim_g; begin
  g_afk = {$random(seed)};
  g_afv = {$random(seed)};
  g_afu = {$random(seed)};
  g_slg__cfg_stack = {$random(seed)};
  g_slg__cfg_group = {$random(seed)};
  g_kreq = {$random(seed),$random(seed)};
  g_vreq = {$random(seed)};
  g_x__est = {$random(seed)};
  g_x__tok = {$random(seed)};
  g_x__tep = {$random(seed)};
  g_i_ctl = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_pc0 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_pc0_h = {$random(seed)};
  g_i_pc1 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_pc1_h = {$random(seed)};
  g_i_pc2 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_pc2_h = {$random(seed)};
  g_i_pc3 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_pc3_h = {$random(seed)};
  g_i_up = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  g_i_ctl[174] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[181] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[182] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[183] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[184] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[185] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[186] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[187] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[188] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[189] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[190] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[191] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[192] = $random(seed) & $random(seed) & $random(seed);
  g_i_ctl[193] = $random(seed) & $random(seed) & $random(seed);
end endtask
reg [0:0] h_afk = 0;
reg [0:0] h_afv = 0;
reg [1:0] h_slg__cfg_stack = 0;
reg [2:0] h_slg__cfg_group = 0;
reg [37:0] h_kreq = 0;
reg [14:0] h_vreq = 0;
reg [12:0] h_x__est = 0;
reg [12:0] h_x__est_d = 0; always @(posedge ck) h_x__est_d <= h_x__est;
reg [17:0] h_x__tok = 0;
reg [15:0] h_x__tep = 0;
wire [1055:0] h_r_rsp;
wire [1061:0] h_r_krsp;
wire [0:0] h_r_af__fault;
wire [0:0] h_r_y__est__0_1;
wire [17:0] h_r_y__tok;
wire [15:0] h_r_y__tep;
reg [270:0] h_i_ctl = 0;
reg [270:0] h_i_ctl_d = 0; always @(posedge ck) h_i_ctl_d <= h_i_ctl;
reg [294:0] h_i_pc0 = 0;
reg [9:0] h_i_pc0_h = 0;
reg [294:0] h_i_pc1 = 0;
reg [9:0] h_i_pc1_h = 0;
reg [294:0] h_i_pc2 = 0;
reg [9:0] h_i_pc2_h = 0;
reg [294:0] h_i_pc3 = 0;
reg [9:0] h_i_pc3_h = 0;
wire [32:0] h_r_o_pc0;
wire [94:0] h_r_o_pc0_h;
wire [32:0] h_r_o_pc1;
wire [94:0] h_r_o_pc1_h;
wire [32:0] h_r_o_pc2;
wire [94:0] h_r_o_pc2_h;
wire [32:0] h_r_o_pc3;
wire [94:0] h_r_o_pc3_h;
wire [270:0] h_r_o_dn_raw; reg [270:0] h_r_o_dn = 0; always @(posedge ck) h_r_o_dn <= h_r_o_dn_raw;
wire [143:0] h_r_o_ctl_raw; reg [143:0] h_r_o_ctl = 0; always @(posedge ck) h_r_o_ctl <= h_r_o_ctl_raw;
wire [1055:0] h_d_rsp;
wire [1061:0] h_d_krsp;
wire [0:0] h_d_af__fault;
wire [0:0] h_d_y__est__0_1;
wire [32:0] h_d_o_pc0;
wire [94:0] h_d_o_pc0_h;
wire [32:0] h_d_o_pc1;
wire [94:0] h_d_o_pc1_h;
wire [32:0] h_d_o_pc2;
wire [94:0] h_d_o_pc2_h;
wire [32:0] h_d_o_pc3;
wire [94:0] h_d_o_pc3_h;
wire [143:0] h_d_o_ctl;
qkd_kvs_grp_h_ref ref_h (.ck(ck), .rst_n(c2), .afk(h_afk), .afv(h_afv), .hck(hck), .hrst_n(h2), .slg__cfg_stack(h_slg__cfg_stack), .slg__cfg_group(h_slg__cfg_group), .kreq(h_kreq), .vreq(h_vreq), .x__est(h_x__est_d), .x__tok(h_x__tok), .x__tep(h_x__tep), .rsp(h_r_rsp), .krsp(h_r_krsp), .af__fault(h_r_af__fault), .y__est__0_1(h_r_y__est__0_1), .y__tok(h_r_y__tok), .y__tep(h_r_y__tep), .i_ctl(h_i_ctl_d), .i_pc0(h_i_pc0), .i_pc0_h(h_i_pc0_h), .i_pc1(h_i_pc1), .i_pc1_h(h_i_pc1_h), .i_pc2(h_i_pc2), .i_pc2_h(h_i_pc2_h), .i_pc3(h_i_pc3), .i_pc3_h(h_i_pc3_h), .o_pc0(h_r_o_pc0), .o_pc0_h(h_r_o_pc0_h), .o_pc1(h_r_o_pc1), .o_pc1_h(h_r_o_pc1_h), .o_pc2(h_r_o_pc2), .o_pc2_h(h_r_o_pc2_h), .o_pc3(h_r_o_pc3), .o_pc3_h(h_r_o_pc3_h), .o_dn(h_r_o_dn_raw), .o_ctl(h_r_o_ctl_raw));
qkd_kvs_grp_h_s5_bench #(.MUT(MUT)) dut_h (.ck(ck), .rst_n(rst_n), .afk(h_afk), .afv(h_afv), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(h_slg__cfg_stack), .slg__cfg_group(h_slg__cfg_group), .kreq(h_kreq), .vreq(h_vreq), .x__est(h_x__est[0:0]), .rsp(h_d_rsp), .krsp(h_d_krsp), .af__fault(h_d_af__fault), .y__est__0_1(h_d_y__est__0_1), .i_ctl(h_i_ctl[193:0]), .i_pc0(h_i_pc0), .i_pc0_h(h_i_pc0_h), .i_pc1(h_i_pc1), .i_pc1_h(h_i_pc1_h), .i_pc2(h_i_pc2), .i_pc2_h(h_i_pc2_h), .i_pc3(h_i_pc3), .i_pc3_h(h_i_pc3_h), .o_pc0(h_d_o_pc0), .o_pc0_h(h_d_o_pc0_h), .o_pc1(h_d_o_pc1), .o_pc1_h(h_d_o_pc1_h), .o_pc2(h_d_o_pc2), .o_pc2_h(h_d_o_pc2_h), .o_pc3(h_d_o_pc3), .o_pc3_h(h_d_o_pc3_h), .o_ctl(h_d_o_ctl));
task stim_h; begin
  h_afk = {$random(seed)};
  h_afv = {$random(seed)};
  h_slg__cfg_stack = {$random(seed)};
  h_slg__cfg_group = {$random(seed)};
  h_kreq = {$random(seed),$random(seed)};
  h_vreq = {$random(seed)};
  h_x__est = {$random(seed)};
  h_x__tok = {$random(seed)};
  h_x__tep = {$random(seed)};
  h_i_ctl = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  h_i_pc0 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  h_i_pc0_h = {$random(seed)};
  h_i_pc1 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  h_i_pc1_h = {$random(seed)};
  h_i_pc2 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  h_i_pc2_h = {$random(seed)};
  h_i_pc3 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
  h_i_pc3_h = {$random(seed)};
  h_i_ctl[174] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[181] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[182] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[183] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[184] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[185] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[186] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[187] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[188] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[189] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[190] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[191] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[192] = $random(seed) & $random(seed) & $random(seed);
  h_i_ctl[193] = $random(seed) & $random(seed) & $random(seed);
end endtask
task compare(input integer side); begin if (e >= 20) begin
  checks = checks + 1; if ((e>=64 || g_d_rsp[0] || g_r_rsp[0]) && g_d_rsp !== g_r_rsp) begin $display("S2_FAIL tile=%s output=rsp edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_rsp, g_r_rsp); $fatal(1); end
  checks = checks + 1; if ((e>=64 || g_d_krsp[0] || g_r_krsp[0]) && g_d_krsp !== g_r_krsp) begin $display("S2_FAIL tile=%s output=krsp edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_krsp, g_r_krsp); $fatal(1); end
  checks = checks + 1; if (g_d_af__fault !== g_r_af__fault) begin $display("S2_FAIL tile=%s output=af__fault edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_af__fault, g_r_af__fault); $fatal(1); end
  checks = checks + 1; if (g_d_y__est__0_1 !== g_r_y__est__0_1) begin $display("S2_FAIL tile=%s output=y__est__0_1 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_y__est__0_1, g_r_y__est__0_1); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc0 !== g_r_o_pc0) begin $display("S2_FAIL tile=%s output=o_pc0 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc0, g_r_o_pc0); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc0_h !== g_r_o_pc0_h) begin $display("S2_FAIL tile=%s output=o_pc0_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc0_h, g_r_o_pc0_h); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc1 !== g_r_o_pc1) begin $display("S2_FAIL tile=%s output=o_pc1 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc1, g_r_o_pc1); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc1_h !== g_r_o_pc1_h) begin $display("S2_FAIL tile=%s output=o_pc1_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc1_h, g_r_o_pc1_h); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc2 !== g_r_o_pc2) begin $display("S2_FAIL tile=%s output=o_pc2 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc2, g_r_o_pc2); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc2_h !== g_r_o_pc2_h) begin $display("S2_FAIL tile=%s output=o_pc2_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc2_h, g_r_o_pc2_h); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc3 !== g_r_o_pc3) begin $display("S2_FAIL tile=%s output=o_pc3 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc3, g_r_o_pc3); $fatal(1); end
  checks = checks + 1; if (g_d_o_pc3_h !== g_r_o_pc3_h) begin $display("S2_FAIL tile=%s output=o_pc3_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_pc3_h, g_r_o_pc3_h); $fatal(1); end
  checks = checks + 1; if (g_d_o_dn !== g_r_o_dn) begin $display("S2_FAIL tile=%s output=o_dn edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_dn, g_r_o_dn); $fatal(1); end
  checks = checks + 1; if (g_d_o_ctl !== g_r_o_ctl) begin $display("S2_FAIL tile=%s output=o_ctl edge=%0d side=%0d mut=%0d dut=%h ref=%h", "g", e, side, mut, g_d_o_ctl, g_r_o_ctl); $fatal(1); end
  checks = checks + 1; if ((e>=64 || h_d_rsp[0] || h_r_rsp[0]) && h_d_rsp !== h_r_rsp) begin $display("S2_FAIL tile=%s output=rsp edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_rsp, h_r_rsp); $fatal(1); end
  checks = checks + 1; if ((e>=64 || h_d_krsp[0] || h_r_krsp[0]) && h_d_krsp !== h_r_krsp) begin $display("S2_FAIL tile=%s output=krsp edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_krsp, h_r_krsp); $fatal(1); end
  checks = checks + 1; if (h_d_af__fault !== h_r_af__fault) begin $display("S2_FAIL tile=%s output=af__fault edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_af__fault, h_r_af__fault); $fatal(1); end
  checks = checks + 1; if (h_d_y__est__0_1 !== h_r_y__est__0_1) begin $display("S2_FAIL tile=%s output=y__est__0_1 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_y__est__0_1, h_r_y__est__0_1); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc0 !== h_r_o_pc0) begin $display("S2_FAIL tile=%s output=o_pc0 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc0, h_r_o_pc0); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc0_h !== h_r_o_pc0_h) begin $display("S2_FAIL tile=%s output=o_pc0_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc0_h, h_r_o_pc0_h); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc1 !== h_r_o_pc1) begin $display("S2_FAIL tile=%s output=o_pc1 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc1, h_r_o_pc1); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc1_h !== h_r_o_pc1_h) begin $display("S2_FAIL tile=%s output=o_pc1_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc1_h, h_r_o_pc1_h); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc2 !== h_r_o_pc2) begin $display("S2_FAIL tile=%s output=o_pc2 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc2, h_r_o_pc2); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc2_h !== h_r_o_pc2_h) begin $display("S2_FAIL tile=%s output=o_pc2_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc2_h, h_r_o_pc2_h); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc3 !== h_r_o_pc3) begin $display("S2_FAIL tile=%s output=o_pc3 edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc3, h_r_o_pc3); $fatal(1); end
  checks = checks + 1; if (h_d_o_pc3_h !== h_r_o_pc3_h) begin $display("S2_FAIL tile=%s output=o_pc3_h edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_pc3_h, h_r_o_pc3_h); $fatal(1); end
  checks = checks + 1; if (h_d_o_ctl !== h_r_o_ctl) begin $display("S2_FAIL tile=%s output=o_ctl edge=%0d side=%0d mut=%0d dut=%h ref=%h", "h", e, side, mut, h_d_o_ctl, h_r_o_ctl); $fatal(1); end
end end endtask
always @(negedge hck) if (e > 0) compare(1);
initial begin
  if (!$value$plusargs("mut=%d", mut)) mut = MUT;
  for (e = 0; e < 6000; e = e + 1) begin
    @(negedge ck);
    compare(0);
    rst_n = !(e < 6 || (e >= 2500 && e < 2507) || (e >= 4100 && e < 4103));
    hrst_n = !(e < 7 || (e >= 2501 && e < 2509) || (e >= 4100 && e < 4104));
    g_i_ctl=0; g_i_ctl[157:144]=14'd8192; g_i_ctl[173:158]=16'd1; g_i_ctl[174]=(e==16);
    for(pj=15;pj>0;pj=pj-1)begin g_rqv[pj]=g_rqv[pj-1];g_rqt[pj]=g_rqt[pj-1];end
    g_rqv[0]=g_d_o_pc0[22]; g_rqt[0]={1'b0,g_d_o_pc0[29:26],2'b00,g_d_o_pc0[30],g_d_o_pc0[25:23],3'b000};
    g_kreq={6'd0,16'd1,1'b0,g_rqt[15],g_rqv[15]};
    if(g_d_o_pc0[22])g_prod_put=g_prod_put+1;
    g_i_pc0[288]=g_d_o_pc0[22]; g_i_pc0[287:278]=g_d_o_pc0[32:23]; g_i_pc0[277:272]=g_d_o_pc0[21:16]; g_i_pc0[271:256]=g_d_o_pc0[15:0]; g_i_pc0[255:0]={8{(32'hA5C00001 ^ {22'd0,g_d_o_pc0[32:23]})}};
    g_i_pc1[288]=g_d_o_pc1[22]; g_i_pc1[287:278]=g_d_o_pc1[32:23]; g_i_pc1[277:272]=g_d_o_pc1[21:16]; g_i_pc1[271:256]=g_d_o_pc1[15:0]; g_i_pc1[255:0]={8{(32'hA5C00002 ^ {22'd0,g_d_o_pc1[32:23]})}};
    g_i_pc2[288]=g_d_o_pc2[22]; g_i_pc2[287:278]=g_d_o_pc2[32:23]; g_i_pc2[277:272]=g_d_o_pc2[21:16]; g_i_pc2[271:256]=g_d_o_pc2[15:0]; g_i_pc2[255:0]={8{(32'hA5C00003 ^ {22'd0,g_d_o_pc2[32:23]})}};
    g_i_pc3[288]=g_d_o_pc3[22]; g_i_pc3[287:278]=g_d_o_pc3[32:23]; g_i_pc3[277:272]=g_d_o_pc3[21:16]; g_i_pc3[271:256]=g_d_o_pc3[15:0]; g_i_pc3[255:0]={8{(32'hA5C00004 ^ {22'd0,g_d_o_pc3[32:23]})}};
    h_i_ctl=0; h_i_ctl[157:144]=14'd8192; h_i_ctl[173:158]=16'd1; h_i_ctl[174]=(e==16);
    for(pj=15;pj>0;pj=pj-1)begin h_rqv[pj]=h_rqv[pj-1];h_rqt[pj]=h_rqt[pj-1];end
    h_rqv[0]=h_d_o_pc0[22]; h_rqt[0]={1'b0,h_d_o_pc0[29:26],2'b00,h_d_o_pc0[30],h_d_o_pc0[25:23],3'b000};
    h_kreq={6'd0,16'd1,1'b0,h_rqt[15],h_rqv[15]};
    if(h_d_o_pc0[22])h_prod_put=h_prod_put+1;
    h_i_pc0[288]=h_d_o_pc0[22]; h_i_pc0[287:278]=h_d_o_pc0[32:23]; h_i_pc0[277:272]=h_d_o_pc0[21:16]; h_i_pc0[271:256]=h_d_o_pc0[15:0]; h_i_pc0[255:0]={8{(32'hA5C00001 ^ {22'd0,h_d_o_pc0[32:23]})}};
    h_i_pc1[288]=h_d_o_pc1[22]; h_i_pc1[287:278]=h_d_o_pc1[32:23]; h_i_pc1[277:272]=h_d_o_pc1[21:16]; h_i_pc1[271:256]=h_d_o_pc1[15:0]; h_i_pc1[255:0]={8{(32'hA5C00002 ^ {22'd0,h_d_o_pc1[32:23]})}};
    h_i_pc2[288]=h_d_o_pc2[22]; h_i_pc2[287:278]=h_d_o_pc2[32:23]; h_i_pc2[277:272]=h_d_o_pc2[21:16]; h_i_pc2[271:256]=h_d_o_pc2[15:0]; h_i_pc2[255:0]={8{(32'hA5C00003 ^ {22'd0,h_d_o_pc2[32:23]})}};
    h_i_pc3[288]=h_d_o_pc3[22]; h_i_pc3[287:278]=h_d_o_pc3[32:23]; h_i_pc3[277:272]=h_d_o_pc3[21:16]; h_i_pc3[271:256]=h_d_o_pc3[15:0]; h_i_pc3[255:0]={8{(32'hA5C00004 ^ {22'd0,h_d_o_pc3[32:23]})}};
  end
  $display("PROD_COUNTS g_put=%0d h_put=%0d g_rsp=%0d h_rsp=%0d",g_prod_put,h_prod_put,g_prod_rsp,h_prod_rsp); if(g_prod_put!=256 || h_prod_put!=256 || g_prod_rsp!=256 || h_prod_rsp!=256)$fatal(1,"PROD_COUNT_FAIL");
  $display("S2_PASS checks=%0d edges=6000 mut=%0d", checks, mut); $finish;
end
integer g_prod_rsp=0,h_prod_rsp=0,g_prod_put=0,h_prod_put=0; integer pj;
reg [15:0] g_rqv=0; reg [13:0] g_rqt[0:15]; initial begin for(integer q=0;q<16;q=q+1)g_rqt[q]=0;end
always @(negedge ck) if(e>=20) begin if(g_d_af__fault !== g_r_af__fault || g_d_y__est__0_1 !== g_r_y__est__0_1 || g_d_o_ctl !== g_r_o_ctl || g_d_o_dn !== g_r_o_dn)$fatal(1,"PROD_STATUS_FAIL"); if(g_d_krsp[0] !== g_r_krsp[0] || (g_d_krsp[0] && g_d_krsp !== g_r_krsp))$fatal(1,"PROD_RESPONSE_FAIL"); if(g_d_rsp[0] !== g_r_rsp[0])$fatal(1,"PROD_VALID_FAIL"); if(g_d_rsp[0])begin if(g_d_rsp !== g_r_rsp)$fatal(1,"PROD_RESPONSE_FAIL");if(g_d_rsp[1055:32]==0)$fatal(1,"PROD_DATA_ZERO"); g_prod_rsp=g_prod_rsp+1;end end
reg [15:0] h_rqv=0; reg [13:0] h_rqt[0:15]; initial begin for(integer q=0;q<16;q=q+1)h_rqt[q]=0;end
always @(negedge ck) if(e>=20) begin if(h_d_af__fault !== h_r_af__fault || h_d_y__est__0_1 !== h_r_y__est__0_1 || h_d_o_ctl !== h_r_o_ctl)$fatal(1,"PROD_STATUS_FAIL"); if(h_d_krsp[0] !== h_r_krsp[0] || (h_d_krsp[0] && h_d_krsp !== h_r_krsp))$fatal(1,"PROD_RESPONSE_FAIL"); if(h_d_rsp[0] !== h_r_rsp[0])$fatal(1,"PROD_VALID_FAIL"); if(h_d_rsp[0])begin if(h_d_rsp !== h_r_rsp)$fatal(1,"PROD_RESPONSE_FAIL");if(h_d_rsp[1055:32]==0)$fatal(1,"PROD_DATA_ZERO"); h_prod_rsp=h_prod_rsp+1;end end
endmodule
