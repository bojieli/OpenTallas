`timescale 1ns/1ps
module tb;
reg  ck=0;
reg  rst_n=0;
reg  source_fault=0;
reg  begin_slot=0;
reg [58:0] begin_tag=0;
reg  request_slot=0;
reg [58:0] request_tag=0;
reg [19:0] result_base_word=0;
reg  qr_committed=0;
reg [58:0] qr_tag=0;
reg  q_slot=0;
reg [75:0] q_slot_pub=0;
reg [4:0] q_slot_beat=0;
reg  q_v=0;
reg [4:0] q_beat=0;
reg [58:0] q_tag=0;
reg [511:0] q_data=0;
reg  result_slot=0;
reg [75:0] result_slot_pub=0;
reg [4:0] result_slot_beat=0;
reg  result_v=0;
reg [4:0] result_beat=0;
reg [58:0] result_tag=0;
reg [511:0] result_data=0;
reg  vm_commit_v=0;
reg [4:0] vm_commit_beat=0;
reg [58:0] vm_commit_tag=0;
reg  kernel_done=0;
reg [58:0] kernel_done_tag=0;
reg  complete_slot=0;
reg [12:0] begin_pub=0;
reg [6:0] request_pub=0;
reg [4:0] q_slot_beat_pub=0;
reg [4:0] result_slot_beat_pub=0;
reg [4:0] vm_commit_beat_pub=0;
reg [4:0] q_slot_beat_pub2=0;
reg [4:0] result_slot_beat_pub2=0;
reg [4:0] vm_commit_beat_pub2=0;
reg [4:0] q_slot_beat_pub3=0;
reg [4:0] result_slot_beat_pub3=0;
reg [4:0] vm_commit_beat_pub3=0;
reg [4:0] vm_commit_beat_pub4=0;
wire  r_kernel_request_v,d_kernel_request_v;
wire [58:0] r_kernel_request_tag,d_kernel_request_tag;
wire  r_kernel_q_v,d_kernel_q_v;
wire [4:0] r_kernel_q_beat,d_kernel_q_beat;
wire [58:0] r_kernel_q_tag,d_kernel_q_tag;
wire [511:0] r_kernel_q_data,d_kernel_q_data;
wire [23:0] r_kernel_request_pub,d_kernel_request_pub;
wire [24:0] r_vm_write_pub,d_vm_write_pub;
wire  r_vm_write_v,d_vm_write_v;
wire [19:0] r_vm_write_word,d_vm_write_word;
wire [4:0] r_vm_write_beat,d_vm_write_beat;
wire [58:0] r_vm_write_tag,d_vm_write_tag;
wire [511:0] r_vm_write_data,d_vm_write_data;
wire  r_completed,d_completed;
wire  r_active,d_active;
wire  r_fault,d_fault;
wire [94:0] r_native_ret,d_native_ret;
wire completing; wire[58:0] completed_tag;
qfd_native59_static_service ref0(.ck(ck),.rst_n(rst_n),.source_fault(source_fault),.begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(result_base_word),.qr_committed(qr_committed),.qr_tag(qr_tag),.kernel_request_v(r_kernel_request_v),.kernel_request_tag(r_kernel_request_tag),.q_slot(q_slot),.q_slot_pub(q_slot_pub),.q_slot_beat(q_slot_beat),.q_v(q_v),.q_beat(q_beat),.q_tag(q_tag),.q_data(q_data),.kernel_q_v(r_kernel_q_v),.kernel_q_beat(r_kernel_q_beat),.kernel_q_tag(r_kernel_q_tag),.kernel_q_data(r_kernel_q_data),.result_slot(result_slot),.result_slot_pub(result_slot_pub),.result_slot_beat(result_slot_beat),.result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),.kernel_request_pub(r_kernel_request_pub),.vm_write_pub(r_vm_write_pub),.vm_write_v(r_vm_write_v),.vm_write_word(r_vm_write_word),.vm_write_beat(r_vm_write_beat),.vm_write_tag(r_vm_write_tag),.vm_write_data(r_vm_write_data),.vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag(vm_commit_tag),.kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),.complete_slot(complete_slot),.completed(r_completed),.active(r_active),.fault(r_fault),.native_ret(r_native_ret),.begin_pub(begin_pub),.request_pub(request_pub),.q_slot_beat_pub(q_slot_beat_pub),.result_slot_beat_pub(result_slot_beat_pub),.vm_commit_beat_pub(vm_commit_beat_pub),.q_slot_beat_pub2(q_slot_beat_pub2),.result_slot_beat_pub2(result_slot_beat_pub2),.vm_commit_beat_pub2(vm_commit_beat_pub2),.q_slot_beat_pub3(q_slot_beat_pub3),.result_slot_beat_pub3(result_slot_beat_pub3),.vm_commit_beat_pub3(vm_commit_beat_pub3),.vm_commit_beat_pub4(vm_commit_beat_pub4));
qfd_native59_static_service_obs1 dut0(.ck(ck),.rst_n(rst_n),.source_fault(source_fault),.begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(result_base_word),.qr_committed(qr_committed),.qr_tag(qr_tag),.kernel_request_v(d_kernel_request_v),.kernel_request_tag(d_kernel_request_tag),.q_slot(q_slot),.q_slot_pub(q_slot_pub),.q_slot_beat(q_slot_beat),.q_v(q_v),.q_beat(q_beat),.q_tag(q_tag),.q_data(q_data),.kernel_q_v(d_kernel_q_v),.kernel_q_beat(d_kernel_q_beat),.kernel_q_tag(d_kernel_q_tag),.kernel_q_data(d_kernel_q_data),.result_slot(result_slot),.result_slot_pub(result_slot_pub),.result_slot_beat(result_slot_beat),.result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),.kernel_request_pub(d_kernel_request_pub),.vm_write_pub(d_vm_write_pub),.vm_write_v(d_vm_write_v),.vm_write_word(d_vm_write_word),.vm_write_beat(d_vm_write_beat),.vm_write_tag(d_vm_write_tag),.vm_write_data(d_vm_write_data),.vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag(vm_commit_tag),.kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),.complete_slot(complete_slot),.completed(d_completed),.active(d_active),.fault(d_fault),.native_ret(d_native_ret),.begin_pub(begin_pub),.request_pub(request_pub),.q_slot_beat_pub(q_slot_beat_pub),.result_slot_beat_pub(result_slot_beat_pub),.vm_commit_beat_pub(vm_commit_beat_pub),.q_slot_beat_pub2(q_slot_beat_pub2),.result_slot_beat_pub2(result_slot_beat_pub2),.vm_commit_beat_pub2(vm_commit_beat_pub2),.q_slot_beat_pub3(q_slot_beat_pub3),.result_slot_beat_pub3(result_slot_beat_pub3),.vm_commit_beat_pub3(vm_commit_beat_pub3),.vm_commit_beat_pub4(vm_commit_beat_pub4),.completing(completing),.completed_tag(completed_tag));
reg cxslot=0,cxv=0; reg[30:0]cxhdr=0;reg[4:0]cxbeat=0;reg[58:0]cxtag=0;wire[128:0]cxr,cxd;wire[1:0]cur,cud;wire cfr,cfd;wire[58:0]ctag;
qfd_mu_ctx_rx cr(.ck(ck),.rst_n(rst_n),.context_slot(cxslot),.rx_v(cxv),.rx_hdr(cxhdr),.rx_beat(cxbeat),.rx_tag(cxtag),.ctx_x(cxr),.ctx_user(cur),.mu_fault(cfr));
qfd_mu_ctx_rx_obs1 cd(.ck(ck),.rst_n(rst_n),.context_slot(cxslot),.rx_v(cxv),.rx_hdr(cxhdr),.rx_beat(cxbeat),.rx_tag(cxtag),.ctx_x(cxd),.ctx_user(cud),.mu_fault(cfd),.ctx_tag(ctag));
reg[43:0]dh=0;wire[1:0]dur,dud,rur,rud;wire dfr,dfd;wire[44:0]robs;
qfd_sys_face_mu_dhuser #(.NU(4),.NS(2),.USER_SEQ(128'h9),.STG_SEQ(384'h941),.RES_SEQ(64'h2)) hr(.ck(ck),.rst_n(rst_n),.dh_run(dh),.dh_user(dur),.res_user(rur),.mu_fault(dfr));
qfd_sys_face_mu_dhuser_obs1 #(.NU(4),.NS(2),.USER_SEQ(128'h9),.STG_SEQ(384'h941),.RES_SEQ(64'h2)) hd(.ck(ck),.rst_n(rst_n),.dh_run(dh),.dh_user(dud),.res_user(rud),.mu_fault(dfd),.res_obs(robs));
integer checks=0;reg[58:0]lasttag;reg[58:0]nativehold;reg[43:0]dhhold;
task tick;begin #2;ck=1;#1;checks=checks+1;
 if(r_kernel_request_v!==d_kernel_request_v || r_kernel_request_tag!==d_kernel_request_tag || r_kernel_q_v!==d_kernel_q_v || r_kernel_q_beat!==d_kernel_q_beat || r_kernel_q_tag!==d_kernel_q_tag || r_kernel_q_data!==d_kernel_q_data || r_kernel_request_pub!==d_kernel_request_pub || r_vm_write_pub!==d_vm_write_pub || r_vm_write_v!==d_vm_write_v || r_vm_write_word!==d_vm_write_word || r_vm_write_beat!==d_vm_write_beat || r_vm_write_tag!==d_vm_write_tag || r_vm_write_data!==d_vm_write_data || r_completed!==d_completed || r_active!==d_active || r_fault!==d_fault || r_native_ret!==d_native_ret)$fatal(1,"native original-output differential");
 if(cxr!==cxd || cur!==cud || cfr!==cfd)$fatal(1,"context original-output differential");
 if(dur!==dud || rur!==rud || dfr!==dfd)$fatal(1,"RESULT original-output differential");
 #1;ck=0;#1;end endtask
 task nativeop(input[15:0]ep,input[17:0]tok);begin
 begin_tag={ep,6'd1,tok,13'd7,6'd0};begin_slot=1;tick;begin_slot=0;
 request_tag=begin_tag;qr_tag=begin_tag;qr_committed=1;request_slot=1;tick;request_slot=0;request_tag=59'h7ffffffffffffff;
 q_tag=begin_tag;q_slot=1;q_v=1;
 for(integer k=0;k<32;k=k+1)begin q_slot_beat=k;q_beat=k;tick;end
 q_slot=0;q_v=0;result_slot=1;result_v=1;result_tag=begin_tag;
 for(integer k=0;k<32;k=k+1)begin result_slot_beat=k;result_beat=k;tick;end
 result_slot=0;result_v=0;vm_commit_v=1;vm_commit_tag=begin_tag;
 for(integer k=0;k<32;k=k+1)begin vm_commit_beat=k;tick;end
 vm_commit_v=0;kernel_done=1;kernel_done_tag=begin_tag;tick;kernel_done=0;
 complete_slot=1;tick;
 $display("NATIVE DEBUG completed=%b fault=%b held=%h expect=%h active=%b ok=%b req=%b done=%b q=%h r=%h c=%h",d_completed,d_fault,completed_tag,begin_tag,d_active,dut0.complete_ok,dut0.requested,dut0.done_seen,dut0.q_seen,dut0.result_seen,dut0.committed);
 if(!d_completed || d_fault || completed_tag!==begin_tag)$fatal(1,"actual accepted native completion identity");
 nativehold=completed_tag;complete_slot=0;tick;
 if(d_completed || completed_tag!==nativehold)$fatal(1,"native identity not held");
 end endtask
 initial begin
 rst_n=0;tick;rst_n=1;tick;
 // Consecutive validated context loads, then invalid/new unrelated RX payload.
 for(integer u=1;u<4;u=u+1)begin
 cxtag={14'd9,2'(u),6'd0,18'(100+u),13'(20+u),6'd0};cxhdr={5'd0,4'd12,6'd63,cxtag[58:43]};cxslot=1;cxv=1;tick;
 if(!cxd[128] || cud!==2'(u) || ctag!==cxtag)$fatal(1,"context event/raw identity phase");
 end
 lasttag=ctag;cxslot=0;cxv=0;cxtag='1;tick;
 if(cxd[128] || ctag!==lasttag)$fatal(1,"context identity did not hold");
 // First h_start is not RESULT, second is; raw44 identity includes its exact h_start.
 dh={1'b0,1'b1,6'd1,36'h123};tick;if(robs[44])$fatal(1,"false RESULT event");
 dh={1'b0,1'b1,6'd37,36'habcd};dhhold=dh;tick;
 if(!robs[44] || rud!==2'd2 || robs[43:0]!==dhhold)$fatal(1,"RESULT event/raw identity phase");
 dh=0;tick;if(robs[44] || robs[43:0]!==dhhold)$fatal(1,"RESULT identity did not hold");
 nativeop(16'h29,18'd900);nativeop(16'h2e,18'd901);
 // Reset clears event validity, not payload. A rejected completion must not rewrite held identity.
 dh={1'b0,1'b1,6'd1,36'h333};tick;
 cxslot=1;cxv=1;cxtag={14'd11,2'd1,6'd0,18'd120,13'd9,6'd0};cxhdr={5'd0,4'd12,6'd63,cxtag[58:43]};
 dh={1'b0,1'b1,6'd37,36'h444};
 rst_n=0;tick;
 if(ctag!==lasttag || robs[43:0]!==dhhold)$fatal(1,"reset fabricated observer identity capture");
 cxslot=0;cxv=0;dh=0;rst_n=1;tick;
 if(d_completed || cxd[128] || robs[44])$fatal(1,"reset event validity");
 complete_slot=1;tick;complete_slot=0;
 if(d_completed || !d_fault || completed_tag!==nativehold)$fatal(1,"rejected completion mutated held tag");
 $display("OBS_CALLBACK_UNIT_PASS checks=%0d real_native_completions=2 context_loads=3 result_events=1 original_output_differential=PASS",checks);$finish;
 end
endmodule
