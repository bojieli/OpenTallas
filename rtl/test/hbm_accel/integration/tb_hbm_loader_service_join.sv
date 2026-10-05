`timescale 1ns/1ps
module tb_hbm_loader_service_join;
 import ot_hbm_r14_pkg::*;
 reg clk=0,rst=0;always #5 clk=~clk;
 reg req_v=0,req_we=0,owner_v=0,rsp_r=0;
 reg[36:0] addr=37'h1c00000000;reg[31:0] strb=0;reg[15:0] tag=16'h8123;
 reg[255:0] data=0;identity_t id;
 wire req_r,rsp_v,rsp_we,busy,fault;wire[15:0] rsp_tag;wire[255:0] rsp_data;
 wire[3:0] sqv,orr,cv,cwe,other_rv,other_cr;
 wire[1819:0] sq;reg[3:0] sr=0,ov=0,owe=0,oc=0,cr=0,other_cv=0,other_cwe=0;
 reg[1859:0] op=0;wire[767:0] ci;wire[47:0] ct;wire[19:0] cb;
 reg[767:0] other_ci=0;reg[47:0] other_ct=0;reg[19:0] other_cb=0;
 owned_t ret;request_t seen;
 ot_hbm_loader_service_join #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst),.req_v(req_v),.req_r(req_r),.req_addr(addr),.req_we(req_we),.req_data(data),.req_strb(strb),.req_tag(tag),
 .hardware_owner_valid(owner_v),.owner_identity(id),.loader_client(6'd16),.global_rank(7'd95),
 .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
 .stack_req_v(sqv),.stack_req_r(sr),.stack_req(sq),.owned_v(ov),.owned_r(orr),.owned(op),.owned_we(owe),.owned_credit(oc),.service_fault(4'b0),
 .other_owned_v(other_rv),.other_owned_r(4'hf),.other_owned(),.other_owned_we(),.other_owned_credit(),
 .credit_v(cv),.credit_r(cr),.credit_we(cwe),.credit_id(ci),.credit_tag(ct),.credit_beat(cb),
 .other_credit_v(other_cv),.other_credit_we(other_cwe),.other_credit_r(other_cr),.other_credit_id(other_ci),.other_credit_tag(other_ct),.other_credit_beat(other_cb),
 .busy(busy),.fault(fault));
 task step;begin @(posedge clk);#1;end endtask
 task send;begin
 @(negedge clk);req_v=1;#1;if(!req_r)$fatal(1,"actual request ready");step();@(negedge clk);req_v=0;
 end endtask
 task inject(input integer s,input bit is_credit,input bit is_write);begin
 @(negedge clk);op[s*465+:465]=ret;ov[s]=1;oc[s]=is_credit;owe[s]=is_write;
 end endtask
 initial begin
 id='0;id.stack=3;id.sector=34'h20000000;id.producer=64'h123456789abcdef;id.transport=32'h98765432;id.caller=tag;id.client=16;id.irs_slot=7;id.irs_serial=123;
 repeat(3)step();rst=1;sr=4'hf;
 @(negedge clk);req_v=1;repeat(2)step();if(req_r||sqv||busy)$fatal(1,"no fabricated hardware owner");
 @(negedge clk);owner_v=1;#1;seen=sq[3*455+:455];if(sqv!=8||seen.id!=id||seen.len!=1||seen.we)$fatal(1,"highaddr full identity stack3");
 step();@(negedge clk);req_v=0;
 ret='0;ret.id=id;ret.data=256'hfedcba98765432100123456789abcdef;ret.physical_tag=12'habc;
 inject(3,0,0);#1;if(!rsp_v||rsp_tag!=tag||rsp_data!=ret.data||rsp_we||orr[3])$fatal(1,"real payload with held receiver");
 repeat(2)step();if(!busy||!rsp_v)$fatal(1,"reply must hold");
 // Unrelated reverse traffic already stalled: loader cannot swap its tuple.
 @(negedge clk);other_cv[3]=1;other_ci[3*192+:192]=192'h333;other_ct[3*12+:12]=12'h333;step();
 @(negedge clk);rsp_r=1;step();@(negedge clk);ov=0;
 #1;if(!cv[3]||ct[3*12+:12]!=12'h333||!busy)$fatal(1,"retained other credit owner");
 cr[3]=1;step();@(negedge clk);other_cv=0;
 #1;if(!cv[3]||ct[3*12+:12]!=12'habc||ci[3*192+:192]!=id||cwe[3])$fatal(1,"full reverse tuple");
 step();@(negedge clk);cr=0;
 inject(3,1,0);#1;if(!orr[3]||rsp_v)$fatal(1,"grant not second reply");step();@(negedge clk);ov=0;oc=0;
 if(busy||fault)$fatal(1,"read reverse completes");
 // Physical write visibility comes from owned_we, not request acceptance.
 addr=37'h1000000200;tag=16'h0012;id.stack=2;id.sector=16;id.caller=tag;id.irs_serial=124;req_we=1;strb=32'hffffffff;data=256'hdeadbeef;
 send();if(rsp_v)$fatal(1,"no acceptance-as-writeACK");
 ret.id=id;ret.data=data;ret.physical_tag=12'h456;
 inject(2,0,1);#1;if(!rsp_v||!rsp_we||rsp_data!=data)$fatal(1,"actual visible write ACK");step();@(negedge clk);ov=0;cr[2]=1;
 #1;if(!cv[2]||!cwe[2])$fatal(1,"write reverse retained");step();@(negedge clk);cr=0;
 inject(2,1,0);step();@(negedge clk);ov=0;oc=0;
 if(busy||fault)$fatal(1,"write final grant");
 // Other actual clients remain routed through the shared service.
 ret.id.client=3;inject(2,0,0);#1;if(other_rv!=4||!orr[2]||rsp_v)$fatal(1,"shared other-client forwarding");step();@(negedge clk);ov=0;
 req_we=0;strb=0;id.irs_serial=125;send();ret.id=id;ret.id.producer=64'd99;ret.physical_tag=12'h777;
 inject(2,0,0);#1;if(orr[2]||rsp_v)$fatal(1,"foreign producer ACK");step();if(!fault||!busy)$fatal(1,"foreign identity must retain");
 $display("PASS_LOADER37_STACK3_PAYLOAD_WRITE_VISIBILITY_SHARED_CLIENTS_REVERSE_HOLD_FOREIGN_REFUSAL");$finish;
 end
endmodule
