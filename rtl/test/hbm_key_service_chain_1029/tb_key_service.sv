`timescale 1ps/1fs
module tb_key_service;
 reg clk=0;always #416.5 clk=~clk;
 reg rst=0,pwe=0,dwe=0,run=0;reg[10:0]pa=0;reg[7:0]da=0;reg[255:0]pd=0,dd=0;
 wire running,done,active,sf,mf;wire[1098:0]packet;wire[82:0]command;
 wire[3:0]gkv,gkrdy,gkwe,gkd,grv,grrdy;wire[119:0]gka;wire[15:0]gkl,grb;wire[67:0]gkt,grt;wire[1023:0]gkw,grd;wire[127:0]gks;
 ot_hbm_svc_sm_group_rel_id_rc #(.LBANKS(4),.NID(6),.IDW(9),.PAW(11),.PREL(1),.DD(256),.ID_COHORT(1),.XSLOT(1),.OPEN_IL(1),.RQD(39)) svg(
 .id_stack(2'd2),.id_sm(3'd0),.stream_clk(clk),.stream_rst_n(rst),.hbm_clk(clk),.hbm_rst_n(rst),.stream_bank_clk({2{clk}}),.hbm_fifo_clk({2{clk}}),.hbm_pc_clk({4{clk}}),
 .program_cfg_we(pwe),.program_cfg_addr(pa),.program_cfg_data(pd),.desc_we(dwe),.desc_addr(da),.desc_data(dd),.run_v(run),.run_base(8'd16),.run_count(9'd6),.run_layer(8'd0),.ids_v(1'b0),.ids_layer(8'd0),.ids(54'd0),.ids_cohort(16'd0),
 .running(running),.run_done(done),.program_active(active),.fault(sf),.sm_packet(packet),.sm_command(command),.sm_request(43'd0),
 .k_v(gkv),.k_rdy(gkrdy),.k_addr(gka),.k_len(gkl),.k_tag(gkt),.k_we(gkwe),.k_wdata(gkw),.k_wstrb(gks),.k_wr_done(gkd),.kr_v(grv),.kr_rdy(grrdy),.kr_tag(grt),.kr_beat(grb),.kr_data(grd));
 wire[3:0]kv,krdy,kwe,kd,rv,rrdy;wire[119:0]ka;wire[15:0]kl,rb;wire[67:0]kt,rt;wire[1023:0]kw,rd;wire[127:0]ks;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0),.KRL1(1)) share(.hbm_clk(clk),.hbm_rst_n(rst),.stream_clk(clk),.stream_rst_n(rst),.sm_stream(3'd0),.sm_hbm(3'd0),
 .g_k_v(gkv),.g_k_rdy(gkrdy),.g_k_addr(gka),.g_k_len(gkl),.g_k_tag(gkt),.g_k_we(gkwe),.g_k_wdata(gkw),.g_k_wstrb(gks),.g_k_wr_done(gkd),.g_kr_v(grv),.g_kr_rdy(grrdy),.g_kr_tag(grt),.g_kr_beat(grb),.g_kr_data(grd),
 .c_k_v(kv),.c_k_rdy(krdy),.c_k_addr(ka),.c_k_len(kl),.c_k_tag(kt),.c_k_we(kwe),.c_k_wdata(kw),.c_k_wstrb(ks),.c_k_wr_done(kd),.c_kr_v(rv),.c_kr_rdy(rrdy),.c_kr_tag(rt),.c_kr_beat(rb),.c_kr_data(rd),
 .vm_v(1'b0),.vm_bank(1'b0),.vm_epoch(16'd0),.vm_row(15'd0),.vm_col(4'd0),.wbw_v(1'b0),.wbw_base(30'd0),.wbw_total(12'd0),.w_k_v(4'd0),.w_k_rdy(),.w_k_addr(120'd0),.w_k_wdata(1024'd0),.w_k_wr_done(),.fill_v(),.fill_bank(),.fill_slot(),.fill_epoch(),.fill_data(),.fault(mf));
 wire[31:0]rowv,colv,colwe,dramv;wire[95:0]rowop;wire[159:0]rowbank,colbank,colcol;wire[607:0]rowrow;wire[8191:0]coldata,dramdata;wire[1023:0]colstrb;wire[3:0]cf;
 for(genvar p=0;p<4;p=p+1)begin:pc
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.QREG(1)) ctl(.clk(clk),.rst_n(rst),.pc_id(5'(p)),.refresh_reload(8'(118+((p*118/32)%118)+((((p*118/32)%118)+118+p)%2))),
  .k_v(kv[p]),.k_rdy(krdy[p]),.k_we(kwe[p]),.k_addr(ka[p*30+:30]),.k_len(kl[p*4+:4]),.k_tag(kt[p*17+:17]),.k_wdata(kw[p*256+:256]),.k_wstrb(ks[p*32+:32]),.kr_v(rv[p]),.kr_rdy(rrdy[p]),.kr_tag(rt[p*17+:17]),.kr_beat(rb[p*4+:4]),.kr_data(rd[p*256+:256]),.k_wr_done(kd[p]),
  .row_v(rowv[p]),.row_op(rowop[p*3+:3]),.row_bank(rowbank[p*5+:5]),.row_row(rowrow[p*19+:19]),.col_v(colv[p]),.col_we(colwe[p]),.col_bank(colbank[p*5+:5]),.col_col(colcol[p*5+:5]),.col_data(coldata[p*256+:256]),.col_strb(colstrb[p*32+:32]),.dram_rvalid(dramv[p]),.dram_rdata(dramdata[p*256+:256]),.pc_fault(cf[p]),.owner_fault_split());
 end
 assign rowv[31:4]=0;assign colv[31:4]=0;assign colwe[31:4]=0;assign rowop[95:12]=0;assign rowbank[159:20]=0;assign colbank[159:20]=0;assign colcol[159:20]=0;assign rowrow[607:76]=0;assign coldata[8191:1024]=0;assign colstrb[1023:128]=0;
 tb_svg_rel_dram_sparse dram(clk,rst,rowv,colv,colwe,rowop,rowbank,colbank,colcol,rowrow,coldata,colstrb,dramv,dramdata);
 reg[255:0]prog[0:3],descs[0:5];reg[1087:0]expected[0:341];
 integer age=0,cyc=0,packets=0,mut=0;reg started=0;integer rowidx,cohortidx,blockidx,delta;reg inject,cohort;reg[7:0]row;
 always @(posedge clk)begin cyc<=cyc+1;if(run)begin age<=0;started<=1;end else if(started)age<=age+1;end
 always @*begin
  inject=0;row=0;cohort=0;
  for(integer b=0;b<6;b=b+1)begin
   delta=age-(520+280*b+7);
   if(started&&delta>=0&&delta%4==0&&delta/4<((b%3==2)?43:64))begin inject=1;row=8'((b%3)*64+delta/4);cohort=(b>=3);end
  end
 end
 wire[1111:0]rail[0:3];wire[3:0]nf;
 ot_hnx_idxn_key_serial_seed seed(clk,rst,inject,3'd0,row,cohort,packet,rail[0],nf[0]);
 for(genvar p=1;p<4;p=p+1)begin:nodes
  ot_hnx_idxn_key_serial_merge merge(clk,rst,rail[p-1],1'b0,3'(p),8'd0,1'b0,1099'd0,rail[p],nf[p]);
 end
 wire[1098:0]out[0:1];wire[1:0]bf;reg prev=0,rep=0;reg[7:0]idx=0;
 for(genvar c=0;c<2;c=c+1)begin:buffers
  ot_hnx_idxn_keybuf_slice kb(.clk(clk),.rst_n(rst),.clear(1'b0),.strap_lane_id(3'd0),.live_v(rail[3][1111]&&rail[3][1110]==1'(c)),.live_index(rail[3][1109:1102]),.key_in(rail[3][1098:0]),.pre_v(prev),.pre_index(idx),.replay_v(rep),.replay_index(idx),.key_out(out[c]),.fault(bf[c]));
 end
 always @(posedge clk)if(rst)begin
  if(sf||mf||(|cf)||(|nf)||(|bf))begin $display("SERVICE_FAULT age=%0d sf=%b mf=%b cf=%b nf=%b bf=%b",age,sf,mf,cf,nf,bf);$fatal(1,"KEY_SERVICE_FAULT");end
  if(svg.u_g.program_start_v)$display("SERVICE_GO age=%0d rc=%0d",age,svg.u_g.issuer.rc);
  if(packet[1098])begin
   if(packets>=342||packet[1097:1088]!==10'(packets%171)||packet[1087:0]!==expected[packets])$fatal(1,"KEY_SERVICE_PAYLOAD packet=%0d tag=%0d",packets,packet[1097:1088]);
   if(!inject)$fatal(1,"KEY_SERVICE_SOURCE_SLOT age=%0d packet=%0d",age,packets);
   if(packets%171==0)$display("KEY_SERVICE_FIRST cohort=%0d age=%0d tag=%0d",packets/171,age,packet[1097:1088]);packets=packets+1;
  end
 end
 initial begin
  integer f,n,code;reg[31:0]a;reg[255:0]d;
  void'($value$plusargs("MUT=%d",mut));$readmemh("programme.hex",prog);$readmemh("descriptors.hex",descs);$readmemh("records.hex",expected);
  f=$fopen("memory.hex","r");if(f==0)$fatal(1,"MEMORY");
  while(!$feof(f))begin code=$fscanf(f,"%h %h\n",a,d);if(code==2)dram.mem[a]=d;end
  $fclose(f);
  repeat(12)@(posedge clk);@(negedge clk);rst=1;repeat(20)@(posedge clk);
  for(n=0;n<4;n=n+1)begin @(negedge clk);pwe=1;pa=11'(32+n);pd=prog[n];end
  @(negedge clk);pwe=0;
  for(n=0;n<6;n=n+1)begin @(negedge clk);dwe=1;da=8'(16+n);dd=descs[n];
   if(mut==1&&n==0)dd[142:119]=24'd100;
   if(mut==2&&n>=3)dd[46:32]=15'd100;
  end
  @(negedge clk);dwe=0;repeat(12)@(posedge clk);
  @(negedge clk);run=1;@(negedge clk);run=0;
  repeat(2400)@(posedge clk);
  if(packets!=342||running)$fatal(1,"KEY_SERVICE_COUNTS packet=%0d running=%b",packets,running);
  for(n=0;n<171;n=n+1)begin
   @(negedge clk);prev=1;idx=8'(n);rep=0;@(posedge clk);#1;
   @(negedge clk);prev=0;rep=1;#1;
   for(integer c=0;c<2;c=c+1)if(out[c]!=={expected[c*171+n],10'(n),1'b1})$fatal(1,"KEY_SERVICE_REPLAY cohort=%0d row=%0d",c,n);
   @(posedge clk);#1;
  end
  $display("KEY_SERVICE_CHAIN_PASS packets=%0d cohorts=2 rows=171 current_pc=h9b KRL1=1 SVG=rel_id_rc SRAM=ACTUAL",packets);$finish;
 end
endmodule
