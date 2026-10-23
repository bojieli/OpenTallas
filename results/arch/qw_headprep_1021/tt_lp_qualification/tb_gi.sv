`timescale 1ns/1ps
module tb;
reg clk=0;always #0.5 clk=~clk; reg [1:0] cu=0;reg ce=0;integer ticks=0,checks=0;
reg  ck=0;
reg  rst_n=0;
reg [74:0] pw=0;
reg [82:0] f16_auth=0;
reg [37:0] f16_obs=0;
wire [16:0] n_f16_st;
wire [16:0] o_f16_st;
wire [8:0] n_treq;
wire [8:0] o_treq;
reg [186:0] dh=0;
reg [1:0] dh_user=0;
reg  init_u0=0;
reg [128:0] ctx_x=0;
reg  mu_fault=0;
reg [106:0] ss5=0;
reg [9:0] ag5=0;
reg  fab=0;
wire [115:0] n_cmd;
wire [115:0] o_cmd;
wire [1087:0] n_tl;
wire [1087:0] o_tl;
wire [75:0] n_cal_program_obs;
wire [75:0] o_cal_program_obs;
wire [68:0] n_cal_descriptor_obs;
wire [68:0] o_cal_descriptor_obs;
wire  n_cal_image_ready;
wire  o_cal_image_ready;
wire  n_emb_start;
wire  o_emb_start;
wire [17:0] n_emb_token;
wire [17:0] o_emb_token;
wire [17:0] n_emb_position;
wire [1:0] n_emb_user;
wire  n_s_start;
wire  o_s_start;
wire [5:0] n_s_stage;
wire [5:0] o_s_stage;
wire [48:0] n_st;
wire [48:0] o_st;
wire [37:0] n_fctx;
wire [37:0] o_fctx;
wire [1:0] n_hu;
wire [1:0] o_hu;
wire [15:0] n_su_obs_o;
wire [15:0] o_su_obs_o;
wire [23:0] n_su_acc_o;
wire [23:0] o_su_acc_o;
wire [15:0] n_x_oprog;
wire [15:0] o_x_oprog;
wire [15:0] n_x_orows;
wire [15:0] o_x_orows;
wire  n_x_oidle;
wire  o_x_oidle;
wire [1:0] n_rom_ret_v;
wire [1:0] o_rom_ret_v;
wire [61:0] n_dcs;
wire [61:0] o_dcs;
always @* ck=clk;
qfd_tt_ctlm_dv_gi #(.STAGE_ME(1), .LAST_STAGE(37), .NU(4), .OPSEG(1), .CTX_SRC(1), .FCTX(1), .OPSEG_EXPANDED(1), .INIT_U0(1), .INIT_FIRST(52), .INIT_CNT(3), .OPSEG_PINREG(1), .PRIVATE_CALR(1), .F16WTN(1)) old(.ck(ck), .rst_n(rst_n), .pw(pw), .f16_auth(f16_auth), .f16_obs(f16_obs), .f16_st(o_f16_st), .treq(o_treq), .dh(dh), .dh_user(dh_user), .init_u0(init_u0), .ctx_x(ctx_x), .mu_fault(mu_fault), .ss5(ss5), .ag5(ag5), .fab(fab), .cmd(o_cmd), .tl(o_tl), .cal_program_obs(o_cal_program_obs), .cal_descriptor_obs(o_cal_descriptor_obs), .cal_image_ready(o_cal_image_ready), .emb_start(o_emb_start), .emb_token(o_emb_token), .s_start(o_s_start), .s_stage(o_s_stage), .st(o_st), .fctx(o_fctx), .hu(o_hu), .su_obs_o(o_su_obs_o), .su_acc_o(o_su_acc_o), .x_oprog(o_x_oprog), .x_orows(o_x_orows), .x_oidle(o_x_oidle), .rom_ret_v(o_rom_ret_v), .dcs(o_dcs));
qfd_tt_ctlm_dv_gi_hp #(.STAGE_ME(1), .LAST_STAGE(37), .NU(4), .OPSEG(1), .CTX_SRC(1), .FCTX(1), .OPSEG_EXPANDED(1), .INIT_U0(1), .INIT_FIRST(52), .INIT_CNT(3), .OPSEG_PINREG(1), .PRIVATE_CALR(1), .F16WTN(1)) dut(.ck(ck), .rst_n(rst_n), .pw(pw), .f16_auth(f16_auth), .f16_obs(f16_obs), .f16_st(n_f16_st), .treq(n_treq), .dh(dh), .dh_user(dh_user), .init_u0(init_u0), .ctx_x(ctx_x), .mu_fault(mu_fault), .ss5(ss5), .ag5(ag5), .fab(fab), .cmd(n_cmd), .tl(n_tl), .cal_program_obs(n_cal_program_obs), .cal_descriptor_obs(n_cal_descriptor_obs), .cal_image_ready(n_cal_image_ready), .emb_start(n_emb_start), .emb_token(n_emb_token), .emb_position(n_emb_position), .emb_user(n_emb_user), .s_start(n_s_start), .s_stage(n_s_stage), .st(n_st), .fctx(n_fctx), .hu(n_hu), .su_obs_o(n_su_obs_o), .su_acc_o(n_su_acc_o), .x_oprog(n_x_oprog), .x_orows(n_x_orows), .x_oidle(n_x_oidle), .rom_ret_v(n_rom_ret_v), .dcs(n_dcs));
task tick; reg[17:0] et,ep;reg[1:0] eu;reg ev;begin
@(negedge clk);#0.01;
et=dut.tok_b[cu];ep=dut.pos_b[cu];eu=cu;ev=ce;
@(posedge clk);#0.01;ticks=ticks+1;
if(rst_n)begin

if(n_f16_st !== o_f16_st) $fatal(1,"original-output differential f16_st");
if(n_treq !== o_treq) $fatal(1,"original-output differential treq");
if(n_cmd !== o_cmd) $fatal(1,"original-output differential cmd");
if(n_tl !== o_tl) $fatal(1,"original-output differential tl");
if(n_cal_program_obs !== o_cal_program_obs) $fatal(1,"original-output differential cal_program_obs");
if(n_cal_descriptor_obs !== o_cal_descriptor_obs) $fatal(1,"original-output differential cal_descriptor_obs");
if(n_cal_image_ready !== o_cal_image_ready) $fatal(1,"original-output differential cal_image_ready");
if(n_emb_start !== o_emb_start) $fatal(1,"original-output differential emb_start");
if(n_emb_token !== o_emb_token) $fatal(1,"original-output differential emb_token");
if(n_s_start !== o_s_start) $fatal(1,"original-output differential s_start");
if(n_s_stage !== o_s_stage) $fatal(1,"original-output differential s_stage");
if(n_st !== o_st) $fatal(1,"original-output differential st");
if(n_fctx !== o_fctx) $fatal(1,"original-output differential fctx");
if(n_hu !== o_hu) $fatal(1,"original-output differential hu");
if(n_su_obs_o !== o_su_obs_o) $fatal(1,"original-output differential su_obs_o");
if(n_su_acc_o !== o_su_acc_o) $fatal(1,"original-output differential su_acc_o");
if(n_x_oprog !== o_x_oprog) $fatal(1,"original-output differential x_oprog");
if(n_x_orows !== o_x_orows) $fatal(1,"original-output differential x_orows");
if(n_x_oidle !== o_x_oidle) $fatal(1,"original-output differential x_oidle");
if(n_rom_ret_v !== o_rom_ret_v) $fatal(1,"original-output differential rom_ret_v");
if(n_dcs !== o_dcs) $fatal(1,"original-output differential dcs");
if(n_emb_start!==ev || n_emb_token!==et || n_emb_position!==ep || n_emb_user!==eu) $fatal(1,"actual pre-edge bank export mismatch user=%0d pos=%0d expected=%0d",cu,n_emb_position,ep);checks=checks+1;end
end endtask
integer u;reg[127:0]ctx;
initial begin

 repeat(4)tick();rst_n=1;repeat(4)tick();
 ctx=0;ctx[127:112]=16'h4d43;ctx[110:108]=7;
 for(u=1;u<4;u=u+1)begin ctx[36*(u-1)+:18]=18'(301+u*17);ctx[36*(u-1)+18+:18]=18'(1001+u*19);end
 ctx_x={1'b1,ctx};tick();ctx_x=0;repeat(4)tick();
 for(u=1;u<4;u=u+1)if(dut.pos_b[u] !==18'(301+u*17)||dut.tok_b[u]!==18'(1001+u*19))$fatal(1,"real context bank load");
 dh=0;dh[42]=1;dh[35:18]=18'd77;dh[17:0]=18'd101;tick();dh=0;repeat(3)tick();
 if(dut.pos_b[0]!==18'd101||dut.tok_b[0]!==18'd77)$fatal(1,"real HOST bank load");
 for(u=0;u<4;u=u+1)begin cu=2'(u);ce=1;tick();ce=0;tick();end
 // A same-edge RESULT write must preserve the pre-edge position in the export.
 cu=2;ce=1;ss5=0;ss5[24]=1;ss5[27:26]=2;ss5[17:0]=18'd2001;tick();ss5=0;tick();tick();ce=0;tick();
 if(dut.pos_b[2]!==18'd336||dut.tok_b[2]!==18'd2001)$fatal(1,"real RESULT bank update");
 cu=2;ce=1;repeat(3)tick();ce=0;repeat(3)tick();
 rst_n=0;repeat(3)tick();rst_n=1;repeat(3)tick();cu=0;ce=1;tick();
 $display("GI_OUTPUT_CUT_PASS ticks=%0d checks=%0d users=4 ctx/HOST/RESULT writes; forced calendar outputs only",ticks,checks);$finish;end
endmodule
