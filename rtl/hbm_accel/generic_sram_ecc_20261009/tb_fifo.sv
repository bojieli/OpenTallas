`timescale 1ns/1ps
module tb_fifo;
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg[544:0] din='0;
 wire ee,re,eov,rov,ce,ue,drop;wire[544:0] ed,rd;wire[8:0] ec,rc;
 ot_hcoll_sfifo #(.W(545),.AW(8),.PAYLOAD_ECC(1)) dut(.clk(clk),.rst_n(rst_n),.push(push),.din(din),.pop(pop),.empty(ee),.dout(ed),.ovf(eov),.count(ec),.ecc_ce(ce),.ecc_ue(ue),.ecc_drop(drop));
 ot_hcoll_sfifo #(.W(545),.AW(8)) refraw(.clk(clk),.rst_n(rst_n),.push(push),.din(din),.pop(pop),.empty(re),.dout(rd),.ovf(rov),.count(rc));
 integer checks=0,ne=0,nr=0,np=0;reg[544:0] sb[0:2047];
 always @(negedge clk)begin #0.001; if(rst_n)begin
  for(integer c=0;c<9;c=c+1)begin
   if(dut.encoded[c*72+:72]!==ot_gpu_w6_secded_pkg::encode64(dut.codec.g_ecc.padded[c*64+:64]))$fatal(1,"canonical encode mismatch");

  end
 end end
 for(genvar c=0;c<9;c=c+1)begin:g_reference
  always @(negedge clk)begin #0.001; if(rst_n && dut.codec.g_ecc.g_c[c].result!==ot_gpu_w6_secded_pkg::decode64(dut.sampled[c*72+:72]))$fatal(1,"canonical decode mismatch"); end
 end
 task flip(input integer b);
 begin case(b/256)
 0:dut.g_bk[0].u_m.g_m[0].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[0].u_sram.arr[0][b%256];
 1:dut.g_bk[0].u_m.g_m[1].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[1].u_sram.arr[0][b%256];
 2:dut.g_bk[0].u_m.g_m[2].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[2].u_sram.arr[0][b%256];
 endcase end endtask
 task trial(input integer a,input integer b);
 integer c,u,seen;
 begin
 @(negedge clk);rst_n=0;push=0;pop=0;repeat(2)@(negedge clk);rst_n=1;push=1;din={17'h175ab,{16{32'h12345678}},16'hffff};
 @(negedge clk);push=0;@(negedge clk);flip(a);if(b>=0)flip(b);c=0;u=0;seen=0;
 repeat(15)begin
 c=c+ce;u=u+ue;
 if(!ee)begin if(b>=0)$fatal(1,"FIFO UE publication"); if(ed!==din)$fatal(1,"FIFO corrupt CE");seen=seen+1;pop=1;end else pop=0;
 @(negedge clk);
 end
 if(b<0 && (c!=1||u||seen!=1))$fatal(1,"FIFO CE counts %0d %0d %0d",c,u,seen);
 if(b>=0 && (u!=1||seen||!ee||dut.ocr!=dut.KC||ec!=0))$fatal(1,"FIFO UE credit/refusal %0d ocr=%0d",u,dut.ocr);
 checks=checks+1;
 end endtask
 initial begin
 repeat(2)@(negedge clk);rst_n=1;
 // Full-rate, bubbles, stalls, both 128-deep macro banks and pointer wrap.  hgi-takeover: the ECC FIFO registers its
 // decode (+1 edge to the head), so the check is transaction-exact (both FIFOs pop the same ordered stream, scoreboard)
 // plus a full-rate burst: after the first word the ECC head never runs dry at one push + one pop a cycle.
 for(integer i=0;i<1500;i=i+1)begin
 @(negedge clk);
 if(eov||rov||ce||ue)$fatal(1,"DS stream fault %0d",i);
 push=(i%7!=0)&&ec<200&&rc<200&&i<1499;pop=(i%5!=0);din={17'(i),{16{32'(i)}},16'(i)};
 if(pop&&!ee)begin if(ed!==sb[ne])$fatal(1,"DS ordered stream mismatch %0d",ne);ne=ne+1;end
 if(pop&&!re)begin if(rd!==sb[nr])$fatal(1,"raw reference mismatch %0d",nr);nr=nr+1;end
 if(push)begin sb[np]=din;np=np+1;end
 end
 push=0;
 repeat(400)begin @(negedge clk);pop=1;
  if(!ee)begin if(ed!==sb[ne])$fatal(1,"DS drain mismatch %0d",ne);ne=ne+1;end
  if(!re)begin if(rd!==sb[nr])$fatal(1,"raw drain mismatch %0d",nr);nr=nr+1;end
 end
 if(ne!=np||nr!=np)$fatal(1,"DS count ne=%0d nr=%0d np=%0d",ne,nr,np);
 begin integer dry,started; dry=0;started=0;
  for(integer i=0;i<600;i=i+1)begin
   @(negedge clk);
   if(!ee)started=started+1; else if(started>0 && i<560)dry=dry+1;
   push=(i<560);pop=1;din={17'(i+7),{16{32'(i)}},16'(i)};
  end
  if(dry!=0)$fatal(1,"ECC FIFO full-rate bubble count %0d",dry);
 end
 push=0;pop=1;repeat(50)@(negedge clk);
 @(negedge clk);push=0;pop=1;repeat(300)@(negedge clk);
 for(integer i=0;i<648;i=i+1)trial(i,-1);
 for(integer c=0;c<9;c=c+1)trial(c*72,c*72+2);
 $display("PAYLOAD_FIFO PASS stream=%0d fullrate=560 faultchecks=%0d",np,checks);$finish;
 end
endmodule
