`timescale 1ps/1ps
module tb_s81_static_collective_slab;
 parameter integer MUT=0;
 import ot_fp32_rne_pkg::*;
 reg clk=0;always #417 clk=~clk;reg s_ck=0;always #556 s_ck=~s_ck;
 reg rst_n=0;reg[84:0]c_cmd=0;wire[8:0]done;wire[1:0]status;
 wire[14:0]crq;wire[512:0]crs;wire[2203:0]writes;
 wire[7:0]tv,rv;wire[4095:0]td,rd;
 reg[513:0]f_wfc=0;wire[513:0]t_wfc;reg[76:0]f_host=0;wire[514:0]t_host;
 wire[8191:0]hc_y;wire hc_v;
 s81_static_collective_slab #(.ROM_FILE("calendar.mem"),.CYCLES(2141),.MUT(MUT)) dut(
 .ck_control({5{clk}}),.ck_lane({8{clk}}),.ck_hc_lane({16{clk}}),.rst_n(rst_n),.f_rank(2'd0),
 .c_cmd(c_cmd),.c_done(done),.c_st(status),.t_crq(crq),.f_crs(crs),.t_vm(writes),
 .phy_rx_valid(rv),.phy_rx_data(rd),.phy_rx_fault(8'd0),.phy_rx_live(8'hff),
 .phy_tx_valid(tv),.phy_tx_data(td),.f_wfc(f_wfc),.t_wfc(t_wfc),.f_host(f_host),.t_host(t_host),
 .t_hc_y(hc_y),.t_hc_yv(hc_v));
 // One actual production VM with all 128 SRAM macros. Other chip producers are
 // declared external stimuli; their digital TP4 transports are actual RTL.
 reg initializing=0;reg[2203:0]init_writes=0;
 reg[15:0]su_rqv=0;reg[223:0]su_rq=0;wire[15:0]su_rsv;wire[8191:0]su_rs;wire[1:0]vm_status;
 dsfd_sp_vm vm(.ck(s_ck),.rst(rst_n),.cks(clk),.rss(rst_n),.c_cmd(85'd0),.c_done(),.c_st(vm_status),
 .t_inp_su(),.t_inp_hc(),.f_su_rqv(su_rqv),.f_su_rq(su_rq),.t_su_rsv(su_rsv),.t_su_rs(su_rs),
 .f_su_wqv(16'd0),.f_su_wq(224'd0),.f_su_wqm(256'd0),.f_su_wqd(8192'd0),
 .f_hc_rqv(2'd0),.f_hc_rq(28'd0),.t_hc_rsv(),.t_hc_rs(),.f_hc_wqv(8'd0),
 .f_hc_wq(112'd0),.f_hc_wqm(128'd0),.f_hc_wqd(4096'd0),.f_pqx(20'd0),.t_pqx(),
 .sel(515'd0),.col(515'd0),.aSW(1027'd0),.f_capture(13376'd0),.f_wfc(560'd0),.t_wfc(),
 .f_collective(initializing?init_writes:writes),.f_crq(crq),.t_crs(crs),.t_gather(),.f_xgo(11'd0),.qSW(),.qSWs(3'b011));
 function automatic[511:0]value(input integer rank,item,kind);
  for(integer w=0;w<16;w=w+1)value[w*32+:32]=32'h3f000000+rank*65536+kind*131072+item*16+w;
 endfunction
 function automatic[511:0]sumvalue(input integer item);
  reg[33:0]a,b,c;reg[511:0]v0,v1,v2,v3;
  begin v0=value(0,item,1);v1=value(1,item,1);v2=value(2,item,1);v3=value(3,item,1);
   for(integer w=0;w<16;w=w+1)begin
    a=fp32_add_rne(v0[w*32+:32],v1[w*32+:32]);b=fp32_add_rne(v2[w*32+:32],v3[w*32+:32]);
    c=fp32_add_rne(a[31:0],b[31:0]);sumvalue[w*32+:32]=c[31:0];
   end
  end
 endfunction
 function automatic integer grow(input integer rank,item);
  if(item<20)grow=4096+20*rank+item;
  else if(item<28)grow=4224+8*rank+item-20;
  else if(item<36)grow=4816+8*rank+item-28;
  else grow=4848+8*rank+item-36;
 endfunction
 wire[11:0]peer_tv,peer_rv;wire[6143:0]peer_td,peer_rd;wire[3:0]peer_fault;
 assign peer_tv[2:0]=tv[2:0];assign peer_td[1535:0]=td[1535:0];
 assign rv[2:0]=peer_rv[2:0];assign rd[1535:0]=peer_rd[1535:0];
 assign peer_fault[0]=0;
 // All physical upper five pass-through wires loop at declared zero external
 // flight for this component. CRC/gearbox/adapter logic is not substituted.
 assign rv[7:3]=tv[7:3];assign rd[4095:1536]=td[4095:1536];
 genvar r,l;
 generate for(r=1;r<4;r=r+1)begin:P
  s81_static_fmt1_rank_dynamic peer(.rank(2'(r)),.clk(clk),.rst_n(rst_n),
  .issue_slot(dut.issue_slot),.src_valid(dut.issue_slot),.src_data(value(r,int'(dut.seq),dut.tag==32'h456)),
  .tag(dut.tag),.seq(dut.seq),.last(dut.last),.rankmask(dut.rankmask),
  .commit_slot(dut.commit_slot),.commit_tag(dut.commit_tag),.commit_seq(dut.commit_seq),
  .commit_last(dut.commit_last),.commit_rankmask(dut.commit_rankmask),.commit_rows(dut.commit_rows),
  .tx_beat_slot(dut.tx_beat_slot),.tx_phase(dut.tx_phase),.tx_frame_slot(dut.tx_frame_slot),
  .rx_beat_slot(dut.rx_beat_slot),.rx_phase(dut.rx_phase),.rx_frame_slot(dut.rx_frame_slot),
  .phy_tx_valid(peer_tv[r*3+:3]),.phy_tx_data(peer_td[r*1536+:1536]),
  .phy_rx_valid(peer_rv[r*3+:3]),.phy_rx_data(peer_rd[r*1536+:1536]),
  .vm_we(),.vm_rows(),.vm_data(),.gather_tag(),.gather_seq(),.gather_last(),.fault(peer_fault[r]));
 end
 for(r=0;r<4;r=r+1)begin:R
  for(l=0;l<3;l=l+1)begin:L
   localparam integer PEER=r^(l+1);
   assign peer_rv[r*3+l]=peer_tv[PEER*3+l];
   assign peer_rd[(r*3+l)*512+:512]=peer_td[(PEER*3+l)*512+:512];
  end
 end endgenerate
 reg[563:0]image[0:2140];integer e,j,k,rr,lp,checked_rows=0,checked_fp32=0,got_hc=0,got_done=0,got_wfc=0,got_host=0;
 reg[3:0]expected_mask;reg[511:0]expected_word;reg[8191:0]expected_hc;
 reg[511:0]raw_payload;reg[40:0]raw_metadata;
 task idle_edges(input integer n);repeat(n)@(negedge clk);endtask
 task initialize_row(input integer row,input[511:0]data);
  begin initializing=1;init_writes=0;init_writes[0+:551]={8'd0,data,16'hffff,14'(row),1'b1};@(negedge clk);end
 endtask
 initial begin
  $readmemh("calendar.mem",image);
  raw_payload=value(2,12,0);raw_metadata={1'b1,40'h9a12345678};
  idle_edges(4);rst_n=1;idle_edges(8);
  for(j=0;j<44;j=j+1)initialize_row(64+j,value(0,j,0));
  for(j=0;j<320;j=j+1)initialize_row(1024+j,value(0,j,1));
  initialize_row(8000,raw_payload);initialize_row(8001,{471'd0,raw_metadata});
  initializing=0;init_writes=0;idle_edges(60);
  for(e=0;e<2150;e=e+1)begin
   c_cmd=e<2141 ? image[e][468+:85]:85'd0;
   f_wfc=e==348 ? {1'b1,value(3,7,0),1'b1}:514'd0;
   f_host=e==348 ? {1'b1,11'h523,1'b1,64'h123456789abcdef0}:77'd0;
   @(posedge clk);#2;
   if(status[0]||vm_status[0]||(|peer_fault))$fatal(1,"fullslab fault edge%0d slab%h VM%h peer%h pack%b transport%b raw%b channel%b reduce%b assemble%b",e,status,vm_status,peer_fault,dut.pack_bad,dut.transport_fault,dut.raw_fault,dut.channel_fault,dut.reduce_fault,dut.assemble_fault);
   if(e>=2&&e<2143)begin
    if(crq[0]!==image[e-2][0])$fatal(1,"VM request edge%0d",e);
    if(crq[0]&&crq[14:1]!==image[e-2][1+:14])$fatal(1,"VM request row");
   end
   expected_mask=0;
   for(j=0;j<44;j=j+1)if(e==64+16*(j/3)+4*(j%3)+14)begin
    expected_mask=15;
    for(k=0;k<4;k=k+1)begin
     if(writes[k*551+:551]!=={8'h23,value(k,j,0),16'hffff,14'(grow(k,j)),1'b1})$fatal(1,"gather VM pins item%0d rank%0d edge%0d",j,k,e);
    end
   end
   for(j=0;j<320;j=j+1)begin
    if(e==400+16*(j/3)+4*(j%3)+32)begin
     expected_mask=1;
     if(writes[0+:551]!=={8'h56,sumvalue(j),16'hffff,14'(6000+j),1'b1})$fatal(1,"reduce VM pins item%0d edge%0d got%h want%h",j,e,writes[31+:32],sumvalue(j));
    end
   end
   if(e==360)begin
    expected_mask=3;
    if(writes[0+:551]!=={8'h27,raw_payload,16'hffff,14'd7000,1'b1})$fatal(1,"raw payload VM pins");
    if(writes[551+:551]!=={8'h27,471'd0,raw_metadata,16'h0003,14'd7001,1'b1})$fatal(1,"raw metadata VM pins");
   end
   for(k=0;k<4;k=k+1)if(writes[k*551]!==expected_mask[k])$fatal(1,"VM write calendar edge%0d port%0d got%b expect%b",e,k,writes[k*551],expected_mask[k]);
   if(done[8])begin if((e!=306||done[7:0]!=133)&&(e!=2134||done[7:0]!=134))$fatal(1,"done edge%0d tag%h",e,done);got_done=got_done+1;end
   if(hc_v)begin
    if(got_hc>=20)$fatal(1,"extra HC row");
    j=got_hc*16+15;
    if(e!=400+16*(j/3)+4*(j%3)+33)$fatal(1,"HC row edge%0d row%0d",e,got_hc);
    for(k=0;k<16;k=k+1)expected_hc[k*512+:512]=sumvalue(got_hc*16+k);
    if(hc_y!==expected_hc)$fatal(1,"HC row data%0d",got_hc);got_hc=got_hc+1;
   end
   if(t_wfc[0])begin if(e!=359||t_wfc!=={1'b1,value(3,7,0),1'b1})$fatal(1,"WFC exact edge%0d",e);got_wfc=got_wfc+1;end
   if(t_host[0])begin if(e!=359||t_host!=={2'b00,431'd0,11'h523,5'd0,1'b1,64'h123456789abcdef0,1'b1})$fatal(1,"host exact edge%0d got%h",e,t_host);got_host=got_host+1;end
   @(negedge clk);
  end
  c_cmd=0;f_wfc=0;f_host=0;idle_edges(50);
  // Actual independent SU readback of every collective destination.
  for(e=0;e<498+14;e=e+1)begin
   su_rqv=0;su_rq=0;
   if(e<498)begin
    if(e<176)rr=grow(e%4,e/4);else if(e<496)rr=6000+e-176;else rr=7000+e-496;
    lp=4+rr%4;su_rqv[lp]=1;su_rq[lp*14+:14]=14'(rr);
   end
   @(posedge clk);#2;
   if(e>=12&&e<510)begin
    j=e-12;
    if(j<176)begin rr=grow(j%4,j/4);expected_word=value(j%4,j/4,0);end
    else if(j<496)begin rr=6000+j-176;expected_word=sumvalue(j-176);end
    else begin rr=7000+j-496;expected_word=(j==496)?raw_payload:{471'd0,raw_metadata};end
    lp=4+rr%4;
    if(su_rsv!==(16'b1<<lp))$fatal(1,"actual SRAM valid edge%0d",e);
    if(j!=497&&su_rs[lp*512+:512]!==expected_word)$fatal(1,"actual SRAM destination data row%0d",rr);
    if(j==497&&su_rs[lp*512+:64]!==expected_word[63:0])$fatal(1,"actual SRAM metadata41 row%0d",rr);
    checked_rows=checked_rows+1;checked_fp32=checked_fp32+16;
   end
   if(status[0]||vm_status[0]||(|peer_fault))$fatal(1,"fault in SRAM readback");
   @(negedge clk);
  end
  if(checked_rows!=498||got_hc!=20||got_done!=2||got_wfc!=1||got_host!=1)$fatal(1,"counts %0d %0d %0d %0d %0d",checked_rows,got_hc,got_done,got_wfc,got_host);
  $display("PASS fullstatic slab actual128SRAM rows=%0d fp32_bits_checked=%0d HCrows=%0d done=%0d WFC=%0d host=%0d",checked_rows,checked_fp32,got_hc,got_done,got_wfc,got_host);$finish;
 end
endmodule
