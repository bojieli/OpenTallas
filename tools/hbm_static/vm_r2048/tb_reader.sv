`timescale 1ps/1ps
module tb_vm_reader_r2048;
 parameter integer RT=173,WFP32=1,MUT=0;
 localparam DELAY=8+RT-3;
 reg clk=0;always begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,fs=0,ws=0,qs=0,legacy=0,armed=0,fault_ok=0;
 reg[1:0]sid=0;reg[6:0]qi=0;
 reg[16:0]wb=0,qb=0,wstr=0,qstr=17'd512;
 wire[143:0]rq;wire[135:0]lrq;wire[2055:0]rr,lrr;
 reg[143:0]pipe[0:DELAY-1];reg[135:0]lpipe[0:DELAY-1];
 wire bv,rf,lbv,lrf;wire[4:0]bh,lbh;wire[1:0]bn,lbn;wire[1023:0]bd,lbd;wire[15:0]hw,lhw;
 integer cycle=0,blocks=0,total_blocks=0,requests=0,legacy_edges=0,phase_kind=0;
 function automatic[15:0]wvalue(input integer row,head);wvalue=16'h3e00+16'(row*37+head);endfunction
 function automatic[255:0]memdata(input[16:0]sec);
  reg hit;integer nr,k;
  begin
   hit=0;memdata=0;
   for(integer r=0;r<2;r=r+1)if(int'(sec)>=int'(wb)+r*int'(wstr)&&int'(sec)<int'(wb)+r*int'(wstr)+(WFP32?4:2))begin
    hit=1;nr=int'(sec)-int'(wb)-r*int'(wstr);
    if(WFP32)for(integer j=0;j<8;j=j+1)memdata[j*32+:32]={wvalue(r,nr*8+j),16'd0};
    else for(integer j=0;j<16;j=j+1)memdata[j*16+:16]=wvalue(r,nr*16+j);
   end
   if(!hit)for(integer j=0;j<8;j=j+1)memdata[j*32+:32]=32'h674512ab ^ {15'd0,sec} ^ 32'(j*323);
  end
 endfunction
 ot_hnx_idx_vm_query_static_n12_r2048 #(.VM_RT_EXTRA(RT),.WEIGHT_FP32(WFP32),.FACE_MUT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.sid(sid),.frame_start(fs),.weight_slot(ws),.query_slot(qs),.query_index(qi),
 .weight_sector(wb),.query_sector(qb),.weight_row_stride(wstr),.query_row_stride(qstr),.vm_rq(rq),.vm_rr(rr),
 .block_v(bv),.block_head(bh),.block_number(bn),.block_data(bd),.head_weight(hw),.fault(rf));
 ot_hnx_idx_vm_query_static_n12_ref #(.VM_RT_EXTRA(RT),.WEIGHT_FP32(WFP32)) refold(
 .clk(clk),.rst_n(rst_n),.sid(sid),.frame_start(fs&&legacy),.weight_slot(ws&&legacy),.query_slot(qs&&legacy),.query_index(qi),
 .weight_sector({wb[16],wb[14:0]}),.query_sector({qb[16],qb[14:0]}),.weight_row_stride(wstr[15:0]),.query_row_stride(qstr[15:0]),.vm_rq(lrq),.vm_rr(lrr),
 .block_v(lbv),.block_head(lbh),.block_number(lbn),.block_data(lbd),.head_weight(lhw),.fault(lrf));
 always @(posedge clk)begin
  if(!rst_n)for(integer d=0;d<DELAY;d=d+1)begin pipe[d]<=0;lpipe[d]<=0;end
  else begin pipe[0]<=rq;lpipe[0]<=lrq;for(integer d=1;d<DELAY;d=d+1)begin pipe[d]<=pipe[d-1];lpipe[d]<=lpipe[d-1];end end
 end
 for(genvar b=0;b<8;b=b+1)begin
  wire[16:0]sec=pipe[DELAY-1][b*18+:17];wire[15:0]ls=lpipe[DELAY-1][b*17+:16];
  assign rr[b*257+:257]={pipe[DELAY-1][b*18+17],memdata(sec)};
  assign lrr[b*257+:257]={lpipe[DELAY-1][b*17+16],memdata({ls[15],1'b0,ls[14:0]})};
 end
 task tick;
  reg[1023:0]expected;integer row,index;
  begin @(posedge clk);#2;
   if(armed&&rst_n)begin
    if(!fault_ok&&rf!==0)$fatal(1,"reader fault phase%0d edge%0d",phase_kind,cycle);
    if(legacy&&!fault_ok)begin
     if(lrf!==0||bv!==lbv||(bv&&{bh,bn,bd,hw}!=={lbh,lbn,lbd,lhw}))$fatal(1,"legacy reader lockstep");
     for(integer b=0;b<8;b=b+1)if(rq[b*18+17]!==lrq[b*17+16] || (lrq[b*17+16]&&rq[b*18+:18]!=={lrq[b*17+16+:1],lrq[b*17+15+:1],1'b0,lrq[b*17+:15]}))$fatal(1,"legacy request identity");
     legacy_edges=legacy_edges+1;
    end
    for(integer b=0;b<8;b=b+1)if(rq[b*18+17])requests=requests+1;
    if(bv)begin
     row=blocks/128;index=blocks%128;
     for(integer s=0;s<4;s=s+1)expected[s*256+:256]=memdata(17'(int'(qb)+row*int'(qstr)+4*index+s));
     if({bh,bn}!==7'(index)||bd!==expected||hw!==wvalue(row,index/4))$fatal(1,"actual query/tag/data mismatch phase%0d block%0d",phase_kind,blocks);
     blocks=blocks+1;total_blocks=total_blocks+1;
    end
   end
   cycle=cycle+1;@(negedge clk);
  end
 endtask
 task prepare(input integer kind);
  begin
   phase_kind=kind;armed=0;rst_n=0;fs=0;ws=0;qs=0;qi=0;fault_ok=0;blocks=0;requests=0;sid=0;
   legacy=(kind!=1);wstr=WFP32?17'd4:17'd8;qstr=512;
   if(kind==1)begin wb=17'h08a80;qb=WFP32?17'h08007:17'h08000;end
   else if(kind==2)begin wb=17'h10000;qb=WFP32?17'h10407:17'h10400;end
   else begin wb=17'h00100;qb=WFP32?17'h00407:17'h00400;end
   if(kind==3)wstr=17'h0ff00;
   repeat(8)tick();rst_n=1;repeat(32)tick();armed=1;fs=1;tick();fs=0;repeat(3)tick();
  end
 endtask
 task run_phase(input integer kind);
  integer nrows;
  begin prepare(kind);nrows=kind==3?1:2;
   for(integer row=0;row<nrows;row=row+1)begin
    ws=1;tick();ws=0;repeat(RT+28)tick();
    for(integer index=0;index<128;index=index+1)begin qs=1;qi=7'(index);tick();end
    qs=0;repeat(RT+28)tick();
   end
   if(blocks!=nrows*128||requests!=nrows*(WFP32?516:514))$fatal(1,"reader counts phase%0d blocks%0d rq%0d",kind,blocks,requests);
  end
 endtask
 task reject(input integer kind);
  begin
   prepare(0);legacy=0;fault_ok=1;armed=0;rst_n=0;repeat(8)tick();
   if(kind==0)begin sid=0;wb=17'h04000;qb=17'h04400;end // remote regular SID2
   if(kind==1)begin sid=0;wb=17'h18000;qb=17'h18400;end // mirror high row
   if(kind==2)begin sid=3;wb=0;qb=17'h0ffff;end // four-sector domain transition
   rst_n=1;repeat(32)tick();armed=1;requests=0;fs=1;tick();fs=0;repeat(3)tick();qs=1;qi=0;tick();qs=0;repeat(RT+32)tick();
   if(rf!==1||requests!=0)$fatal(1,"invalid source was not rejected kind%0d fault%b requests%0d",kind,rf,requests);
  end
 endtask
 initial begin
  run_phase(0);run_phase(1);run_phase(2);run_phase(3);reject(0);reject(1);reject(2);
  $display("VM_READER_R2048 PASS rt=%0d WFP32=%0d blocks=%0d legacy_edges=%0d cycles=%0d added_cycles=0 explicitmirror=1 highregular=1 remote_highmirror_domain_rejected=3 unused_nextrow_not_faulted=1",RT,WFP32,total_blocks,legacy_edges,cycle);$finish;
 end
endmodule
