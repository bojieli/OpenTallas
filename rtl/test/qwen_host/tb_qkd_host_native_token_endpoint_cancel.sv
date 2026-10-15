`timescale 1ns/1ps
module tb_qkd_host_native_token_endpoint_cancel;
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
 qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1),.MUT(MUT))d(.*);
 wire[92:0]off_tk;
 qkd_host_native_token_endpoint #(.ENABLE_NATIVE(0))off(.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(hc),.legacy_tk(legacy_tk),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),.request_cr(0),.result_v(0),.result_tag(59'd0),.result_gen(2'd0),.result_done(0),.result_fault(0),.result_cause(4'd0),.result_token(18'd0),.result_value(32'd0),.result_cycles(32'd0),.vm_drained(0),.host_drained(0),.kv_drained(0),.collective_drained(0),.collective_busy(0),.kv_flush(0),.local_tk(off_tk));
 integer checks=0,nreq=0,ncr=0,i,j;reg[58:0]saved;
 always @(negedge ck)begin if(request_v)nreq=nreq+1;if(result_cr)ncr=ncr+1;end
 task tick(input integer n);begin repeat(n)begin @(posedge ck);#0.05;end end endtask
 task check(input reg yes,input[255:0]msg);begin checks=checks+1;if(!yes)$fatal(1,"endpoint %s",msg);end endtask
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
 tick(3);@(negedge ck);por_n=1;rst_n=1;hc[181:39]=143'h456123789abcdef;legacy_tk=93'h1234567890abcdef;
 tick(5);check(native_pr==hc[181:39],"actual program metadata");check(off_tk==legacy_tk,"DEFAULT_OFF exact legacy status");
 // Epoch zero is valid when explicitly granted by the sole allocator.
 launch(0,100,8191,0);response({16'd0,6'd37,18'd100,13'd8191,6'd0},0,1,0);
 @(negedge ck);kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(4);
 check(local_tk[92]&&!protocol_fault,"sole allocator may grant epoch zero");
 @(negedge ck);kv_drained=0;vm_drained=0;host_drained=0;collective_drained=0;recycle_credit();
 for(i=1;i<=12;i=i+1)begin
 launch(i,101+i,8191-i,i%4);saved={16'(i),6'd37,18'(101+i),13'(8191-i),6'd0};
 response(saved,i%4,1,0);check(!local_tk[92]&&!result_cr&&!protocol_fault,"terminal waits actual drains");
 @(negedge ck);kv_drained=1;tick(4);check(!local_tk[92],"collective drain required");
 @(negedge ck);collective_drained=1;tick(4);check(!local_tk[92],"VM drain required");
 @(negedge ck);vm_drained=1;tick(4);check(!local_tk[92],"HOST drain required");
 @(negedge ck);host_drained=1;tick(4);
 check(local_tk[92]&&local_tk[91:90]==i%4&&local_tk[89]&&!local_tk[88],"true completion status");
 check(local_tk[81:64]==18'h12345&&local_tk[63:32]==32'h89abcdef&&local_tk[31:0]==1234,"actual head result only");
 @(negedge ck);kv_drained=0;vm_drained=0;host_drained=0;collective_drained=0;recycle_credit();
 end
 // Every identity field and generation must match, even if next-token data agrees.
 for(j=0;j<6;j=j+1)begin
 reset_host();launch(30+j,444,777,1);saved={16'(30+j),6'd37,18'd444,13'd777,6'd0};
 case(j)0:saved[43]=~saved[43];1:saved[37]=~saved[37];2:saved[19]=~saved[19];3:saved[6]=~saved[6];4:saved[0]=~saved[0];endcase
 response(saved,j==5?2:1,1,0);tick(3);check(protocol_fault&&!local_tk[92],"stale full identity rejected");
 end
 // Old completion after warm reset cannot impersonate a new shared epoch.
 reset_host();launch(60,222,333,1);saved={16'd60,6'd37,18'd222,13'd333,6'd0};
 reset_host();launch(61,222,333,1);response(saved,1,1,0);check(protocol_fault&&!local_tk[92],"warm reset rejects old terminal");
 reset_host();launch(70,222,333,1);response({16'd70,6'd37,18'd222,13'd333,6'd0},1,0,1);tick(2);
 check(local_tk[88]&&!local_tk[92]&&local_tk[87:84]==7&&!protocol_fault,"done-zero genuine fault captured");
 response({16'd70,6'd37,18'd222,13'd333,6'd0},1,1,1);
 @(negedge ck);kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(4);check(local_tk[92]&&local_tk[88],"fault terminal requires drains");
 reset_host();launch(80,222,333,1);response({16'd80,6'd37,18'd222,13'd333,6'd0},1,1,0);
 @(negedge ck);kv_drained=1;vm_drained=1;host_drained=1;collective_drained=1;tick(4);
 j=nreq;@(negedge ck);shared_epoch_valid=1;shared_epoch=81;hc[38]=1;hc[37:36]=2;hc[35:18]=223;hc[17:0]=334;
 tick(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;tick(10);
 check(nreq==j&&!request_v&&!protocol_fault,"withheld execution credit stalls");
 @(negedge ck);request_cr=1;tick(1);@(negedge ck);request_cr=0;
 wait(request_v);#0.05;check(request_tag=={16'd81,6'd0,18'd223,13'd334,6'd0},"pending identity held for credit");tick(2);
 reset_host();@(negedge ck);hc[38]=1;hc[37:36]=1;hc[17:0]=18'd8192;shared_epoch_valid=1;shared_epoch=71;tick(4);check(protocol_fault&&!request_v,"no position truncation");
 reset_host();@(negedge ck);hc[38]=1;hc[37:36]=1;hc[17:0]=10;shared_epoch_valid=0;tick(4);check(protocol_fault&&!request_v,"start requires allocator grant");
 // A true fault-only alert returns its own result slot; accepting cancellation
 // must not fabricate a second slot return or release before all drains.
 reset_host();launch(90,999,81,2);recycle_credit();
 response({16'd90,6'd37,18'd999,13'd81,6'd0},2,0,1);j=ncr;
 @(negedge ck);cancel_release_v=1;cancel_release_tag={16'd90,6'd37,18'd999,13'd81,6'd0};cancel_release_gen=2;
 tick(1);@(negedge ck);cancel_release_v=0;tick(6);check(releases==0&&ncr==j,"cancel holds real drains without fake result credit");
 @(negedge ck);kv_drained=1;vm_drained=1;collective_drained=1;tick(5);check(releases==0,"cancel still needs HOST drain");
 @(negedge ck);host_drained=1;tick(6);check(releases==1&&ncr==j&&!protocol_fault,"fault-only cancel releases exact identity once");
 reset_host();launch(91,1000,82,1);recycle_credit();
 @(negedge ck);cancel_release_v=1;cancel_release_tag={16'd90,6'd37,18'd1000,13'd82,6'd0};cancel_release_gen=1;
 tick(1);@(negedge ck);cancel_release_v=0;kv_drained=1;vm_drained=1;collective_drained=1;host_drained=1;tick(6);
 check(protocol_fault&&releases==1,"stale cancellation cannot release live context");
 // Installed-image revocation prevents creation of an execution request.
 reset_host();image_ready=0;tick(3);j=nreq;
 @(negedge ck);shared_epoch_valid=1;shared_epoch=92;hc[38]=1;hc[35:18]=1001;hc[17:0]=83;
 tick(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;tick(8);
 check(protocol_fault&&nreq==j,"uninstalled image created native context");image_ready=1;
 // Even an empty-context certificate retains the terminal identity. An old
 // HC START arriving after that certificate cannot resurrect the retired job.
 reset_host();launch(93,1002,84,1);recycle_credit();response({16'd93,6'd37,18'd1002,13'd84,6'd0},1,1,0);
 @(negedge ck);kv_drained=1;vm_drained=1;collective_drained=1;host_drained=1;tick(5);
 @(negedge ck);cancel_release_v=1;cancel_release_tag={16'd93,6'd37,18'd1002,13'd84,6'd0};cancel_release_gen=1;
 tick(1);@(negedge ck);cancel_release_v=0;tick(5);j=nreq;
 @(negedge ck);shared_epoch_valid=1;shared_epoch=93;hc[38]=1;hc[37:36]=1;hc[35:18]=1002;hc[17:0]=84;
 tick(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;tick(8);
 check(protocol_fault&&nreq==j,"retired empty context resurrected by late HC");
 $display("PASS HOST_NATIVE_CANCEL checks=%0d requests=%0d credits=%0d",checks,nreq,ncr);$finish;
 end
 initial begin #10000;$fatal(1,"endpoint timeout");end
endmodule
