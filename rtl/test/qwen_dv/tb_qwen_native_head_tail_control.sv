`timescale 1ns/1fs
// Control witness only: real captured TG4 words are replayed at all station
// component inputs. They are NOT claimed to be eight executed L6 streams.
// keep3 is an external contract model, not an implemented publisher repair.
module tb_qwen_native_head_tail_control;
 reg clk=0; always #0.416500 clk=~clk;
 reg rst_n=0,cfg=0,tw_we=0;
 reg [7:0] nw=8; reg [8:0] sb=72; reg [23:0] tw_addr=0; reg [1023:0] tw_data=0;
 reg [63:0] d[0:3]; reg [3:0] cs=0;
 wire [63:0] nb,yd; wire [1:0] nc;
 wire sfault,rfault,rv,rl,bre; wire [7:0] ri; wire [8:0] bw; wire [255:0] bq;
 reg [511:0] captured[0:127]; reg [63:0] good16[0:15],bad3[0:2];
 reg [1023:0] boots[0:3];
 integer cyc=0,origin=0,accepted=0,selected=0,outputs=0,nbbeats=0,btbeats=0;
 integer t,j,ix,rawordinal,want,first_r=-1,last_r=-1,mut_keep=0,raw_slots=64;
 reg cfg_overlap_seen=0;
 string dir,which="raw8";
 qfd_dv_s8_station_tail1_nb0 sender(
  .ck(clk),.rst_n(rst_n),.cfg_v_p(cfg),.cfg_mode_p(2'd3),.cfg_wsrc_p(1'b0),
  .cfg_nwords_p(nw),.cfg_sbase_p(9'd0),.cfg_kcm1_p(8'd7),
  .rs_s_lo_p(d[0]),.rs_s_hi_p(d[1]),.rs_n_lo_p(d[2]),.rs_n_hi_p(d[3]),
  .rs_s_c_p(cs),.rs_n_c_p(cs),.nb_od(nb),.nb_oc(nc),
  .bt_q_p(32'd0),.bt_re(),.bt_word(),.r_v(),.r_idx(),.r_last(),.r_d(),
  .flt_bank_i(4'd0),.flt_vld_i(4'd0),.flt_bank_o(),.flt_vld_o(),.fault(sfault));
 qfd_dv_s8_station_tail1 receiver(
  .ck(clk),.rst_n(rst_n),.cfg_v_p(cfg),.cfg_mode_p(2'd2),.cfg_wsrc_p(1'b0),
  .cfg_nwords_p(nw),.cfg_sbase_p(sb),.cfg_kcm1_p(8'd7),
  .rs_s_lo_p(d[0]),.rs_s_hi_p(d[1]),.rs_n_lo_p(d[2]),.rs_n_hi_p(d[3]),
  .rs_s_c_p(cs),.rs_n_c_p(cs),.nb_d_p(nb),.nb_c_p(nc),
  .nb_od(),.nb_oc(),.bt_q_p(bq[31:0]),.bt_re(bre),.bt_word(bw),
  .r_v(rv),.r_idx(ri),.r_last(rl),.r_d(yd),
  .flt_bank_i(4'd0),.flt_vld_i(4'd0),.flt_bank_o(),.flt_vld_o(),.fault(rfault));
 qfd_dv_s6_btab btab(.ck(clk),.bt_re(bre),.bt_word(bw),.bt_q(bq),
  .tw_we(tw_we),.tw_kind(2'd2),.tw_addr(tw_addr),.tw_data(tw_data));

 // Read-only observation of the actual counter's own consumed valid/selection.
 // No hierarchical force or state writes. Input position is independent of
 // the data oracle and counts genuine accepted near/far pairs.
 always @(posedge clk) begin
  cyc=cyc+1;
  if(cyc>400)$fatal(1,"TAIL watchdog case=%s accepted=%0d selected=%0d outputs=%0d",which,accepted,selected,outputs);
  if(rst_n&&(sender.cfg_schedule_fault||receiver.cfg_schedule_fault))cfg_overlap_seen=1;
  if(rst_n&&sender.plo)begin
   rawordinal=which=="keep3"?(accepted/3)*8+(accepted%3)+mut_keep:accepted;
   if(sender.vlo_in)begin
    if(which=="bad3")want=(selected/3)*24+21+(selected%3);
    else want=(selected/8)*64+56+(selected%8);
    if(rawordinal!=want)$fatal(1,"TAIL_SELECTION mismatch case=%s selected=%0d ordinal=%0d expected=%0d",which,selected,rawordinal,want);
    $display("TAIL_SELECTED case=%s ordinal=%0d cycle=%0d",which,rawordinal,cyc-origin);
    selected=selected+1;
   end
   accepted=accepted+1;
  end
  #0.2;
  if(rst_n)begin
   if(sfault||rfault)begin
    if(which=="cfg_between"&&cfg_overlap_seen&&accepted>0&&accepted<128)
     $fatal(1,"EXPECTED_NATIVE_CONTIGUOUS_ROUND_CFG_FAULT accepted=%0d selected=%0d outputs=%0d",accepted,selected,outputs);
    if(which=="bad3"&&rfault&&!sfault&&accepted==64&&selected==6&&outputs==3)begin
     $display("TAIL_COUNTER_BUG accepted64 selected21_22_23_45_46_47 outputs3 receiver_j=%0d",receiver.j);
     $fatal(1,"EXPECTED_NATIVE_RAW64_NWORDS3_FAULT");
    end
    $fatal(1,"unexpected native station fault case=%s sender=%b receiver=%b accepted=%0d selected=%0d outputs=%0d",which,sfault,rfault,accepted,selected,outputs);
   end
   if(nc[0])nbbeats=nbbeats+1;
   if(bre)begin
    if(bw!==9'(72+btbeats))$fatal(1,"TAIL BTAB address");
    btbeats=btbeats+1;
   end
   if(rv)begin
    if(outputs>=nw||ri!==8'(outputs)||rl!==(outputs==nw-1))$fatal(1,"TAIL result identity/count");
    if(which=="bad3")begin
     if(yd!==bad3[outputs])$fatal(1,"TAIL bad3 expected wrong-prefix value mismatch");
    end else if(yd!==good16[outputs])$fatal(1,"TAIL output mismatch case=%s index=%0d",which,outputs);
    if(which=="round16")$display("HEAD_ROW_MODEL idx=%0d linear=%0d stride768=%0d",ri,16*ri,768*(ri>>3)+16*(ri&7));
    if(first_r<0)first_r=cyc-origin;last_r=cyc-origin;outputs=outputs+1;
   end
  end
 end
 initial begin
  if($value$plusargs("CASE=%s",which))begin end
  if($value$plusargs("MUT_KEEP=%d",mut_keep))begin end
  if(which!="raw8"&&which!="bad3"&&which!="keep3"&&which!="round16"&&which!="cfg_between")$fatal(1,"unknown case");
  if(mut_keep<0||mut_keep>1||(mut_keep!=0&&which!="keep3"))$fatal(1,"invalid keep mutant");
  if(!$value$plusargs("INPUT=%s",dir))$fatal(1,"INPUT required");
  raw_slots=(which=="round16"||which=="cfg_between")?128:64;
  nw=which=="round16"?16:(which=="raw8"||which=="cfg_between")?8:3;
  $readmemh({dir,"/captured_TG4_128.hex"},captured);
  $readmemh({dir,"/good16.hex"},good16);$readmemh({dir,"/bad3_first.hex"},bad3);
  $readmemh({dir,"/genuine_btab_four_records.hex"},boots);
  for(j=0;j<4;j=j+1)d[j]=0;
  repeat(24)@(negedge clk);rst_n=1;repeat(24)@(negedge clk);
  for(j=0;j<4;j=j+1)begin tw_we=1;tw_addr=72+4*j;tw_data=boots[j];@(negedge clk);end
  tw_we=0;cfg=1;@(negedge clk);cfg=0;repeat(8)@(negedge clk);origin=cyc;
  for(t=0;t<raw_slots+14;t=t+1)begin
   cfg=which=="cfg_between"&&t==64;if(cfg)sb=80;
   cs=0;for(j=0;j<4;j=j+1)d[j]=0;
   for(j=0;j<2;j=j+1)begin
    ix=t-(j==0?0:14);
    if(ix>=0&&ix<raw_slots)begin
     d[j]=captured[ix][63:0];d[j+2]=captured[ix][63:0];
     if(which!="keep3"||(ix%8>=mut_keep&&ix%8<3+mut_keep))cs[2*j]=1;
    end
   end
   @(negedge clk);
  end
  cs=0;cfg=0;
  if(which=="bad3"||which=="cfg_between")begin repeat(180)@(negedge clk);$fatal(1,"negative case failed to trigger native fault");end
  while(outputs<nw)@(negedge clk);repeat(24)@(negedge clk);
  if(selected!=nw||nbbeats!=nw||btbeats!=nw||accepted!=(which=="keep3"?24:raw_slots))$fatal(1,"TAIL terminal counts");
  $display("PASS_NATIVE_TAIL_CONTROL case=%s accepted=%0d selected=%0d outputs=%0d result_age=%0d..%0d nominal833ps CONTROL_REPLAY_NOT_L6",which,accepted,selected,outputs,first_r,last_r);
  $finish;
 end
endmodule
