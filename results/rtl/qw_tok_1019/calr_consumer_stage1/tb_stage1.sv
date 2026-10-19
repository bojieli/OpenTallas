`timescale 1ns/1ps
// Private passive source cone: exact original column0, S near first station,
// tile16. Other columns/tree outputs are outside scope, never completion proxies.
module tb_stage1(input wire ck);
 reg rst_n=0; reg [115:0] cmd0=0,cmd_q;reg[452:0]hr0=0,hr_q;reg[1087:0]swi=0,sw_q;
 reg rs1,rst; always @(posedge ck or negedge rst_n) if(!rst_n)begin rs1<=0;rst<=0;end else begin rs1<=1;rst<=rs1;end
 always @(posedge ck or negedge rst) if(!rst)begin cmd_q<=0;hr_q<=0;sw_q<=0;end else begin cmd_q<=cmd0;hr_q<=hr0;sw_q<=swi;end
 reg[3:0]sid_q;reg sid_ok;
 wire setid=cmd_q[0]&&cmd_q[3:1]==3'd7;
 always @(posedge ck or negedge rst)if(!rst)begin sid_q<=0;sid_ok<=0;end else if(setid)begin sid_q<=cmd_q[7:4];sid_ok<=1;end
 wire go=cmd_q[0]&&sid_ok&&(cmd_q[115:112]==sid_q||cmd_q[115:112]==4'hf)&&cmd_q[3:1]!=3'd7;
 wire c_stm=go&&cmd_q[3:1]==3'd5;
 wire xt_v,xt_bad,stm_fault;wire[23:0]xt_a;wire[1023:0]xt_d;reg[2047:0]xt_f;integer l;
 qfd_dv_stream u_stm(.ck(ck),.rst_n(rst),.sid(sid_q),.cfg_v(c_stm),.cfg_dir(cmd_q[5:4]),.cfg_tag(cmd_q[33:6]),
 .sw_i(sw_q),.se_i(1088'd0),.so_e(),.so_w(),.xw_we(8'd0),.xw_addr(192'd0),.xw_data(256'd0),
 .tw_we(),.tw_kind(),.tw_addr(),.tw_data(),.xt_v(xt_v),.xt_a(xt_a),.xt_d(xt_d),.xt_bad(xt_bad),.fault(stm_fault));
 always @*for(l=0;l<64;l=l+1)xt_f[32*l+:32]={xt_d[16*l+:16],16'd0};
 wire[515:0]cn,cs;wire hd_fault;wire hv=hr_q[0];
 stage1_one_column u_hd(.ck(ck),.rst_n(rst),.sid(sid_q),.xpf({hr_q[72:2],hr_q[1]&hv}),.gi({hr_q[451:73],hr_q[452]&hv}),
 .sw_v(xt_v),.sw_a(xt_a),.sw_m(64'hffffffffffffffff),.sw_d(xt_f),.fe_i(xt_bad),.n_d(cn),.s_d(cs),.fault(hd_fault));
 wire rstl_t_0_0,rstl_x_0_0;
    wire [0:0] rpin_c0r0_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rpin_c0r0 (.ck(ck), .d(rst_n), .q(rpin_c0r0_q));   // (340.92, 43.20) c0r0 region reset pin register
    wire [0:0] rr_t_0_0_0_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rr_t_0_0_0 (.ck(ck), .d(rpin_c0r0_q), .q(rr_t_0_0_0_q));   // (82.08, 153.24) c0r0 region reset run
    wire [0:0] rr_t_0_0_1_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rr_t_0_0_1 (.ck(ck), .d(rr_t_0_0_0_q), .q(rr_t_0_0_1_q));   // (82.08, 522.11) c0r0 region reset run
    wire [0:0] rq_t_0_0_0_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_0 (.ck(ck), .d(rr_t_0_0_1_q), .q(rq_t_0_0_0_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_1_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_1 (.ck(ck), .d(rq_t_0_0_0_q), .q(rq_t_0_0_1_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_2_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_2 (.ck(ck), .d(rq_t_0_0_1_q), .q(rq_t_0_0_2_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_3_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_3 (.ck(ck), .d(rq_t_0_0_2_q), .q(rq_t_0_0_3_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_4_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_4 (.ck(ck), .d(rq_t_0_0_3_q), .q(rq_t_0_0_4_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_5_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_5 (.ck(ck), .d(rq_t_0_0_4_q), .q(rq_t_0_0_5_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_6_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_6 (.ck(ck), .d(rq_t_0_0_5_q), .q(rq_t_0_0_6_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_7_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_7 (.ck(ck), .d(rq_t_0_0_6_q), .q(rq_t_0_0_7_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_8_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_8 (.ck(ck), .d(rq_t_0_0_7_q), .q(rq_t_0_0_8_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_9_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_9 (.ck(ck), .d(rq_t_0_0_8_q), .q(rq_t_0_0_9_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_10_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_10 (.ck(ck), .d(rq_t_0_0_9_q), .q(rq_t_0_0_10_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_11_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_11 (.ck(ck), .d(rq_t_0_0_10_q), .q(rq_t_0_0_11_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_12_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_12 (.ck(ck), .d(rq_t_0_0_11_q), .q(rq_t_0_0_12_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_13_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_13 (.ck(ck), .d(rq_t_0_0_12_q), .q(rq_t_0_0_13_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_14_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_14 (.ck(ck), .d(rq_t_0_0_13_q), .q(rq_t_0_0_14_q));   // (82.08, 522.11) c0r0 region reset pad
    wire [0:0] rq_t_0_0_15_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rq_t_0_0_15 (.ck(ck), .d(rq_t_0_0_14_q), .q(rq_t_0_0_15_q));   // (82.08, 522.11) c0r0 region reset pad
    assign rstl_t_0_0 = rq_t_0_0_15_q;
    wire [0:0] rr_x_0_0_0_q;  qfd_q3h_stn #(.W(1), .N(1)) u_rr_x_0_0_0 (.ck(ck), .d(rq_t_0_0_14_q), .q(rr_x_0_0_0_q));   // (43.20, 547.93) c0r0 region reset run
    assign rstl_x_0_0 = rr_x_0_0_0_q;
 wire[515:0]dn0_entry,dn0_rly0,dn0_xcst0;wire[507:0]tap;wire[513:0]tout;
 qfd_c_stn516 u_entry(.ck(ck),.d(cs),.q(dn0_entry));qfd_c_stn516 u_relay(.ck(ck),.d(dn0_entry),.q(dn0_rly0));
 qfd_c_xstn u_station(.ck(ck),.rst_n(rstl_x_0_0),.sidx(3'd0),.b_d(dn0_rly0),.a_d(dn0_xcst0),.tap_d(tap));
 qfd_tile_nk_rp2_romleaf_rr #(.ROM_TILE(16)) u_tile(.ck(ck),.ck_rp0(ck),.ck_rp1(ck),.ck_rp2(ck),.ck_rp3(ck),.ck_rp4(ck),.ck_rp5(ck),.ck_rp6(ck),.ck_rp7(ck),.ck_rp8(ck),.ck_rp9(ck),.ck_tx0(ck),.ck_tx1(ck),.ck_tx2(ck),.ck_tx3(ck),.ck_tx4(ck),.ck_tx5(ck),.ck_tx6(ck),.ck_tx7(ck),.ck_rsw(ck),.ck_rnw(ck),.ck_dw(ck),.ck_de(ck),.ck_rs(ck),.ck_rn(ck),.ck_fa0(ck),.ck_fa1(ck),.ck_fa2(ck),.ck_fa3(ck),.ck_fa4(ck),.ck_lsl0(ck),.ck_lsl1(ck),.ck_lsl2(ck),.ck_lsl3(ck),.ck_lsl4(ck),.ck_lsl5(ck),.ck_lsl6(ck),.ck_lsl7(ck),.ck_node(ck),.rst_n(rstl_t_0_0),.tile_id(16'd16),.tie_hi(),.tie_lo(),.tap(tap),.t_out(tout),.n_a(514'd0),.n_b(514'd0),.n_y());
 integer fd,lg,cyc=0,ncyc,ec,ep,r,pre=0;reg[1087:0]ev;reg have;reg[1023:0]evf,lgf;
 initial begin if(!$value$plusargs("EV=%s",evf))$fatal(1,"EV");if(!$value$plusargs("LOG=%s",lgf))$fatal(1,"LOG");
 if(!$value$plusargs("NCYC=%d",ncyc))ncyc=6460;fd=$fopen(evf,"r");lg=$fopen(lgf,"w");if(!fd||!lg)$fatal(1,"file open");
 r=$fscanf(fd,"%d %d %h\n",ec,ep,ev);have=r==3;end
 always @(negedge ck)begin
 if(pre<4)begin pre=pre+1;if(pre==4)rst_n=1;end else begin
 if(tap[0])$fdisplay(lg,"%0d TGO %h",cyc,tap[379:1]);
 if(|tap[507:380])$fdisplay(lg,"%0d TX %h",cyc,tap[507:380]);
 if(tout[512]||tout[513])$fdisplay(lg,"%0d TOUT %0d %h",cyc,tout[513],tout[511:0]);
 cmd0=0;hr0=0;swi=0;while(have&&ec==cyc)begin
 if(ep==0)cmd0=ev[115:0];else if(ep==1)hr0=ev[452:0];else if(ep==2)swi=ev;else $fatal(1,"bad port");
 r=$fscanf(fd,"%d %d %h\n",ec,ep,ev);have=r==3;end
 if(have&&ec<cyc)$fatal(1,"unsorted");cyc=cyc+1;
 if(cyc>=ncyc)begin $display("STAGE1_CONSUMER_TERMINAL hd_fault=%0d stream_fault=%0d",hd_fault,stm_fault);$fclose(lg);$finish;end
 end end
endmodule
