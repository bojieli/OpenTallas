`timescale 1ns/1ps
// Declared component boundary: real ME command and already-reduced tree words.
// Actual DUT owns controller/frame, 384 released ROM macros, all multiplier/argmax RTL.
// Expected arrays are observers only and never feed a DUT compute or memory port.
module tb_b2_rom_e3;
reg clk=0,rs=0;always #1 clk=~clk;
reg[379:0]cmd=0;wire scale_re,pv;wire[23:0]gre;wire[575:0]scale_addr;wire[112:0]pf;
wire[12:0]sel,tv;wire[305:0]pam;wire[5:0]p_fault;
wire[23:0]acc;wire idle;wire[15:0]prog;wire[94:0]ret;wire mxwe;wire[23:0]mxa;wire[15:0]mxm;wire[511:0]mxd;
qfd_tt_ctlm_tree_b2 tree(.clk(clk),.rst_n(rs),.me_acc_o(acc),.me_idle_o(idle),.me_prog_o(prog),
 .up_fault(1'b0),.land_cnt(ld),.scale_re(scale_re),.scale_gre(gre),.scale_addr(scale_addr),.t_sel_e(sel),.t_tv_e(tv),.tr_fault(16'd0),
 .p_v_e2(pv),.p_f_e2(pf),.p_am(pam),.p_fault(p_fault),.fab_fault(1'b0),.ov(),.mx_we(mxwe),.mx_addr(mxa),.mx_mask(mxm),.mx_data(mxd),.cmd(cmd),.ret(ret));
wire[340:0]tc[0:5];wire[2212:0]rq[0:5];wire[51:0]am[0:5];wire[2049:0]cw[0:5];
for(genvar h=0;h<6;h=h+1)begin:g_port
 assign tc[h]={scale_addr[192*(h/2)+:192],gre[8*(h/2)+:8],scale_re,pf,pv,tv,sel};
 qfd_port_half_b2 #(.ROM_BAND(h/2),.ROM_HALF(h%2))port(
  .hb(3'(h)),.ck(clk),.rst_n(rs),
  .ck_bw0(clk),.ck_bw1(clk),.ck_bw2(clk),.ck_bw3(clk),.ck_bw4(clk),.ck_bw5(clk),.ck_bw6(clk),.ck_bw7(clk),
  .ck_pair0(clk),.ck_pair1(clk),.ck_pair2(clk),.ck_pair3(clk),
  .ck_col0(clk),.ck_col1(clk),.ck_col2(clk),.ck_col3(clk),.ck_col4(clk),.ck_col5(clk),.ck_col6(clk),.ck_col7(clk),.ck_col8(clk),.ck_col9(clk),.ck_col10(clk),.ck_col11(clk),.ck_col12(clk),.ck_col13(clk),.ck_col14(clk),.ck_col15(clk),
  .ck_mul0(clk),.ck_mul1(clk),.ck_mul2(clk),.ck_mul3(clk),.ck_mul4(clk),.ck_mul5(clk),.ck_mul6(clk),.ck_mul7(clk),.ck_mul8(clk),.ck_mul9(clk),.ck_mul10(clk),.ck_mul11(clk),.ck_mul12(clk),.ck_mul13(clk),.ck_mul14(clk),.ck_mul15(clk),
  .ck_group0(clk),.ck_group1(clk),.ck_group2(clk),.ck_group3(clk),
  .bw0(514'd0),.bw1(514'd0),.bw2(514'd0),.bw3(514'd0),.bw4(514'd0),.bw5(514'd0),.bw6(514'd0),.bw7(514'd0),
  .tc(tc[h]),.ty({64{32'h3f800000}}),.rq(rq[h]),.am(am[h]),.cw0(cw[h]));
 assign pam[51*h+:51]=am[h][50:0];assign p_fault[h]=am[h][51];
end
wire start,payload,issuer_fault;wire[3:0]count,nh;wire[31:0]stride;
wire[550:0]rb[0:5];wire[5:0]sf;reg[20:0]svr=0;wire[511:0]svq;wire svq_v;wire[15:0]ld;wire vf;
wire ig,io,itv,itl;wire[17:0]itiles;wire[23:0]its;wire[3:0]isplit;
qfd_b2_train_source src(.ck_head(clk),.ck_tree(clk),.rst_n(rs),.ib(cmd),.tc2(tc[2]),.me_go(ig),.me_tiles(itiles),.me_ts(its),.me_split(isplit),.me_oen(io),.tag_v(itv),.tag_last(itl));
// Literal component phase: raw controller tag->RQ14; independent sourcecopy adds1.
// Issuer TE13 starts on the same observed edge as RQ, consumed by banks next edge.
qfd_res_train_issue_b2 #(.TRAIN_EDGES(13))issuer(.ck(clk),.rst_n(rs),.me_go(ig),.me_tiles(itiles),.me_ts(its),.me_split(isplit),.me_oen(io),.tag_v(itv),.tag_last(itl),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.fault(issuer_fault));
qfd_res_train_half_b2_0 u_ser0(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[0]),.rb(rb[0]),.fault(sf[0]));
qfd_res_train_half_b2_1 u_ser1(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[1]),.rb(rb[1]),.fault(sf[1]));
qfd_res_train_half_b2_2 u_ser2(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[2]),.rb(rb[2]),.fault(sf[2]));
qfd_res_train_half_b2_3 u_ser3(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[3]),.rb(rb[3]),.fault(sf[3]));
qfd_res_train_half_b2_4 u_ser4(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[4]),.rb(rb[4]),.fault(sf[4]));
qfd_res_train_half_b2_5 u_ser5(.ck(clk),.ck_bank({24{clk}}),.rst_n(rs),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.rq(rq[5]),.rb(rb[5]),.fault(sf[5]));
qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3 vm(.native_ck({1008{clk}}),
.return_ck({96{clk}}),
.read_control_ck({3{clk}}),
.write_ck({240{clk}}),
.relay_ck({849{clk}}),
.ck(clk),
.rst_n(rs),
.ck_r0_0(clk),
.ck_r0_1(clk),
.ck_r0_3(clk),
.ck_r0_4(clk),
.ck_r0_5(clk),
.ck_r0_7(clk),
.ck_r0_8(clk),
.ck_r0_9(clk),
.ck_r0_11(clk),
.ck_r0_12(clk),
.ck_r0_13(clk),
.ck_r0_15(clk),
.ck_r0_16(clk),
.ck_r0_17(clk),
.ck_r0_19(clk),
.ck_r0_20(clk),
.ck_r0_21(clk),
.ck_r0_23(clk),
.ck_r0_24(clk),
.ck_r0_25(clk),
.ck_r0_27(clk),
.ck_r0_28(clk),
.ck_r0_29(clk),
.ck_r0_31(clk),
.ck_r0_32(clk),
.ck_r0_33(clk),
.ck_r0_35(clk),
.ck_r0_36(clk),
.ck_r0_38(clk),
.ck_r0_39(clk),
.ck_r0_41(clk),
.ck_r0_42(clk),
.ck_r0_44(clk),
.ck_r0_45(clk),
.ck_r0_47(clk),
.ck_r0_48(clk),
.ck_r0_50(clk),
.ck_r0_51(clk),
.ck_r0_52(clk),
.ck_r0_53(clk),
.ck_r0_54(clk),
.ck_r0_55(clk),
.ck_r1_0(clk),
.ck_r1_1(clk),
.ck_r1_3(clk),
.ck_r1_4(clk),
.ck_r1_5(clk),
.ck_r1_7(clk),
.ck_r1_8(clk),
.ck_r1_9(clk),
.ck_r1_11(clk),
.ck_r1_12(clk),
.ck_r1_13(clk),
.ck_r1_15(clk),
.ck_r1_16(clk),
.ck_r1_17(clk),
.ck_r1_19(clk),
.ck_r1_20(clk),
.ck_r1_21(clk),
.ck_r1_23(clk),
.ck_r1_24(clk),
.ck_r1_25(clk),
.ck_r1_27(clk),
.ck_r1_28(clk),
.ck_r1_29(clk),
.ck_r1_31(clk),
.ck_r1_32(clk),
.ck_r1_33(clk),
.ck_r1_35(clk),
.ck_r1_36(clk),
.ck_r1_38(clk),
.ck_r1_39(clk),
.ck_r1_41(clk),
.ck_r1_42(clk),
.ck_r1_44(clk),
.ck_r1_45(clk),
.ck_r1_47(clk),
.ck_r1_48(clk),
.ck_r1_50(clk),
.ck_r1_51(clk),
.ck_r1_52(clk),
.ck_r1_53(clk),
.ck_r1_54(clk),
.ck_r1_55(clk),
.ck_r2_0(clk),
.ck_r2_1(clk),
.ck_r2_3(clk),
.ck_r2_4(clk),
.ck_r2_5(clk),
.ck_r2_7(clk),
.ck_r2_8(clk),
.ck_r2_9(clk),
.ck_r2_11(clk),
.ck_r2_12(clk),
.ck_r2_13(clk),
.ck_r2_15(clk),
.ck_r2_16(clk),
.ck_r2_17(clk),
.ck_r2_19(clk),
.ck_r2_20(clk),
.ck_r2_21(clk),
.ck_r2_23(clk),
.ck_r2_24(clk),
.ck_r2_25(clk),
.ck_r2_27(clk),
.ck_r2_28(clk),
.ck_r2_29(clk),
.ck_r2_31(clk),
.ck_r2_32(clk),
.ck_r2_33(clk),
.ck_r2_35(clk),
.ck_r2_36(clk),
.ck_r2_38(clk),
.ck_r2_39(clk),
.ck_r2_41(clk),
.ck_r2_42(clk),
.ck_r2_44(clk),
.ck_r2_45(clk),
.ck_r2_47(clk),
.ck_r2_48(clk),
.ck_r2_50(clk),
.ck_r2_51(clk),
.ck_r2_52(clk),
.ck_r2_53(clk),
.ck_r2_54(clk),
.ck_r2_55(clk),
.ck_r3_0(clk),
.ck_r3_1(clk),
.ck_r3_3(clk),
.ck_r3_4(clk),
.ck_r3_5(clk),
.ck_r3_7(clk),
.ck_r3_8(clk),
.ck_r3_9(clk),
.ck_r3_11(clk),
.ck_r3_12(clk),
.ck_r3_13(clk),
.ck_r3_15(clk),
.ck_r3_16(clk),
.ck_r3_17(clk),
.ck_r3_19(clk),
.ck_r3_20(clk),
.ck_r3_21(clk),
.ck_r3_23(clk),
.ck_r3_24(clk),
.ck_r3_25(clk),
.ck_r3_27(clk),
.ck_r3_28(clk),
.ck_r3_29(clk),
.ck_r3_31(clk),
.ck_r3_32(clk),
.ck_r3_33(clk),
.ck_r3_35(clk),
.ck_r3_36(clk),
.ck_r3_38(clk),
.ck_r3_39(clk),
.ck_r3_41(clk),
.ck_r3_42(clk),
.ck_r3_44(clk),
.ck_r3_45(clk),
.ck_r3_47(clk),
.ck_r3_48(clk),
.ck_r3_50(clk),
.ck_r3_51(clk),
.ck_r3_52(clk),
.ck_r3_53(clk),
.ck_r3_54(clk),
.ck_r3_55(clk),
.ck_r4_0(clk),
.ck_r4_1(clk),
.ck_r4_3(clk),
.ck_r4_4(clk),
.ck_r4_5(clk),
.ck_r4_7(clk),
.ck_r4_8(clk),
.ck_r4_9(clk),
.ck_r4_11(clk),
.ck_r4_12(clk),
.ck_r4_13(clk),
.ck_r4_15(clk),
.ck_r4_16(clk),
.ck_r4_17(clk),
.ck_r4_19(clk),
.ck_r4_20(clk),
.ck_r4_21(clk),
.ck_r4_23(clk),
.ck_r4_24(clk),
.ck_r4_25(clk),
.ck_r4_27(clk),
.ck_r4_28(clk),
.ck_r4_29(clk),
.ck_r4_31(clk),
.ck_r4_32(clk),
.ck_r4_33(clk),
.ck_r4_35(clk),
.ck_r4_36(clk),
.ck_r4_38(clk),
.ck_r4_39(clk),
.ck_r4_41(clk),
.ck_r4_42(clk),
.ck_r4_44(clk),
.ck_r4_45(clk),
.ck_r4_47(clk),
.ck_r4_48(clk),
.ck_r4_50(clk),
.ck_r4_51(clk),
.ck_r4_52(clk),
.ck_r4_53(clk),
.ck_r4_54(clk),
.ck_r4_55(clk),
.ck_r5_0(clk),
.ck_r5_1(clk),
.ck_r5_3(clk),
.ck_r5_4(clk),
.ck_r5_5(clk),
.ck_r5_7(clk),
.ck_r5_8(clk),
.ck_r5_9(clk),
.ck_r5_11(clk),
.ck_r5_12(clk),
.ck_r5_13(clk),
.ck_r5_15(clk),
.ck_r5_16(clk),
.ck_r5_17(clk),
.ck_r5_19(clk),
.ck_r5_20(clk),
.ck_r5_21(clk),
.ck_r5_23(clk),
.ck_r5_24(clk),
.ck_r5_25(clk),
.ck_r5_27(clk),
.ck_r5_28(clk),
.ck_r5_29(clk),
.ck_r5_31(clk),
.ck_r5_32(clk),
.ck_r5_33(clk),
.ck_r5_35(clk),
.ck_r5_36(clk),
.ck_r5_38(clk),
.ck_r5_39(clk),
.ck_r5_41(clk),
.ck_r5_42(clk),
.ck_r5_44(clk),
.ck_r5_45(clk),
.ck_r5_47(clk),
.ck_r5_48(clk),
.ck_r5_50(clk),
.ck_r5_51(clk),
.ck_r5_52(clk),
.ck_r5_53(clk),
.ck_r5_54(clk),
.ck_r5_55(clk),
.ck_r6_0(clk),
.ck_r6_1(clk),
.ck_r6_3(clk),
.ck_r6_4(clk),
.ck_r6_5(clk),
.ck_r6_7(clk),
.ck_r6_8(clk),
.ck_r6_9(clk),
.ck_r6_11(clk),
.ck_r6_12(clk),
.ck_r6_13(clk),
.ck_r6_15(clk),
.ck_r6_16(clk),
.ck_r6_17(clk),
.ck_r6_19(clk),
.ck_r6_20(clk),
.ck_r6_21(clk),
.ck_r6_23(clk),
.ck_r6_24(clk),
.ck_r6_25(clk),
.ck_r6_27(clk),
.ck_r6_28(clk),
.ck_r6_29(clk),
.ck_r6_31(clk),
.ck_r6_32(clk),
.ck_r6_33(clk),
.ck_r6_35(clk),
.ck_r6_36(clk),
.ck_r6_38(clk),
.ck_r6_39(clk),
.ck_r6_41(clk),
.ck_r6_42(clk),
.ck_r6_44(clk),
.ck_r6_45(clk),
.ck_r6_47(clk),
.ck_r6_48(clk),
.ck_r6_50(clk),
.ck_r6_51(clk),
.ck_r6_52(clk),
.ck_r6_53(clk),
.ck_r6_54(clk),
.ck_r6_55(clk),
.ck_r7_0(clk),
.ck_r7_1(clk),
.ck_r7_3(clk),
.ck_r7_4(clk),
.ck_r7_5(clk),
.ck_r7_7(clk),
.ck_r7_8(clk),
.ck_r7_9(clk),
.ck_r7_11(clk),
.ck_r7_12(clk),
.ck_r7_13(clk),
.ck_r7_15(clk),
.ck_r7_16(clk),
.ck_r7_17(clk),
.ck_r7_19(clk),
.ck_r7_20(clk),
.ck_r7_21(clk),
.ck_r7_23(clk),
.ck_r7_24(clk),
.ck_r7_25(clk),
.ck_r7_27(clk),
.ck_r7_28(clk),
.ck_r7_29(clk),
.ck_r7_31(clk),
.ck_r7_32(clk),
.ck_r7_33(clk),
.ck_r7_35(clk),
.ck_r7_36(clk),
.ck_r7_38(clk),
.ck_r7_39(clk),
.ck_r7_41(clk),
.ck_r7_42(clk),
.ck_r7_44(clk),
.ck_r7_45(clk),
.ck_r7_47(clk),
.ck_r7_48(clk),
.ck_r7_50(clk),
.ck_r7_51(clk),
.ck_r7_52(clk),
.ck_r7_53(clk),
.ck_r7_54(clk),
.ck_r7_55(clk),
.ck_r7_56(clk),
.ck_r7_57(clk),
.ck_r7_58(clk),
.ck_r7_59(clk),
.ck_r7_60(clk),
.ck_r7_61(clk),
.ck_r7_62(clk),
.ck_r3_56(clk),
.ck_r3_57(clk),
.ck_r3_58(clk),
.ck_r3_59(clk),
.ck_r3_60(clk),
.ck_r3_61(clk),
.ck_r3_62(clk),
.ck_r3_63(clk),
.ck_r4_56(clk),
.ck_r4_57(clk),
.ck_r4_58(clk),
.ck_r4_59(clk),
.ck_r4_60(clk),
.ck_r4_61(clk),
.ck_r4_62(clk),
.ck_r4_63(clk),
.ck_r5_56(clk),
.ck_r5_57(clk),
.ck_r5_58(clk),
.ck_r5_59(clk),
.ck_r5_60(clk),
.ck_r5_61(clk),
.ck_r5_62(clk),
.ck_r5_63(clk),
.ck_r6_56(clk),
.ck_r6_57(clk),
.ck_r6_58(clk),
.ck_r6_59(clk),
.ck_r6_60(clk),
.ck_r6_61(clk),
.ck_r6_62(clk),
.ck_r6_63(clk),
.sa('0),
.sq(),
.mx('0),
.rb0(rb[0]),
.rb1(rb[1]),
.rb2(rb[2]),
.rb3(rb[3]),
.rb4(rb[4]),
.rb5(rb[5]),
.ld(ld),
.mo(),
.mee(1'b1),
.svr(svr),
.svr_rdy(),
.svq(svq),
.svq_v(svq_v),
.svw('0),
.ar('0),
.xaw(),
.q_epoch('0),
.q_start('0),
.q_committed(),
.q(),
.q_done(),
.write_commit_v(),
.write_commit_line(),
.write_commit_mask(),
.fault(vf));

reg[255:0]expected_scale[0:30575];reg[8191:0]expected_path;
integer op_pc=0,op_sp=0,op_tiles=0,op_nout=0,op_wcs=0,op_base=0,op_ots=0,op_ojs=0,op_oen=1,op_amax=0;
integer burst[0:5],firstcap[0:5],firsttag=-1,cycle=0,rowchecks=0,actualwrites=0,checked_lanes=0;
integer g,k,nb,addr,mask,sa;reg[31:0]want;
reg[50:0]am_expect[0:5][0:7];integer am_due[0:5][0:7];
reg[50:0]head_winner,entry,global_winner;
integer amchecks=0;
reg[511:0]gold[0:11112];reg[15:0]goldmask[0:11112];integer pendingrow[0:11112],nread=0,nresponse=0;
integer startcycle=-1,opstride=0,opends=0;reg[550:0]erb;reg[511:0]edata;integer ens,egid,erow,enb,esa,emask;

function automatic [31:0]okey(input[31:0]v);okey=v[31]?~v:{1'b1,v[30:0]};endfunction
function automatic [50:0]winner(input[50:0]a,b);
 winner=(a[50]&&(!b[50]||{a[49:18],~a[17:0]}>{b[49:18],~b[17:0]}))?a:b;
endfunction
always @(negedge clk)if(rs)begin
 cycle=cycle+1;
 if(start)begin
  if(!rq[0][2212]||firsttag<0||cycle-firsttag!=14)$fatal(1,"actual sourcecopy/issuer start misaligned pc%0d cycle%0d tag%0d",op_pc,cycle,firsttag);
  startcycle=cycle;
 end
 if(startcycle>=0)for(integer h=0;h<6;h=h+1)begin
  erb=0;ens=(op_sp==7)?4:(op_sp==8)?2:(op_sp==10)?3:1;
  for(integer bk=0;bk<8*op_tiles;bk=bk+1)for(integer j=0;j<ens;j=j+1)
  if(cycle==startcycle+2+h*ens+(bk/8)*((8*ens>opstride)?8*ens:opstride)+(bk%8)*ens+j+(op_oen?2:1))begin
   if(op_oen&&(op_sp<=9||h==0))begin
    egid=(op_sp<=9)?h*(1<<(9-op_sp))+j:j;
    erow=op_base+(bk/8)*op_ots*(3072>>op_sp)+(bk%8)*op_ojs+egid*op_ots;
    enb=(bk/8)*(3072>>op_sp)*128+(bk%8)*16;
    esa=op_wcs+enb/16+egid*8;emask=0;edata=0;
    for(integer l=0;l<16;l=l+1)if(enb+egid*128+l<op_nout)begin emask=emask|(1<<l);edata[32*l+:32]={expected_scale[esa][16*l+:16],16'd0};end
    erb={1'b1,1'(h==5&&j==ens-1),1'b0,20'(erow),16'(emask),edata};
   end else if(h==5&&j==ens-1)erb={1'b1,1'b1,1'b1,20'd0,16'd0,512'd0};
  end
  if(rb[h]!==erb)$fatal(1,"actual ROM/E3 exactRB pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,rb[h],erb);
  if(rb[h][550]&&rb[h][549])opends=opends+1;
 end
 if(svq_v)begin
  if(nresponse>=nread)$fatal(1,"unexpected native read response");
  for(integer l=0;l<16;l=l+1)if(goldmask[pendingrow[nresponse]][l]&&svq[32*l+:32]!==gold[pendingrow[nresponse]][32*l+:32])$fatal(1,"actual ROM/E3 readback row%0d lane%0d got%h want%h",pendingrow[nresponse],l,svq[32*l+:32],gold[pendingrow[nresponse]][32*l+:32]);
  nresponse=nresponse+1;
 end
 if(pv&&pf[112]&&firsttag<0)firsttag=cycle;
 for(integer h=0;h<6;h=h+1)for(integer j=0;j<8;j=j+1)if(am_due[h][j]==cycle)begin
  if(am[h][50]!==am_expect[h][j][50]||(am_expect[h][j][50]&&am[h][50:0]!==am_expect[h][j]))$fatal(1,"actual wholeport AM data/phase pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,am[h][50:0],am_expect[h][j]);
  amchecks=amchecks+1;am_due[h][j]=-1;
 end
 for(integer h=0;h<6;h=h+1)if(rq[h][2212])begin
  if(firstcap[h]<0)begin firstcap[h]=cycle;$display("CALIBRATION pc%0d h%0d firsttag%0d firstcap%0d age%0d",op_pc,h,firsttag,cycle,cycle-firsttag);end
  head_winner=0;
  k=burst[h];nb=(k/8)*(3072>>op_sp)*128+(k%8)*16;
  for(integer q=0;q<4;q=q+1)begin
   g=(op_sp<=9)?h*(1<<(9-op_sp))+q:q;
   if(q<((op_sp<=7)?4:(op_sp==8)?2:(op_sp==9)?1:(op_sp==10)?3:1)&&(op_sp<=9||h==0))begin
    if(rq[h][2208+q]!==1'(op_oen))$fatal(1,"missing realport row pc%0d h%0d q%0d",op_pc,h,q);
    addr=op_base+(k/8)*op_ots*(3072>>op_sp)+(k%8)*op_ojs+g*op_ots;
    mask=0;for(integer l=0;l<16;l=l+1)if(nb+g*128+l<op_nout)mask=mask|(1<<l);
    if(rq[h][552*q+528+:24]!==24'(addr)||rq[h][552*q+512+:16]!==16'(mask))$fatal(1,"actual port row/mask pc%0d h%0d q%0d k%0d gotrow%0d want%0d gotmask%h want%h",op_pc,h,q,k,rq[h][552*q+528+:24],addr,rq[h][552*q+512+:16],16'(mask));
    sa=op_wcs+nb/16+g*8;
    for(integer l=0;l<16;l=l+1)if(mask&(1<<l))begin
     want={expected_scale[sa][16*l+:16],16'd0};
     if(rq[h][552*q+32*l+:32]!==want)$fatal(1,"actual ROM→hardmul mismatch pc%0d h%0d q%0d k%0d lane%0d scaleaddr%0d got%h want%h",op_pc,h,q,k,l,sa,rq[h][552*q+32*l+:32],want);
     entry={1'b1,okey(want),18'(nb+g*128+l)};
     head_winner=winner(head_winner,entry);global_winner=winner(global_winner,entry);
     checked_lanes=checked_lanes+1;
    end
    rowchecks=rowchecks+1;if(op_oen)begin
     actualwrites=actualwrites+1;if(addr>11112)$fatal(1,"native row capacity exceeded");
     for(integer l=0;l<16;l=l+1)if(mask&(1<<l))begin gold[addr][32*l+:32]={expected_scale[sa][16*l+:16],16'd0};goldmask[addr][l]=1;end
    end
   end else if(rq[h][2208+q])$fatal(1,"out of b2frame row");
  end
  am_expect[h][k%8]=head_winner;am_due[h][k%8]=cycle+5;
  burst[h]=burst[h]+1;
 end
end
task automatic op(input integer pc,nout,tiles,ksize,spacing,wbase,split,wcs,obase,ots,ojs,rounds,xbase,xcs,input integer output_en=1,input integer amax_en=0);
 begin
 rs=0;cmd=0;repeat(5)@(negedge clk);#0.01;
 startcycle=-1;opends=0;opstride=spacing;nread=0;nresponse=0;svr=0;
 for(integer r=0;r<11113;r=r+1)goldmask[r]=0;
 op_oen=output_en;op_amax=amax_en;global_winner=0;
 op_pc=pc;op_sp=split;op_tiles=tiles;op_nout=nout;op_wcs=wcs;op_base=obase;op_ots=ots;op_ojs=ojs;firsttag=-1;
 for(integer h=0;h<6;h=h+1)begin burst[h]=0;firstcap[h]=-1;for(integer j=0;j<8;j=j+1)am_due[h][j]=-1;end
 rs=1;repeat(40)@(negedge clk);#0.01;
 cmd={24'd0,1'b0,1'(amax_en),1'(output_en),1'b0,24'(ojs),24'(ots),24'(obase),1'(rounds),24'(wcs),4'(split),3'd0,24'(xcs),24'd0,24'd1,24'(xbase),24'd1,24'd8,24'(spacing),24'(wbase),1'b0,18'(ksize),18'(tiles),18'(nout),1'b1};
 @(negedge clk);#0.01;cmd[0]=0;
 repeat(3000)@(negedge clk);#0.01;
 for(integer h=0;h<6;h=h+1)if(burst[h]!=8*tiles)$fatal(1,"actual port capture count pc%0d h%0d got%0d want%0d",pc,h,burst[h],8*tiles);
 if(opends!=8*tiles||ld!=16'(8*tiles)||sf||vf||issuer_fault)$fatal(1,"native ROM/issuer/train/E3 fault pc%0d ends%0d landed%0d sf%b vf%b issuer%b",pc,opends,ld,sf,vf,issuer_fault);
 for(integer r=0;r<11113;r=r+1)if(goldmask[r])begin
  pendingrow[nread]=r;nread=nread+1;svr={1'b1,20'(r)};@(negedge clk);#0.01;
 end
 svr=0;repeat(80)@(negedge clk);#0.01;
 if(nresponse!=nread)$fatal(1,"missing actual E3 readback pc%0d got%0d want%0d",pc,nresponse,nread);
 $display("PASS actualROM_E3 pc%0d writes%0d reads%0d landed%0d exactallRB",pc,actualwrites,nresponse,ld);
 if(amax_en&&(!ret[77]||ret[44:27]!==global_winner[17:0]||okey(ret[76:45])!==global_winner[49:18]))$fatal(1,"native controller scalarAM mismatch got%h idx%0d any%0d wantkey%h idx%0d",ret[76:45],ret[44:27],ret[77],global_winner[49:18],global_winner[17:0]);
 if(|p_fault||ret[94])$fatal(1,"actual controller/port fault pc%0d ret%h p_fault%b",pc,ret,p_fault);
 $display("PASS actualROMport pc%0d firsttag%0d caps%0d,%0d,%0d,%0d,%0d,%0d tag_to_capture%0d",pc,firsttag,firstcap[0],firstcap[1],firstcap[2],firstcap[3],firstcap[4],firstcap[5],firstcap[0]-firsttag);
 end
endtask
initial begin
 if(!$value$plusargs("EXPECTED=%s",expected_path))$fatal(1,"missing released expected scale observer");
 $readmemh(expected_path,expected_scale);
 op(1,768,1,8,64,0,9,0,768,8,1,1,4096,8);
 op(12,4096,3,2,16,64,8,48,0,8,1,1,50672,2);
 op(16,3072,1,32,256,112,7,336,2975,8,1,1,4096,32);
 op(20,4096,3,6,48,368,8,528,0,8,1,1,55280,6);
 op(103,6144,8,8,64,0,9,29376,0,8,1,1,8192,8,0,1);
 $display("PASS actual native controller→releasedROM→384hardmul→source50FF→issuer→sixhalftrain→E3 component checkedrows%0d actualwrites%0d checkedlanes%0d",rowchecks,actualwrites,checked_lanes);$finish;
end
endmodule
