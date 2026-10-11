`timescale 1ps/1ps
module tb;
 reg ck=0; always #5 ck=~ck;
 reg rn=0,iv=0,ready=0,dv=0;
 wire kv;wire[29:0] addr;wire[3:0]len;wire[16:0]tag;
 ot_svs_pcs #(.PCID(0),.END(1)) dut(.ck(ck),.rn(rn),.rdy_q2(1'b1),.iss_v(iv),
 .iss_d({17'd7,4'd5,30'd1234}),.k_v(kv),.k_rdy(ready),.k_addr(addr),.k_len(len),.k_tag(tag),
 .kr_v(1'b0),.kr_tag(17'd0),.kr_beat(4'd0),.kr_data(256'd0),
 .di_v(dv),.di_d({1'b1,1'b0,1'b1,15'd9,12'd4,32'd1}),.dni_ok(1'b0),.dni_ph(1'b0),.cr_v(1'b0));
 integer pattern,arrival,c,nsm,nps,ncase=0;
 always @(posedge ck) if(rn && kv && ready) begin
  if (^tag===1'bx || ^addr===1'bx || ^len===1'bx) $fatal(1,"X request");
  if(tag[16:15]==0) begin
   if(tag!==17'd7 ||len!==4'd5||addr!==30'd1234) $fatal(1,"Malformed SM request");
   nsm=nsm+1;
  end else if(tag[16:15]==3)begin
   if(len!==4'd4) $fatal(1,"Malformed stream request");
   nps=nps+1;
  end else $fatal(1,"Unexpected request kind");
 end
 initial begin
  for(pattern=0;pattern<4096;pattern=pattern+1)for(arrival=0;arrival<14;arrival=arrival+1)begin
   @(negedge ck);rn=0;iv=0;ready=0;dv=0;nsm=0;nps=0;
   @(negedge ck);rn=1;dv=1;
   @(negedge ck);dv=0;
   for(c=0;c<36;c=c+1)begin
    iv=(c==arrival);ready=c<12?((pattern>>c)&1):1;
    @(negedge ck);
   end
   iv=0;
   if(nsm!=1||nps!=1)$fatal(1,"COUNT pattern=%d arrival=%d SM=%d PS=%d",pattern,arrival,nsm,nps);
   ncase=ncase+1;
  end
  $display("PASS PCS_CONTROL %0d cases exact SM/PS length/tag/address no duplicates or drops",ncase);$finish;
 end
endmodule
