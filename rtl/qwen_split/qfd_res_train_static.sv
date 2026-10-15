`timescale 1ns/1ps
// Candidate only. Fixed compiler-provided start, NTRAIN and STRIDE describe
// actual IL8 producer trains. rq.ov is checked, never drives capture/issue.
// Independent bank clocks retain <=4975 storage bits per bank. ck owns
// calendar/fault and output pin register. No physical qualification.
module qfd_res_train_bank #(parameter integer INDEX=0,BAND=0,NB=3,D=2,STRIDE=16)(
 input wire ck,rst_n,enable,input wire[31:0]cycle,input wire[4424:0]rq,
 output reg[550:0]q);
 reg[4415:0]data;reg[7:0]we;
 localparam integer CAP=(INDEX/8)*STRIDE+(INDEX%8);
 localparam integer FIRST=D+24*INDEX+8*BAND;
 wire emit=enable&&cycle>=FIRST&&cycle<FIRST+8;
 wire[2:0]j=3'(cycle-FIRST);
 wire[551:0]w=data[552*j+:552];
 wire ending=emit&&(BAND==NB-1)&&j==7;
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin data<=0;we<=0;q<=0;end
 else begin
 if(enable&&cycle==CAP)begin data<=rq[4415:0];we<=rq[4423:4416];end
 q<={emit&&(we[j]||ending),ending,ending&&!we[j],
 (emit&&we[j]?w[547:528]:20'd0),(emit&&we[j]?w[527:512]:16'd0),(emit&&we[j]?w[511:0]:512'd0)};
 end end
endmodule
module qfd_res_train_static #(
 parameter integer BAND=0,NB=3,D=2,NTRAIN=3,STRIDE=16
)(input wire ck,rst_n,input wire[23:0]ck_bank,input wire train_start,
 input wire[4424:0]rq,output reg[550:0]rb,output reg fault);
 localparam integer N=8*NTRAIN;
 localparam integer STOP=D+24*N+1;
 reg active;reg[31:0]age;
 wire accept_start=train_start&&!active;
 wire enable=active||accept_start;
 wire[31:0]cycle=accept_start?32'd0:age;
 reg expected,bad_addr;integer i;
 always @*begin
 expected=0;bad_addr=0;
 for(integer k=0;k<N;k=k+1)
 if(enable&&cycle==(k/8)*STRIDE+(k%8))expected=1;
 for(integer k=0;k<8;k=k+1)
 if(rq[4416+k]&&|rq[552*k+548+:4])bad_addr=1;
 end
 wire[24*551-1:0]bank_q;
 generate for(genvar k=0;k<24;k=k+1)begin:bank
 if(k<N)begin:g_used
 qfd_res_train_bank #(.INDEX(k),.BAND(BAND),.NB(NB),.D(D),.STRIDE(STRIDE))u(
 .ck(ck_bank[k]),.rst_n(rst_n),.enable(enable),.cycle(cycle),.rq(rq),.q(bank_q[551*k+:551]));
 end else assign bank_q[551*k+:551]=0;
 end endgenerate
 reg[550:0]merged;
 always @*begin merged=0;for(integer k=0;k<24;k=k+1)merged=merged|bank_q[551*k+:551];end
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin active<=0;age<=0;fault<=0;rb<=0;end
 else begin
 rb<=merged;
 if(accept_start)begin active<=1;age<=1;end
 else if(active)begin age<=age+1;if(age==STOP)active<=0;end
 if(train_start&&active || rq[4424]!=expected || expected&&bad_addr)fault<=1;
 end end
 initial begin
 if(NTRAIN<1||NTRAIN>3||STRIDE<8||D<2||NB!=3||BAND<0||BAND>=NB)$fatal(1,"unsupported fixed train contract");
 // All captures must precede the selected bank's first emission.
 for(integer k=0;k<N;k=k+1)
 if((k/8)*STRIDE+(k%8)>=D+24*k+8*BAND)$fatal(1,"capture after bank emission");
 end
endmodule
