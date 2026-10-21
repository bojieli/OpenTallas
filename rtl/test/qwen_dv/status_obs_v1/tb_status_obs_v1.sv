`timescale 1ns/1ps
module tb_status_obs_v1 #(parameter integer MUT=0);
 reg ck=0;always #0.5 ck=~ck;
 reg [5:0] rh=0; reg rt=0; reg[2:0] orn=0; reg rrx=0;
 reg[15:0] epoch=16'h1234;reg[61:0]cx=0;reg[46:0]rr=0;reg[59:0]nn=0;
 wire[59:0] injected_native=(MUT==1)?{nn[59],cx[58:0]}:nn;
 reg slot=0;reg[21:0]rv=0;wire tv,tf,lv,lf;wire[547:0]tp,legacy;
 ot_qwen_d2d_status_tx_s7_obs1 u_tx(.ck(ck),.rst_h_k(rh),.rst_t(rt),.epoch16(epoch),
 .vm_drained(1'b1),.collective_drained(1'b1),.collective_busy(1'b0),.crom_fault(1'b0),.execution_active(1'b1),.admit_ready(1'b1),
 .result_v_k(rv),.result_done(1'b1),.result_fault(1'b0),.result_cause(4'd0),.result_tag(59'h123),.result_gen(2'd2),.result_token(18'd19),.result_value(32'h3f800000),.result_cycles(32'd100),
 .status_event_valid(slot),.status_port_match(1'b1),.tx_slot_canonical(slot),.tx_kind(4'd15),
 .obs_rst_n(orn),.obs_ctx(cx),.obs_res(rr),.obs_native(injected_native),.tx_valid(tv),.tx_payload(tp),.fault(tf));
 ot_qwen_d2d_status_tx_s7 u_legacy(.ck(ck),.rst_h_k(rh),.rst_t(rt),.epoch16(epoch),
 .vm_drained(1'b1),.collective_drained(1'b1),.collective_busy(1'b0),.crom_fault(1'b0),.execution_active(1'b1),.admit_ready(1'b1),
 .result_v_k(rv),.result_done(1'b1),.result_fault(1'b0),.result_cause(4'd0),.result_tag(59'h123),.result_gen(2'd2),.result_token(18'd19),.result_value(32'h3f800000),.result_cycles(32'd100),
 .status_event_valid(slot),.status_port_match(1'b1),.tx_slot_canonical(slot),.tx_kind(4'd15),.tx_valid(lv),.tx_payload(legacy),.fault(lf));
 reg re=0,rs=0;reg[547:0]payload=0;reg eb=0;
 wire[23:0]hk;wire good;wire[207:0]ox;wire ov;wire[15:0]oe;wire rf;
 ot_qwen_status_obs_v1_valid valid(.x(payload[511:304]),.good(good));
 assign hk={24{payload[547:543]==0&&payload[542:539]==15&&payload[538:533]==63&&payload[516:512]==0&&payload[303:156]==0&&good}};
 wire vd,cd,cb,cf,ea,ar,sf,orv,rd,er;wire[3:0]rc;wire[58:0]tag;wire[1:0]gen;wire[17:0]tok;wire[31:0]val,cyc;
 ot_qwen_d2d_status_rx_sfm3_obs1 #(.NG(24)) u_rx(.ck(ck),.rst_n(rrx),.epoch16(epoch),.rx_event(re),.rx_slot(rs),.ev_c({24{re}}),.rs_c({24{rs}}),.hk_c(hk),.he_c({24{payload[532:517]}}),.rx_payload(payload),
 .vm_drained(vd),.collective_drained(cd),.collective_busy(cb),.crom_fault(cf),.execution_active(ea),.admit_ready(ar),.status_fresh(sf),.result_v(orv),.result_done(rd),.result_fault(er),.result_cause(rc),.result_tag(tag),.result_gen(gen),.result_token(tok),.result_value(val),.result_cycles(cyc),.epoch_begin(eb),.status_obs_v(ov),.status_obs_epoch16(oe),.status_obs_payload(ox),.fault(rf));
 integer checks=0;integer bad=0;reg[547:0]saved;
 function automatic[58:0] mk(input[13:0]seq,input[1:0]user,input[17:0]token);
 mk={seq,user,6'd37,token,13'd7,2'd1,4'd0};endfunction
 task chk(input logic yes,input string why);begin checks++;if(!yes)begin bad++;$display("OBS_BAD %s",why);end end endtask
 task tick;begin @(posedge ck);#0.1;end endtask
 task release_reset;begin @(negedge ck);rh=6'h3f;rt=1;orn=7;rrx=1;tick;end endtask
 task publish;begin @(negedge ck);slot=1;tick;chk(tv&&lv,"TX valid same edge");chk(tp[547:512]==legacy[547:512]&&tp[155:0]==legacy[155:0],"legacy header/low156 identical");saved=tp;@(negedge ck);slot=0;cx[61]=0;rr[46]=0;nn[59]=0;end endtask
 task accept_saved;begin payload=saved;re=1;rs=1;tick;chk(ov&&!rf,"accepted STATUS observation");chk(oe==epoch&&ox==saved[511:304],"payload and receipt epoch aligned");@(negedge ck);re=0;rs=0;end endtask
 task rx_reset;begin @(negedge ck);rrx=0;re=0;rs=0;tick;@(negedge ck);rrx=1;end endtask
 task reject_saved(input integer bitno,input string why);begin rx_reset;saved[bitno]=~saved[bitno];payload=saved;re=1;rs=1;tick;chk(rf&&!ov,why);@(negedge ck);re=0;rs=0;saved[bitno]=~saved[bitno];end endtask
 initial begin
 repeat(3)tick;release_reset;
 publish;accept_saved;chk(ox[203:2]==0,"canonical unseen identities zero");chk(ox[207:204]==1,"schema version1");
 @(negedge ck);cx={1'b1,2'd2,mk(14'd17,2'd2,18'd91)};rr={1'b1,2'd0,(44'd1<<42)|(44'd19<<18)};nn={1'b1,mk(14'd31,2'd3,18'd117)};
 // Event and STATUS slot same edge: include true event now, without a new frame or capture edge.
 slot=1;rv={22{1'b1}};tick;chk(tv,"same-edge event valid");saved=tp;
 @(negedge ck);slot=0;rv=0;cx[61]=0;rr[46]=0;nn[59]=0;accept_saved;
 chk(ox[203]&&ox[202:201]==2&&ox[200:142]==mk(17,2,91),"true context identity");
 chk(ox[141]&&ox[140:139]==0&&ox[137],"actual RESULT h_start identity");
 chk(ox[94]&&ox[92:61]==1&&ox[60:2]==mk(31,3,117),"actual completed owner not latest context");
 chk(ox[60:45]!=epoch,"operation epoch distinct from receipt epoch");
 // Repeated TX never clears an epoch-owned cumulative count or loses held identity.
 publish;accept_saved;chk(ox[92:61]==1,"TX does not clear completion count");
 // Link epoch reset without receipt-epoch change preserves count (only baseline codec reset).
 @(negedge ck);rh=0;rt=0;tick;@(negedge ck);rh=63;rt=1;publish;accept_saved;chk(ox[92:61]==1,"link epoch reset preserves receipt-window count");
 // A receipt epoch fence clears seen state; coincident native event counts as 1 in the new window.
 @(negedge ck);epoch=16'h1235;nn={1'b1,mk(14'd32,2'd1,18'd118)};slot=1;tick;saved=tp;
 @(negedge ck);slot=0;nn[59]=0;accept_saved;chk(!ox[203]&&!ox[141]&&ox[92:61]==1,"epoch fence and coincident completion");chk(ox[60:2]==mk(32,1,118),"new-window true completion identity");
 // Strict grammar rejection; preserve the actual low156 result grammar.
 reject_saved(511,"unknown version rejected");reject_saved(200,"reserved gap rejected");reject_saved(304,"extension reserved bits rejected");
 rx_reset;publish;accept_saved;
 // Overflow boundary seeded only in the testbench: production counter width remains exactly32.
 @(negedge ck);u_tx.u_obs.count_lo=16'hfffe;u_tx.u_obs.count_hi=16'hffff;nn={1'b1,mk(33,1,119)};slot=1;tick;saved=tp;
 @(negedge ck);slot=0;nn[59]=0;accept_saved;chk(ox[92:61]==32'hffffffff&&!ox[93],"last representable completion");
 @(negedge ck);nn[59]=1;slot=1;tick;saved=tp;chk(tf,"overflow raises real codec fault");
 @(negedge ck);slot=0;nn[59]=0;accept_saved;chk(ox[92:61]==32'hffffffff&&ox[93],"saturating counter and sticky overflow");
 @(negedge ck);epoch++;slot=1;tick;saved=tp;@(negedge ck);slot=0;accept_saved;chk(!ox[94]&&!ox[93]&&ox[92:61]==0,"epoch fence clears count/overflow");
 if(bad==0)$display("STATUS_OBS_V1 PASS MUT=%0d checks=%0d",MUT,checks);else $display("STATUS_OBS_V1 FAIL MUT=%0d checks=%0d bad=%0d",MUT,checks,bad);
 $finish;
 end
endmodule
