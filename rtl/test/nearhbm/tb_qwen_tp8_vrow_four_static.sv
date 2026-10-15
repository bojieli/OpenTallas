`timescale 1ns/1ps
module tb_qwen_tp8_vrow_four_static;
 parameter integer MODE=0;
 localparam RL=5;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,start=0;reg[13:0] context_len;reg[15:0] epoch;
 wire[3:0] req,ov,done,fault,first,last;
 wire[13:0] qt[0:3],ot[0:3];wire[2:0] qs[0:3];wire[15:0] qe[0:3],oe[0:3];
 wire[1023:0] data[0:3];wire[63:0] expdata[0:3];
 reg[RL:0] valid_p[0:3];reg[13:0] tag_p[0:3][0:RL];reg[2:0] slot_p[0:3][0:RL];reg[15:0] ep_p[0:3][0:RL];
 integer cyc,case_no,n,i,j;integer requested[0:3],returned[0:3],last_req[0:3];reg[3:0] done_seen;
 reg seen[0:8191];integer contexts[0:12];
 for(genvar s=0;s<4;s++)begin:g
  localparam D=(MODE==1)?RL:RL-1;
  wire[13:0] rt=tag_p[s][D]^((MODE==2)?14'd1:14'd0);
  wire[31:0] word={2'(s),16'b0,rt};
  ot_qwen_tp8_vrow_stack_static #(.STACK(s),.RETURN_LATENCY(RL)) dut(
   .clk(clk),.rst_n(rst_n),.start(start),.context_len(context_len),.epoch(epoch),
   .req_valid(req[s]),.req_ready(!(MODE==3&&cyc==200)),.req_t(qt[s]),.req_slot(qs[s]),.req_epoch(qe[s]),
   .rsp_valid(valid_p[s][D]),.rsp_slot(slot_p[s][D]),.rsp_t(rt),.rsp_epoch(ep_p[s][D]),
   .rsp_vrow({32{word}}),.rsp_exp(64'h3f803f803f803f80),.out_valid(ov[s]),.out_ready(!(MODE==4&&cyc==200)),
   .out_vrow(data[s]),.out_exp(expdata[s]),.out_t(ot[s]),.out_epoch(oe[s]),.out_first(first[s]),.out_last(last[s]),
   .done(done[s]),.fault(fault[s]));
 end
 always @(posedge clk)begin
  for(integer s=0;s<4;s++)begin
   if(!rst_n||start)valid_p[s]<=0;
   else begin
    valid_p[s]<={valid_p[s][RL-1:0],req[s]};tag_p[s][0]<=qt[s];slot_p[s][0]<=qs[s];ep_p[s][0]<=qe[s];
    for(integer d=1;d<=RL;d++)begin tag_p[s][d]<=tag_p[s][d-1];slot_p[s][d]<=slot_p[s][d-1];ep_p[s][d]<=ep_p[s][d-1];end
   end
  end
 end
 initial begin
  contexts[0]=1;contexts[1]=127;contexts[2]=128;contexts[3]=129;contexts[4]=255;contexts[5]=256;contexts[6]=257;
  contexts[7]=300;contexts[8]=511;contexts[9]=512;contexts[10]=513;contexts[11]=8191;contexts[12]=8192;
  for(case_no=0;case_no<(MODE==0?13:1);case_no++)begin
   context_len=(MODE==0)?14'(contexts[case_no]):14'd8192;epoch=16'(17+case_no);
   rst_n=0;start=0;cyc=0;done_seen=0;
   for(n=0;n<4;n++)begin requested[n]=0;returned[n]=0;last_req[n]=-1;end
   for(n=0;n<8192;n++)seen[n]=0;
   repeat(3)@(negedge clk);rst_n=1;start=1;
   @(negedge clk);start=0;
   for(cyc=0;cyc<2400;cyc++)begin
    for(n=0;n<4;n++)begin
     if(req[n])begin
      if(qt[n]!==14'(n*128+(requested[n]/128)*512+requested[n]%128)||qs[n]!==3'(requested[n]%8)||qe[n]!==epoch)
       $fatal(1,"request identity stack%0d ordinal%0d t%0d",n,requested[n],qt[n]);
      if(requested[n]&&cyc!=last_req[n]+1)$fatal(1,"runtime stall stack%0d",n);
      last_req[n]=cyc;requested[n]++;
     end
     if(ov[n])begin
      if(ot[n]>=context_len||seen[ot[n]]||((ot[n]>>7)&3)!=n||oe[n]!==epoch||first[n]!=(ot[n]<256)||last[n]!=(ot[n]+256>=context_len))
       $fatal(1,"return identity stack%0d t%0d",n,ot[n]);
      if(data[n]!=={32{{2'(n),16'b0,ot[n]}}}||expdata[n]!==64'h3f803f803f803f80)$fatal(1,"return payload");
      seen[ot[n]]=1;returned[n]++;
     end
    end
    if(|fault)begin
     if(MODE!=0)begin $display("EXPECTED_MUTANT_FAULT mode%0d cycle%0d",MODE,cyc);$fatal(1,"mutant rejected");end
     $fatal(1,"unexpected four issuer fault cycle%0d mask%h",cyc,fault);
    end
    done_seen=done_seen|done;
    @(negedge clk);
   end
   if(MODE!=0)$fatal(1,"MUTANT_ESCAPED");
   for(n=0;n<4;n++)begin
    j=0;for(i=n*128;i<context_len;i+=512)j+=((context_len-i)<128)?context_len-i:128;
    if(requested[n]!=j||returned[n]!=j||!done_seen[n])$fatal(1,"stack coverage %0d req%0d returned%0d expected%0d done%b",n,requested[n],returned[n],j,done_seen[n]);
   end
   for(n=0;n<context_len;n++)if(!seen[n])$fatal(1,"missing canonical row %0d",n);
   $display("PASS four static V issuers context%0d exactrows%0d full4stackcoverage",context_len,context_len);
  end
  $display("PASS FOUR_ISSUER_FULL8192_AND_PARTIAL");$finish;
 end
endmodule
