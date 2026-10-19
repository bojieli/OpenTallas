`timescale 1ns/1ps
module tb_component;
 `include "d2d_cal_image_mu.svh"
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[142:0] boot_pr=0;reg[3:0] target=0;
 reg ready=0,reload=0,go=0,halt=0;reg[15:0] ep=16'h1234;
 reg[15:0] drop=0;reg half=0,base=0,meta=0,valid_bad=0,wrong_ep=0;
 reg[7:0] start_bad=0;reg manual_status=0,manual_bad=0;
 integer mode=0,cycle=0,errors=0,compares=0,first_token=-1,status_cycle=-1,events=0,token_count=0,last_token=-1;reg[35:0] layer_seen=0;reg poison_edge=0;integer poison_checks=0;
 wire[127:0] bo[0:2];wire[31:0] co[0:2];wire[2:0] pr,pp,bf,df,te,re,cs,seg;
 wire[15:0] pe[0:2];wire[63:0] seen[0:2];wire[1:0] bases[0:2],firsts[0:2];
 wire[2:0] tp[0:2],rp[0:2];wire[3:0] tk[0:2],rk[0:2];wire[4:0] tb[0:2],rb[0:2];wire[5:0] layer[0:2];
 wire[2:0] fresh,sfault;
 qkd_d2d_firstepoch_component #(.ORIGINAL(1),.ENABLE_FIRST_EPOCH_GUARD(0)) d0(
 .ck(ck),.rst_n(rst_n),.boot_pr(boot_pr),.boot_image_target(target),.boot_image_ready(ready),
 .boot_image_fault(1'b0),.boot_image_epoch(ep),.reload(reload),.epoch_go(go),.halt(halt),.epoch_id(ep),.epoch_valid(1'b1),
 .drop_word(drop),.corrupt_half(half),.corrupt_base(base),.corrupt_epoch(meta),.corrupt_valid(valid_bad),
 .corrupt_start(start_bad),.wrong_start_epoch(wrong_ep),.original_outputs(bo[0]),.calendar_outputs(co[0]),
 .pair_ready(pr[0]),.pair_poison(pp[0]),.pair_epoch(pe[0]),.seen_pair(seen[0]),.base_pair(bases[0]),.first_pair(firsts[0]),
 .dispatcher_fault(df[0]),.bc_fault(bf[0]),.tx_event(te[0]),.rx_event(re[0]),
 .tx_port(tp[0]),.rx_port(rp[0]),.tx_kind(tk[0]),.rx_kind(rk[0]),.tx_beat(tb[0]),.rx_beat(rb[0]),
 .cal_start_o(cs[0]),.cal_seg_o(seg[0]),.layer_o(layer[0]));
 wire status_event0=re[0] && rp[0]==2 && rk[0]==15;
 wire[547:0] payload0={5'd0,4'd15,6'd63,ep,5'd0,356'd0,156'h15};
 ot_qwen_d2d_status_rx_sf sr0(.ck(ck),.rst_n(rst_n),.epoch16(ep),.rx_event(status_event0),.rx_slot(status_event0),
 .ev_c({10{status_event0}}),.rs_c({10{status_event0}}),.rx_payload(payload0),.epoch_begin(go),
 .status_fresh(fresh[0]),.fault(sfault[0]));
 qkd_d2d_firstepoch_component #(.ORIGINAL(0),.ENABLE_FIRST_EPOCH_GUARD(0)) d1(
 .ck(ck),.rst_n(rst_n),.boot_pr(boot_pr),.boot_image_target(target),.boot_image_ready(ready),
 .boot_image_fault(1'b0),.boot_image_epoch(ep),.reload(reload),.epoch_go(go),.halt(halt),.epoch_id(ep),.epoch_valid(1'b1),
 .drop_word(drop),.corrupt_half(half),.corrupt_base(base),.corrupt_epoch(meta),.corrupt_valid(valid_bad),
 .corrupt_start(start_bad),.wrong_start_epoch(wrong_ep),.original_outputs(bo[1]),.calendar_outputs(co[1]),
 .pair_ready(pr[1]),.pair_poison(pp[1]),.pair_epoch(pe[1]),.seen_pair(seen[1]),.base_pair(bases[1]),.first_pair(firsts[1]),
 .dispatcher_fault(df[1]),.bc_fault(bf[1]),.tx_event(te[1]),.rx_event(re[1]),
 .tx_port(tp[1]),.rx_port(rp[1]),.tx_kind(tk[1]),.rx_kind(rk[1]),.tx_beat(tb[1]),.rx_beat(rb[1]),
 .cal_start_o(cs[1]),.cal_seg_o(seg[1]),.layer_o(layer[1]));
 wire status_event1=re[1] && rp[1]==2 && rk[1]==15;
 wire[547:0] payload1={5'd0,4'd15,6'd63,ep,5'd0,356'd0,156'h15};
 ot_qwen_d2d_status_rx_sf sr1(.ck(ck),.rst_n(rst_n),.epoch16(ep),.rx_event(status_event1),.rx_slot(status_event1),
 .ev_c({10{status_event1}}),.rs_c({10{status_event1}}),.rx_payload(payload1),.epoch_begin(go),
 .status_fresh(fresh[1]),.fault(sfault[1]));
 qkd_d2d_firstepoch_component #(.ORIGINAL(0),.ENABLE_FIRST_EPOCH_GUARD(1)) d2(
 .ck(ck),.rst_n(rst_n),.boot_pr(boot_pr),.boot_image_target(target),.boot_image_ready(ready),
 .boot_image_fault(1'b0),.boot_image_epoch(ep),.reload(reload),.epoch_go(go),.halt(halt),.epoch_id(ep),.epoch_valid(1'b1),
 .drop_word(drop),.corrupt_half(half),.corrupt_base(base),.corrupt_epoch(meta),.corrupt_valid(valid_bad),
 .corrupt_start(start_bad),.wrong_start_epoch(wrong_ep),.original_outputs(bo[2]),.calendar_outputs(co[2]),
 .pair_ready(pr[2]),.pair_poison(pp[2]),.pair_epoch(pe[2]),.seen_pair(seen[2]),.base_pair(bases[2]),.first_pair(firsts[2]),
 .dispatcher_fault(df[2]),.bc_fault(bf[2]),.tx_event(te[2]),.rx_event(re[2]),
 .tx_port(tp[2]),.rx_port(rp[2]),.tx_kind(tk[2]),.rx_kind(rk[2]),.tx_beat(tb[2]),.rx_beat(rb[2]),
 .cal_start_o(cs[2]),.cal_seg_o(seg[2]),.layer_o(layer[2]));
 wire actual_status2=re[2] && rp[2]==2 && rk[2]==15;
 wire status_event2=actual_status2 || manual_status;
 wire[547:0] payload2={5'd0,4'd15,6'd63,(ep ^ ((mode==14 || manual_bad) ? 16'd1 : 16'd0)),5'd0,356'd0,156'h15};
 ot_qwen_d2d_status_rx_sf sr2(.ck(ck),.rst_n(rst_n),.epoch16(ep),.rx_event(status_event2),.rx_slot(status_event2),
 .ev_c({10{status_event2}}),.rs_c({10{status_event2}}),.rx_payload(payload2),.epoch_begin(go),
 .status_fresh(fresh[2]),.fault(sfault[2]));

 task tick;begin @(negedge ck);end endtask
 task check(input condition,input[255:0] msg);begin if(condition!==1'b1)begin errors=errors+1;$display("CHECK_FAIL mode=%0d cycle=%0d %0s",mode,cycle,msg);end end endtask
 function integer nwords(input integer t);
 case(t)1:nwords=327;2:nwords=181;3:nwords=4;4,5:nwords=192;default:nwords=1024;endcase
 endfunction
 task target_image(input integer t,input integer n);
 integer a;reg[31:0] w;
 begin
 target=t;ready=0;boot_pr=0;tick;
 for(a=0;a<n;a=a+1)begin
 w=0;
 if(t==11)begin
 if(a<64) w=a%2 ? D2D_CAL_K_RX_IMG[32*(a/2)+:32] : D2D_CAL_K_TX_IMG[32*(a/2)+:32];
 else w=a==64 ? D2D_CAL_K_TX_SEG2 : D2D_CAL_K_RX_SEG2;
 end
 boot_pr=0;boot_pr[74]=1;boot_pr[73:64]=a;boot_pr[31:0]=w;tick;
 end
 boot_pr=0;ready=1;tick;tick;ready=0;tick;
 end endtask
 always @(posedge ck)begin
 cycle=cycle+1;
 poison_edge=d2.bc_generation_poison;
 // Anchor at the actual calendar consumer edge (old SF pin FF values).
 if(rst_n && cs[2] && layer[2]<36)layer_seen[layer[2]]=1;
 if(rst_n && cs[2] && seg[2] && layer[2]==0)begin
 if(first_token<0)first_token=cycle;
 if(last_token>=0)check(cycle-last_token==D2D_TOKEN_PERIOD,"ordinary token period unchanged");
 last_token=cycle;token_count=token_count+1;$display("TOKEN_CONSUMER cycle=%0d",cycle);end
 #1;
 if(rst_n && mode==17 && poison_edge)begin
 poison_checks=poison_checks+1;
 check(!re[2]&&!te[2],"BC poison vetoes actual event");
 check(d2.g_tx_private.u_cal.running===0 && d2.g_rx_private.u_cal.running===0,"BC poison halts both calendars");
 end
 if(rst_n)begin
 compares=compares+1;
 if(bo[0]!==bo[1] || co[0]!==co[1]) begin
 if(errors<8)$display("DISABLED_MISMATCH c=%0d bo=%h/%h co=%h/%h",cycle,bo[0],bo[1],co[0],co[1]);errors=errors+1;
 end
 if((mode==0 || mode==16) && (bo[0]!==bo[2] || co[0]!==co[2]))begin
 if(errors<8)$display("HEALTHY_MISMATCH c=%0d bo=%h/%h co=%h/%h ready=%b poison=%b",cycle,bo[0],bo[2],co[0],co[2],pr,pp);errors=errors+1;
 end

 if(re[2])begin
 events=events+1;
 if(rp[2]==2 && rk[2]==15 && status_cycle<0)begin status_cycle=cycle;$display("FIRST_STATUS cycle=%0d token_delta=%0d",cycle,cycle-first_token);end
 end
 end
 end
 // Corrupt actual SF accepted metadata only after an initial valid epoch was established.
 always @(negedge ck)begin
 if(mode==5)meta=(d2.qa==6'd20 && (d2.qt||d2.qr));
 if(mode==6)valid_bad=(d2.qa==6'd20 && (d2.qt||d2.qr));
 if(mode==12)begin
 meta=0;
 if(d2.qa==6'd20 && (d2.qt||d2.qr))valid_bad=1'bx;else valid_bad=0;
 end
 end
 integer t;
 initial begin
 if(!$value$plusargs("MODE=%d",mode))mode=0;
 repeat(5)tick;rst_n=1;
 if(mode==1)drop=16'h801f;
 if(mode==2)drop=16'h8060;
 if(mode==3)half=1;
 if(mode==4)base=1;
 if(mode==7)wrong_ep=1;
 for(t=1;t<=9;t=t+1)target_image(t,nwords(t));
 if(mode==8)begin go=1;tick;go=0;end
 target_image(11,66);
 if(mode==10)begin go=1;tick;go=0;end
 repeat(16)tick;
 $display("RECEIPT mode=%0d ready=%b poison=%b seen=%h base=%b",mode,pr,pp,seen[2],bases[2]);
 if(mode==0 || mode==16 || mode==17)begin check(pr[2],"healthy pair receipt");check(!pp[2],"healthy pair not poison");end
 if(mode==9)begin reload=1;tick;reload=0;repeat(5)tick;check(!pr[2],"reload invalidates both receipts");end
 if(mode==13)begin start_bad=8'h22;tick;start_bad=0;end
 if(mode==11)begin rst_n=0;repeat(3)tick;rst_n=1;repeat(5)tick;check(!pr[2],"reset invalidates both receipts");end
 go=1;tick;go=0;
 if(mode==17)begin
 wait(first_token>0);repeat(20)tick;
 check(d2.g_tx_private.u_cal.running || d2.g_rx_private.u_cal.running,"fault trigger during actual run");
 go=1;tick;go=0;repeat(100)tick;
 end else repeat(mode==16 ? D2D_TOKEN_PERIOD+2400 : 2400)tick;
 if(mode==15)begin
 check(fresh[2] && !sfault[2],"receiver healthy before idle mutant");
 repeat(100)tick;manual_bad=1;manual_status=1;tick;manual_status=0;tick;
 check(sfault[2],"malformed STATUS after idle detected");
 end
 if(mode==17)begin
 check(poison_checks>0,"real BC poison witnessed");check(bf[2]&&pp[2],"BC fault sticky through pair");
 end else if(mode==14 || mode==15)begin
 check(events>0,"real calendar STATUS source live");check(sfault[2],"malformed receiver sticky fault");
 check(!bf[2]&&!pp[2],"consumer mutant calendar unaffected");
 end else if(mode==0 || mode==16)begin
 check(!bf[2]&&!pp[2]&&!sfault[2],"healthy fault-free");
 check(first_token>0,"real token start");check(status_cycle-first_token==15,"first STATUS token plus15");
 check(fresh[2],"unchanged STATUS receiver accepted");check(firsts[2]==3,"both firsts consumed");
 if(mode==16)begin check(token_count>=2,"second ordinary token reached");check(&layer_seen,"all36 layer start anchors");end
 end else begin
 check(bf[2]||pp[2],"negative sticky veto");check(events==0,"negative no calendar event");
 check(first_token<0,"negative no token branch");check(!fresh[2],"negative no STATUS accepted");
 check(d2.g_tx_private.u_cal.running===0 && d2.g_rx_private.u_cal.running===0,"both run branches unchanged");
 check(d2.g_tx_private.u_cal.pc0===32'd1 && d2.g_rx_private.u_cal.pc0===32'd1,"both pointer branches unchanged");
 check(d2.g_tx_private.u_cal.cnt===0 && d2.g_rx_private.u_cal.cnt===0,"both counter branches unchanged");
 check(d2.g_tx_private.u_cal.cur===0 && d2.g_rx_private.u_cal.cur===0,"both current words unchanged");
 check(d2.g_tx_private.u_cal.rep===0 && d2.g_rx_private.u_cal.rep===0 && d2.g_tx_private.u_cal.bcur===0 && d2.g_rx_private.u_cal.bcur===0,"both repeat/beat unchanged");
 check(d2.g_tx_private.u_cal.pc1===32'd1 && d2.g_rx_private.u_cal.pc1===32'd1 && d2.g_tx_private.u_cal.ph===0 && d2.g_rx_private.u_cal.ph===0,"both pointer copies unchanged");
 check(d2.g_tx_private.u_cal.run_c===0 && d2.g_rx_private.u_cal.run_c===0,"both run copies unchanged");
 end
 $display("COMPONENT_RESULT mode=%0d compares=%0d events=%0d errors=%0d",mode,compares,events,errors);
 if(errors)$fatal(1,"component failed");$finish;
 end
endmodule
