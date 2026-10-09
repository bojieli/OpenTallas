`timescale 1ps/1fs
// H1 local TX only. Endpoint owner flags are bench bookkeeping, not wire fields.
module tb_emb_hub_integrated_H1;
 parameter integer MODE=0;
 reg ck=0,rst_n=0; always #416.666667 ck=~ck;
 reg su_v=0;reg [511:0] su_d=0;reg [10:0] su_tag=0;
 reg host_v=0,host_we=1;reg [31:0] host_addr=0;reg [255:0] host_d=0;
 wire su_credit,host_credit,host_accept,runtime_v,mfault;
 wire [2111:0] lo;reg [2111:0] li=0;
 wire hfault,ar_v,ea_cr,eq_v,ready,efault;wire [5:0] hcause;wire [7:0] ecode;wire [511:0] ar_d,eq_d;
 ot_qwen_die_hub_emb_integrated_top #(.BOOT_MERGE(1)) dut(.ck(ck),.rst_n(rst_n),.fck0(ck),.fck1(ck),.fck2(ck),.fck3(ck),
 .l0_i(li[0+:528]),.l1_i(li[528+:528]),.l2_i(li[1056+:528]),.l3_i(li[1584+:528]),.l0_o(lo[0+:528]),.l1_o(lo[528+:528]),.l2_o(lo[1056+:528]),.l3_o(lo[1584+:528]),
 .x3_v(su_v),.x3_d(su_d),.x3_tag(su_tag),.x3_cr(su_credit),.ar_v(ar_v),.ar_d(ar_d),.ar_cr(1'b0),.fault(hfault),.fault_cause(hcause),
 .ea_v(1'b0),.ea_kind(1'b0),.ea_addr(24'b0),.ea_cr(ea_cr),.eq_v(eq_v),.eq_d(eq_d),.host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),
 .host_boot_credit(host_credit),.host_boot_accept(host_accept),.host_runtime_v(runtime_v),.merge_fault(mfault),.emb_ready(ready),.emb_fault(efault),.emb_fault_code(ecode));
 wire [2111:0] off_lo,ref_lo;wire off_credit,ref_credit,off_hcr,off_haccept,off_fault,ref_fault,off_mfault,off_ready,ref_ready,off_efault,ref_efault;
 wire [5:0] off_cause,ref_cause;wire [7:0] off_ecode,ref_ecode;
 ot_qwen_die_hub_emb_integrated_top off(.ck(ck),.rst_n(rst_n),.fck0(ck),.fck1(ck),.fck2(ck),.fck3(ck),
 .l0_i(li[0+:528]),.l1_i(li[528+:528]),.l2_i(li[1056+:528]),.l3_i(li[1584+:528]),.l0_o(off_lo[0+:528]),.l1_o(off_lo[528+:528]),.l2_o(off_lo[1056+:528]),.l3_o(off_lo[1584+:528]),
 .x3_v(su_v),.x3_d(su_d),.x3_tag(su_tag),.x3_cr(off_credit),.ar_cr(1'b0),.fault(off_fault),.fault_cause(off_cause),
 .ea_v(1'b0),.ea_kind(1'b0),.ea_addr(24'b0),.host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),
 .host_boot_credit(off_hcr),.host_boot_accept(off_haccept),.merge_fault(off_mfault),.emb_ready(off_ready),.emb_fault(off_efault),.emb_fault_code(off_ecode));
 ot_qwen_die_hub_emb refhub(.ck(ck),.rst_n(rst_n),.fck({4{ck}}),.l_i(li),.l_o(ref_lo),.x3_v(su_v),.x3_d(su_d),.x3_tag(su_tag),.x3_cr(ref_credit),
 .ar_cr(1'b0),.fault(ref_fault),.fault_cause(ref_cause),.ea_v(1'b0),.ea_kind(1'b0),.ea_addr(24'b0),.emb_ready(ref_ready),.emb_fault(ref_efault),.emb_fault_code(ref_ecode));
 reg enc_iv=0;reg [15:0] enc_seq=0;wire enc_v,enc_bad;wire [509:0] enc_packet;
 function automatic [255:0] data_word(input integer index);
  integer x;begin for(x=0;x<8;x=x+1)data_word[x*32+:32]=32'h19e369ab^(index*103)^x;end
 endfunction
 ot_qwen_kvc_packet_encode_parallel #(.ENABLE(1)) enc(.clk(ck),.rst_n(rst_n),.i_v(enc_iv),.i_op(4'd1),.i_epoch(8'd0),.i_pc(7'd3),.i_seq(enc_seq),.i_tag(enc_seq[8:0]),.i_sec(24'h120000+enc_seq),.i_data(data_word(enc_seq)),.o_v(enc_v),.o_bad(enc_bad),.o_packet(enc_packet));
 reg dec_iv=0;reg [509:0] dec_packet=0;wire dec_v,dec_bad;wire [15:0] dec_seq;wire [255:0] dec_data;wire [509:0] decoded_packet;
 ot_qwen_kvc_packet_decode_parallel #(.ENABLE(1)) dec(.clk(ck),.rst_n(rst_n),.i_v(dec_iv),.i_packet(dec_packet),.o_v(dec_v),.o_bad(dec_bad),.o_packet(decoded_packet),.o_op(),.o_epoch(),.o_pc(),.o_seq(dec_seq),.o_tag(),.o_sec(),.o_data(dec_data));
 import ot_qfd_emb_pkg::*;
 reg [522:0] se[0:2047],he[0:160],rq[0:3][0:127];reg rq_host[0:3][0:127];
 integer scycle[0:2047],hcycle[0:160],sw=0,sr=0,hw=0,hr=0;
 integer qw[0:3],qr[0:3],count[0:3],gcount[0:3],rawcount[0:3];reg [31:0] rawsum[0:3];
 reg status_v[0:3];reg [63:0] status_meta[0:3];
 integer sc=8,hc=8,returned_su=0,returned_host=0,cyc=0,consume=0,ends=0,marker_cycle=0,bend_cycle=0,ready_cycle=0,high_tags=0;
 integer max_remote=0,max_su=0,max_host=0,max_sq=0,max_hq=0,min_su_delay=999999,min_host_delay=999999,decoded=0,stalls=0;
 integer i,j,k,sout,hout;reg [527:0] word;reg [522:0] packet;reg owner;reg [31:0] checksum=0;
 wire observed_scredit=MODE==2?host_credit:su_credit;
 wire observed_hcredit=MODE==2?su_credit:host_credit;
 task step;begin @(negedge ck);#2;end endtask
 always @(posedge ck)begin
  cyc=cyc+1;
  if(rst_n)begin
   if(su_v)begin
    if(sc==0)$fatal(1,"FABRICATED_SU_CREDIT");sc=sc-1;
    se[sw]={su_tag,su_d[509:0],2'b0};scycle[sw]=cyc;sw=sw+1;
   end
   if(host_v&&host_we&&host_addr[31])begin
    if(hc==0)$fatal(1,"FABRICATED_HOST_CREDIT");hc=hc-1;
    he[hw]=host_addr==32'hffffffff ? {11'h600,448'b0,host_d[63:0]}:{11'h500,231'b0,host_d,host_addr[24:0]};hcycle[hw]=cyc;hw=hw+1;
    if(host_addr==32'hffffffff)marker_cycle=cyc;
   end
   if(8-sc>max_su)max_su=8-sc;if(8-hc>max_host)max_host=8-hc;
   if(dut.enabled.u.bend_v)bend_cycle=cyc;
   if((dut.enabled.u.sne||dut.enabled.u.hne)&&!dut.enabled.u.send)stalls=stalls+1;
  end
  #1;
  if(rst_n)begin
   if({off_lo,off_credit,off_fault,off_cause,off_ready,off_efault,off_ecode}!=={ref_lo,ref_credit,ref_fault,ref_cause,ref_ready,ref_efault,ref_ecode}||off_hcr||off_haccept||off_mfault)$fatal(1,"DEFAULT_OFF_NATIVE_EQUIVALENCE");
   if(mfault||hfault||efault||enc_bad||dec_bad)$fatal(1,"NATIVE_FAULTS merge=%b hub=%b emb=%b code=%h",mfault,hfault,efault,ecode);
   if(host_accept!==(host_v&&host_we&&host_addr[31]))$fatal(1,"HOST_CAPTURE_ACCEPT");
   dec_iv=0;sout=0;hout=0;
   for(k=0;k<4;k=k+1)begin
    status_v[k]=0;word=lo[k*528+:528];
    if(word[0])begin
     packet={word[15:5],word[527:16]};
     if(k==0&&sr<sw&&packet===se[sr])begin
      owner=0;sout=sout+1;dec_iv=1;dec_packet=word[527:18];
      if(cyc-scycle[sr]<min_su_delay)min_su_delay=cyc-scycle[sr];
      if(word[15])high_tags=high_tags+1;sr=sr+1;
     end else if(hr<hw&&packet===he[hr]&&(k==0||he[hr][522:512]==11'h600))begin
      owner=1;hout=hout+1;
      if(cyc-hcycle[hr]<min_host_delay)min_host_delay=cyc-hcycle[hr];
     end else $fatal(1,"FULL_PACKET_CLASS_TAG_ORDER link=%0d SUordinal=%0d HOSTordinal=%0d outertag=%h",k,sr,hr,word[15:5]);
     if(count[k]==128)$fatal(1,"REMOTE_CR128_OVERFLOW");
     rq[k][qw[k]%128]=packet;rq_host[k][qw[k]%128]=owner;qw[k]=qw[k]+1;count[k]=count[k]+1;
     if(count[k]>max_remote)max_remote=count[k];
    end
    if(consume&&count[k]>0)begin
     packet=rq[k][qr[k]%128];owner=rq_host[k][qr[k]%128];qr[k]=qr[k]+1;count[k]=count[k]-1;gcount[k]=gcount[k]+1;
     if(owner&&packet[521:520]==K_BOOT_WR)begin rawcount[k]=rawcount[k]+1;rawsum[k]=rawsum[k]+crc_sector(packet[24:0],packet[280:25]);end
     if(owner&&packet[521:520]==K_BOOT_END)begin ends=ends+1;status_meta[k]={rawsum[k],32'(rawcount[k])};status_v[k]=1;end
    end
   end
   if(sout>1||!(hout==0||hout==1||hout==4)||sout&&hout)$fatal(1,"NATIVE_SEND_ONE_EVENT");
   if({observed_hcredit,observed_scredit}!=={hout!=0,sout!=0})$fatal(1,"SOURCE_CREDIT_TRUE_SEND_OWNER");
   if(sout)begin sc=sc+1;returned_su=returned_su+1;end
   if(hout)begin hc=hc+1;returned_host=returned_host+1;hr=hr+1;end
   if(sc>8||hc>8)$fatal(1,"EXTRA_CREDIT");
   if(dut.enabled.u.soccupancy>max_sq)max_sq=dut.enabled.u.soccupancy;
   if(dut.enabled.u.hoccupancy>max_hq)max_hq=dut.enabled.u.hoccupancy;
   if(dut.enabled.u.soccupancy>8||dut.enabled.u.hoccupancy>8)$fatal(1,"NINTH_PENDING_RESERVATION");
   if(ready)begin if(ends!=4||bend_cycle==0)$fatal(1,"READY_BEFORE_FOUR_STATUS");if(ready_cycle==0)ready_cycle=cyc;end
   if(dec_v)begin
    if(dec_seq!==decoded[15:0]||dec_data!==data_word(decoded)||decoded_packet!==se[decoded][511:2])$fatal(1,"NATIVE_CODEC_FULL_SEQUENCE_EXACT expected=%0d got=%0d data=%h",decoded,dec_seq,dec_data);
    decoded=decoded+1;
   end
  end
 end
 always @(negedge ck)begin #1;
  for(k=0;k<4;k=k+1)li[k*528+:528]={status_v[k]?{448'b0,status_meta[k]}:512'b0,11'h600,4'((gcount[k]%16)^((gcount[k]%16)>>1)),status_v[k]};
 end
 initial begin
  for(i=0;i<4;i=i+1)begin qw[i]=0;qr[i]=0;count[i]=0;gcount[i]=0;rawcount[i]=0;rawsum[i]=0;status_v[i]=0;status_meta[i]=0;end
  for(i=0;i<160;i=i+1)checksum=checksum+crc_sector(25'(i*128),data_word(i));
  repeat(6)step();rst_n=1;repeat(16)step();
  host_v=1;host_addr=32'h1234;step();if(!runtime_v||host_accept||host_credit)$fatal(1,"RUNTIME_HOST_UNCONSUMED");host_v=0;repeat(3)step();
  fork
   begin
    for(j=0;j<2048;j=j+1)begin
     step();enc_iv=1;enc_seq=j;step();enc_iv=0;
     wait(sc>0);step();su_v=1;su_tag=j;su_d={2'b0,enc_packet};step();su_v=0;
    end
   end
   begin
    for(i=0;i<160;i=i+1)begin
     wait(hc>0);step();host_v=1;host_addr=32'h80000000+i*128;host_d=data_word(i);step();host_v=0;
    end
    wait(hc>0);step();host_v=1;host_addr=32'hffffffff;host_d={192'b0,checksum,32'd160};step();host_v=0;
   end
   begin wait(cyc>=600);step();consume=1;end
  join
  wait(ready&&returned_su==2048&&returned_host==161&&decoded==2048);repeat(8)step();
  if(sc!=8||hc!=8||max_su!=8||max_host!=8||max_sq!=8||max_hq!=8||max_remote!=128||high_tags!=1024||min_su_delay!=2||min_host_delay!=2||marker_cycle>=bend_cycle||bend_cycle>=ready_cycle||rawcount[0]!=160||rawsum[0]!=checksum)$fatal(1,"TOTALS_BOUND_LATENCY SU=%0d HOST=%0d SQ=%0d HQ=%0d remote=%0d high=%0d delay=%0d/%0d marker=%0d/%0d/%0d",max_su,max_host,max_sq,max_hq,max_remote,high_tags,min_su_delay,min_host_delay,marker_cycle,bend_cycle,ready_cycle);
  for(i=0;i<4;i=i+1)if(count[i]!=0)$fatal(1,"FINAL_REMOTE_DRAIN");
  $display("PASS H1 localTX SU2048 allseq11/full510/nativecodec exact highseq1024 HOST_RAW160 END1 credit2048/161 bound8/8 pending8/8 CR128 stalls%0d minforward%0d/%0d directcredit_same_send_edge marker%0d bend%0d ready%0d fourSTATUS defaultoff_native_exact checksum%h core833.333334ps RX_PACKAGE_OPEN",stalls,min_su_delay,min_host_delay,marker_cycle,bend_cycle,ready_cycle,checksum);$finish;
 end
 // Constant force only after a real high-seq SU head exists. Icarus does
 // not continuously reevaluate procedural force expressions.
 always @(negedge ck) begin #3;
  if(MODE==1 && rst_n && dut.enabled.u.sne && !dut.enabled.u.choose_host && dut.enabled.u.sht[10])
   force dut.enabled.u.semb=1'b1;
 end
 initial begin repeat(20000)@(posedge ck);$fatal(1,"FINITE_TRANSPORT_NO_COMPLETION SU=%0d/%0d HOST=%0d/%0d decoded=%0d",sr,sw,hr,hw,decoded);end
endmodule
