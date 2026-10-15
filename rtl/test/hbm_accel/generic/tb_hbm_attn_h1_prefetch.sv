`timescale 1ns/1ps
module tb_hbm_attn_h1_prefetch;
 reg clk=0;always #2 clk=~clk;reg rst_n=0;
 reg qfv=0,pfv=0,epoch=0;reg[3:0]fh=0,pb=0;reg[2:0]qb=0;reg[15:0]qbase=0,pbase=0,rows=128;
 reg qrv=0,prv=0;reg[3:0]rh=0;reg[9:0]row=0;
 wire[135:0]qrq,prq;wire[2055:0]rr,qrr,prr;wire[8191:0]qw,qfields;wire[4095:0]pfields;wire[1023:0]pw;wire qv,pv,qfault,pfault;
 reg[7:0]qo=0,po=0;reg[2247:0]preload=0;wire[143:0]status;wire[15:0]wdone;
 ot_hbm_attn_query_prefetch_h1 q(.clk(clk),.rst_n(rst_n),.fetch_v(qfv),.fetch_epoch(epoch),.fetch_head(fh),.fetch_burst(qb),.fetch_base_sector(qbase),.rq(qrq),.rr(qrr),.read_v(qrv),.read_epoch(epoch),.read_head(rh),.q_v(qv),.q_w(qw),.field_q_w(qfields),.fault(qfault));
 ot_hbm_attn_p_prefetch_h1 p(.clk(clk),.bank_clk({4{clk}}),.rst_n(rst_n),.fetch_v(pfv),.fetch_epoch(epoch),.fetch_head(fh),.fetch_burst(pb),.fetch_base_sector(pbase),.profile_rows(rows),.rq(prq),.rr(prr),.read_v(prv),.read_epoch(epoch),.read_row(row),.p_v(pv),.p_w(pw),.field_p_w(pfields),.fault(pfault));
 always @(posedge clk)if(!rst_n)begin qo<=0;po<=0;end else begin qo<={qo[6:0],qfv&&fh==0};po<={po[6:0],pfv&&fh==0};end
 for(genvar b=0;b<8;b++)begin:g_bank
  wire[6*257-1:0]allrr;wire[16:0]rq=qrq[b*17+16]?qrq[b*17+:17]:prq[b*17+:17];
  ot_vms_bank_static #(.RG(6),.WG(2))u(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'd0),
   .rq({85'd0,rq}),.rr(allrr),.wq({281'd0,preload[b*281+:281]}),.wq_done(wdone[b*2+:2]),
   .dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]));
  assign rr[b*257+:257]=allrr[0+:257];
  assign qrr[b*257+:257]={rr[b*257+256]&&qo[7],rr[b*257+:256]};
  assign prr[b*257+:257]={rr[b*257+256]&&po[7],rr[b*257+:256]};
 end
 integer seq=0,T=128,h,k,d,r,g,mut=0,qn=0,pn=0,checked=0;reg active=0;
 function automatic[15:0]qval(input integer s,dim);qval=16'h3f00^16'((dim*3+s*17)&255);endfunction
 function automatic[15:0]pval(input integer s,rr_);pval=16'h3e80^16'((rr_*5+s*13)&255);endfunction
 always @(posedge clk)begin
  if(active)begin
   if(qrq[16])begin qn++;if(qn>8)$fatal(1,"H1_PREFETCH inactive query VM request");end
   if(prq[16])begin pn++;if(pn>T/64)$fatal(1,"H1_PREFETCH inactive P VM request");end
   for(integer bb=0;bb<8;bb++)if(qrq[bb*17+16]&&prq[bb*17+16])$fatal(1,"H1_PREFETCH slot collision");
  end
  #1;
  if(active)begin
   if(qfault||pfault)$fatal(1,"H1_PREFETCH actual helper fault");
   for(integer bb=0;bb<8;bb++)if(status[bb*18+17])$fatal(1,"H1_PREFETCH actual bank fault");
  end
 end
 task tick;@(negedge clk);endtask
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(5)tick();rst_n=1;active=1;
  for(integer profile_=0;profile_<2;profile_++)begin
   T=profile_==0?128:640;rows=16'(T);
   for(seq=0;seq<3;seq++)begin
    epoch=1'(seq%2);qn=0;pn=0;
    // Real canonical SID0 Q/EB sources only. No inactive source heads exist.
    for(k=0;k<8;k++)begin
     tick();preload=0;
     for(integer bb=0;bb<8;bb++)begin
      preload[bb*281+:281]={1'b1,16'(6672+k*8+bb),256'd0,8'hff};
      for(integer w=0;w<8;w++)preload[bb*281+8+w*32+:32]={qval(seq,k*64+bb*8+w),16'((mut==1&&k==0&&bb==0&&w==0)?1:0)};
     end
    end
    for(k=0;k<T/64;k++)begin
     tick();preload=0;
     for(integer bb=0;bb<8;bb++)begin
      preload[bb*281+:281]={1'b1,16'(6912+k*8+bb),256'd0,8'hff};
      for(integer w=0;w<8;w++)preload[bb*281+8+w*32+:32]={pval(seq,k*64+bb*8+w),16'd0};
     end
    end
    tick();preload=0;repeat(8)tick();
    for(h=0;h<16;h++)for(k=0;k<8;k++)begin tick();qfv=1;fh=4'(h);qb=3'(k);qbase=16'(6672+h*64+k*8);end
    tick();qfv=0;repeat(12)tick();
    for(h=0;h<16;h++)begin
     tick();qrv=1;rh=4'(h);tick();qrv=0;
     if(!qv)$fatal(1,"H1_PREFETCH query valid");
     for(d=0;d<512;d++)begin
      if(qw[d*16+:16]!==((h==0)?qval(seq,d):16'd0))$fatal(1,"H1_PREFETCH query zero/data mismatch head%0d dim%0d",h,d);
      if(qfields[((d/32)%4)*2048+((d/32)/4)*512+(d%32)*16+:16]!==qw[d*16+:16])$fatal(1,"H1_PREFETCH query field mismatch");checked++;
     end
    end
    for(h=0;h<16;h++)for(k=0;k<T/64;k++)begin tick();pfv=1;fh=4'(h);pb=4'(k);pbase=16'(6912+h*(T/8)+k*8);end
    tick();pfv=0;repeat(12)tick();
    for(r=0;r<T;r+=4)begin
     tick();prv=1;row=10'(r);tick();prv=0;if(!pv)$fatal(1,"H1_PREFETCH P valid");
     for(g=0;g<4;g++)for(integer ll=0;ll<4;ll++)for(h=0;h<16;h++)begin
      if(pfields[g*1024+(ll*16+h)*16+:16]!==((h==0)?pval(seq,r+ll):16'd0))$fatal(1,"H1_PREFETCH P zero/data mismatch field%0d head%0d row%0d",g,h,r+ll);checked++;
     end
    end
    if(qn!=8||pn!=T/64)$fatal(1,"H1_PREFETCH source request counts%0d/%0d",qn,pn);
   end
  end
  $display("PASS H1_PREFETCH H16 hardware query64 P512 actualSID0bankRG6WG2 exclusiveRG0WG0 realzero initialization checked%0d epochs0_1_0 T128640 sourceQ512words P128640 noinactiveVMrequests",checked);$finish;
 end
endmodule
