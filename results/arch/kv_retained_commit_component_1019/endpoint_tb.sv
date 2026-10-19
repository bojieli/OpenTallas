`timescale 1ns/1ps
module endpoint_tb;
parameter M=0;
reg ck=0; always #5 ck=~ck;
reg por_n=0,rst_n=0,raw_por_n=0,warm_rst_n=0,pll_locked_i=0,health_bad_i=0,health_armed_i=0,execution_restart_i=0,role_fault_i=0;
reg[181:0]hc=0;reg[92:0]legacy_tk=0;
reg image_ready=1,shared_epoch_valid=1;reg[15:0]shared_epoch=16'h1234;
wire request_v;wire[58:0]request_tag;wire[31:0]request_trace;wire[1:0]request_gen;
wire[17:0]request_token,request_pos;reg request_cr=0;wire[142:0]native_pr;
reg result_v=0;reg[58:0]result_tag=0;reg[1:0]result_gen=0;reg result_done=0,result_fault=0;reg[3:0]result_cause=0;
reg[17:0]result_token=18'd77;reg[31:0]result_value=32'hdeadbeef,result_cycles=100;
wire result_cr;reg kv_drained=1,vm_drained=1,collective_drained=1,host_drained=1,collective_busy=0,kv_flush=0;
reg recovery_clear=0,cancel_release_v=0;reg[58:0]cancel_release_tag=0;reg[1:0]cancel_release_gen=0;
wire context_owned,cancel_released,protocol_fault;wire[92:0]local_tk;wire retained_bad_o,retained_owned_o,retained_armed_o;
qkd_host_native_token_endpoint_cancel_rc #(.ENABLE_NATIVE(1),.ENABLE_RETAINED_COMMIT(1),.RC_MUT(M)) dut(.*);

wire  orig_request_v;
wire [58:0] orig_request_tag;
wire [31:0] orig_request_trace;
wire [1:0] orig_request_gen;
wire [17:0] orig_request_token;
wire [17:0] orig_request_pos;
wire [142:0] orig_native_pr;
wire  orig_result_cr;
wire  orig_context_owned;
wire  orig_cancel_released;
wire [92:0] orig_local_tk;
wire  orig_protocol_fault;
qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1)) orig (.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(legacy_tk),.image_ready(image_ready),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),.request_cr(request_cr),.result_v(result_v),.result_tag(result_tag),.result_gen(result_gen),.result_done(result_done),.result_fault(result_fault),.result_cause(result_cause),.result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),.host_drained(host_drained),.collective_busy(collective_busy),.kv_flush(kv_flush),.recovery_clear(recovery_clear),.cancel_release_v(cancel_release_v),.cancel_release_tag(cancel_release_tag),.cancel_release_gen(cancel_release_gen),.request_v(orig_request_v),.request_tag(orig_request_tag),.request_trace(orig_request_trace),.request_gen(orig_request_gen),.request_token(orig_request_token),.request_pos(orig_request_pos),.native_pr(orig_native_pr),.result_cr(orig_result_cr),.context_owned(orig_context_owned),.cancel_released(orig_cancel_released),.local_tk(orig_local_tk),.protocol_fault(orig_protocol_fault));
wire  off_request_v;
wire [58:0] off_request_tag;
wire [31:0] off_request_trace;
wire [1:0] off_request_gen;
wire [17:0] off_request_token;
wire [17:0] off_request_pos;
wire [142:0] off_native_pr;
wire  off_result_cr;
wire  off_context_owned;
wire  off_cancel_released;
wire [92:0] off_local_tk;
wire  off_protocol_fault;
qkd_host_native_token_endpoint_cancel_rc #(.ENABLE_NATIVE(1)) off (.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(legacy_tk),.image_ready(image_ready),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),.request_cr(request_cr),.result_v(result_v),.result_tag(result_tag),.result_gen(result_gen),.result_done(result_done),.result_fault(result_fault),.result_cause(result_cause),.result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),.host_drained(host_drained),.collective_busy(collective_busy),.kv_flush(kv_flush),.recovery_clear(recovery_clear),.cancel_release_v(cancel_release_v),.cancel_release_tag(cancel_release_tag),.cancel_release_gen(cancel_release_gen),.request_v(off_request_v),.request_tag(off_request_tag),.request_trace(off_request_trace),.request_gen(off_request_gen),.request_token(off_request_token),.request_pos(off_request_pos),.native_pr(off_native_pr),.result_cr(off_result_cr),.context_owned(off_context_owned),.cancel_released(off_cancel_released),.local_tk(off_local_tk),.protocol_fault(off_protocol_fault),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),.health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i));
always @(negedge ck) if(raw_por_n)begin
 if ({orig_request_v,orig_request_tag,orig_request_trace,orig_request_gen,orig_request_token,orig_request_pos,orig_native_pr,orig_result_cr,orig_context_owned,orig_cancel_released,orig_local_tk,orig_protocol_fault} !== {off_request_v,off_request_tag,off_request_trace,off_request_gen,off_request_token,off_request_pos,off_native_pr,off_result_cr,off_context_owned,off_cancel_released,off_local_tk,off_protocol_fault})$fatal(1,"DEFAULT_IDENTITY edge=%0d",edge_n);
end
integer edge_n=0;always @(posedge ck)edge_n<=edge_n+1;
task tick;begin @(posedge ck);#1;end endtask
task init;begin
 @(negedge ck);raw_por_n=0;por_n=0;rst_n=0;warm_rst_n=0;pll_locked_i=0;health_armed_i=0;health_bad_i=0;hc=0;request_cr=0;result_v=0;result_done=0;cancel_release_v=0;
 tick();tick();
 @(negedge ck);raw_por_n=1;por_n=1;
 tick();tick();if(retained_bad_o)$fatal(1,"STARTUP_POISON edge=%0d",edge_n);
 @(negedge ck);rst_n=1;warm_rst_n=1;pll_locked_i=1;health_armed_i=1;tick();tick();
end endtask
task launch;begin
 @(negedge ck);hc=0;hc[38]=1;hc[37:36]=2;hc[35:18]=18'd23;hc[17:0]=18'd5;
 tick();@(negedge ck);hc=0;tick();
end endtask
reg[58:0]tag;reg[1:0]gen;integer j;reg got,credit_seen;
task issued;begin
 got=0;for(j=0;j<12;j=j+1)begin tick();if(request_v)begin got=1;tag=request_tag;tag[42:37]=6'd37;gen=request_gen;j=12;end end
 if(!got)$fatal(1,"NO_REAL_REQUEST edge=%0d",edge_n);
 @(negedge ck);request_cr=1;tick();@(negedge ck);request_cr=0;tick();tick();
end endtask
initial begin
 // A genuine accepted owner survives warm reset; actual matching result retires.
 init();launch();issued();
 @(negedge ck);rst_n=0;warm_rst_n=0;tick();
 if(!context_owned)$fatal(1,"OWNER_LOST edge=%0d",edge_n);
 if(!retained_bad_o)$fatal(1,"FAULT_NOT_STICKY edge=%0d",edge_n);
 @(negedge ck);rst_n=1;warm_rst_n=1;result_v=1;result_done=1;result_tag=tag;result_gen=gen;
 tick();@(negedge ck);result_v=0;result_done=0;
 credit_seen=0;repeat(8)begin tick();if(result_cr)credit_seen=1;end
 if(context_owned||!credit_seen)$fatal(1,"RAWDONE_DEBT edge=%0d",edge_n);
 if(!local_tk[88])$fatal(1,"POISON_SUCCESS edge=%0d",edge_n);
 $display("PASS real result cleanup edge=%0d",edge_n);
 // A real identity error poisons admission, but the matching owned return drains.
 init();launch();issued();
 @(negedge ck);result_v=1;result_done=1;result_tag=tag;result_gen=gen^2'b01;
 tick();@(negedge ck);result_v=0;result_done=0;tick();tick();
 if(!protocol_fault||!context_owned)$fatal(1,"IDENTITY_OWNER_LOST edge=%0d",edge_n);
 @(negedge ck);result_v=1;result_done=1;result_gen=gen;
 tick();@(negedge ck);result_v=0;result_done=0;credit_seen=0;
 repeat(8)begin tick();if(result_cr)credit_seen=1;end
 if(context_owned||!credit_seen||!protocol_fault)$fatal(1,"PROTOCOL_DRAIN_STUCK edge=%0d",edge_n);
 $display("PASS protocol fault real matching cleanup edge=%0d",edge_n);
 // Fault arrives after acceptance and before issue. No request may escape.
 init();launch();
 if(!context_owned)$fatal(1,"NO_PENDING_OWNER edge=%0d",edge_n);
 @(negedge ck);health_bad_i=1;
 repeat(5)begin tick();if(request_v)$fatal(1,"POST_POISON_ISSUE edge=%0d",edge_n);end
 if(!context_owned)$fatal(1,"PENDING_OWNER_LOST edge=%0d",edge_n);
 $display("PASS same-edge new issue cut edge=%0d",edge_n);
 // Exceptional release remains live under poison and requires real identity/drain.
 init();launch();issued();
 @(negedge ck);health_bad_i=1;kv_drained=0;cancel_release_v=1;cancel_release_tag=tag;cancel_release_gen=gen;
 tick();@(negedge ck);cancel_release_v=0;repeat(3)tick();
 if(!context_owned||cancel_released)$fatal(1,"EARLY_CANCEL_RELEASE edge=%0d",edge_n);
 @(negedge ck);kv_drained=1;got=0;repeat(6)begin tick();if(cancel_released)got=1;end
 if(context_owned||!got)$fatal(1,"CANCEL_DRAIN_STUCK edge=%0d",edge_n);
 if(!retained_bad_o)$fatal(1,"POISON_CLEARED edge=%0d",edge_n);
 @(negedge ck);raw_por_n=0;health_bad_i=0;tick();if(context_owned||retained_bad_o)$fatal(1,"RAW_POR_NOT_CLEAR edge=%0d",edge_n);
 // A returned result cannot erase a still-unreturned request reservation.
 init();launch();got=0;
 for(j=0;j<12;j=j+1)begin tick();if(request_v)begin got=1;tag=request_tag;tag[42:37]=6'd37;gen=request_gen;j=12;end end
 if(!got)$fatal(1,"NO_CREDIT_DEBT_REQUEST edge=%0d",edge_n);
 @(negedge ck);health_bad_i=1;result_v=1;result_done=1;result_tag=tag;result_gen=gen;
 tick();@(negedge ck);result_v=0;result_done=0;repeat(8)tick();
 if(context_owned||!retained_owned_o)$fatal(1,"CREDIT_OWNER_LOST edge=%0d",edge_n);
 @(negedge ck);request_cr=1;tick();@(negedge ck);request_cr=0;repeat(4)tick();
 if(retained_owned_o)$fatal(1,"REAL_CREDIT_NOT_DRAINED edge=%0d",edge_n);
 $display("ENDPOINT_PASS M=%0d edges=%0d",M,edge_n);$finish;
end
endmodule
