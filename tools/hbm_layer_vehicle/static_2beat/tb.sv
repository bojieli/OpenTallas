`timescale 1ns/1ps
module tb;
 parameter integer W=3749,B=1875,MUT=0,BAD_PHASE=0,LINK_STAGES=0,DUP_MUT=0,RESTART=0;
 parameter integer S=17;localparam integer D=LINK_STAGES+2;
 parameter[W-1:0] MASK=(W'(1)<<0)|(W'(1)<<31)|(W'(1)<<(B-1))|(W'(1)<<B)|(W'(1)<<(W-1));
 parameter[S-1:0] SMASK=17'h00203;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg[W-1:0] d=0;reg[S-1:0] side_d=0;
 wire[B-1:0] beat,channel_beat;wire[S-1:0] side_beat,channel_side,side_q;
 wire[W-1:0] q;wire tf,rf,slot0;
 ot_hbm_static_2beat_tx #(.W(W),.B(B),.S(S),.CONTROL_MASK(MASK),.SIDE_CONTROL_MASK(SMASK),.MUT(DUP_MUT?2:(MUT==1?1:0))) tx(clk,rst_n,start,d,side_d,beat,side_beat,tf,slot0);
 if(LINK_STAGES==0)begin assign channel_beat=beat;assign channel_side=side_beat;end
 else begin
  reg[B+S-1:0] pipe_q[0:LINK_STAGES-1];
  always @(posedge clk)begin
   pipe_q[0]<={side_beat,beat};
   for(integer j=1;j<LINK_STAGES;j=j+1)pipe_q[j]<=pipe_q[j-1];
  end
  assign {channel_side,channel_beat}=pipe_q[LINK_STAGES-1];
 end
 ot_hbm_static_2beat_rx #(.W(W),.B(B),.S(S),.LINK_STAGES(LINK_STAGES),.CONTROL_MASK(MASK),.SIDE_CONTROL_MASK(SMASK),.MUT(MUT==2?1:(MUT==3?2:(MUT==4?3:0)))) rx(clk,rst_n,start,channel_beat,channel_side,q,side_q,rf);
 reg[W-1:0] expected[0:D];reg[S-1:0] side_expected[0:D];
 reg[D:0] due=0;reg[W-1:0] reference=0;reg[S-1:0] side_reference=0;
 integer checks=0,words=0,errors=0;bit injected=0,emitted=0,seen_start=0;
 always @(posedge clk)begin
  if(!rst_n)begin due=0;reference=0;side_reference=0;seen_start=0;end
  else if(start&&!seen_start)begin due=0;reference=0;side_reference=0;seen_start=1;end
  else begin
   emitted=due[D-1];
   if(emitted)begin reference=expected[D-1];side_reference=side_expected[D-1];words=words+1;end
   for(integer j=D;j>0;j=j-1)begin expected[j]=expected[j-1];side_expected[j]=side_expected[j-1];end
   expected[0]=d;side_expected[0]=side_d;
   due={due[D-1:0],slot0};
   #1;
   if(words>0)begin
    checks=checks+1;
    if(q!==((reference&~MASK)|((rf||!emitted)?W'(0):(reference&MASK)))||side_q!==((side_reference&~SMASK)|((rf||!emitted)?S'(0):(side_reference&SMASK))))begin
     if(errors<3)$display("2BEAT ERROR word=%0d qlo=%h reflo=%h side=%h want=%h fault=%b",words,q[31:0],reference[31:0],side_q,side_reference,rf);
     errors=errors+1;
    end
   end
   if(!BAD_PHASE&&!DUP_MUT&&!RESTART&&(tf||rf))$fatal(1,"legal stream faulted");
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
  for(integer i=0;i<262;i=i+1)begin
   if(RESTART)start=(i==21);
   for(integer k=0;k<W;k=k+32)for(integer j=0;j<32&&j+k<W;j=j+1)d[k+j]=$urandom_range(0,1);
   side_d=S'($urandom());
   if(!slot0)begin d=d&~MASK;side_d=side_d&~SMASK;end
   if(BAD_PHASE&&i==13)begin
    if(BAD_PHASE==2)side_d=side_d|SMASK;else d=d|MASK;
    injected=1;
   end
   @(negedge clk);
  end
  d=0;side_d=0;repeat(D+6)@(negedge clk);
  if(BAD_PHASE&&(!injected||!tf||!rf||(q&MASK)!=0||(side_q&SMASK)!=0))$fatal(1,"illegal phase escaped fail-closed gate");
  if(RESTART&&(!tf||!rf))$fatal(1,"repeated boot start escaped fault");
  if(DUP_MUT&&(!rf||tf||(q&MASK)!=0))$fatal(1,"duplicate mismatch escaped RX fault");
  if(words<128||errors)$fatal(1,"2BEAT FAIL words=%0d checks=%0d errors=%0d",words,checks,errors);
  $display("2BEAT PASS W=%0d B=%0d words=%0d checks=%0d latency=%0d II=2 BAD_PHASE=%0d fault=%b",W,B,words,checks,D,BAD_PHASE,rf);$finish;
 end
endmodule
