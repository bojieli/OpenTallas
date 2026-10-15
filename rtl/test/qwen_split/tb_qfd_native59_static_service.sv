`timescale 1ns/1ps
module tb_qfd_native59_static_service;
 parameter integer MISSING_COMMIT=0,STALE_Q=0,MUT_EARLY_COMPLETE=0,FINAL_FAULT=0;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg begin_slot=0,request_slot=0,q_slot=0,q_v=0,result_slot=0,result_v=0,vm_commit_v=0,kernel_done=0,complete_slot=0;
 reg[58:0]tag=0,qtag=0;reg[4:0]qb=0,rb=0,cb=0;
 reg[511:0]qd=0,rd=0;
 wire[94:0]ret;wire req,qout,wv,completed,active,fault;wire[58:0]reqtag,outqtag,write_tag;wire[4:0]outqb,write_beat;wire[511:0]outqd,write_data;wire[19:0]write_word;
 qfd_native59_static_service #(.MUT_EARLY_COMPLETE(MUT_EARLY_COMPLETE))dut(
 .ck(ck),.rst_n(rst_n),.source_fault(FINAL_FAULT&&complete_slot),.begin_slot(begin_slot),.begin_tag(tag),.request_slot(request_slot),.request_tag(tag),.result_base_word(20'd3167),
 .qr_committed(1'b1),.qr_tag(tag),.kernel_request_v(req),.kernel_request_tag(reqtag),
 .q_slot(q_slot),.q_slot_beat(qb),.q_v(q_v),.q_beat(qb),.q_tag(qtag),.q_data(qd),.kernel_q_v(qout),.kernel_q_beat(outqb),.kernel_q_tag(outqtag),.kernel_q_data(outqd),
 .result_slot(result_slot),.result_slot_beat(rb),.result_v(result_v),.result_beat(rb),.result_tag(tag),.result_data(rd),
 .vm_write_v(wv),.vm_write_word(write_word),.vm_write_beat(write_beat),.vm_write_tag(write_tag),.vm_write_data(write_data),
 .vm_commit_v(vm_commit_v),.vm_commit_beat(cb),.vm_commit_tag(tag),.kernel_done(kernel_done),.kernel_done_tag(tag),
 .complete_slot(complete_slot),.completed(completed),.active(active),.fault(fault),.native_ret(ret));
 integer ep,i,errors=0;
 task step;begin @(negedge ck);end endtask
 initial begin
 repeat(3)step();rst_n=1;
 for(ep=0;ep<3;ep=ep+1)begin
  tag={16'(ep+7),6'(ep+1),18'd50994,13'(ep),6'd0};
  begin_slot=1;step();begin_slot=0;if(!ret[0]||!ret[1])errors=errors+1;request_slot=1;step();request_slot=0;
  if(!req||reqtag!=tag||ret[1:0]!=0)errors=errors+1;
  for(i=0;i<32;i=i+1)begin
   q_slot=1;q_v=1;qb=i;qtag=tag^(STALE_Q!=0?59'd1:59'd0);qd={16{32'(ep*1000+i)}};
   step();
   if(!qout||outqb!=i||outqtag!=qtag||outqd!==qd)errors=errors+1;
   if(STALE_Q!=0)begin
    if(!fault)$fatal(1,"stale Q not rejected");$display("PASS static59 stale actualQtag faults");$finish;
   end
  end
  q_slot=0;q_v=0;
  for(i=0;i<32;i=i+1)begin
   result_slot=1;result_v=1;rb=i;rd={16{32'(ep*2000+i)}};step();
   if(!wv||write_word!=3167+i||write_beat!=i||write_tag!=tag||write_data!==rd)errors=errors+1;
  end
  result_slot=0;result_v=0;
  for(i=0;i<32-MISSING_COMMIT;i=i+1)begin vm_commit_v=1;cb=i;step();if(ret[93:78]!=i+1)errors=errors+1;end
  vm_commit_v=0;kernel_done=1;step();kernel_done=0;
  complete_slot=1;step();complete_slot=0;
  if(MISSING_COMMIT!=0||FINAL_FAULT!=0)begin
   if(!fault||completed)$fatal(1,"FAIL completion without actual last VMcommit");
   $display("PASS static59 completion rejects missingactualVMcommit or finalsourcefault");$finish;
  end
  if(fault||!completed||active||ret[1:0]!=3||ret[93:78]!=32||ret[77:2]!=0)errors=errors+1;
  step();
 end
 if(errors)$fatal(1,"FAIL static59 actualdata/identity lifecycle errors%0d",errors);
 $display("PASS static59 3epochs TAG59 96Q+96results actualVMcommit exactcompiledslots no credits");$finish;
 end
 initial begin #5000;$fatal(1,"timeout");end
endmodule
