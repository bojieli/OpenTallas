`timescale 1ns/1ps
module tb;
 import ot_gpu_w6_secded_pkg::*;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,stop=0,start_v=0;reg[20:0]pos=1048575,token=128799;reg[2:0]g=0;
 wire sr;wire[24:0]lease;reg av=0;reg[24:0]akey=0;reg[2:0]ag=0;wire ar;
 reg ovready=0;reg[24:0]ack=0;wire ov,ad,aa;wire[2:0]a;wire[3:0]n;wire[20:0]bonus;wire[167:0]s,t;
 reg fv=0,frearm=0;reg[24:0]fkey=0;reg[5:0]receipts=63;wire fr,fault,ce;
 reg[1:0]pv=0,pfinish=0,ctl=0;reg[49:0]pk=0;reg[5:0]ps=0;reg[41:0]pt=0;
 wire[1:0]pr,rv,rr;wire[49:0]rk;wire[5:0]rs;wire[41:0]rt;wire cb,tr,mr;
 assign rr={mr,tr}&ctl;
 ot_hdc_mtp_source_holders #(.ENABLE(1)) holder(.clk(clk),.rst_n(rst_n),.quarantine(fault),
 .p_v(pv),.p_finish(pfinish),.p_ready(pr),.p_lease(pk),.p_slot(ps),.p_token(pt),
 .req_v(rv),.req_ready(rr),.req_lease(rk),.req_slot(rs),.req_token(rt),.caller_bad(cb));
 ot_hdc_mtp_accept_guarded #(.NSLOT(8),.NW(21),.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.admission_stop(stop),.caller_bad(cb),
 .start_v(start_v),.start_pos(pos),.start_tok(token),.start_g(g),.start_ready(sr),
 .tokx_v(rv[0]&ctl[0]),.tokx_lease(rk[0+:25]),.tokx_slot(rs[0+:3]),.tokx_tok(rt[0+:21]),.tokx_ready(tr),
 .amax_v(rv[1]&ctl[1]),.amax_lease(rk[25+:25]),.amax_slot(rs[3+:3]),.amax_tok(rt[21+:21]),.amax_ready(mr),
 .accept_v(av),.accept_lease(akey),.accept_g(ag),.accept_ready(ar),.stok(s),.ttok(t),.out_v(ov),.acc_done(ad),.acc_any(aa),
 .acc_a(a),.n_emit(n),.bonus(bonus),.lease(lease),.out_ready(ovready),.ack_lease(ack),
 .fence_v(fv),.fence_lease(fkey),.fence_receipts(receipts),.fence_rearm(frearm),.fence_ready(fr),.fault(fault),.corrected(ce));
 wire off_sr,off_tr,off_mr,off_ar,off_fr,off_v,off_fault;
 ot_hdc_mtp_accept_guarded disabled(.clk(clk),.rst_n(rst_n),.admission_stop(1'b0),.caller_bad(1'b1),
 .start_v(1'b1),.start_pos(21'd0),.start_tok(21'd129280),.start_g(3'd7),.start_ready(off_sr),
 .tokx_v(1'b1),.tokx_lease(25'd0),.tokx_slot(3'd0),.tokx_tok(21'd0),.tokx_ready(off_tr),
 .amax_v(1'b1),.amax_lease(25'd0),.amax_slot(3'd0),.amax_tok(21'd0),.amax_ready(off_mr),
 .accept_v(1'b1),.accept_lease(25'd0),.accept_g(3'd0),.accept_ready(off_ar),
 .stok(),.ttok(),.out_v(off_v),.acc_done(),.acc_any(),.acc_a(),.n_emit(),.bonus(),.lease(),
 .out_ready(1'b1),.ack_lease(25'd0),.fence_v(1'b1),.fence_lease(25'd0),.fence_receipts(6'd0),.fence_rearm(1'b1),.fence_ready(off_fr),.fault(off_fault),.corrected());
 // Literal source greedy accept is the semantic oracle, full NW21/NSLOT8.
 reg gs=0,gt=0,gm=0,ga=0;reg[2:0]gslot=0;reg[20:0]gtok=0;wire[167:0]gst,gtt;
 wire gd,gany;wire[2:0]gout;wire[3:0]gn;wire[20:0]gb;
 ot_hdc_accept #(.NSLOT(8),.NW(21)) golden(.clk(clk),.rst_n(rst_n),.start_v(gs),.start_tok(token),
 .tokx_v(gt),.tokx_slot(gslot),.tokx_tok(gtok),.amax_v(gm),.amax_slot(gslot),.amax_tok(gtok),
 .acc_v(ga),.acc_g(g),.stok(gst),.ttok(gtt),.acc_done(gd),.acc_any(gany),.acc_a(gout),.n_emit(gn),.bonus(gb));
 integer cycles=0,which=-1,cohort=0,k,x,y,desired,expected_gen;reg[71:0]before_q;reg[167:0]holdt;
 task tick;begin @(posedge clk);#1;cycles=cycles+1;end endtask
 task check(input reg ok,input string text);begin if(!ok)$fatal(1,"GATE_FAIL case=%0d cycles=%0d %s",which,cycles,text);end endtask
 task start(input integer gamma);begin
 @(negedge clk);g=3'(gamma);pos=1048575+21'(cohort);start_v=1;gs=1;#1;check(sr,"start credit");
 tick();@(negedge clk);start_v=0;gs=0;expected_gen=(cohort+1)%16;
 check(lease=={4'(expected_gen),pos},"full original lease/generation");cohort=cohort+1;
 end endtask
 task producer(input integer kind,input integer slot,input integer tok);
 begin
 @(negedge clk);pv=2'(1<<kind);pfinish=0;pk[kind*25+:25]=lease;ps[kind*3+:3]=3'(slot);pt[kind*21+:21]=0;
 #1;check(pr[kind],"origin acceptance");tick();@(negedge clk);pv=0;
 check(!rv[kind],"no stale token before terminal");
 pv=2'(1<<kind);pfinish=2'(1<<kind);pt[kind*21+:21]=21'(tok);#1;check(pr[kind],"terminal acceptance");
 tick();@(negedge clk);pv=0;pfinish=0;
 check(rv[kind]&&rt[kind*21+:21]==21'(tok)&&rk[kind*25+:25]==lease,"held fullwidth original terminal");
 tick();tick();check(rv[kind]&&!fault,"held source ready");
 @(negedge clk);ctl=2'(1<<kind);gslot=3'(slot);gtok=21'(tok);gt=(kind==0);gm=(kind==1);
 #1;check(rr[kind],"matching leaf query acceptance");tick();@(negedge clk);ctl=0;gt=0;gm=0;tick();
 check(!rv[kind]&&!fault,"holder local release and publish");
 end endtask
 task fill(input integer gamma,input integer acceptcount);
 begin
 for(k=0;k<=gamma;k=k+1)begin
 producer(1,k,100000+k);
 if(k<gamma)producer(0,k+1,(k==acceptcount)?120000:100000+k);
 end
 end endtask
 task accept_result(input integer expected);
 begin
 @(negedge clk);av=1;akey=lease;ag=g;ga=1;#1;check(ar,"accept query ready");tick();
 @(negedge clk);av=0;ga=0;tick();check(!ov,"freshness/match stage");tick();check(!ov,"encoded prefix stage");
 tick();check(ov&&ad&&!fault,"guarded result three edges");
 check(a==3'(expected)&&n==4'(expected+1)&&bonus==21'(100000+expected),"expected fullwidth prefix/bonus");
 check(a==gout&&n==gn&&bonus==gb,"literal source golden prefix/bonus");
 for(desired=0;desired<=g;desired=desired+1)check(t[desired*21+:21]==gtt[desired*21+:21]&&s[desired*21+:21]==gst[desired*21+:21],"literal source golden every active21-bit slot");
 holdt=t;tick();tick();check(ov&&!ad&&t==holdt,"held result and done pulse");
 end endtask
 task drain;
 begin
 @(negedge clk);ovready=1;ack=lease;tick();@(negedge clk);ovready=0;check(!ov&&!fault,"matching local output ACK");
 fv=1;fkey=lease;receipts=63;#1;check(fr,"positive allcopies fence");tick();@(negedge clk);fv=0;tick();check(sr&&!fault,"fenced cohort reuse");
 end endtask
 initial begin
 if($value$plusargs("case=%d",which))begin end
 tick();tick();@(negedge clk);rst_n=1;tick();check(!fault,"cold allcopies-fenced power-on");
 if(which==-1)begin
 for(x=0;x<8;x=x+1)for(y=0;y<=x;y=y+1)begin start(x);fill(x,y);accept_result(y);drain();$display("PREFIX_PASS g=%0d a=%0d",x,y);end
 // Continuous wrap has no finite generation cap; truthful allcopies fences supplied.
 for(x=0;x<4;x=x+1)begin start(1);fill(1,1);accept_result(1);drain();end
 // Idle stop/rearm only, matching retained lease and positive six receipts.
 @(negedge clk);stop=1;tick();@(negedge clk);stop=0;check(!sr,"admission stop");
 fv=1;frearm=1;fkey=lease;tick();@(negedge clk);fv=0;frearm=0;#1;check(sr&&!fault,"idle fenced rearm");
 $display("COMPONENT_PASS cycles=%0d cohorts=%0d",cycles,cohort);$finish;
 end else if(which>=0&&which<24)begin
 start(1);fill(1,1);accept_result(1);
 @(negedge clk);before_q=dut.g_enabled.q[which];dut.g_enabled.q[which]=before_q^72'd3;ovready=1;ack=lease;#1;
 check(fault&&!ov,"discovery edge double fault blocks output consume");tick();
 check(dut.g_enabled.q[which]==(before_q^72'd3)||which==17,"accepted encoded debt preserved");check(dut.g_enabled.d[16][28+:3]==4,"phase not retired on fault");
 $display("FAULT_PASS record=%0d cycles=%0d",which,cycles);$finish;
 end else if(which>=24&&which<28)begin
 start(1);@(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;pt[0+:21]=0;tick();@(negedge clk);pv=0;
 holder.g_enabled.q[which-24]=holder.g_enabled.q[which-24]^72'd3;#1;check(cb&&fault&&!pr[0],"caller protected double fault");tick();
 $display("CALLER_FAULT_PASS record=%0d",which-24);$finish;
 end else if(which==28)begin
 start(1);producer(1,0,113689);@(negedge clk);av=1;akey=lease;ag=1;tick();@(negedge clk);av=0;tick();
 check(fault,"missing input freshness refused");$display("FRESHNESS_PASS");$finish;
 end else if(which==29)begin
 start(1);fill(1,1);accept_result(1);@(negedge clk);ovready=1;ack=lease^25'd1;#1;check(fault&&!ov,"wrong output ACK blocks discovery edge");tick();
 check(dut.g_enabled.d[16][28+:3]==4,"wrong ACK cannot retire");$display("ACK_REFUSAL_PASS");$finish;
 end else if(which==30)begin
 start(1);@(negedge clk);fv=1;frearm=1;fkey=lease;#1;check(fault&&!fr,"runtime rearm refuses owned debt");tick();
 check(dut.g_enabled.d[16][28+:3]==1,"owned cohort not erased");$display("REARM_REFUSAL_PASS");$finish;
 end else if(which==31)begin
 start(1);fill(1,1);accept_result(1);
 for(k=0;k<72;k=k+1)begin
 @(negedge clk);before_q=dut.g_enabled.q[8];dut.g_enabled.q[8]=before_q^(72'd1<<k);#1;
 check(!fault&&t[0+:21]==100000,"every single-bit corrected target");tick();
 @(negedge clk);dut.g_enabled.q[8]=before_q;
 end
 check(ov&&!fault,"single corrected holder preserves output occupancy");$display("SINGLE72_PASS");$finish;
 end else if(which==32)begin
 start(1);@(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;tick();@(negedge clk);pfinish=1;pk[0+:25]=lease^25'd1;pt[0+:21]=113689;
 #1;check(cb&&fault&&!pr[0],"original producer lease mismatch");tick();$display("PRODUCER_STALE_PASS");$finish;
 end else if(which==33)begin
 start(1);producer(0,1,113689);
 @(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;pt[0+:21]=0;tick();@(negedge clk);pfinish=1;pt[0+:21]=113689;tick();@(negedge clk);pv=0;pfinish=0;ctl=1;
 #1;check(fault&&!tr,"duplicate published slot refuses new grant");tick();$display("DUPLICATE_PASS");$finish;
 end else if(which==34)begin
 @(negedge clk);token=129280;start_v=1;#1;check(fault&&!sr,"start token bounds");tick();$display("START_BOUNDS_PASS");$finish;
 end else if(which==35)begin
 start(1);@(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;tick();@(negedge clk);pfinish=1;pt[0+:21]=113689;tick();
 @(negedge clk);pfinish=0;pt[0+:21]=0;#1;check(!pr[0]&&rt[0+:21]==113689,"busy origin cannot overwrite selected token");tick();
 check(rt[0+:21]==113689&&rv[0]&&!fault,"held producer debt preserved");$display("BUSY_ORIGIN_PASS");$finish;
 end else if(which==36)begin
 start(1);@(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;tick();@(negedge clk);pfinish=1;pt[0+:21]=129280;
 #1;check(cb&&fault&&!pr[0],"terminal fullwidth bounds");tick();$display("TERMINAL_BOUNDS_PASS");$finish;
 end else if(which==37)begin
 start(1);@(negedge clk);pv=1;pk[0+:25]=lease;ps[0+:3]=1;tick();@(negedge clk);pfinish=1;pt[0+:21]=113689;tick();@(negedge clk);pv=0;pfinish=0;
 for(k=0;k<72;k=k+1)begin
 @(negedge clk);before_q=holder.g_enabled.q[0];holder.g_enabled.q[0]=before_q^(72'd1<<k);#1;
 check(!cb&&!fault&&rv[0]&&rt[0+:21]==113689,"every single-bit corrected source holder");tick();
 @(negedge clk);holder.g_enabled.q[0]=before_q;
 end
 $display("CALLER_SINGLE72_PASS");$finish;
 end else if(which==38)begin
 start(1);@(negedge clk);dut.g_enabled.q[0]=encode64(dut.g_enabled.d[0]|(64'd1<<40));#1;
 check(fault&&!tr,"coded semantic padding refusal");tick();$display("PADDING_PASS");$finish;
 end else if(which==39)begin
 start(1);fill(1,1);accept_result(1);@(negedge clk);holder.g_enabled.q[0]=holder.g_enabled.q[0]^72'd3;ovready=1;ack=lease;#1;
 check(cb&&fault&&!ov,"caller fault and matching consume joint old-state gate");tick();check(dut.g_enabled.d[16][28+:3]==4,"caller fault cannot retire result");$display("JOINT_FAULT_PASS");$finish;
 end else if(which==40)begin
 start(1);fill(1,1);accept_result(1);@(negedge clk);ovready=1;ack=lease;tick();@(negedge clk);ovready=0;fv=1;fkey=lease;receipts=62;
 #1;check(fault&&!fr,"all six positive fence receipts required");tick();check(dut.g_enabled.d[16][28+:3]==5,"failed fence retains drain debt");$display("FENCE_REFUSAL_PASS");$finish;
 end else if(which==41)begin
 check(!off_sr&&!off_tr&&!off_mr&&!off_ar&&!off_fr&&!off_v&&!off_fault,"defaultoff has no grants/state qualification");
 $display("DEFAULT_OFF_PASS");$finish;
 end else $fatal(1,"unknown case");
 end
endmodule
