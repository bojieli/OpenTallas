`timescale 1ps/1ps
module tb_sh_host_fifo #(parameter integer W=514,AW=4,PHASE=0);
 reg wc=0,rc=0,rst_n=0,stop=0;
 always #416 wc=~wc;
 initial begin #(PHASE); forever #416 rc=~rc; end
 integer wn=0,rn=0,wcyc=0,rcyc=0,errors=0,reads=0,burst=0,maxburst=0;
 wire full,empty,ovf;wire[AW:0]freed,count;
 wire wr=rst_n&&!stop&&!full&&(wcyc%512<400);
 wire rd=rst_n&&(stop||(rcyc%512>=32&&rcyc%512<416));
 function automatic [W-1:0] word(input integer seq);
  reg[31:0]x;integer b;begin x=32'hfe12ab34^32'(seq);for(b=0;b<W;b=b+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);word[b]=x[11];end end
 endfunction
 wire[W-1:0] d=word(wn),q;
 ot_dsdv_host_afifo_sram #(.W(W),.AW(AW)) dut(.wclk(wc),.wrst_n(rst_n),.wr(wr),.wdata(d),.wfull(full),.wfreed(freed),.ovf(ovf),
 .rclk(rc),.rrst_n(rst_n),.rd(rd),.rempty(empty),.rdata(q),.rcount(count));
 always @(posedge wc or negedge rst_n)
  if(!rst_n)begin wn<=0;wcyc<=0;end else begin wcyc<=wcyc+1;if(wr)wn<=wn+1;end
 always @(posedge rc or negedge rst_n)
  if(!rst_n)begin rn<=0;rcyc<=0;burst<=0;end else begin
   rcyc<=rcyc+1;
   if(rd&&!empty)begin
    if(q!==word(rn))begin errors=errors+1;if(errors<6)$display("SH_FIFO_MISMATCH read%0d",rn);end
    rn<=rn+1;reads=reads+1;burst=burst+1;if(burst>maxburst)maxburst=burst;
   end else burst=0;
  end
 initial begin
  #(832*12)rst_n=1;
  #(832*2300)rst_n=0;
  #(832*8)rst_n=1;
  #(832*2700)stop=1;
  #(832*64);
  $display("SH_FIFO_RESULT W%0d AW%0d phase%0d reads%0d errors%0d outstanding%0d ovf%0d maxburst%0d",W,AW,PHASE,reads,errors,wn-rn,ovf,maxburst);
  if(errors||wn!=rn||ovf||reads<1000||maxburst<64)$fatal(1,"SH_FIFO_FAIL");
  $display("SH_FIFO_PASS");$finish;
 end
endmodule
