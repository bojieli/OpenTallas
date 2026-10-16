`timescale 1ns/1ps
// Fixed external host slots, real native ingest arithmetic/FIFOs and real
// decoder leaves. Only off-chip HBM storage/ACKs and expected data are modeled.
module tb_host_c_sliced_native;
 parameter integer MUT=0;
 reg ck=0,cv=0,rst=0;always #3 ck=~ck;always #4 cv=~cv;
 reg[1:0]div=1;always @(posedge ck)div<=div+1'b1;wire cb=div[1];
 reg[514:0]packets[0:4095];reg[255:0]mem[0:65535],expected_mem[0:65535];
 integer np=0,cyc=0,sent=0,emits=0,dones=0,compared=0,emit_fd,stage_seen=0,pq_seen=0;
 reg[514:0]f=0;reg[8:0]hc=0;
 wire[291:0]hw,refhw;wire[76:0]t,reft;wire[35:0]sp,pq,rsp,rpq;wire[7:0]plen,rplen;
 dsfd_host_c_sliced #(.MUT(MUT))dut(.ck(ck),.ckv(cv),.ck_boot(cb),.ck_return(ck),.ck_launch(ck),.ck_native(ck),.ck_data({4{ck}}),.ck_ingest({ck,ck}),.rst(rst),.rsv(rst),.f_collective(f),.f_lf(4'b0101),.t_collective(t),.t_sseq_pw(sp),.t_pq_pw(pq),.t_sseq_plen(plen),.f_sseq_st(6'd0),.f_wfc_ft(4'd0),.hw(hw),.hc(hc));
 dsfd_host_c ref_dut(.ck(ck),.ckv(cv),.ck_boot(cb),.ck_ingest({ck,ck}),.rst(rst),.rsv(rst),.f_collective(f),.f_lf(4'b0101),.t_collective(reft),.t_sseq_pw(rsp),.t_pq_pw(rpq),.t_sseq_plen(rplen),.f_sseq_st(6'd0),.f_wfc_ft(4'd0),.hw(refhw),.hc(hc));
 initial begin
  emit_fd=$fopen($sformatf("emit_calendar_m%0d.tsv",MUT),"w");
  $fdisplay(emit_fd,"edge\tsector_addr\thw292");
  if(!$value$plusargs("NP=%d",np))$fatal(1,"HOST_SLICED_NATIVE missing NP");
  $readmemh("packets.mem",packets,0,np-1);$readmemh("init.mem",mem);$readmemh("exp.mem",expected_mem);
  #29 rst=1;
 end
 always @(negedge ck)if(rst)begin
  cyc=cyc+1;f=0;hc={7'd0,hw[0],hw[0]};
  // Immutable compiler boundary schedule: no observed ready/credit/status
  // chooses an input slot or moves the declared final verification edge.
  if(cyc>100&&cyc%32==0&&sent<np)begin f=packets[sent];sent=sent+1;end
  if(cyc==60000)begin
   if(sent!=np||emits==0||dones==0||stage_seen!=1||pq_seen!=1||plen!=4||t[75]||reft[75])$fatal(1,"HOST_SLICED_NATIVE FAIL counts/fault sent=%0d/%0d emits=%0d dones=%0d fault=%b/%b",sent,np,emits,dones,t[75],reft[75]);
   for(integer i=0;i<65536;i=i+1)if(mem[i]!==expected_mem[i])$fatal(1,"HOST_SLICED_NATIVE FAIL external memory sector=%0d",i);
   $display("HOST_SLICED_NATIVE PASS exact_calendar=%0d real_packets=%0d sectors=%0d completions=%0d",compared,sent,emits,dones);$finish;
  end
 end
 always @(posedge ck)if(rst)begin
  #0.01;
  if(cyc>10)begin
   compared=compared+1;
   if(hw[0]!==refhw[0] || (hw[0]&&hw!==refhw) || t[64]!==reft[64] || (t[64]&&t[63:0]!==reft[63:0]))
    $fatal(1,"HOST_SLICED_NATIVE FAIL exact producer/calendar edge=%0d",cyc);
   if(hw[0])begin
    if(!hw[289]||hw[291:290]!=0||hw[288:257]>=65536)$fatal(1,"HOST_SLICED_NATIVE FAIL unsupported external write");
    mem[hw[288:257]]=hw[256:1];emits=emits+1;
    $fdisplay(emit_fd,"%0d\t%0d\t%h",cyc,hw[288:257],hw);
   end
   if(dut.ingest.native_ingest.host.h_v && dut.ingest.native_ingest.host.h_cls==0 &&
      (dut.ingest.native_ingest.host.h_d[7:0]==8'h10 || dut.ingest.native_ingest.host.h_d[7:0]==8'h11 || dut.ingest.native_ingest.host.h_d[7:0]==8'h12))
    $fatal(1,"HOST_SLICED_NATIVE FAIL interceptedCSR reached native ingest port");
   if(t[64])begin
    if(t[63:56]!=1)$fatal(1,"HOST_SLICED_NATIVE FAIL non-DONE physical completion");
    dones=dones+1;
   end
  end
 end
 always @(posedge cv)if(rst)begin
  #0.01;
  if(sp!==rsp||pq!==rpq||plen!==rplen)$fatal(1,"HOST_SLICED_NATIVE FAIL exact boot calendar");
  if(sp[35])stage_seen=stage_seen+1;
  if(pq[35])pq_seen=pq_seen+1;
 end
endmodule
