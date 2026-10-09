`timescale 1ns/1ps
module tb_s81_ingest_afifo;
 parameter MUT=0;
 reg wc=0,rc=0,wn=0,rn=0,wr=0,rd=0;reg[513:0]data=0;
 wire full,empty,ovf;wire[513:0]out;wire[4:0]freed,count;
 always #.5 wc=~wc;always #.416667 rc=~rc;
 ot_s81_ingest_afifo #(.W(514),.AW(4),.READ_INJECT(MUT==2?648'd3:(MUT==1?648'd1:648'd0))) dut(wc,wn,wr,data,full,freed,ovf,rc,rn,rd,empty,out,count);
 integer n=0,i;
 always @(negedge rc)if(rn&&!empty)begin
  if(out!={2'b10,16{32'h12340000+n}})$fatal(1,"payload mismatch %d",n);
  rd=1;n=n+1;
 end else rd=0;
 initial begin
 repeat(4)@(negedge wc);wn=1;rn=1;
 for(i=0;i<32;i=i+1)begin
  @(negedge wc);while(full)@(negedge wc);
  wr=1;data={2'b10,16{32'h12340000+i}};
  @(negedge wc);wr=0;
  if(MUT==2)i=32;
 end
 repeat(20)@(negedge wc);
 if(MUT==2)begin if(!ovf||n!=0)$fatal(1,"double error escaped");$display("PROTECTED_FIFO DOUBLE_DETECTED");end
 else begin if(n!=32||ovf)$fatal(1,"missing payload %d",n);$display("PROTECTED_FIFO PASS514bits32words");end
 $finish;
 end
endmodule
