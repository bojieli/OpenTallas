`timescale 1ps/1fs
module tb_emb_hub_boot_merge;
 parameter integer MODE=0;
 reg ck=0,rst_n=0;always #416.666667 ck=~ck;
 reg su_v=0;reg [511:0] su_d=0;reg [10:0] su_tag=0;wire su_credit;
 reg host_v=0,host_we=1;reg [31:0] host_addr=0;reg [255:0] host_d=0;
 wire host_credit,host_accept,runtime_v,mfault;
 wire mx_v,mx_credit;wire [511:0] mx_d;wire [10:0] mx_tag;
 wire off_v,off_scr,off_hcr,off_haccept,off_runtime,off_fault;wire [511:0] off_d;wire [10:0] off_tag;
 wire [2111:0] lo;reg [2111:0] li=0;
 wire hfault,ar_v,ea_cr,eq_v,ready,efault;wire [5:0] hcause;wire [7:0] ecode;wire [511:0] ar_d,eq_d;
 wire [511:0] actual_mx_d=mx_d ^ ((MODE==1 && mx_v && mx_tag==11'h500) ? 512'b1 : 512'b0);
 ot_qfd_hub_boot_merge #(.ENABLE(1)) merge(.ck(ck),.rst_n(rst_n),.su_v(su_v),.su_d(su_d),.su_tag(su_tag),.su_credit(su_credit),.host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),.host_boot_credit(host_credit),.host_boot_accept(host_accept),.host_runtime_v(runtime_v),.hub_v(mx_v),.hub_d(mx_d),.hub_tag(mx_tag),.hub_credit(mx_credit),.fault(mfault));
 ot_qfd_hub_boot_merge disabled(.ck(ck),.rst_n(rst_n),.su_v(su_v),.su_d(su_d),.su_tag(su_tag),.su_credit(off_scr),.host_v(host_v),.host_we(host_we),.host_addr(host_addr),.host_d(host_d),.host_boot_credit(off_hcr),.host_boot_accept(off_haccept),.host_runtime_v(off_runtime),.hub_v(off_v),.hub_d(off_d),.hub_tag(off_tag),.hub_credit(mx_credit),.fault(off_fault));
 ot_qwen_die_hub_emb hub(.ck(ck),.rst_n(rst_n),.fck({4{ck}}),.l_i(li),.l_o(lo),.x3_v(mx_v),.x3_d(actual_mx_d),.x3_tag(mx_tag),.x3_cr(mx_credit),.ar_v(ar_v),.ar_d(ar_d),.ar_cr(1'b0),.fault(hfault),.fault_cause(hcause),.ea_v(1'b0),.ea_kind(1'b0),.ea_addr(24'b0),.ea_cr(ea_cr),.eq_v(eq_v),.eq_d(eq_d),.emb_ready(ready),.emb_fault(efault),.emb_fault_code(ecode));
 import ot_qfd_emb_pkg::*;
 function automatic [255:0] raw_data(input integer index);
  raw_data={8{32'(32'h9e3779b9*index ^ 32'h89abcdef)}};
 endfunction
 reg [522:0] expected[0:3][0:255],queue[0:3][0:127];
 integer ew[0:3],er[0:3],qw[0:3],qr[0:3],count[0:3],rawcount[0:3],gcount[0:3];
 reg [31:0] rawsum[0:3];reg status_v[0:3];reg [63:0] status_meta[0:3];
 reg [511:0] packet;reg [10:0] tag;reg [527:0] word;
 integer owner_expect[0:255],owner_w=0,owner_r=0;reg credit_expected=0,credit_owner=0,accept_expected=0;
 integer source_su_credit=8,source_host_credit=8,sent_su=0,sent_host=0,returned_su=0,returned_host=0;
 integer cyc=0,consume=0,marker_accept_cycle=0,bend_cycle=0,ready_cycle=0,end_consumed=0,max_remote=0,max_owner=0,max_su_q=0,max_host_q=0,max_su_debt=0,max_host_debt=0,hub_stalls=0;
 reg [31:0] expected_sum=0;
 integer k,dst,i,j;
 always @(posedge ck)begin
  cyc=cyc+1;
  if(rst_n)begin
   if({off_v,off_tag,off_d,off_scr}!=={su_v,su_tag,su_d,mx_credit} || off_hcr || off_haccept || off_fault)$fatal(1,"FAIL default-off historicalSU bypass");
   if(mfault||hfault||efault)$fatal(1,"FAIL actualhub/merger faults %b%b%b code=%h",mfault,hfault,efault,ecode);
   if({host_credit,su_credit} !== (credit_expected ? (credit_owner ? 2'b10 : 2'b01) : 2'b00))$fatal(1,"FAIL source credit owner routing");
   if(host_accept!==accept_expected)$fatal(1,"FAIL host acceptance ownership");
   accept_expected<=host_v&&host_we&&host_addr[31];
   if(su_v)begin if(source_su_credit==0)$fatal(1,"FAIL SU used fabricatedcredit");source_su_credit=source_su_credit-1;sent_su=sent_su+1;end
   if(host_v&&host_we&&host_addr[31])begin
    if(source_host_credit==0)$fatal(1,"FAIL host used fabricatedcredit");source_host_credit=source_host_credit-1;sent_host=sent_host+1;
    if(host_addr==32'hffffffff)marker_accept_cycle=cyc;
   end
   if(su_credit)begin source_su_credit=source_su_credit+1;returned_su=returned_su+1;end
   if(host_credit)begin source_host_credit=source_host_credit+1;returned_host=returned_host+1;end
   if(source_su_credit>8||source_host_credit>8)$fatal(1,"FAIL extra sourcecredit");
   if(mx_v)begin
    owner_expect[owner_w]=mx_tag[10];owner_w=owner_w+1;
    if(mx_tag[10] && mx_tag[9:8]==K_BOOT_END)begin
     for(k=0;k<4;k=k+1)begin expected[k][ew[k]]={mx_tag,mx_d};ew[k]=ew[k]+1;end
    end else begin
     dst=mx_tag[10] ? stack_of(mx_d[24:0]) : mx_d[511:510];
     expected[dst][ew[dst]]={mx_tag,mx_tag[10] ? mx_d : {mx_d[509:0],2'b00}};ew[dst]=ew[dst]+1;
    end
   end
   credit_expected<=mx_credit;
   if(mx_credit)begin
    if(owner_r==owner_w)$fatal(1,"FAIL hub returned unownedcredit");
    credit_owner<=owner_expect[owner_r];owner_r=owner_r+1;
   end
   if(hub.bend_v)begin
    if(marker_accept_cycle==0||bend_cycle!=0)$fatal(1,"FAIL premature/duplicateBOOT_END");
    bend_cycle=cyc;
   end
   if(ready)begin
    if(end_consumed!=4||bend_cycle==0)$fatal(1,"FAIL emb_ready beforeactualBOOT_END consumption/status");
    if(ready_cycle==0)ready_cycle=cyc;
   end
   if(merge.enabled.oc>max_owner)max_owner=merge.enabled.oc;
   if(merge.enabled.sc>max_su_q)max_su_q=merge.enabled.sc;
   if(merge.enabled.hc>max_host_q)max_host_q=merge.enabled.hc;
   if(merge.enabled.su_debt>max_su_debt)max_su_debt=merge.enabled.su_debt;
   if(merge.enabled.host_debt>max_host_debt)max_host_debt=merge.enabled.host_debt;
   if(hub.sne && !hub.send)hub_stalls=hub_stalls+1;
   for(k=0;k<4;k=k+1)begin
    status_v[k]<=0;word=lo[k*528+:528];
    if(word[0])begin
     if(er[k]==ew[k]||{word[15:5],word[527:16]}!==expected[k][er[k]])$fatal(1,"FAIL nativehub packet/link order link=%0d ordinal=%0d",k,er[k]);
     er[k]=er[k]+1;
     if(count[k]==128)$fatal(1,"FAIL ignored actualCR128 remotecredits");
     queue[k][qw[k]%128]={word[15:5],word[527:16]};qw[k]=qw[k]+1;count[k]=count[k]+1;
     if(count[k]>max_remote)max_remote=count[k];
    end
    if(consume && count[k]>0)begin
     {tag,packet}=queue[k][qr[k]%128];qr[k]=qr[k]+1;count[k]=count[k]-1;gcount[k]=gcount[k]+1;
     if(tag[10] && tag[9:8]==K_BOOT_WR)begin
      rawcount[k]=rawcount[k]+1;rawsum[k]=rawsum[k]+crc_sector(packet[24:0],packet[280:25]);
     end
     if(tag[10] && tag[9:8]==K_BOOT_END)begin
      end_consumed=end_consumed+1;status_meta[k]<={rawsum[k],32'(rawcount[k])};status_v[k]<=1;
     end
    end
   end
  end
 end
 always @(negedge ck)begin #1;
  for(k=0;k<4;k=k+1)li[k*528+:528]={status_v[k] ? {448'b0,status_meta[k]} : 512'b0,11'h600,4'((gcount[k]%16)^((gcount[k]%16)>>1)),status_v[k]};
 end
 task step;begin @(negedge ck);#2;end endtask
 initial begin
  for(i=0;i<4;i=i+1)begin ew[i]=0;er[i]=0;qw[i]=0;qr[i]=0;count[i]=0;rawcount[i]=0;rawsum[i]=0;gcount[i]=0;status_v[i]=0;status_meta[i]=0;end
  for(i=0;i<160;i=i+1)expected_sum=expected_sum+crc_sector(25'(i*128),raw_data(i));
  repeat(6)step();rst_n=1;repeat(16)step();
  // Native runtimeKV probe is classified but never consumed/credited bybootmerger.
  host_v=1;host_addr=32'h00001234;host_d=raw_data(9);step();
  if(!runtime_v)$fatal(1,"FAIL runtimeKV demux");host_v=0;repeat(3)step();
  if(host_accept||host_credit||merge.enabled.hc!=0)$fatal(1,"FAIL runtimeKV consumed bybootmerger");
  fork
   begin
    for(j=0;j<32;j=j+1)begin
     wait(source_su_credit>0);step();su_v=1;su_tag=11'(j);su_d={2'(j%4),510'(32'h9e3779b9*j+32'hfe125781)};step();su_v=0;
    end
   end
   begin
    for(i=0;i<160;i=i+1)begin
     wait(source_host_credit>0);step();host_v=1;host_we=1;host_addr=32'h80000000+32'(i*128);host_d=raw_data(i);step();host_v=0;
    end
    wait(source_host_credit>0);step();host_v=1;host_addr=32'hffffffff;host_d={192'b0,expected_sum,32'd160};step();host_v=0;
   end
   begin wait(cyc>=300);step();consume=1;end
  join
  wait(ready && returned_su==32 && returned_host==161 && owner_r==owner_w);repeat(6)step();
  if(mfault||hfault||efault||sent_su!=32||sent_host!=161||source_su_credit!=8||source_host_credit!=8||max_remote!=128||max_owner!=8||hub_stalls==0||marker_accept_cycle>=bend_cycle||bend_cycle>=ready_cycle)$fatal(1,"FAIL actualboot/finiteflow totals");
  for(i=0;i<4;i=i+1)if(count[i]!=0||er[i]!=ew[i])$fatal(1,"FAIL finalremote occupancy/order");
  if(rawcount[0]!=160||rawsum[0]!=expected_sum)$fatal(1,"FAIL RAW byte/checksum visibility");
  $display("PASS hub_boot_merge nativehub RAW160 SU32 END1 sourcecredits161/32 actualCR128 XS8 owner8 maxremote%0d owner%0d source_debt%0d/%0d inputFIFO%0d/%0d stalls%0d marker_accept%0d actualbend%0d ready%0d checksum%h runtimeunconsumed defaultbypass core833.333334ps",max_remote,max_owner,max_su_debt,max_host_debt,max_su_q,max_host_q,hub_stalls,marker_accept_cycle,bend_cycle,ready_cycle,expected_sum);$finish;
 end
 initial begin repeat(4096)@(posedge ck);$fatal(1,"FAIL bounded193packet gate completion");end
endmodule
