`timescale 1ps/1fs
module tb_hbm_index_lines_sram #(parameter integer MODE=0);
 reg clk=0,rst_n=0,start=0;always #416 clk=~clk;
 reg[8:0]blocks=342;reg[31:0]v=0;reg[383:0]sj=0;reg[8191:0]sd=0;reg[7:0]credit=0;
 wire[8791:0]lines;wire[63:0]pop,corrected;wire done,fault,retained;
 ot_hbm_index_lines_sram #(.ENABLE(1),.CRED(64),.MUT_DATA(MODE==1),.MUT_CHECK(MODE==2),.MUT_DOUBLE(MODE==3),.MUT_SCOREBOARD(MODE==4))
 dut(.clk(clk),.rst_n(rst_n),.start(start),.blocks(blocks),.sector_v(v),.sector_j(sj),.sector_data(sd),.credit(credit),
 .lines(lines),.pop(pop),.done(done),.fault(fault),.retained(retained),.corrected(corrected));
 integer nextj[0:31],avail[0:31],owed[0:7];integer p,j,b,g,l,got=0,cyc=0,rep_=0,delay_=1,cecount=0,rs=0;
 reg endseen=0;time launch,lastline;integer nsector;
 initial begin
  if($value$plusargs("credit_delay=%d",delay_))begin end
  if($value$plusargs("blocks=%d",rs))blocks=9'(rs);
  nsector=(blocks*544+31)/32;
  for(l=0;l<8;l=l+1)owed[l]=0;
  repeat(3)@(negedge clk);rst_n=1;
  for(rep_=0;rep_<2;rep_=rep_+1)begin
   got=0;cyc=0;endseen=0;
   for(p=0;p<32;p=p+1)begin nextj[p]=0;avail[p]=64;end
   @(negedge clk);start=1;launch=$time;@(negedge clk);start=0;
   while(!endseen)begin
    credit=0;v=0;
    for(l=0;l<8;l=l+1)if(lines[l*1099])begin
     if(lines[l*1099+1+:10]!==10'(got+l))$fatal(1,"tag line%0d",got+l);
     for(b=0;b<136;b=b+1)if(lines[l*1099+11+b*8+:8]!==((got+l<blocks*4)?8'((got+l)*136+b):8'd0))$fatal(1,"byte line=%0d byte=%0d",got+l,b);
     owed[l]=owed[l]+1;
    end
    if(lines[0])begin got=got+8;lastline=$time;end
    if(cyc%delay_==0)for(l=0;l<8;l=l+1)if(owed[l]>0)begin credit[l]=1;owed[l]=owed[l]-1;end
    for(p=0;p<32;p=p+1)begin
     avail[p]=avail[p]+pop[p*2+:2];
     if(avail[p]>64)$fatal(1,"slot conservation PC%0d=%0d",p,avail[p]);
     if(nextj[p]*32+p<nsector&&avail[p]>=(nextj[p]%2==0?2:1)&&((cyc+p)%7!=0))begin
      j=nextj[p]^1;if(j*32+p>=nsector)j=nextj[p];
      v[p]=1;sj[p*12+:12]=j;
      for(b=0;b<32;b=b+1)sd[p*256+b*8+:8]=8'((j*32+p)*32+b);
      nextj[p]=nextj[p]+1;avail[p]=avail[p]-1;
     end
    end
    if(|corrected)cecount=cecount+1;
    if(fault)begin
     if(MODE==3||MODE==4)begin
      if(lines!=0)$fatal(1,"poison escaped");
      $display("PASS_EXPECTED_PROTECTED_FAULT mode=%0d lines=%0d cycles=%0d",MODE,got,cyc);$finish;
     end else $fatal(1,"unexpected fault lines=%0d cycles=%0d",got,cyc);
    end
    endseen=done;cyc=cyc+1;if(cyc>2000000)$fatal(1,"protocol timeout got=%0d",got);
    @(negedge clk);
   end
   v=0;
   if(got!=((blocks*4+7)/8)*8)$fatal(1,"count got=%0d",got);
   for(j=0;j<200;j=j+1)begin
    credit=0;
    for(l=0;l<8;l=l+1)if(owed[l]>0)begin credit[l]=1;owed[l]=owed[l]-1;end
    for(p=0;p<32;p=p+1)begin avail[p]=avail[p]+pop[p*2+:2];if(avail[p]>64)$fatal(1,"final slot conservation");end
    if(fault)$fatal(1,"final credit fault");@(negedge clk);
   end
   credit=0;
   for(l=0;l<8;l=l+1)if(owed[l]!=0)$fatal(1,"final credit debt");
   for(p=0;p<32;p=p+1)if(avail[p]!=64)$fatal(1,"unreturned slot PC%0d=%0d",p,avail[p]);
   $display("SRAM_IKS rep=%0d mode=%0d lines=%0d last_line_ps=%0d cycles=%0d ce_events=%0d",rep_,MODE,got,lastline-launch,cyc,cecount);
  end
  if((MODE==1||MODE==2)&&cecount==0)$fatal(1,"correction mutation ineffective");
  if(MODE==3||MODE==4)$fatal(1,"negative control escaped");
  $display("PASS_HBM_INDEX_LINES_SRAM");$finish;
 end
endmodule
