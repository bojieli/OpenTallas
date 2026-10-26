`timescale 1ns/1ps
// Candidate only. Compiler provides a command start and immutable count/stride.
// rq.ov is checked; capture/emission never waits, gates issue or reschedules.
// MAX_TRAIN=8 covers exact source head PC3..5 (8 tiles,k8); decoder max3.
// 24 data banks cover decoder max3 trains. oen0 head retains all64 markers
// in the control calendar without storing nonexistent payload. Each real data
// bank has4424 capture+551 output bits on its own clock entry.
module qfd_res_train_bank #(parameter integer INDEX=0,BAND=0,NB=3,D=2)(
 input wire ck,rst_n,enable,input wire[31:0]cycle,stride,input wire[4424:0]rq,
 output reg[550:0]q);
 reg[4415:0]data;reg[7:0]we;
 wire[31:0]cap=(INDEX/8)*stride+(INDEX%8);
 localparam integer FIRST=D+23*INDEX+8*BAND;
 wire emit=enable&&cycle>=FIRST&&cycle<FIRST+8;
 wire[2:0]j=3'(cycle-FIRST);
 wire[551:0]w=data[552*j+:552];
 wire ending=emit&&(BAND==NB-1)&&j==7;
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin data<=0;we<=0;q<=0;end
 else begin
 if(enable&&cycle==cap)begin data<=rq[4415:0];we<=rq[4423:4416];end
 q<={emit&&(we[j]||ending),ending,ending&&!we[j],
 (emit&&we[j]?w[547:528]:20'd0),(emit&&we[j]?w[527:512]:16'd0),(emit&&we[j]?w[511:0]:512'd0)};
 end end
endmodule
module qfd_res_train_static #(
 parameter integer BAND=0,NB=3,D=2,MAX_TRAIN=8
)(input wire ck,rst_n,input wire[23:0]ck_bank,
 input wire train_start,input wire[3:0]train_count,input wire[31:0]capture_stride,input wire payload_write,
 input wire[4424:0]rq,output reg[550:0]rb,output reg fault);
 localparam integer BANKS=24;
 localparam integer MARKERS=8*MAX_TRAIN;
 reg active,payload_q;reg[31:0]age,stride_q,stop_q;reg[3:0]count_q;
 wire accept_start=train_start&&!active;
 // Invalid fields fault at the same edge. A fixed MAX_TRAIN window follows;
 // there is no waiting for corrected configuration or runtime extension.
 reg config_bad;
 always @*begin
 config_bad=train_count<1||train_count>MAX_TRAIN||capture_stride<8||(payload_write&&train_count>3)||
 (64'(train_count-1)*capture_stride+7>=D+24*8*train_count);
 for(integer k=0;k<MARKERS;k=k+1)
 if(payload_write&&k<8*train_count && (64'(k/8)*capture_stride+(k%8)>=D+24*k))config_bad=1;
 end
 wire[3:0]selected_count=accept_start?(config_bad?4'(MAX_TRAIN):train_count):count_q;
 wire[31:0]stride=accept_start?capture_stride:stride_q;
 wire payload=accept_start?payload_write:payload_q;
 wire enable=active||accept_start;
 wire[31:0]cycle=accept_start?32'd0:age;
 reg expected,bad_addr;
 always @*begin
 expected=0;bad_addr=0;
 for(integer k=0;k<MARKERS;k=k+1)
 if(enable&&k<8*selected_count&&cycle==(k/8)*stride+(k%8))expected=1;
 for(integer k=0;k<8;k=k+1)
 if(rq[4416+k]&&|rq[552*k+548+:4])bad_addr=1;
 end
 wire[BANKS*551-1:0]bank_q;
 generate for(genvar bi=0;bi<BANKS;bi=bi+1)begin:bank
 localparam integer IDX=bi;
 qfd_res_train_bank #(.INDEX(IDX),.BAND(BAND),.NB(NB),.D(D))u(
 .ck(ck_bank[IDX]),.rst_n(rst_n),.enable(enable&&payload&&(IDX<8*selected_count)),.cycle(cycle),.stride(stride),.rq(rq),.q(bank_q[551*IDX+:551]));
 end endgenerate
 reg[550:0]merged;
 always @*begin merged=0;for(integer k=0;k<BANKS;k=k+1)merged=merged|bank_q[551*k+:551];end
 wire marker=enable&&!payload&&(BAND==NB-1)&&cycle>=D+8*BAND+8&&
 ((cycle-(D+8*BAND+8))%24==0)&&((cycle-(D+8*BAND+8))/24<8*selected_count);
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin payload_q<=0;active<=0;age<=0;stride_q<=0;count_q<=0;stop_q<=0;fault<=0;rb<=0;end
 else begin
 rb<=payload?merged:{marker,marker,marker,548'd0};
 if(accept_start)begin
 active<=1;age<=1;count_q<=selected_count;stride_q<=capture_stride;payload_q<=payload_write;
 stop_q<=D+24*8*selected_count+1;
 end else if(active)begin age<=age+1;if(age==stop_q)active<=0;end
 if(train_start&&active || accept_start&&config_bad || rq[4424]!=expected || expected&&bad_addr || enable&&!payload&&|rq[4423:4416])fault<=1;
 end end
 initial if(MAX_TRAIN<1||MAX_TRAIN>8||D<2||NB!=3||BAND<0||BAND>=NB)$fatal(1,"unsupported fixed train contract");
endmodule
