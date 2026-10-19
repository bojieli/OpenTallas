`timescale 1ns/1ps
module tb_sysface_accepted_identity;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,slot=0,rxv=0,active=0,role=0;reg[1:0]role_user=0;reg[547:0]record=0;
 wire av,hv,rf,mf,df,ov;wire[15:0]he,me,de;wire[58:0]ht;wire[1:0]hg,mu,du;
 wire[17:0]atok;wire[1:0]agen;
 wire[128:0]ctx,defctx,oldctx;wire defv,oldf;
 qfd_host_native_context_rx rx(.ck(ck),.rst_n(rst_n),.receive_slot(slot),.rx_v(rxv),.rx_record(record),
 .program_begin_v(1'b0),.program_ready(1'b1),.installed_fusedcap(1'b1),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),.native_active(active),
 .accepted_v(av),.host_epoch_valid(hv),.host_epoch(he),.host_tag(ht),.host_gen(hg),.host_fusedcap(),.host_image_epoch(),.host_image_digest(),.fault(rf));
 `define PINS .ck(ck),.rst_n(rst_n),.offer_slot(slot),.offer_v(rxv),.offer_record(record),.host_accept_v(av),.host_epoch_valid(hv),.host_epoch(he),.host_tag(ht),.host_gen(hg),.program_ready(1'b1),.program_cap(1'b1),.program_fault(rf),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0)
 qfd_sys_face_accepted_mu_identity #(.EPOCH_EXPORT(1),.MUT(MUT)) dut(`PINS,.epoch_slot(role),.epoch_user(role_user),.accepted_epoch_v(ov),.accepted_epoch_user(mu),.accepted_epoch(me),.accepted_token(atok),.accepted_generation(agen),.ctx_x(ctx),.fault(mf));
 qfd_sys_face_accepted_mu_identity defdut(`PINS,.epoch_slot(role),.epoch_user(role_user),.accepted_epoch_v(defv),.accepted_epoch_user(du),.accepted_epoch(de),.ctx_x(defctx),.fault(df));
 qfd_sys_face_accepted_mu_ctx refdut(`PINS,.ctx_x(oldctx),.fault(oldf));
 integer checks=0;
 task automatic check(input bit cond,input string why);
 checks++;if(!cond)begin $display("ACCEPTIDENTITY_FAIL MUT%0d %s",MUT,why);$fatal(1);end
 endtask
 always @(negedge ck)if(rst_n)begin
  check(!defv,"default off never emits epoch");check(defctx==oldctx&&df==oldf,"defaultoff exactly preserves legacy context");
  check(ctx==oldctx,"epoch extension preserves context folding");
 end
 function automatic[547:0]rec(input integer u);
 reg[547:0]r;reg[58:0]t;
 begin t={14'h123,2'(u),6'd0,18'(1234+u),13'(100+u),6'd0};r=0;r[542:539]=12;r[538:533]=63;r[532:517]=t[58:43];r[141:78]=64'h123456789abcdef0;r[77:62]=16'hbeef;r[61]=1;r[60:59]=2;r[58:0]=t;return r;end
 endfunction
 task automatic reset;
 @(negedge ck);rst_n=0;slot=0;rxv=0;active=0;role=0;record=0;
 repeat(3)@(negedge ck);check(!ov&&!ctx[128],"reset suppresses context/epoch");rst_n=1;
 endtask
 task automatic good(input integer u);
 @(negedge ck);slot=1;rxv=1;record=rec(u);role=1;role_user=2'(u);
 @(negedge ck);check(av&&hv&&!ov,"fresh actual receiver accepts before metadata");
 record=rec(0);role=0; // ordinary user0 restore is explicitly outside the epoch role
 @(negedge ck);check(ov&&mu==u&&me==16'((14'h123<<2)|u),"role-bound user/epoch sample E+2");check(atok==18'(1234+u)&&agen==2,"authenticated selected token/generation");check(!mf&&!rf,"accepted record no fault");
 slot=0;rxv=0;role=0;
 @(negedge ck);check(!ov,"ordinary user0 restore does not seed a pending epoch");
 endtask
 task automatic bad(input integer k);
 // Hold an identical accepted tag, then reject its next offer.
 @(negedge ck);slot=1;rxv=1;record=rec(2);role=1;role_user=2;
 @(negedge ck);check(av,"precursor accepted");slot=0;rxv=0;role=0;
 @(negedge ck);check(ov&&mu==2,"precursor emits once");
 @(negedge ck);check(hv&&!av&&!ov,"held accepted tag is not a fresh event");
 slot=1;rxv=1;record=rec(2);role=1;
 case(k)
 0:record[77:62]^=1;1:record[141:78]^=1;2:record[61]=0;3:active=1;
 4:record[532:517]^=1;5:record[547]=1;6:record[37]=1;7:record[0]=1;
 endcase
 @(negedge ck);check(!av&&!hv&&rf,"same-tag mutation rejected by actual receiver");slot=0;rxv=0;active=0;role=0;
 @(negedge ck);check(!ov&&!ctx[128],"rejected record never emits epoch/context");
 endtask
 initial begin
  for(integer u=0;u<4;u++)begin reset();good(u);good(u);end
  for(integer k=0;k<8;k++)begin reset();good(2);bad(k);end
  reset();@(negedge ck);slot=1;rxv=1;role=1;role_user=3;record=rec(2);
  repeat(2)@(negedge ck);check(!ov&&mf,"wrong static role user faults without epoch publication");
  reset();@(negedge ck);slot=1;rxv=1;role=1;role_user=1;record=rec(1);
  @(negedge ck);rst_n=0;slot=0;rxv=0;role=0;
  @(negedge ck);check(!ov,"reset cancels pending epoch metadata");
  $display("ACCEPTIDENTITY_PASS MUT%0d checks%0d all4users/reuse/restore/8rejects/staticrole/reset",MUT,checks);$finish;
 end
endmodule
