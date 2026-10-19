`timescale 1ns/1ps
module tb_qkd_host_native_token_endpoint_health_fault;
 parameter integer MUT=0;
 reg ck=0;always #0.5 ck=~ck;
 reg por_n=0,rst_n=0;reg[181:0]hc=0;reg[92:0]legacy_tk=0;
 reg shared_epoch_valid=0;reg[15:0]shared_epoch=0;
 wire request_v;wire[58:0]request_tag;wire[31:0]request_trace;wire[1:0]request_gen;
 wire[17:0]request_token,request_pos;reg request_cr=0;wire[142:0]native_pr;
 reg result_v=0;reg[58:0]result_tag=0;reg[1:0]result_gen=0;
 reg result_done=0,result_fault=0;reg[3:0]result_cause=0;
 reg[17:0]result_token=0;reg[31:0]result_value=0,result_cycles=0;
 wire result_cr;reg vm_drained=0,host_drained=0,kv_drained=0,collective_drained=0,collective_busy=0,kv_flush=0;
 wire[92:0]local_tk;wire protocol_fault;
 reg image_ready=1,recovery_clear=0,cancel_release_v=0;reg[58:0]cancel_release_tag=0;reg[1:0]cancel_release_gen=0;wire context_owned,cancel_released;integer releases=0;
 always @(negedge ck)if(cancel_released)releases=releases+1;
 qkd_host_native_token_endpoint_cancel_health #(.ENABLE_NATIVE(1),.MUT(MUT),.HEALTH_RETIRE(1))d(.*);
 wire[92:0]off_tk;
 qkd_host_native_token_endpoint #(.ENABLE_NATIVE(0))off(.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(legacy_tk),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),.request_cr(0),.result_v(0),.result_tag(59'd0),.result_gen(2'd0),.result_done(0),.result_fault(0),.result_cause(4'd0),.result_token(18'd0),.result_value(32'd0),.result_cycles(32'd0),.vm_drained(0),.host_drained(0),.kv_drained(0),.collective_drained(0),.collective_busy(0),.kv_flush(0),.local_tk(off_tk));
 wire request_v_orig;
 wire [58:0] request_tag_orig;
 wire [31:0] request_trace_orig;
 wire [1:0] request_gen_orig;
 wire [17:0] request_token_orig;
 wire [17:0] request_pos_orig;
 wire [142:0] native_pr_orig;
 wire result_cr_orig;
 wire context_owned_orig;
 wire cancel_released_orig;
 wire [92:0] local_tk_orig;
 wire protocol_fault_orig;
 qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1),.MUT(MUT)) shadow_orig(.request_v(request_v_orig),.request_tag(request_tag_orig),.request_trace(request_trace_orig),.request_gen(request_gen_orig),.request_token(request_token_orig),.request_pos(request_pos_orig),.native_pr(native_pr_orig),.result_cr(result_cr_orig),.context_owned(context_owned_orig),.cancel_released(cancel_released_orig),.local_tk(local_tk_orig),.protocol_fault(protocol_fault_orig),.*);
 wire request_v_off;
 wire [58:0] request_tag_off;
 wire [31:0] request_trace_off;
 wire [1:0] request_gen_off;
 wire [17:0] request_token_off;
 wire [17:0] request_pos_off;
 wire [142:0] native_pr_off;
 wire result_cr_off;
 wire context_owned_off;
 wire cancel_released_off;
 wire [92:0] local_tk_off;
 wire protocol_fault_off;
 qkd_host_native_token_endpoint_cancel_health #(.ENABLE_NATIVE(1),.MUT(MUT),.HEALTH_RETIRE(0)) shadow_off(.request_v(request_v_off),.request_tag(request_tag_off),.request_trace(request_trace_off),.request_gen(request_gen_off),.request_token(request_token_off),.request_pos(request_pos_off),.native_pr(native_pr_off),.result_cr(result_cr_off),.context_owned(context_owned_off),.cancel_released(cancel_released_off),.local_tk(local_tk_off),.protocol_fault(protocol_fault_off),.*);
 always @(negedge ck) if(por_n) begin
  if({request_v_orig,request_tag_orig,request_trace_orig,request_gen_orig,request_token_orig,request_pos_orig,native_pr_orig,result_cr_orig,context_owned_orig,cancel_released_orig,local_tk_orig,protocol_fault_orig} !== {request_v_off,request_tag_off,request_trace_off,request_gen_off,request_token_off,request_pos_off,native_pr_off,result_cr_off,context_owned_off,cancel_released_off,local_tk_off,protocol_fault_off}) $fatal(1,"DEFAULT_OFF all output identity");
 end
 integer checks=0,nreq=0,ncr=0,i,j;reg[58:0]saved;
 always @(negedge ck)begin if(request_v)nreq=nreq+1;if(result_cr)ncr=ncr+1;end
 task tick(input integer n);begin repeat(n)begin @(posedge ck);#0.05;end end endtask
 task check(input reg yes,input[1023:0]msg);begin checks=checks+1;if(!yes)$fatal(1,"endpoint %s",msg);end endtask
 task reset_host;begin @(negedge ck);rst_n=0;hc=0;shared_epoch_valid=0;result_v=0;request_cr=0;kv_drained=0;vm_drained=0;host_drained=0;collective_drained=0;tick(3);@(negedge ck);rst_n=1;tick(3);end endtask
 task launch(input integer ep,input integer tok,input integer pos,input integer gen);begin
 @(negedge ck);shared_epoch_valid=1;shared_epoch=ep;hc[38]=1;hc[37:36]=gen;hc[35:18]=tok;hc[17:0]=pos;
 tick(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;
 wait(request_v);#0.05;
 check(request_tag=={16'(ep),6'd0,18'(tok),13'(pos),6'd0},"request full TAG59");
 check(request_gen==2'(gen)&&request_token==tok&&request_pos==pos,"request original operands");
 tick(2);end endtask
 task response(input[58:0]tag,input integer gen,input reg dn,input reg fl);begin
 @(negedge ck);result_v=1;result_tag=tag;result_gen=gen;result_done=dn;result_fault=fl;result_cause=4'h7;result_token=18'h12345;result_value=32'h89abcdef;result_cycles=32'd1234;
 tick(1);@(negedge ck);result_v=0;tick(3);end endtask
 task recycle_credit;begin @(negedge ck);request_cr=1;tick(1);@(negedge ck);request_cr=0;tick(2);end endtask
 initial begin
 tick(3);@(negedge ck);por_n=1;rst_n=1;tick(5);
 // Genuine terminal arrives while physical drains are still incomplete.
 launch(1,101,21,0); response({16'd1,6'd37,18'd101,13'd21,6'd0},0,1,0);
 check(!local_tk[92],"terminal still pending");
 @(negedge ck);kv_flush=1;tick(2);@(negedge ck);kv_flush=0;
 kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(5);
 check(!local_tk[92]&&local_tk[88]&&context_owned,"HEALTH_RETIRE late real flush veto");
 check(ncr==0,"HEALTH_RETIRE no normal slot return");
 // Warm reset and nominal recovery cannot erase physical health history.
 reset_host();kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(4);
 recovery_clear=1;tick(2);recovery_clear=0;tick(3);
 check(!protocol_fault,"healthy legal recovery precondition");
 j=nreq;@(negedge ck);shared_epoch_valid=1;shared_epoch=2;hc[38]=1;hc[35:18]=102;hc[17:0]=22;
 tick(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;tick(8);
 check(nreq==j&&!context_owned&&!local_tk[92]&&local_tk[88],"HEALTH_ADMIT warm reset retains veto");
 // Only actual POR discards the recorded event.
 @(negedge ck);por_n=0;rst_n=0;tick(3);@(negedge ck);por_n=1;rst_n=1;tick(5);
 launch(3,103,23,1);response({16'd3,6'd37,18'd103,13'd23,6'd0},1,1,0);
 @(negedge ck);kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(5);
 check(local_tk[92]&&!local_tk[88],"healthy POR recovery");
 // A fault after endpoint completion removes the continued done level.
 @(negedge ck);kv_flush=1;tick(3);@(negedge ck);kv_flush=0;tick(3);
 check(!local_tk[92]&&local_tk[88],"HEALTH_DONE continuous done level veto");
 $display("PASS HOST_ENDPOINT_HEALTH checks=%0d requests=%0d credits=%0d",checks,nreq,ncr);$finish;
 end
 initial begin #10000;$fatal(1,"health timeout");end
endmodule
