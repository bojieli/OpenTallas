`timescale 1ns/1ps
module tb_kvn_ctx_ovl;
 parameter integer MUT_USER=0,MUT_STALE=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,reseed=0,adm_done=1;
 reg [551:0] head_record=0;
 reg [3:0] ovl_users=0,calrx=0;
 wire [58:0] identity;wire [1:0] generation;wire fault;
 qkd_kvn_ctx_ovl_rope #(.MUT_USER(MUT_USER),.MUT_STALE(MUT_STALE)) d
 (.ck(ck),.rst_n(rst_n),.head_record(head_record),.ovl_users(ovl_users),.calrx(calrx),.adm_done(adm_done),.reseed(reseed),
 .compiled_identity(identity),.compiled_generation(generation),.fault(fault));
 function automatic [60:0] own(input[15:0]ep,input[17:0]tok,input[12:0]pos);
 own={2'd1,ep,6'd0,tok,pos,6'd0};endfunction
 task automatic tick(input integer n);repeat(n)begin @(posedge ck);#1;end endtask
 task automatic reset;
 @(negedge ck);rst_n=0;head_record=0;calrx=0;tick(8);@(negedge ck);rst_n=1;tick(8);
 endtask
 task automatic send(input[1:0]u,input[60:0]o);
 @(negedge ck);ovl_users={u,u};head_record={5'd0,4'd12,6'd63,o[58:43],5'd0,451'd0,o,1'b1,1'b0,2'd0};
 tick(1);@(negedge ck);head_record=0;tick(4);
 endtask
 task automatic start(input[1:0]u,input bit seg);
 @(negedge ck);calrx={u,seg,1'b1};tick(1);@(negedge ck);calrx={u,seg,1'b0};tick(4);
 endtask
 task automatic expect_owner(input[60:0]o,input[5:0]stage);
 if(identity!=={o[58:43],stage,o[36:6],6'd0}||generation!==o[60:59]||fault)
  $fatal(1,"OWNER_FAIL got=%h gen=%d fault=%b expected=%h",identity,generation,fault,{o[58:43],stage,o[36:6],6'd0});
 endtask
 integer u;reg[60:0]o;
 initial begin
 reset();
 for(u=0;u<4;u=u+1)begin o=own(16'(64+u),18'(10+u),13'(100+u));send(2'(u),o);start(2'(u),1);expect_owner(o,1);end
 for(u=0;u<4;u=u+1)begin o=own(16'(64+u),18'(10+u),13'(100+u));start(2'(u),0);expect_owner(o,2);end
 o=own(16'd68,18'd20,13'd101);send(0,o);start(0,1);expect_owner(o,1);
 send(0,own(16'd64,18'd10,13'd100));if(!fault)$fatal(1,"STALE_TOKEN_NOT_REJECTED");
 reset();send(1,own(16'd64,18'd10,13'd100));if(!fault)$fatal(1,"WRONG_USER_NOT_REJECTED");
 reset();send(0,own(16'd64,18'd10,13'd100));send(0,own(16'd64,18'd11,13'd100));if(!fault)$fatal(1,"SAME_EPOCH_TOKEN_NOT_REJECTED");
 $display("KVN_CTX_OVL_PASS users4 stages2 advance stale wronguser sameepoch");$finish;
 end
endmodule
