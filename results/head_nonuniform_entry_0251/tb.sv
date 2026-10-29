`timescale 1ns/100fs
module tb_head_provider_entry;
reg ck=0,rn=0,start=0;always #0.4165 ck=~ck;
wire[511:0]ht0,ht1,pt0,pt1;reg[1:0]pv=0;reg[552:0]pd0=0,pd1=0;
wire[1:0]prv;wire[552:0]prd0,prd1;wire[3:0]pf0,pf1;
wire[276:0]hosttx;wire[275:0]hostrx;
ot_s81hd_mesh_lane p0(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,ht0}),.tx(pt0),.tx_v(pv[0]),.tx_d(pd0),.rx_v(prv[0]),.rx_d(prd0),.flt(pf0));
ot_s81hd_mesh_lane p1(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,ht1}),.tx(pt1),.tx_v(pv[1]),.tx_d(pd1),.rx_v(prv[1]),.rx_d(prd1),.flt(pf1));
ot_s81hd_host_ep_core #(.LOCAL_STAGE(81),.LOCAL_RANK(3),.PHASE_BOUND(1),
 .CLOCK_RESET_ID(64'd581311648385559719),.BOOT_HEADER_EDGE(48'd275),.BOOT_COMMIT_EDGE(48'd283))host(
 .ck(ck),.rst_n(rn),.start_i(start),.coll_i0({2'b10,pt0}),.coll_i1({2'b10,pt1}),
 .coll_o0(ht0),.coll_o1(ht1),.h_tx_i(hosttx),.h_rx_o(hostrx));
reg[1103:0]ri=0;reg[31:0]tag=0;
wire[1103:0]ro;wire fault;wire[44:0]unitbus;wire[564:0]stream;wire[63:0]ma,mb,mn;
ot_s81hd_ctl_core ctl(.ck(ck),.rst_n(rn),.start_i(start),.lep_fault_i(1'b0),.lw_i(11'd0),
 .lepk_i0(ri),.lepk_o0(ro),.lepf_o0(fault),.unit_o0(unitbus),.ctrl_i0(tag),.x_o(stream),.b_i(565'd0),
 .h_tx_o(hosttx),.h_rx_i(hostrx),.a_tx_o(ma),.b7_tx_o(mb),.n_tx_o(mn),.a_rx_i(64'd0),.b7_rx_i(64'd0),.n_rx_i(64'd0));
reg[607:0]setup[0:10];reg[1023:0]data[0:79];reg[47:0]xb_edge[0:79];
integer c=0,i,index,m=0,sent=0,issues=0,mut=0;
reg[552:0]fr;reg[255:0]ea,eb;string dir;
initial begin
 if(!$value$plusargs("DATA=%s",dir))$fatal(1,"DATA required");
 if($value$plusargs("MUT=%d",mut))begin end
 $readmemh({dir,"/setup.memh"},setup);$readmemh({dir,"/xb.memh"},data);$readmemh({dir,"/xb_edges.memh"},xb_edge);
end
always@(negedge ck)begin
 c++;rn=(c>=8);start=(c>=498);pv=0;pd0=0;pd1=0;ri=0;tag=0;
 for(i=0;i<11;i++)if(c==int'(setup[i]>>554))begin
  fr=setup[i][552:0];
  if(mut==1&&fr[3:0]==6&&fr[23:16]==2)fr[24]=~fr[24];
  if(setup[i][553])begin pv[1]=1;pd1=fr;end else begin pv[0]=1;pd0=fr;end
 end
 for(index=0;index<80;index++)if(c==int'(xb_edge[index]))begin
  if(!(mut==2&&index==79))begin
   ri=(1104'(data[index])<<21)|(1104'(index)<<13)|1104'd5;
   tag=32'd3223322641;sent++;
  end
 end
 if(c==498-1)begin
  if(!host.ctxv||host.hbc_fault||host.host_fault||fault)$fatal(1,"actual HBC/CTL setup not admitted");
  if(ctl.u_logic.c_rank!=3)$fatal(1,"wrong rank CSR2");
  if(ctl.u_logic.c_plen!=1||ctl.u_logic.c_glen!=0||ctl.u_logic.c_rbase!=97024||!ctl.u_logic.c_run)
   $fatal(1,"actual CTL CSR setup incomplete");
  if(ctl.u_logic.nbeat!=80||sent!=80)$fatal(1,"actual XB residency missing");
 end
 if(ctl.u_logic.start)begin
  issues++;
  if(c!=518)$fatal(1,"issue moved from compiled edge got%0d expected518",c);
 end
 if(c>100&&((|pf0)||(|pf1)||(|host.host_fault)||fault))$fatal(1,"current provider fault c%0d peer%h/%h host%h ctl%b",c,pf0,pf1,host.host_fault,fault);
 if(stream[513])begin
  ea=data[m/4][(m%4)*256+:256];eb=data[64+(m%64)/4][(m%4)*256+:256];
  if(stream[255:0]!==ea||stream[511:256]!==eb)$fatal(1,"actual xstore replay mismatch m%0d",m);
  m++;
  if(m==256)begin
   if(issues!=1||!ctl.u_logic.job_active_o)$fatal(1,"missing static job admission");
   $display("HEAD_PROVIDER_ENTRY PASS HBC3 CSR8 XB80 HALF512160 BF165120 stored_bits81920 replay256 rank3 static_START498 issue518 AR_ONLY no_full_HEAD_token");$finish;
  end
 end
 if(c>518+400)$fatal(1,"entry stream did not complete");
end
endmodule
