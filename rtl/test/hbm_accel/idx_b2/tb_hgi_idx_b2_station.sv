`timescale 1ns/1ps
module tb_hgi_idx_b2_station;
 reg clk=0;always #5 clk=~clk;reg rn=0;
 reg [5:0] ug=0,dr=0;reg[7:0] uc=0;reg[2055:0] ur=0;
 reg lr=0;reg[135:0] lq=0,dq=0;
 wire[5:0] req,dg;wire[135:0] q;wire[7:0] dc,lc;wire[2055:0] ds,ls;wire grant;
 ot_hgi_idx_b2_station dut(.clk(clk),.rst_n(rn),.r_up_req(req),.r_up_q(q),.r_up_gnt(ug),.r_up_cr(uc),.r_up_rsp(ur),
 .r_dn_req(dr),.r_dn_q(dq),.r_dn_gnt(dg),.r_dn_cr(dc),.r_dn_rsp(ds),.r_req(lr),.r_gnt(grant),.rq(lq),.rq_cr(lc),.rr(ls),
 .w_up_req(wreq),.w_up_q(wqout),.w_up_gnt(wug),.w_up_cr(wuc),.w_up_rsp(wur),.w_dn_req(wdr),.w_dn_q(wdq),.w_dn_gnt(wdg),.w_dn_cr(wdc),.w_dn_rsp(wds),.w_req(wlr),.w_gnt(wg),.wq(wlq),.wq_cr(wlc),.wq_done(wls));
 reg[5:0] wug=0,wdr=0;reg[7:0] wuc=0,wur=0;reg wlr=0;reg[2247:0] wlq=0,wdq=0;
 wire[5:0] wreq,wdg;wire[2247:0] wqout;wire[7:0] wdc,wlc,wds,wls;wire wg;
 integer i,b;task edge1;begin @(posedge clk);#1;end endtask
 initial begin
  edge1;rn=1;lr=1;dr=6'b001001;edge1;
  if(req!=6'b101001)$fatal(1,"slot5 request missing");
  ug=6'b100000;uc=8'ha5;for(b=0;b<8;b=b+1)ur[b*257+:257]={1'b1,256'(b+1)};
  edge1;if(!grant||lc!=uc||ls!=ur||ds!=ur||dg!=ug)$fatal(1,"reply credit bind");
  for(i=0;i<100;i=i+1)begin
   for(b=0;b<8;b=b+1)lq[b*17+:17]={1'b1,1'b1,2'b00,13'(8*i+b)};
   edge1;if(q!=lq)$fatal(1,"native mirror sec16 lost");
  end
  lr=0;edge1;if(grant)$fatal(1,"released grant exposed");
  lr=1;edge1;if(grant)$fatal(1,"stale grant reused");
  ug=0;edge1;ug=6'b100000;edge1;if(!grant)$fatal(1,"new grant absent");
  ug=6'b000010;edge1;if(lc||ls||grant)$fatal(1,"wrong owner response");
  wlr=1;wdr=6'b000101;edge1;if(wreq!=6'b100101)$fatal(1,"write slot5 request");
  wug=6'b100000;wuc=8'h5a;wur=8'h3c;edge1;
  if(!wg||wlc!=wuc||wls!=wur||wds!=wur||wdg!=wug)$fatal(1,"write credit versus done bind");
  for(i=0;i<100;i=i+1)begin
   for(b=0;b<8;b=b+1)wlq[b*281+:281]={1'b1,1'b0,2'b00,13'(8*i+b),{8{32'(i+b)}},8'(i+b)};
   edge1;if(wqout!=wlq)$fatal(1,"write sector/data/mask bind");
  end
  wlr=0;edge1;if(wg)$fatal(1,"write release");
  wlr=1;edge1;if(wg)$fatal(1,"write stale grant");
  wug=0;edge1;wug=6'b100000;edge1;if(!wg)$fatal(1,"write new grant");
  wug=6'b000001;edge1;if(wlc||wls||wg)$fatal(1,"write wrong owner");
  $display("PASS IDX_B2_STATION slot5 native lanes mirror release credit/reply");$finish;
 end
endmodule
