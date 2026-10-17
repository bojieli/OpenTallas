`timescale 1ns/1ps
// NEW production b2 halftrain:24 actual capturebanks,4 rows each,6 fixed-calendar producers.
// F(HB,k,j)=D+HB*NH+(k/8)*max(8NH,stride)+(k%8)*NH+j.
// NH=4,2,1,3,1 for split7..11. HB5 owns final end markers.
// Six simultaneous rows must target distinct native banks (compiler proof and sticky faults).
// No inherited physical views. 24 independent bank clock entries plus parent ck.
module qfd_res_train_half_b2_bank #(parameter integer INDEX=0,BAND=0,NB=6,D=2,MUT=0)(
 input wire ck,rst_n,enable,input wire[10:0]cycle,input wire[31:0]stride,input wire[10:0]base,input wire[3:0]ns,
 input wire[2212:0]rq,output reg[550:0]q);
 // Cold-init reset station: raw parent face sees one flop per independent root.
 reg reset_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<=1;
 wire rs=reset_q;
 reg[2207:0]data;reg[3:0]we;
`ifdef OT_QFD_B2_LATE_CAPTURE
 localparam integer LATE_CAPTURE=1; // Native hardware negative control: captures the wrong producer beat.
`else
 localparam integer LATE_CAPTURE=(MUT==3);
`endif
 wire[31:0]cap=(INDEX/8)*stride+(INDEX%8)+(LATE_CAPTURE?32'd1:32'd0);
 wire emit=enable&&cycle>=base&&cycle<base+11'(ns);
 wire[1:0]j=2'(cycle-base);
 wire[551:0]w=data[552*j+:552];
 wire ending=emit&&(BAND==NB-1)&&(MUT==2 ? j==0 : 4'(j)==ns-4'd1);
 always @(posedge ck or negedge rs)begin
 if(!rs)begin data<=0;we<=0;q<=0;end
 else begin
 if(enable&&32'(cycle)==cap)begin data<=rq[2207:0];we<=rq[2211:2208];end
 q<={emit&&(we[j]||ending),ending,ending&&!we[j],
 (emit&&we[j]?w[547:528]:20'd0),(emit&&we[j]?w[527:512]:16'd0),(emit&&we[j]?w[511:0]:512'd0)};
 end end
endmodule
module qfd_res_train_half_b2 #(
 parameter integer BAND=0,NB=6,D=2,MAX_TRAIN=8,MUT=0,BSTN=0
)(input wire ck,rst_n,input wire[23:0]ck_bank,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[3:0]slot_count,
 input wire[2212:0]rq,output reg[550:0]rb,output reg fault);
 // Parent reset face station; only cold release gains one edge.
 reg reset_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<=1;
 wire rs=reset_q;
 localparam integer BANKS=24;
 localparam integer MARKERS=8*MAX_TRAIN;
 localparam integer LAG=(MUT==1)?0:BAND;
 reg active,payload_q;reg[10:0]age,stop_q,period_q,base0_q;reg[31:0]stride_q;reg[3:0]count_q,ns_q;
 wire accept_start=train_start&&!active;
 wire ns_ok=slot_count==1||slot_count==2||slot_count==3||slot_count==4;
 reg config_bad;
 always @*begin
 config_bad=train_count<1||train_count>MAX_TRAIN||capture_stride<8||(payload_write&&train_count>3)||!ns_ok||
 (train_count>1&&capture_stride>255);
 end
 wire[3:0]selected_count=accept_start?(config_bad?4'(MAX_TRAIN):train_count):count_q;
 wire[3:0]sel_ns=config_bad?4'd4:slot_count;
 wire[10:0]sel_period=(config_bad||capture_stride>255)?11'd255:((11'(capture_stride)>{sel_ns,3'd0})?11'(capture_stride):11'({sel_ns,3'd0}));
 wire[31:0]stride=accept_start?capture_stride:stride_q;
 wire payload=accept_start?payload_write:payload_q;
 wire enable=active||accept_start;
 wire[10:0]cycle=accept_start?11'd0:age;
 // capture check (the bursts the calendar expects on rq.ov) uses the accept-edge fields, as the banks do
 reg expected,bad_addr,bad_slot;
 always @*begin
 expected=0;bad_addr=0;bad_slot=0;
 for(integer k=0;k<MARKERS;k=k+1)
 if(enable&&k<8*selected_count&&32'(cycle)==(k/8)*stride+(k%8))expected=1;
 for(integer k=0;k<4;k=k+1)begin
 if(rq[2208+k]&&|rq[552*k+548+:4])bad_addr=1;
 if(rq[2208+k]&&k>=(accept_start?sel_ns:ns_q))bad_slot=1;
 end
 end
 // per-bank emission base F(k,0) for this band, registered at accept (no emission before age D >= 2)
 function automatic [10:0] fbase(input integer k,input [3:0]n,input [10:0]p);
 fbase=11'(D)+11'(LAG)*11'(n)+11'(k/8)*p+11'(k%8)*11'(n);
 endfunction
 wire[BANKS*551-1:0]bank_q;
 // BSTN=1 (Q-B2r 10-16, multi-root leaf kit): every bank input leaves ONE parent-root (ck) station register, so each
 // primary input is captured only in the ck domain and the 24 bank roots see ordinary related reg->reg paths.  Exact
 // retiming, external edges unchanged: a bank sees cycle one edge late, so it captures rq (station copy) one edge
 // later -- still >= 1 edge before its first emission (fbase - cap >= D >= 2) -- and compares emission against
 // base-1, which lands on the same absolute edge as before.  rb / fault / the capture checks are untouched.
 reg[2211:0]rq_s;reg[10:0]cycle_s;reg[31:0]stride_s;reg[3:0]ns_s;reg[BANKS-1:0]en_s;reg[11*BANKS-1:0]base_s;
 always @(posedge ck)begin
  rq_s<=rq[2211:0];cycle_s<=cycle;stride_s<=stride;ns_s<=ns_q;
  for(integer k=0;k<BANKS;k=k+1)begin
   en_s[k]<=enable&&payload&&(k<8*selected_count);
   base_s[11*k+:11]<=fbase(k,ns_q,period_q)-11'd1;
  end
 end
 generate for(genvar bi=0;bi<BANKS;bi=bi+1)begin:bank
 localparam integer IDX=bi;
 if(BSTN!=0)begin:g_s
 qfd_res_train_half_b2_bank #(.INDEX(IDX),.BAND(BAND),.NB(NB),.D(D),.MUT(MUT))u(
 .ck(ck_bank[IDX]),.rst_n(rst_n),.enable(en_s[IDX]),.cycle(cycle_s),.stride(stride_s),
 .base(base_s[11*IDX+:11]),.ns(ns_s),.rq({1'b0,rq_s}),.q(bank_q[551*IDX+:551]));
 end else begin:g_d
 qfd_res_train_half_b2_bank #(.INDEX(IDX),.BAND(BAND),.NB(NB),.D(D),.MUT(MUT))u(
 .ck(ck_bank[IDX]),.rst_n(rst_n),.enable(enable&&payload&&(IDX<8*selected_count)),.cycle(cycle),.stride(stride),
 .base(fbase(IDX,ns_q,period_q)),.ns(ns_q),.rq(rq),.q(bank_q[551*IDX+:551]));
 end
 end endgenerate
 reg[550:0]merged;
 always @*begin merged=0;for(integer k=0;k<BANKS;k=k+1)merged=merged|bank_q[551*k+:551];end
 reg marker;
 always @*begin
 marker=0;
 for(integer k=0;k<MARKERS;k=k+1)
 if(active&&!payload_q&&(BAND==NB-1)&&k<8*count_q&&age==fbase(k,ns_q,period_q)+11'(ns_q)-11'd1)marker=1;
 end
 always @(posedge ck or negedge rs)begin
 if(!rs)begin payload_q<=0;active<=0;age<=0;stride_q<=0;count_q<=0;ns_q<=0;period_q<=0;stop_q<=0;fault<=0;rb<=0;end
 else begin
 rb<=payload?merged:{marker,marker,marker,548'd0};
 if(accept_start)begin
 active<=1;age<=1;count_q<=selected_count;stride_q<=capture_stride;payload_q<=payload_write;ns_q<=sel_ns;period_q<=sel_period;
 stop_q<=fbase(8*selected_count-1,sel_ns,sel_period)+11'(sel_ns);
 end else if(active)begin age<=age+1;if(age==stop_q)active<=0;end
 if(train_start&&active || accept_start&&config_bad || rq[2212]!=expected || expected&&bad_addr ||
 expected&&payload&&bad_slot || enable&&!payload&&|rq[2211:2208])fault<=1;
 end end
 initial if(MAX_TRAIN<1||MAX_TRAIN>8||D<2||NB!=6||BAND<0||BAND>=NB)$fatal(1,"unsupported fixed train contract");
endmodule
