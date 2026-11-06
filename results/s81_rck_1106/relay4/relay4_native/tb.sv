`timescale 1ns/1fs
module tb;
parameter integer MUT=0;
reg rck=0,ck=0,run_rck=1;always #5 begin if(run_rck)rck=~rck;else rck=0;end
always #5.0015 ck=~ck;
reg rst=0,pma_lock=0;
wire rst_g,hold_ready;ot_pdie_pma_reset_hold #(.HOLD_EDGES(64)) guard(.rst_n(rst),.pma_lock(pma_lock),.pma_rck(rck),.core_rst_n(rst_g),.hold_ready(hold_ready));
reg [1:0] rs_r,rs_t;
always @(posedge rck or negedge rst_g)if(!rst_g)rs_r<=0;else rs_r<={rs_r[0],1'b1};
always @(posedge ck or negedge rst_g)if(!rst_g)rs_t<=0;else rs_t<={rs_t[0],1'b1};
wire rn_r=rs_r[1],rn_t=rs_t[1];
reg [543:0] word=0;
wire av,bv,af,bf,au,bu,al,bl;wire [511:0] ad,bd;wire [4:0] ae,be;wire [7:0] as,bs;wire [31:0] ac,bc,an,bn,ar,br;
ot_s81_kp4_dec_native_flat_lp_old olddut(.ck_syn(rck),.ck_dly(rck),.ck_chn(rck),.ck_out(rck),.rst_n(rn_r),.p_v(rn_r),.p_d(word),.q_v(av),.q_d(ad),.q_first(af),.q_unc(au),.q_nerr(ae),.q_seq(as),.lock(al),.n_corr(ac),.n_unc(an),.n_relock(ar));
ot_s81_kp4_dec_native_flat_lp #(.MUT(MUT)) newdut(.ck_syn(rck),.ck_dly(rck),.ck_chn(rck),.ck_out(rck),.rst_n(rn_r),.p_v(rn_r),.p_d(word),.q_v(bv),.q_d(bd),.q_first(bf),.q_unc(bu),.q_nerr(be),.q_seq(bs),.lock(bl),.n_corr(bc),.n_unc(bn),.n_relock(br));
wire [624:0] oldword={av,ad,af,au,ae,as,al,ac,an,ar};wire [624:0] newword={bv,bd,bf,bu,be,bs,bl,bc,bn,br};
reg [624:0] hist [0:3];integer h;
always @(posedge rck)begin hist[0]<=oldword;for(h=1;h<4;h=h+1)hist[h]<=hist[h-1];end
// Actual production rate matcher, with each DUT's OWN real decoder output.
wire [511:0] rx_a,rx_b;wire flt_a,flt_b;
ot_s81_rate_match rm_a(.wclk(rck),.wrst_n(rn_r),.w_v(av),.w_d(ad),.rclk(ck),.rrst_n(rn_t),.r_d(rx_a),.fault(flt_a));
ot_s81_rate_match rm_b(.wclk(rck),.wrst_n(rn_r),.w_v(bv),.w_d(bd),.rclk(ck),.rrst_n(rn_t),.r_d(rx_b),.fault(flt_b));
reg [511:0] expected [0:8191];integer wa=0,rb=0,matched=0,epochs=0;
always @(negedge rst_g)begin wa=0;rb=0;epochs=epochs+1;end
always @(posedge ck)begin
 #0.001;
 if(rn_t)begin
  if((^rx_a)===1'bx || (^rx_b)===1'bx)$fatal(1,"native FIFO output X");
  if(rx_a!=512'd2)begin expected[wa]=rx_a;wa=wa+1;end
  if(rx_b!=512'd2)begin
   if(rb>=wa || rx_b!==expected[rb])$fatal(1,"native FIFO stream differs epoch%0d index%0d available%0d",epochs,rb,wa);
   rb=rb+1;matched=matched+1;
  end
  if(flt_a || flt_b)$fatal(1,"native rate-match overflow");
 end
end
integer cycle,j,valid_words=0,lock_edges=0,low_run=0,min_low=99999;reg prior_rn=0,prior_lock=0;
always @(posedge rck)begin
 #0.002;
 if(!rn_r)low_run=low_run+1;else if(!prior_rn)begin if(low_run<min_low)min_low=low_run;if(low_run<64)$fatal(1,"outer lock guard too short: %0d",low_run);low_run=0;end
 prior_rn=rn_r;
 if(cycle>150)begin
  if((^({bv,bl,bc,bn,br,hist[3][624],hist[3][96:0]}))===1'bx)$fatal(1,"native control X at%0d",cycle);
  if(bv!==hist[3][624] || newword[96:0]!==hist[3][96:0])$fatal(1,"native control phase differs at%0d",cycle);
  if(bv)begin
   if((^newword)===1'bx || (^hist[3])===1'bx)$fatal(1,"valid native payload X at%0d",cycle);
   if(newword!==hist[3])$fatal(1,"native payload phase differs at%0d",cycle);
   valid_words=valid_words+1;
  end
  if(bl&&!prior_lock)lock_edges=lock_edges+1;prior_lock=bl;
 end
end
initial begin
 for(cycle=0;cycle<1500;cycle=cycle+1)begin
  @(negedge rck);
  for(j=0;j<17;j=j+1)word[j*32+:32]=$urandom;
  word[543:532]=(cycle%10==0)?12'hA5C:12'hFFF;
  if(cycle==8)begin rst=1;pma_lock=1;end
  if(cycle==500)begin #1;pma_lock=0;#2;pma_lock=1;end
  if(cycle==900)begin #1;run_rck=0;pma_lock=0;#77;pma_lock=1;run_rck=1;end
 end
 #20;
 if(valid_words<20 || matched<20 || lock_edges<2)$fatal(1,"insufficient real native coverage valid%0d FIFO%0d locks%0d",valid_words,matched,lock_edges);
 $display("NATIVE_RELAY4_PASS cycles1500 valid_words%0d FIFO_words%0d locks%0d min_reset_low%0d epochs%0d MUT%0d core_ppm300",valid_words,matched,lock_edges,min_low,epochs,MUT);
 $finish;
end
endmodule
