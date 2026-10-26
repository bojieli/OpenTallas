`timescale 1ns/1ps
// Q-ATTN r3 serializer trade bench. Actual ot_qwen_me_spctl_w12 + ot_qwen_me_spport_w12 (Codex extraction, same
// params as tools/qwen_producer_train/tb.sv) run one decoded decoder ME instruction (plusargs). Records the actual
// capture cycles, then feeds (a) qfd_res_train_static x3 bands with the ACTUAL producer timing, train_start on the
// compiler-known first capture edge, count=me_tiles, stride=me_ts; and (b) qfd_res_ser_static x3 bands twice:
// b_raw = the actual producer timing (must fault) and b_spaced = a hypothetical producer whose capture k is held to
// max(actual_k, capture_{k-1}+24) (the spacing (b) requires). Reports per variant: last end-beat cycle, faults.
module tb_sertrade;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,go=0;wire pv;wire[112:0]pf;wire ov;wire we;wire[23:0]addr;wire[15:0]mask;wire[511:0]data;
reg[17:0]nout,tiles,k;reg wsrc,round,oen,mmode;reg[23:0]wbase,ts,ks,js,xbase,xks,xjs,xcs,wcs,obase,ots,ojs;reg[3:0]split;
ot_qwen_me_spctl_w12 #(.W(16),.IL(8),.NW(18),.GT(3072),.SMIN(7),.SMAX(11),.TCUT(7),.XD(105),.XVM(15),.ORD(7),.ACC_LAT(7),.TREE_LAT(7),.MUL_LAT(6),.SCALE_LAT(8),.FAST_ISSUE(1),.KV_PREP(3),.BANDF(1),.SPRE(2),.XADDR(0),.PQ(1)) ctl(
.clk(ck),.rst_n(rst_n),.go(go),.land_cnt(16'd0),
.i_nout(nout),.i_tiles(tiles),.i_k(k),.i_wsrc(wsrc),.i_wbase(wbase),.i_ts(ts),.i_ks(ks),.i_js(js),.i_xbase(xbase),.i_xks(xks),.i_xjs(xjs),.i_xcs(xcs),.i_jsh(3'd0),.i_split(split),.i_wcs(wcs),.i_round(round),.i_obase(obase),.i_ots(ots),.i_ojs(ojs),.i_mmode(mmode),.i_oen(oen),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(24'd0),.x_q('0),.tr_fault('0),.p_am('0),.p_fault('0),.fab_fault(1'b0),.p_v_e2(pv),.p_f_e2(pf));
ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),.SMIN(7),.PQ(1),.TREE_LAT(7),.SCALE_LAT(8),.BANDF(1),.TCUT(7),.HARD_MUL(0)) port0(
.clk(ck),.ck_mul('0),.rst_n(rst_n),.pt_id(16'd0),.lv_in({16{32'h3f800000}}),.a_v_e2(pv),.a_f_e2(pf),.scale_q({8{32'h3f800000}}),.o_we(we),.o_addr(addr),.o_mask(mask),.o_data(data),.o_ov(ov));
// slab-packed burst (qfd_port_tiles_b.rq order): slot s = {addr24,mask16,data512} at 552 s, we@4416+s, ov@4424.
// The one actual port fills slot 0; the other slots carry tagged synthetic rows so every slot is exercised.
wire[4424:0]rq_act;
genvar s;generate for(s=0;s<8;s=s+1)begin:gs
 assign rq_act[552*s+:552]={addr+24'(s*0),mask,data^512'(s)};
 assign rq_act[4416+s]=we;
end endgenerate
assign rq_act[4424]=ov;
integer cycle=0,ncap=0,first=-1,go_cyc=-1;integer cap[0:255];
always @(negedge ck)begin cycle=cycle+1;if(rst_n&&ov)begin cap[ncap]=cycle;ncap=ncap+1;if(first<0)first=cycle;end end
// replay buffers: actual rq per capture (same values feed every variant)
reg[4424:0]hist[0:255];always @(negedge ck)if(rst_n&&ov)hist[ncap-1]=rq_act;
// phase 2: replay into the three serializer variants from a second clean reset, cycle-exact
reg rst2=0;integer rc=0;integer sp[0:255];
reg tstart=0;reg[4424:0]rq_a=0,rq_braw=0,rq_bsp=0;
wire[550:0]rb_a[0:2],rb_braw[0:2],rb_bsp[0:2];wire[2:0]f_a,f_braw,f_bsp;
reg[3:0]tcount;reg[31:0]tstride;
generate for(s=0;s<3;s=s+1)begin:gb
 qfd_res_train_static #(.BAND(s),.NB(3),.D(2),.MAX_TRAIN(8)) ua(.ck(ck),.rst_n(rst2),.ck_bank({24{ck}}),.train_start(tstart),.train_count(tcount),.capture_stride(tstride),.payload_write(1'b1),.rq(rq_a),.rb(rb_a[s]),.fault(f_a[s]));
 qfd_res_ser_static #(.BAND(s),.NB(3),.D(2)) ub(.ck(ck),.rst_n(rst2),.me_en(1'b1),.rq(rq_braw),.rb(rb_braw[s]),.fault(f_braw[s]));
 qfd_res_ser_static #(.BAND(s),.NB(3),.D(2)) uc(.ck(ck),.rst_n(rst2),.me_en(1'b1),.rq(rq_bsp),.rb(rb_bsp[s]),.fault(f_bsp[s]));
end endgenerate
integer end_a=-1,end_braw=-1,end_bsp=-1,n_a=0,n_bsp=0,beats_a=0,beats_bsp=0,i,base;
integer rows_a=0,rows_b=0;
always @(negedge ck)if(rst2)begin
 if(rb_a[2][550]&&rb_a[2][549])begin end_a=rc;n_a=n_a+1;end
 if(rb_braw[2][550]&&rb_braw[2][549])end_braw=rc;
 if(rb_bsp[2][550]&&rb_bsp[2][549])begin end_bsp=rc;n_bsp=n_bsp+1;end
 for(i=0;i<3;i=i+1)begin if(rb_a[i][550]&&!rb_a[i][548])rows_a=rows_a+1;if(rb_bsp[i][550]&&!rb_bsp[i][548])rows_b=rows_b+1;end
end
initial begin
 if(!$value$plusargs("NOUT=%d",nout))$fatal(1,"NOUT");if($value$plusargs("TILES=%d",tiles));if($value$plusargs("K=%d",k));
 wsrc=0;round=0;oen=0;mmode=0;wbase=0;ts=0;ks=0;js=0;xbase=0;xks=0;xjs=0;xcs=0;wcs=0;obase=0;ots=0;ojs=0;split=0;
 if($value$plusargs("WSRC=%d",wsrc));if($value$plusargs("ROUND=%d",round));if($value$plusargs("OEN=%d",oen));if($value$plusargs("MMODE=%d",mmode));
 if($value$plusargs("WBASE=%d",wbase));if($value$plusargs("TS=%d",ts));if($value$plusargs("KS=%d",ks));if($value$plusargs("JS=%d",js));
 if($value$plusargs("XBASE=%d",xbase));if($value$plusargs("XKS=%d",xks));if($value$plusargs("XJS=%d",xjs));if($value$plusargs("XCS=%d",xcs));
 if($value$plusargs("WCS=%d",wcs));if($value$plusargs("OBASE=%d",obase));if($value$plusargs("OTS=%d",ots));if($value$plusargs("OJS=%d",ojs));if($value$plusargs("SPLIT=%d",split));
 repeat(5)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);go=1;go_cyc=cycle;@(negedge ck);go=0;
 repeat(6000)@(negedge ck);
 $display("PRODUCER go=%0d ncap=%0d first=%0d last=%0d",go_cyc,ncap,first,ncap?cap[ncap-1]:-1);
 if(ncap==0)begin $display("{\"ncap\":0}");$finish;end
 // spaced schedule required by (b)
 sp[0]=cap[0];for(i=1;i<ncap;i=i+1)sp[i]=(cap[i]>sp[i-1]+24)?cap[i]:sp[i-1]+24;
 tcount=4'(tiles);tstride=(ts<8)?32'd8:32'(ts);  // a single train ignores the stride; the contract needs >= 8
 // replay: rc counts edges of phase 2; time 0 aligned so rc==cap[i]-go_cyc presents capture i
 repeat(3)@(negedge ck);rst2=1;repeat(3)@(negedge ck);
 for(rc=0;rc<9000;rc=rc+1)begin
  tstart=(rc==cap[0]-go_cyc);rq_a=0;rq_braw=0;rq_bsp=0;
  for(i=0;i<ncap;i=i+1)begin if(rc==cap[i]-go_cyc)begin rq_a=hist[i];rq_braw=hist[i];end if(rc==sp[i]-go_cyc)rq_bsp=hist[i];end
  @(negedge ck);
 end
 $display("{\"go\":%0d,\"ncap\":%0d,\"first_cap_rel\":%0d,\"last_cap_rel\":%0d,\"a_last_end_rel\":%0d,\"a_ends\":%0d,\"a_rows\":%0d,\"a_fault\":\"%b\",\"braw_fault\":\"%b\",\"bsp_last_cap_rel\":%0d,\"bsp_last_end_rel\":%0d,\"bsp_ends\":%0d,\"bsp_rows\":%0d,\"bsp_fault\":\"%b\"}",
  go_cyc,ncap,cap[0]-go_cyc,cap[ncap-1]-go_cyc,end_a,n_a,rows_a,f_a,f_braw,sp[ncap-1]-go_cyc,end_bsp,n_bsp,rows_b,f_bsp);
 $finish;
end
endmodule
