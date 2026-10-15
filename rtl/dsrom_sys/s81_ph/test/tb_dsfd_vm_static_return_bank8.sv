`timescale 1ns/1ps
module tb_dsfd_vm_static_return_bank8;
 reg ck=0;always #2 ck=~ck;
 reg rn=0;reg [31:0] iv=0;reg [255:0] it=0;reg [4095:0] id=0;
 reg rv=0,pv=0;reg [2:0] rg=0,pg=0;reg [31:0] rm=0,pm=0;
 wire [31:0] oldv,newv;wire [4095:0] oldd,newd;wire [2:0] oldg;wire [11:0] newg;wire oldf;wire [3:0] newf;
 dsfd_vm_static_return #(.NROW(32)) old(.ck(ck),.rst_n(rn),.i_v(iv),.i_tag(it),.i_data(id),
 .release_v(rv),.release_group(rg),.release_mask(rm),.o_v(oldv),.o_data(oldd),.o_group(oldg),.fault(oldf));
`ifdef OT_VM_RETURN_BANK8_PROFILES
 dsfd_vm_static_return32_native_lanes dut(
`else
 dsfd_vm_static_return32_lanes dut(
`endif
.ck({4{ck}}),.rst_n({4{rn}}),.i_v(iv),.i_tag(it),.i_data(id),
 .release_v(rv),.release_group(rg),.release_mask(rm),.prepare_v(pv),.prepare_group(pg),.prepare_mask(pm),
 .o_v(newv),.o_data(newd),.o_group(newg),.fault(newf));
 integer errors=0,checks=0,releases=0,words=0,atomic_missing=0,seed=1,mode=0;
 reg [31:0] issuedmask;integer g,t,s,b,drop;
 function automatic [127:0] value(input integer group_id,input integer slot_id);
  value={32'(group_id),32'(slot_id),32'hfedcba98,32'(group_id*127+slot_id*773)};
 endfunction
 task automatic check;
  begin
   @(posedge ck);#0.1;checks=checks+1;
   if(oldv!==newv || oldf!==( |newf))begin
    $display("MISMATCH mode%0d check%0d ov%h nv%h of%b nf%h",mode,checks,oldv,newv,oldf,newf);errors=errors+1;
   end
   if(rv)begin
    releases=releases+1;
    for(integer l=0;l<4;l=l+1)if(newg[3*l+:3]!==oldg)errors=errors+1;
    for(integer q=0;q<32;q=q+1)if(oldv[q])begin
     words=words+1;if(oldd[128*q+:128]!==newd[128*q+:128])begin
      $display("DATA check%0d slot%0d",checks,q);errors=errors+1;
     end
    end
   end
  end
 endtask
 task automatic reset;
  begin
   @(negedge ck);rn=0;iv=0;rv=0;pv=0;rm=0;pm=0;
   repeat(3)@(negedge ck);rn=1;repeat(5)@(negedge ck);
  end
 endtask
 initial begin
  if($value$plusargs("seed=%d",seed))begin end
  if($value$plusargs("mode=%d",mode))begin end
  t=$urandom(seed);
  reset();
  // 1000 adjacent parity groups, full-shape sustained32 records/cycle.
  // At each edge release the previous group while accepting/preparing the next.
  for(g=0;g<1000;g=g+1)begin
   @(negedge ck);rv=(g!=0);rg=3'(g-1);rm=pm;
   pv=1;pg=3'(g);issuedmask=(mode==1 || g%4==0)?32'hffffffff:$urandom;
   pm=issuedmask;iv=issuedmask;
   for(s=0;s<32;s=s+1)begin
    // Permute8 bank indices within each lane each edge; lane/tag invariant holds.
    b=(s%4)+4*((s/4+g)%8);
    iv[b]=issuedmask[s];it[8*b+:8]={3'(g),5'(s)};id[128*b+:128]=value(g,s);
   end
   check();
   if(g!=0)for(s=0;s<32;s=s+1)if(newv[s] && newd[128*s+:128]!==value(g-1,s))errors=errors+1;
  end
  @(negedge ck);iv=0;pv=0;rv=1;rg=3'(g-1);rm=pm;check();
  // Each missing lane must suppress ALL32slots, even the24present other lanes.
  for(drop=0;drop<4;drop=drop+1)begin
   reset();@(negedge ck);pv=1;pg=3;pm=32'hffffffff;iv=32'hffffffff & ~(32'b1<<drop);
   for(s=0;s<32;s=s+1)begin it[8*s+:8]={3'd3,5'(s)};id[128*s+:128]=value(3,s);end
   check();@(negedge ck);iv=0;pv=0;rv=1;rg=3;rm=32'hffffffff;check();
   if(newv!==0 || !oldf || !(|newf))errors=errors+1;else atomic_missing=atomic_missing+1;
  end
  // Duplicate, occupied overwrite, wrong group, late-at-release and same-parity
  // clear+arrival semantics compared to the actual monolithic old leaf.
  for(t=0;t<5;t=t+1)begin
   reset();@(negedge ck);iv=32'hffffffff;
   for(s=0;s<32;s=s+1)begin it[8*s+:8]={3'd2,5'(s)};id[128*s+:128]=value(2,s);end
   if(t==0)it[8*4+:8]=it[0+:8];
   if(t==2)it[0+:8]={3'd4,5'd0};
   if(t==3)iv[0]=0;
   pv=(t!=1);pg=2;pm=32'hffffffff;check();
   if(t==1)begin
    @(negedge ck);iv=32'hffffffff;pv=1;pg=2;pm=32'hffffffff;check();
   end
   @(negedge ck);rv=1;rg=2;rm=32'hffffffff;pv=1;pg=4;pm=32'hffffffff;iv=32'hffffffff;
   for(s=0;s<32;s=s+1)begin it[8*s+:8]={3'd4,5'(s)};id[128*s+:128]=value(4,s);end
   check();
   @(negedge ck);iv=0;pv=0;rg=4;rm=32'hffffffff;check();
  end
  $display("RETURN_BANK8 groups%0d words%0d checks%0d atomic_missing%0d errors%0d",releases,words,checks,atomic_missing,errors);
  if(errors==0 && releases>=1000 && atomic_missing==4)$display("RETURN_BANK8 PASS");else $display("RETURN_BANK8 FAIL");
  $finish;
 end
endmodule
