`timescale 1ns/1ps
module tb;
reg ck=0,hck=0; always #5 ck=~ck; always #7 hck=~hck;
integer edge_i,checks=0,mut=0; integer seed=173;
reg [0:0] grp_rst_n=0;
reg [0:0] grp_afk=0;
reg [0:0] grp_afv=0;
reg [0:0] grp_afu=0;
reg [0:0] grp_hrst_n=0;
reg [1:0] grp_slg__cfg_stack=0;
reg [2:0] grp_slg__cfg_group=0;
reg [37:0] grp_kreq=0;
reg [14:0] grp_vreq=0;
reg [12:0] grp_x__est=0;
reg [17:0] grp_x__tok=0;
reg [15:0] grp_x__tep=0;
wire [1055:0] grp_rsp;
wire [1061:0] grp_krsp;
wire [0:0] grp_af__fault;
wire [0:0] grp_y__est__0_1;
wire [17:0] grp_y__tok;
wire [15:0] grp_y__tep;
reg [270:0] grp_i_ctl=0;
reg [304:0] grp_i_pc0=0;
reg [304:0] grp_i_pc1=0;
reg [304:0] grp_i_pc2=0;
reg [304:0] grp_i_pc3=0;
wire [127:0] grp_o_pc0;
wire [127:0] grp_o_pc1;
wire [127:0] grp_o_pc2;
wire [127:0] grp_o_pc3;
wire [270:0] grp_o_dn;
reg [143:0] grp_i_up=0;
wire [143:0] grp_o_ctl;
wire [1055:0] n_grp_rsp;
wire [1061:0] n_grp_krsp;
wire [0:0] n_grp_af__fault;
wire [0:0] n_grp_y__est__0_1;
wire [127:0] n_grp_o_pc0;
wire [127:0] n_grp_o_pc1;
wire [127:0] n_grp_o_pc2;
wire [127:0] n_grp_o_pc3;
wire [270:0] n_grp_o_dn;
wire [143:0] n_grp_o_ctl;
qkd_kvs_grp old_grp(.ck(ck),.rst_n(grp_rst_n),.afk(grp_afk),.afv(grp_afv),.afu(grp_afu),.hck(hck),.hrst_n(grp_hrst_n),.slg__cfg_stack(grp_slg__cfg_stack),.slg__cfg_group(grp_slg__cfg_group),.kreq(grp_kreq),.vreq(grp_vreq),.x__est(grp_x__est),.x__tok(grp_x__tok),.x__tep(grp_x__tep),.rsp(grp_rsp),.krsp(grp_krsp),.af__fault(grp_af__fault),.y__est__0_1(grp_y__est__0_1),.y__tok(grp_y__tok),.y__tep(grp_y__tep),.i_ctl(grp_i_ctl),.i_pc0(grp_i_pc0),.i_pc1(grp_i_pc1),.i_pc2(grp_i_pc2),.i_pc3(grp_i_pc3),.o_pc0(grp_o_pc0),.o_pc1(grp_o_pc1),.o_pc2(grp_o_pc2),.o_pc3(grp_o_pc3),.o_dn(grp_o_dn),.i_up(grp_i_up),.o_ctl(grp_o_ctl));
qkd_kvs_grp_private0 new_grp(.ck(ck),.rst_n(grp_rst_n),.afk(grp_afk),.afv(grp_afv),.afu(grp_afu),.hck(hck),.hrst_n(grp_hrst_n),.slg__cfg_stack(grp_slg__cfg_stack),.slg__cfg_group(grp_slg__cfg_group),.kreq(grp_kreq),.vreq(grp_vreq),.x__est(grp_x__est[0:0]),.rsp(n_grp_rsp),.krsp(n_grp_krsp),.af__fault(n_grp_af__fault),.y__est__0_1(n_grp_y__est__0_1),.i_ctl(grp_i_ctl),.i_pc0(grp_i_pc0),.i_pc1(grp_i_pc1),.i_pc2(grp_i_pc2),.i_pc3(grp_i_pc3),.o_pc0(n_grp_o_pc0),.o_pc1(n_grp_o_pc1),.o_pc2(n_grp_o_pc2),.o_pc3(n_grp_o_pc3),.o_dn(n_grp_o_dn),.i_up(grp_i_up),.o_ctl(n_grp_o_ctl));
reg [0:0] grp_h_rst_n=0;
reg [0:0] grp_h_afk=0;
reg [0:0] grp_h_afv=0;
reg [0:0] grp_h_hrst_n=0;
reg [1:0] grp_h_slg__cfg_stack=0;
reg [2:0] grp_h_slg__cfg_group=0;
reg [37:0] grp_h_kreq=0;
reg [14:0] grp_h_vreq=0;
reg [12:0] grp_h_x__est=0;
reg [17:0] grp_h_x__tok=0;
reg [15:0] grp_h_x__tep=0;
wire [1055:0] grp_h_rsp;
wire [1061:0] grp_h_krsp;
wire [0:0] grp_h_af__fault;
wire [0:0] grp_h_y__est__0_1;
wire [17:0] grp_h_y__tok;
wire [15:0] grp_h_y__tep;
reg [270:0] grp_h_i_ctl=0;
reg [304:0] grp_h_i_pc0=0;
reg [304:0] grp_h_i_pc1=0;
reg [304:0] grp_h_i_pc2=0;
reg [304:0] grp_h_i_pc3=0;
wire [127:0] grp_h_o_pc0;
wire [127:0] grp_h_o_pc1;
wire [127:0] grp_h_o_pc2;
wire [127:0] grp_h_o_pc3;
wire [270:0] grp_h_o_dn;
wire [143:0] grp_h_o_ctl;
wire [1055:0] n_grp_h_rsp;
wire [1061:0] n_grp_h_krsp;
wire [0:0] n_grp_h_af__fault;
wire [0:0] n_grp_h_y__est__0_1;
wire [127:0] n_grp_h_o_pc0;
wire [127:0] n_grp_h_o_pc1;
wire [127:0] n_grp_h_o_pc2;
wire [127:0] n_grp_h_o_pc3;
wire [143:0] n_grp_h_o_ctl;
qkd_kvs_grp_h old_grp_h(.ck(ck),.rst_n(grp_h_rst_n),.afk(grp_h_afk),.afv(grp_h_afv),.hck(hck),.hrst_n(grp_h_hrst_n),.slg__cfg_stack(grp_h_slg__cfg_stack),.slg__cfg_group(grp_h_slg__cfg_group),.kreq(grp_h_kreq),.vreq(grp_h_vreq),.x__est(grp_h_x__est),.x__tok(grp_h_x__tok),.x__tep(grp_h_x__tep),.rsp(grp_h_rsp),.krsp(grp_h_krsp),.af__fault(grp_h_af__fault),.y__est__0_1(grp_h_y__est__0_1),.y__tok(grp_h_y__tok),.y__tep(grp_h_y__tep),.i_ctl(grp_h_i_ctl),.i_pc0(grp_h_i_pc0),.i_pc1(grp_h_i_pc1),.i_pc2(grp_h_i_pc2),.i_pc3(grp_h_i_pc3),.o_pc0(grp_h_o_pc0),.o_pc1(grp_h_o_pc1),.o_pc2(grp_h_o_pc2),.o_pc3(grp_h_o_pc3),.o_dn(grp_h_o_dn),.o_ctl(grp_h_o_ctl));
qkd_kvs_grp_h_private0 new_grp_h(.ck(ck),.rst_n(grp_h_rst_n),.afk(grp_h_afk),.afv(grp_h_afv),.hck(hck),.hrst_n(grp_h_hrst_n),.slg__cfg_stack(grp_h_slg__cfg_stack),.slg__cfg_group(grp_h_slg__cfg_group),.kreq(grp_h_kreq),.vreq(grp_h_vreq),.x__est(grp_h_x__est[0:0]),.rsp(n_grp_h_rsp),.krsp(n_grp_h_krsp),.af__fault(n_grp_h_af__fault),.y__est__0_1(n_grp_h_y__est__0_1),.i_ctl(grp_h_i_ctl[193:0]),.i_pc0(grp_h_i_pc0),.i_pc1(grp_h_i_pc1),.i_pc2(grp_h_i_pc2),.i_pc3(grp_h_i_pc3),.o_pc0(n_grp_h_o_pc0),.o_pc1(n_grp_h_o_pc1),.o_pc2(n_grp_h_o_pc2),.o_pc3(n_grp_h_o_pc3),.o_ctl(n_grp_h_o_ctl));
initial begin
if (!$value$plusargs("mut=%d",mut)) mut=0;
for(edge_i=0;edge_i<2048;edge_i=edge_i+1) begin
@(negedge ck);
grp_rst_n = !(edge_i<8 || (edge_i>=900 && edge_i<909) || (edge_i>=1400 && edge_i<1408));
grp_afk = {$random(seed)};
grp_afv = {$random(seed)};
grp_afu = {$random(seed)};
grp_hrst_n = !(edge_i<8 || (edge_i>=900 && edge_i<909) || (edge_i>=1400 && edge_i<1408));
grp_slg__cfg_stack = {$random(seed)};
grp_slg__cfg_group = {$random(seed)};
grp_kreq = {$random(seed),$random(seed)};
grp_vreq = {$random(seed)};
grp_x__est = {$random(seed)};
grp_x__tok = {$random(seed)};
grp_x__tep = {$random(seed)};
grp_i_ctl = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_i_pc0 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_i_pc1 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_i_pc2 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_i_pc3 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_i_up = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_x__est[0] = edge_i[0];
grp_h_rst_n = !(edge_i<8 || (edge_i>=900 && edge_i<909) || (edge_i>=1400 && edge_i<1408));
grp_h_afk = {$random(seed)};
grp_h_afv = {$random(seed)};
grp_h_hrst_n = !(edge_i<8 || (edge_i>=900 && edge_i<909) || (edge_i>=1400 && edge_i<1408));
grp_h_slg__cfg_stack = {$random(seed)};
grp_h_slg__cfg_group = {$random(seed)};
grp_h_kreq = {$random(seed),$random(seed)};
grp_h_vreq = {$random(seed)};
grp_h_x__est = {$random(seed)};
grp_h_x__tok = {$random(seed)};
grp_h_x__tep = {$random(seed)};
grp_h_i_ctl = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_h_i_pc0 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_h_i_pc1 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_h_i_pc2 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_h_i_pc3 = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
grp_h_x__est[0] = edge_i[0];
@(posedge ck); #1;
checks=checks+1; if (grp_rsp !== n_grp_rsp) begin $display("PRIVATE_FAIL kind=grp output=rsp edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_krsp !== n_grp_krsp) begin $display("PRIVATE_FAIL kind=grp output=krsp edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_af__fault !== n_grp_af__fault) begin $display("PRIVATE_FAIL kind=grp output=af__fault edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_y__est__0_1 !== n_grp_y__est__0_1) begin $display("PRIVATE_FAIL kind=grp output=y__est__0_1 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_pc0 !== n_grp_o_pc0) begin $display("PRIVATE_FAIL kind=grp output=o_pc0 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_pc1 !== n_grp_o_pc1) begin $display("PRIVATE_FAIL kind=grp output=o_pc1 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_pc2 !== n_grp_o_pc2) begin $display("PRIVATE_FAIL kind=grp output=o_pc2 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_pc3 !== n_grp_o_pc3) begin $display("PRIVATE_FAIL kind=grp output=o_pc3 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_dn !== n_grp_o_dn) begin $display("PRIVATE_FAIL kind=grp output=o_dn edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_o_ctl !== n_grp_o_ctl) begin $display("PRIVATE_FAIL kind=grp output=o_ctl edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_rsp !== n_grp_h_rsp) begin $display("PRIVATE_FAIL kind=grp_h output=rsp edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_krsp !== n_grp_h_krsp) begin $display("PRIVATE_FAIL kind=grp_h output=krsp edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_af__fault !== n_grp_h_af__fault) begin $display("PRIVATE_FAIL kind=grp_h output=af__fault edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_y__est__0_1 !== n_grp_h_y__est__0_1) begin $display("PRIVATE_FAIL kind=grp_h output=y__est__0_1 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_o_pc0 !== n_grp_h_o_pc0) begin $display("PRIVATE_FAIL kind=grp_h output=o_pc0 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_o_pc1 !== n_grp_h_o_pc1) begin $display("PRIVATE_FAIL kind=grp_h output=o_pc1 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_o_pc2 !== n_grp_h_o_pc2) begin $display("PRIVATE_FAIL kind=grp_h output=o_pc2 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_o_pc3 !== n_grp_h_o_pc3) begin $display("PRIVATE_FAIL kind=grp_h output=o_pc3 edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
checks=checks+1; if (grp_h_o_ctl !== n_grp_h_o_ctl) begin $display("PRIVATE_FAIL kind=grp_h output=o_ctl edge=%0d mut=%0d",edge_i,mut); $fatal(1); end
end
$display("PRIVATE_PASS checks=%0d edges=2048 mut=%0d",checks,mut); $finish; end
endmodule
