`timescale 1ns/1ps
// Q-VMWB (2026-10-15): static PARALLEL-BAND result write-back serializer for the native Qwen TP8 compute join.
// Successor of qfd_res_train_static (train24: one band beat per VM cycle, 24 fixed slots per burst, +1,445 cyc/layer,
// ~15.6 % e2e).  Same banks and capture law; two calendar changes, both compiler-fixed:
//   (1) PARALLEL BANDS: the three bands write the VM in the same cycles on their own rb lane (the VM face already has
//       three 551-b lanes rb0..rb2; ot_qfd_sp_vector_memory_bv PAR_RB=1 lands up to three rows an edge on distinct
//       banks).  Band b lags band 0 by b bursts (b * NS cycles): with the Qwen output layouts (row = base + g*ots +
//       burst) concurrent rows then differ by one or two bursts, i.e. distinct banks mod 16 (checked by the compiler,
//       tools/qwen_vmwb/wb_calendar.py, and as a sticky static fault in the VM).
//   (2) ROW-COMPRESSED SLOTS: a burst reserves NS = slot_count slots per band instead of 8.  NS is the op's active
//       slot prefix (split law of the port bframe: 8 >> (split - 7), 8 for split <= 7, 1 above), known to the compiler
//       from the instruction; a real row (we) on a slot >= NS is a SCHEDULE FAULT, never silently dropped.
// Calendar (cycle 0 = the train_start edge = capture of burst 0):  burst k = 8 t + i (train t, index i) of band b is
// captured at t * stride + i and its slot s (< NS) is on the rb pins after edge
//      F(k, s) = D + b NS + t P + i NS + s,      P = max(8 NS, stride)  (train period, >= the capture spacing).
// F >= capture + D for every k (P >= stride, NS >= 1), so a bank never emits before its capture.  The last band's
// slot NS-1 carries `end` (a NUL beat when it holds no row): the VM lands burst k at F(k, NS-1) of band NB-1, after
// every row of bursts <= k of all bands (band NB-1 lags most).  No ready, credit, wait or runtime extension: an
// off-calendar capture, a start while active, an illegal field, a row address above 20 bits or a real row outside
// the reserved slots raises the sticky `fault` and the timeline is unchanged.
// MUT (bench negative controls): 1 = no band lag (concurrent rows collide in the VM banks); 2 = `end` on slot 0.
module qfd_res_train_par_bank #(parameter integer INDEX=0,BAND=0,NB=3,D=2,MUT=0)(
 input wire ck,rst_n,enable,input wire[10:0]cycle,input wire[31:0]stride,input wire[10:0]base,input wire[3:0]ns,
 input wire[4424:0]rq,output reg[550:0]q);
 reg[4415:0]data;reg[7:0]we;
 wire[31:0]cap=(INDEX/8)*stride+(INDEX%8);
 wire emit=enable&&cycle>=base&&cycle<base+11'(ns);
 wire[2:0]j=3'(cycle-base);
 wire[551:0]w=data[552*j+:552];
 wire ending=emit&&(BAND==NB-1)&&(MUT==2 ? j==0 : 4'(j)==ns-4'd1);
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin data<=0;we<=0;q<=0;end
 else begin
 if(enable&&32'(cycle)==cap)begin data<=rq[4415:0];we<=rq[4423:4416];end
 q<={emit&&(we[j]||ending),ending,ending&&!we[j],
 (emit&&we[j]?w[547:528]:20'd0),(emit&&we[j]?w[527:512]:16'd0),(emit&&we[j]?w[511:0]:512'd0)};
 end end
endmodule
module qfd_res_train_par #(
 parameter integer BAND=0,NB=3,D=2,MAX_TRAIN=8,MUT=0
)(input wire ck,rst_n,input wire[23:0]ck_bank,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[3:0]slot_count,
 input wire[4424:0]rq,output reg[550:0]rb,output reg fault);
 localparam integer BANKS=24;
 localparam integer MARKERS=8*MAX_TRAIN;
 localparam integer LAG=(MUT==1)?0:BAND;
 reg active,payload_q;reg[10:0]age,stop_q,period_q,base0_q;reg[31:0]stride_q;reg[3:0]count_q,ns_q;
 wire accept_start=train_start&&!active;
 wire ns_ok=slot_count==1||slot_count==2||slot_count==4||slot_count==8;
 reg config_bad;
 always @*begin
 config_bad=train_count<1||train_count>MAX_TRAIN||capture_stride<8||(payload_write&&train_count>3)||!ns_ok||
 (train_count>1&&capture_stride>255);
 end
 wire[3:0]selected_count=accept_start?(config_bad?4'(MAX_TRAIN):train_count):count_q;
 wire[3:0]sel_ns=config_bad?4'd8:slot_count;
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
 for(integer k=0;k<8;k=k+1)begin
 if(rq[4416+k]&&|rq[552*k+548+:4])bad_addr=1;
 if(rq[4416+k]&&k>=(accept_start?sel_ns:ns_q))bad_slot=1;
 end
 end
 // per-bank emission base F(k,0) for this band, registered at accept (no emission before age D >= 2)
 function automatic [10:0] fbase(input integer k,input [3:0]n,input [10:0]p);
 fbase=11'(D)+11'(LAG)*11'(n)+11'(k/8)*p+11'(k%8)*11'(n);
 endfunction
 wire[BANKS*551-1:0]bank_q;
 generate for(genvar bi=0;bi<BANKS;bi=bi+1)begin:bank
 localparam integer IDX=bi;
 qfd_res_train_par_bank #(.INDEX(IDX),.BAND(BAND),.NB(NB),.D(D),.MUT(MUT))u(
 .ck(ck_bank[IDX]),.rst_n(rst_n),.enable(enable&&payload&&(IDX<8*selected_count)),.cycle(cycle),.stride(stride),
 .base(fbase(IDX,ns_q,period_q)),.ns(ns_q),.rq(rq),.q(bank_q[551*IDX+:551]));
 end endgenerate
 reg[550:0]merged;
 always @*begin merged=0;for(integer k=0;k<BANKS;k=k+1)merged=merged|bank_q[551*k+:551];end
 reg marker;
 always @*begin
 marker=0;
 for(integer k=0;k<MARKERS;k=k+1)
 if(active&&!payload_q&&(BAND==NB-1)&&k<8*count_q&&age==fbase(k,ns_q,period_q)+11'(ns_q)-11'd1)marker=1;
 end
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin payload_q<=0;active<=0;age<=0;stride_q<=0;count_q<=0;ns_q<=0;period_q<=0;stop_q<=0;fault<=0;rb<=0;end
 else begin
 rb<=payload?merged:{marker,marker,marker,548'd0};
 if(accept_start)begin
 active<=1;age<=1;count_q<=selected_count;stride_q<=capture_stride;payload_q<=payload_write;ns_q<=sel_ns;period_q<=sel_period;
 stop_q<=fbase(8*selected_count-1,sel_ns,sel_period)+11'(sel_ns);
 end else if(active)begin age<=age+1;if(age==stop_q)active<=0;end
 if(train_start&&active || accept_start&&config_bad || rq[4424]!=expected || expected&&bad_addr ||
 expected&&payload&&bad_slot || enable&&!payload&&|rq[4423:4416])fault<=1;
 end end
 initial if(MAX_TRAIN<1||MAX_TRAIN>8||D<2||NB!=3||BAND<0||BAND>=NB)$fatal(1,"unsupported fixed train contract");
endmodule
