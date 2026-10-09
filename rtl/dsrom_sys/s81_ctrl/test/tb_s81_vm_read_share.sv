`timescale 1ns/1ps
// Native NP8 fixture: only documented write0/read1 used; slots2..7 explicitly
// idle in this component, not a claim about production scheduler ownership.
module tb_s81_vm_read_share;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg hop_re=0,hc_req_valid=0;reg[13:0] hop_row=0,hc_req_row=0;
 wire hv,cv,hr,vr;wire[13:0] va;wire[511:0] hd,cd;wire fault;
 reg we=0;reg[13:0] wa=0;wire[7:0] ov;wire[4095:0] od;wire vf;
 integer bad=0,cycles=0,hn=0,cn=0,hs=0,cs=0,pending=0;
 reg extra_rsp=0,block_rsp=0;reg[13:0] hexp[0:639],cexp[0:1279];
 function automatic[511:0] data(input[13:0] row);
  integer k;begin for(k=0;k<16;k=k+1)data[32*k+:32]={2'd0,row,16'(k)};end
 endfunction
 wire[1:0] iv,iw;wire[27:0] ir;wire[31:0] im;wire[1023:0] id;
 ot_s81_vm_shared_adapter #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),
  .we(we),.wa(wa),.wd(data(wa)),.re(hop_re),.ra(hop_row),.rq_v(hv),.rq(hd),
  .hc_req_valid(hc_req_valid),.hc_req_ready(hr),.hc_req_row(hc_req_row),
  .hc_rsp_valid(cv),.hc_rsp_data(cd),.i_v(iv),.i_we(iw),.i_row(ir),.i_mask(im),.i_d(id),
  .o_v({extra_rsp||(ov[1]&&!block_rsp),ov[0]}),.o_d(od[1023:0]),.vm_fault(vf),.fault(fault));
 ot_s81ph_vm_mem #(.NP(8),.NB(32),.QD(4),.RQ(8),.MACRO(1)) vm(
  .clk(clk),.rst_n(rst_n),.grp(1'b0),.i_v({6'd0,iv}),.i_we({6'd0,iw}),
  .i_row({84'd0,ir}),.i_mask({96'd0,im}),.i_d({3072'd0,id}),
  .o_v(ov),.o_d(od),.fault(vf),.fault_code(),.max_occ());
 integer hc_start=0,hc_finish=0,hop_start=0,hop_finish=0;
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;
  if(hv)begin
   if(hn>=hs||hd!==data(hexp[hn]))$fatal(1,"hop response owner/data hn%0d",hn);
   hn=hn+1;pending=pending-1;if(hn==640)hop_finish=cycles;
  end
  if(cv)begin
   if(cn>=cs||cd!==data(cexp[cn]))$fatal(1,"HC response owner/data cn%0d",cn);
   cn=cn+1;if(cn==1280)hc_finish=cycles;
  end
  if(hop_re)begin if(hs==0)hop_start=cycles;hexp[hs]=hop_row;hs=hs+1;pending=pending+1;end
  if(hc_req_valid&&hr)begin if(cs==0)hc_start=cycles;cexp[cs]=hc_req_row;cs=cs+1;end
  if(vf)$fatal(1,"real native VM bank schedule fault");
 end
 integer i,c,r,lr,idx;
 initial begin
  if($value$plusargs("bad=%d",bad))begin end
  repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);
  if(bad==1)begin extra_rsp=1;@(negedge clk);extra_rsp=0;end
  else begin
   for(i=0;i<1280;i=i+1)begin we=1;wa=i;@(negedge clk);end
   we=0;repeat(20)@(negedge clk);
   if(bad==2)begin
    block_rsp=1;
    for(i=0;i<33;i=i+1)begin hop_re=1;hop_row=i;@(negedge clk);end
    hop_re=0;
   end else if(bad==3||bad==4)begin
    hop_re=1;hop_row=0;@(negedge clk);hop_re=0;
    if(bad==3)dut.g_share.share.hop_rows[dut.g_share.share.hp][27]=!dut.g_share.share.hop_rows[dut.g_share.share.hp][27];
    else begin repeat(2)@(negedge clk);dut.g_share.share.owners[dut.g_share.share.op][1]=dut.g_share.share.owners[dut.g_share.share.op][0];end
   end else begin
    // Every physical rank's320actual Hrows; full1280rows overall. Hop640rows
    // overlap, with real OUT_DEPTH32 ownership and sporadic offer bubbles.
    idx=0;
    while(cn<1280||hn<640)begin
     hop_re=hs<640&&pending<32&&cycles%5!=0;hop_row=hs;
     hc_req_valid=cs<1280&&cycles%7!=0;
     r=cs/320;c=(cs%320)/80;lr=cs%80;
     hc_req_row=c*320+r*80+lr;
     @(negedge clk);
     if(fault)$fatal(1,"arbiter positive fault");
    end
    hop_re=0;hc_req_valid=0;
    repeat(16)@(negedge clk);
    if(fault||hn!=640||cn!=1280)$fatal(1,"final response debt");
    // Common reset flush; no stale responses may be treated as owned.
    rst_n=0;repeat(5)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
    if(fault||hv||cv)$fatal(1,"partial reset debt");
    $display("VM_READ_SHARE nativeNP8 PASS hop640 HC1280 exactrows realrvalid cycles%0d hc_read_cycles%0d hop_read_cycles%0d",cycles,hc_finish-hc_start+1,hop_finish-hop_start+1);$finish;
   end
  end
  repeat(15)@(negedge clk);
  if(!fault)$fatal(1,"negative%0d not rejected",bad);
  $display("VM_READ_SHARE negative%0d rejected PASS",bad);$finish;
 end
 initial begin #1000000;$fatal(1,"component fixture deadlock");end
endmodule
