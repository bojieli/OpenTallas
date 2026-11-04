`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: lockstep bench of ot_hbm_host_link_capture CRCSPLIT=1 (codec RXPRE 2 / TXPRE 1) against the
// origin/main form (gold_ prefix, = CRCSPLIT 0 with RXPRE 1).  Contract: 0 added cycles, every output identical on every
// edge.  Random stimulus on every input; RX frames carry a correct CRC (and a correct header) on ~half of the frames so
// both crc_bad polarities and the clean path are exercised; resets at random every 40..200 edges (sticky aborts).
// CMUT 1/2/3 (codec bench mutants) must FAIL.
module tb;
 parameter integer CMUT=0;
 parameter integer CYC=200000;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0,epoch_begin=0,wr_v=0,wr_observed_v=0,rd_v=0,rx_expect_v=0,phy_up=0,rx_pin_v=0;
 reg [7:0] epoch=0; reg [15:0] wr_seq=0,rd_seq=0,rx_expect_seq=0; reg [544:0] wr_flit=0; reg [611:0] rx_pin_flit=0;
 wire tv_g,tv_d,rv_g,rv_d,ab_g,ab_d; wire [611:0] tf_g,tf_d; wire [544:0] rf_g,rf_d; wire [10:0] fc_g,fc_d;
 gold_ot_hbm_host_link_capture g(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),.wr_v(wr_v),
  .wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),.rx_expect_v(rx_expect_v),
  .rx_expect_seq(rx_expect_seq),.phy_up(phy_up),.tx_pin_v(tv_g),.tx_pin_flit(tf_g),.rx_pin_v(rx_pin_v),
  .rx_pin_flit(rx_pin_flit),.rx_v(rv_g),.rx_flit(rf_g),.epoch_abort(ab_g),.fault_cause(fc_g));
 ot_hbm_host_link_capture #(.CRCSPLIT(1),.CMUT(CMUT)) d(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),.phy_up(phy_up),.tx_pin_v(tv_d),.tx_pin_flit(tf_d),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rv_d),.rx_flit(rf_d),.epoch_abort(ab_d),.fault_cause(fc_d));
 // CRC of a candidate RX body (same polynomial as the codec)
 reg [579:0] body; wire [31:0] bcrc;
 ot_qwen_crc_parallel #(.DW(580),.CW(32)) u_ref(.d(body),.q(bcrc));
 integer seed=11,cyc=0,mism=0,checks=0,nrx=0,ngood=0,nclean=0,ntx=0,nab=0,rstcnt=0,nextrst=400,i;
 reg good; reg [607:0] wide; reg [575:0] wwide; integer w=0,r=0,x=0; integer wt[0:63];
 reg ab_q=0;
 always @(negedge clk)begin
  cyc<=cyc+1;
  // compare the previous posedge results
  if(cyc>2)begin
   checks<=checks+1;
   if({tv_g,ab_g,rv_g,fc_g}!=={tv_d,ab_d,rv_d,fc_d} || tf_g!==tf_d || rf_g!==rf_d)begin
    mism<=mism+1;
    if(mism<5)$display("CRCSPLIT_MISMATCH cyc=%0d tv %b/%b ab %b/%b rv %b/%b fc %h/%h tf_eq %0d rf_eq %0d",cyc,tv_g,tv_d,
      ab_g,ab_d,rv_g,rv_d,fc_g,fc_d,tf_g===tf_d,rf_g===rf_d);
   end
   if(rv_g && !ab_g)nclean<=nclean+1;
   if(tv_g)ntx<=ntx+1;
   if(ab_g && !ab_q)nab<=nab+1; ab_q<=ab_g;
  end
  // next inputs: a protocol-legal session (epoch_begin, in-order write / read / expect sequences, reads >= 4 edges after
  // their write, <= 32 outstanding) with rare injected faults (bad CRC 1/16 frames, flipped body bit 1/32, epoch
  // change / sequence skip 1/4096 edges); a new reset + session every 300..4400 edges.
  rstcnt=rstcnt+1;
  if(rstcnt>=nextrst)begin rstcnt=0; nextrst=300+($random(seed)&12'hfff); w=0; r=0; x=0; end
  rst_n<=(rstcnt>1);
  epoch_begin<=(rstcnt==4);
  epoch<=((($random(seed)&4095)==0)?8'h33:8'h5a);
  phy_up<=(rstcnt>2) && (($random(seed)&4095)!=0);
  wr_v<=0; rd_v<=0; rx_expect_v<=0; rx_pin_v<=0; wr_observed_v<=0;
  wr_seq<=$random(seed); rd_seq<=$random(seed); rx_expect_seq<=$random(seed);
  for(i=0;i<576;i=i+32)wwide[i+:32]=$random(seed);
  wr_flit<=wwide[544:0];
  for(i=0;i<608;i=i+32)wide[i+:32]=$random(seed);
  body=wide[579:0];
  #0; rx_pin_flit<={wide[607:576],body};
  if(rstcnt>6)begin
   if((w-r)<32 && ($random(seed)%3)==0)begin
    wr_v<=1; wr_observed_v<=1; wr_seq<=w+((($random(seed)&4095)==0)?1:0); wt[w%64]=cyc; w=w+1;
   end
   if(r<w && cyc-wt[r%64]>=4 && ($random(seed)%3)==0)begin rd_v<=1; rd_seq<=r; r=r+1; end
   if(($random(seed)&3)==0)begin
    rx_expect_v<=1; rx_pin_v<=1; rx_expect_seq<=x;
    body[560:545]=x; body[561+18]=1'b0; body[561+17-:8]=8'h5a; body[561+9]=1'b0; body[561+8]=1'b1;
    body[561+7:561]={2'b00,x[5:0]};
    good=(($random(seed)&15)!=0);
    #0;
    if(good)begin rx_pin_flit<={bcrc,body}; ngood<=ngood+1; end else rx_pin_flit<={~bcrc,body};
    if(($random(seed)&31)==0)rx_pin_flit[$unsigned($random(seed))%580]<=~body[0];
    x=x+1;
   end
  end
  if(rx_pin_v)nrx<=nrx+1;
 end
 initial begin
  #(CYC);
  if(mism==0)$display("CRCSPLIT_EQ PASS CMUT=%0d checks=%0d rx_frames=%0d crc_good_frames=%0d clean_rx_v=%0d tx_v=%0d aborts=%0d shift=0",
    CMUT,checks,nrx,ngood,nclean,ntx,nab);
  else $display("CRCSPLIT_EQ FAIL CMUT=%0d mismatches=%0d of %0d",CMUT,mism,checks);
  $finish;
 end
endmodule
