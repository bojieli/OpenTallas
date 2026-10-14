`timescale 1ns/1ps
module tb_qkd_host_native_token_endpoint;
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
 qkd_host_native_token_endpoint #(.ENABLE_NATIVE(1),.MUT(MUT))d(.*);
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
 $display("PASS HOST_NATIVE_TOKEN_ENDPOINT checks=%0d requests=%0d credits=%0d TAG59=exact",checks,nreq,ncr);$finish;
 end
 initial begin #10000;$fatal(1,"endpoint timeout");end
endmodule
