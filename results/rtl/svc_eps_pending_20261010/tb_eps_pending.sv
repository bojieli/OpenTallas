`timescale 1ps/1ps
module tb;
 reg ck=0,fck=0;always #512 ck=~ck;always #416 fck=~fck;
 reg rst=0;reg[127:0]e=0;wire wv,kv,iv,sdv;wire[39:0]od;reg done=0;
 reg bw=0,bk=0,bi=0;
 always @(posedge ck) begin bw<=wv;bk<=kv;bi<=iv;end
 integer nw=0,nk=0,ni=0,ns=0,drops=0;
 ot_svs_eps dut(.ck(ck),.rst(rst),.rn(rst),.e_d(e),.e_fclk(fck),
 .ow_v(wv),.ok_v(kv),.oi_v(iv),.o_d(od),.bw(bw),.bk(bk),.bi(bi),.sd_v(sdv),
 .dw_ok(done),.dw_ph(dut.ph),.de_ok(done),.de_ph(dut.ph));
 always @(posedge ck)if(rst)begin
  if(wv)begin nw=nw+1;$display("W_DISPATCH tag%0d",od[39:30]);end
  if(kv)nk=nk+1;if(iv)ni=ni+1;
  if(sdv)begin
   if (ns==1 && !done) $fatal(1,"STREAM_OVERLAP");
   if(dut.sd_d[58:44]!==15'(ns==0?11:22) || dut.sd_d[43:32]!==12'd4 || dut.sd_d[31:0]!==32'd1)
    $fatal(1,"STREAM_DESCRIPTOR mismatch index%0d",ns);
   if(dut.sg_d!==13'(ns==0?101:102))$fatal(1,"STREAM_TAG mismatch index%0d",ns);
   ns=ns+1;
  end
 end
 always @(negedge fck)if(rst&&dut.e_f[0]&&dut.e_full)begin drops=drops+1;$display("INGRESS_DROP kind%0d tag%0d",dut.e_f[2:1],dut.e_f[48:39]);end
 task send(input bit strm,input[1:0]kind,input[9:0]tag);
 begin
  @(posedge fck);e=0;e[0]=1;e[2:1]=kind;e[48:39]=tag;e[127]=strm;
  if(strm)begin e[84:72]=13'(tag==1?101:102);e[17:3]=15'(tag==1?11:22);e[29:18]=12'd4;e[61:30]=32'd1;end
  @(posedge fck);e=0;
  repeat(4)@(posedge fck);
 end endtask
 initial begin
  repeat(4)@(negedge ck);rst=1;repeat(8)@(negedge ck);
  send(1,1,1);send(1,1,2);send(0,0,516);send(0,1,1);send(0,2,2);send(0,0,524);
  repeat(80)@(negedge ck);done=1;repeat(80)@(negedge ck);
  $display("EPS_RESULT stream=%0d W=%0d KV=%0d IK=%0d drops=%0d",ns,nw,nk,ni,drops);
  if(ns!=2||nw!=2||nk!=1||ni!=1||drops!=0)$fatal(1,"EPS_LOST_COMMAND");$finish;
 end
endmodule
