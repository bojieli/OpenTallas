`timescale 1ns/1ps
module tb_hfd_tkm_native_codec #(parameter integer MUT=0,STALL=1);
 reg clk=0;always #5 clk=~clk;reg rn=0,start=0;
 reg[11:0]n;reg[12:0]k,nout;reg[7:0]g,gb;reg[15:0]pf;reg[39:0]ob,rb;reg hr;
 wire[39:0]cfg_packet;wire cfgbusy,rs,rf;wire[11:0]nn;wire[12:0]kk,nno;
 wire[7:0]gg,ggb;wire[15:0]pp;wire[39:0]oo,rr;wire hh;
 wire[39:0]cfg_wire=(MUT==1&&cfg_packet[38]&&cfg_packet[37:32]==4)?40'd0:cfg_packet;
 ot_hfd_tkm_cfg_tx c_tx(.clk(clk),.rst_n(rn),.start(start),.n(n),.k(k),.nout(nout),.g(g),.gbase(gb),.pf(pf),.obase(ob),.rbase(rb),.has_r(hr),.packet(cfg_packet),.busy(cfgbusy));
 ot_hfd_tkm_cfg_rx c_rx(.clk(clk),.rst_n(rn),.packet(cfg_wire),.start(rs),.fault(rf),.n(nn),.k(kk),.nout(nno),.g(gg),.gbase(ggb),.pf(pp),.obase(oo),.rbase(rr),.has_r(hh));
 reg wi=0,wr=0;reg[39:0]wa;reg[15:0]wm;reg[511:0]wd;
 wire ready,wv,wfault;wire[39:0]oa;wire[15:0]om;wire[511:0]od;
 wire[544:0]wp;wire wpr;
 wire[544:0]w_wire=(MUT==2&&wp[544]&&!wp[543])?{wp[544:1],~wp[0]}:wp;
 ot_hfd_tkm_write_tx w_tx(.clk(clk),.rst_n(rn),.w_v(wi),.w_addr(wa),.w_mask(wm),.w_data(wd),.w_rdy(ready),.packet(wp),.packet_rdy(wpr));
 ot_hfd_tkm_write_rx w_rx(.clk(clk),.rst_n(rn),.packet(w_wire),.packet_rdy(wpr),.w_v(wv),.w_addr(oa),.w_mask(om),.w_data(od),.w_rdy(wr),.fault(wfault));
 reg[39:0]ga[0:127];reg[15:0]gm[0:127];reg[511:0]gd[0:127];
 integer sent=0,recv=0,cyc=0,cfgchecked=0,cfgstartcycle=0,cfglatmax=0,flits=0,write_first=0,write_last=0;
 always @(posedge clk)if(rn)begin
  if(wi&&ready)begin if(sent==0)write_first=cyc;ga[sent]=wa;gm[sent]=wm;gd[sent]=wd;sent=sent+1;end
  if(wp[544]&&wpr)flits=flits+1;
  if(wv&&wr)begin
   if(recv>=sent||oa!==ga[recv]||om!==gm[recv]||od!==gd[recv])begin $display("TKM_NATIVE_CODEC FAIL write record=%0d sent=%0d",recv,sent);$fatal(1);end
   recv=recv+1;write_last=cyc;
  end
  if(wfault)begin $display("TKM_NATIVE_CODEC FAIL protocol");$fatal(1);end
 end
 always @(negedge clk)begin cyc=cyc+1;wr=(STALL==0)||((cyc%9)>3&&(cyc%17)!=0);end
 initial begin
  n=0;k=0;nout=0;g=0;gb=0;pf=0;ob=0;rb=0;hr=0;wa=0;wm=0;wd=0;
  repeat(4)@(negedge clk);rn=1;repeat(4)@(negedge clk);
  for(integer c=0;c<64;c=c+1)begin
   n=12'($random);k=13'($random);nout=13'($random);g=8'($random);gb=8'($random);pf=16'($random);
   ob={8'($random),32'($random)};rb={8'($random),32'($random)};hr=1'($random);
   start=1;cfgstartcycle=cyc;@(negedge clk);start=0;
   // Six wire records plus tx/rx pin stages imply <=10 cycles in this no-stall cfg transport.
   repeat(8)begin @(negedge clk);if(rs)begin
    if({nn,kk,nno,gg,ggb,pp,oo,rr,hh}!={n,k,nout,g,gb,pf,ob,rb,hr})begin $display("TKM_NATIVE_CODEC FAIL cfg bits");$fatal(1);end
    cfgchecked=cfgchecked+1;if(cyc-cfgstartcycle>cfglatmax)cfglatmax=cyc-cfgstartcycle;
   end end
   if(cfgchecked!=c+1||rf)begin $display("TKM_NATIVE_CODEC FAIL cfg missing/fault count=%0d expected=%0d",cfgchecked,c+1);$fatal(1);end
  end
  for(integer i=0;i<128;i=i+1)begin
   while(!ready)@(negedge clk);
   wa={8'($random),32'($random)};wm=16'($random);
   for(integer b=0;b<16;b=b+1)wd[32*b+:32]=$random;
   wi=1;@(negedge clk);wi=0;
  end
  // 128 writes, two flits each; consumer's bounded stall pattern and encoder's two capture stages
  // give <128*12 cycles to drain. This is a finite protocol bound, not a wall-time cap.
  repeat(1536)@(negedge clk);
  if(recv!=128||flits!=256)begin $display("TKM_NATIVE_CODEC FAIL drain recv=%0d flits=%0d",recv,flits);$fatal(1);end
  $display("TKM_NATIVE_CODEC PASS cfg=%0d writes=%0d flits=%0d cfg_lat_max=%0d write_cycles=%0d cycles=%0d",cfgchecked,recv,flits,cfglatmax,write_last-write_first+1,cyc);$finish;
 end
endmodule
