`timescale 1ns/1ps
module tb_sysface_accepted_ctx;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,slot=0,rx_v=0,active=0;reg[547:0]record=0;
 wire accepted,valid,cf;wire[15:0]he;wire[58:0]ht;wire[1:0]hg;
 wire[128:0]ctx;wire ofault;
 qfd_host_native_context_rx receiver(.ck(ck),.rst_n(rst_n),.receive_slot(slot),.rx_v(rx_v),.rx_record(record),
 .program_begin_v(1'b0),.program_ready(1'b1),.installed_fusedcap(1'b1),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),.native_active(active),
 .accepted_v(accepted),.host_epoch_valid(valid),.host_epoch(he),.host_tag(ht),.host_gen(hg),
 .host_fusedcap(),.host_image_epoch(),.host_image_digest(),.fault(cf));
 qfd_sys_face_accepted_mu_ctx #(.MUT(MUT)) observer(.ck(ck),.rst_n(rst_n),.offer_slot(slot),.offer_v(rx_v),.offer_record(record),
 .host_accept_v(accepted),.host_epoch_valid(valid),.host_epoch(he),.host_tag(ht),.host_gen(hg),
 .program_ready(1'b1),.program_cap(1'b1),.program_fault(cf),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),.ctx_x(ctx),.fault(ofault));
 integer checks=0;
 task automatic check(input bit cond,input string why);
  checks++;if(!cond)begin $display("ACCEPTCTX_FAIL MUT%0d %s",MUT,why);$fatal(1);end
 endtask
 function automatic [547:0] rec(input integer u);
 reg[547:0]r;reg[58:0]t;
 begin t={14'h123,2'(u),6'd0,18'(1234+u),13'(100+u),6'd0};
 r=0;r[542:539]=12;r[538:533]=63;r[532:517]=t[58:43];r[141:78]=64'h123456789abcdef0;
 r[77:62]=16'hbeef;r[61]=1;r[60:59]=2;r[58:0]=t;return r;end
 endfunction
 task automatic idle;
 @(negedge ck);slot=0;rx_v=0;record=0;active=0;
 endtask
 task automatic reset;
 @(negedge ck);rst_n=0;slot=0;rx_v=0;active=0;record=0;
 repeat(3)@(negedge ck);check(!ctx[128]&&!accepted,"reset suppresses all acceptance/load");rst_n=1;
 endtask
 task automatic good(input integer u);
 reg[127:0]want;
 @(negedge ck);slot=1;rx_v=1;record=rec(u);
 @(negedge ck);check(accepted&&valid&&!ctx[128],"fresh receiver acceptance at offered E");
 record=rec(0); // Consecutive user0 restore accepts at E+1 NBA.
 @(negedge ck);check(accepted&&valid&&ht[44:43]==0,"user0 restore accepted");
 want=0;want[127:112]=16'h4d43;want[110:108]=3'b001<<(u-1);
 want[36*(u-1)+18+:18]=18'(1234+u);want[36*(u-1)+:18]=18'(100+u);
 check(ctx[128]&&ctx[127:0]==want&&!ofault&&!cf,"exact MU load E+1 before user0 restore");
 slot=0;rx_v=0;
 @(negedge ck);check(!ctx[128]&&!accepted,"acceptance and load are pulses");
 endtask
 task automatic bad_same_tag(input integer kind);
 // First leave this EXACT MU tag held valid, without a user0 restore.
 @(negedge ck);slot=1;rx_v=1;record=rec(2);
 @(negedge ck);check(accepted&&valid,"same-tag good precursor accepted");slot=0;rx_v=0;
 @(negedge ck);check(ctx[128],"same-tag precursor emits once");
 @(negedge ck);check(valid&&!accepted&&!ctx[128]&&ht[44:43]==2&&ht[36:19]==1236,"held identical accepted tag before rejection");
 slot=1;rx_v=1;record=rec(2);
 case(kind)
 0:record[77:62]^=1;
 1:record[141:78]^=1;
 2:record[61]=0;
 3:active=1;
 4:record[532:517]^=1;
 5:record[547]=1;
 6:record[37]=1;
 7:record[0]=1;
 endcase
 @(negedge ck);check(!accepted&&!valid&&cf,"rejected identical TAG must not retain accepted valid");
 slot=0;rx_v=0;active=0;
 @(negedge ck);check(!ctx[128]&&ofault,"rejected identical TAG never loads; sticky observer fault");
 endtask
 initial begin
  for(integer u=1;u<=3;u++)begin reset();good(u);good(u);end
  for(integer k=0;k<8;k++)begin reset();good(2);bad_same_tag(k);end
  reset();@(negedge ck);slot=1;rx_v=1;record=rec(1);
  @(negedge ck);rst_n=0;slot=0;rx_v=0;
  @(negedge ck);check(!ctx[128]&&!accepted,"reset cancels pending acceptance");
  $display("ACCEPTCTX_PASS MUT%0d checks%0d offerE ctxEplus1; actualbank timing still GI obligation",MUT,checks);$finish;
 end
endmodule
