`timescale 1ns/1ps
// Q-VMWB stage 1: actual ot_qwen_me_spctl_w12 + the 24 ACTUAL slab result ports of one rank (pt_id = 8*band + slot,
// qfd_slab_port_leaf strap law) run one decoded decoder ME instruction (plusargs, as tb_sertrade). Prints every
// burst row the ports emit: capture index, band, slot, we, row address, mask. This is the compiler's input for the
// VM write-back calendar (which slots carry real rows, which VM banks they hit).
module tb_vmwb_rows;
reg ck=0;always #5 ck=~ck;
reg rst_n=0,go=0;wire pv;wire[112:0]pf;
reg[17:0]nout,tiles,k;reg wsrc,round,oen,mmode;reg[23:0]wbase,ts,ks,js,xbase,xks,xjs,xcs,wcs,obase,ots,ojs;reg[3:0]split;
ot_qwen_me_spctl_w12 #(.W(16),.IL(8),.NW(18),.GT(3072),.SMIN(7),.SMAX(11),.TCUT(7),.XD(105),.XVM(15),.ORD(7),.ACC_LAT(7),.TREE_LAT(7),.MUL_LAT(6),.SCALE_LAT(8),.FAST_ISSUE(1),.KV_PREP(3),.BANDF(1),.SPRE(2),.XADDR(0),.PQ(1)) ctl(
.clk(ck),.rst_n(rst_n),.go(go),.land_cnt(16'd0),
.i_nout(nout),.i_tiles(tiles),.i_k(k),.i_wsrc(wsrc),.i_wbase(wbase),.i_ts(ts),.i_ks(ks),.i_js(js),.i_xbase(xbase),.i_xks(xks),.i_xjs(xjs),.i_xcs(xcs),.i_jsh(3'd0),.i_split(split),.i_wcs(wcs),.i_round(round),.i_obase(obase),.i_ots(ots),.i_ojs(ojs),.i_mmode(mmode),.i_oen(oen),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(24'd0),.x_q('0),.tr_fault('0),.p_am('0),.p_fault('0),.fab_fault(1'b0),.p_v_e2(pv),.p_f_e2(pf));
wire[23:0]we,ov;wire[24*24-1:0]addr;wire[24*16-1:0]mask;wire[24*512-1:0]data;
genvar p;generate for(p=0;p<24;p=p+1)begin:gp
 ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),.SMIN(7),.PQ(1),.TREE_LAT(7),.SCALE_LAT(8),.BANDF(1),.TCUT(7),.HARD_MUL(0)) u(
 .clk(ck),.ck_mul('0),.rst_n(rst_n),.pt_id(16'(p)),.lv_in({16{32'h3f800000+32'(p)}}),.a_v_e2(pv),.a_f_e2(pf),.scale_q({8{32'h3f800000}}),
 .o_we(we[p]),.o_addr(addr[24*p+:24]),.o_mask(mask[16*p+:16]),.o_data(data[512*p+:512]),.o_ov(ov[p]));
end endgenerate
integer cycle=0,ncap=0,go_cyc=-1,i;
always @(negedge ck)begin cycle=cycle+1;
 if(rst_n&&ov[0])begin
  for(i=0;i<24;i=i+1)$display("ROW cap=%0d rel=%0d band=%0d slot=%0d we=%0d addr=%0d mask=%h",ncap,cycle-go_cyc,i/8,i%8,we[i],addr[24*i+:24],mask[16*i+:16]);
  ncap=ncap+1;
 end
 if(rst_n&&(ov!=0&&ov!={24{1'b1}}))$fatal(1,"ports disagree on the burst marker");
end
initial begin
 if(!$value$plusargs("NOUT=%d",nout))$fatal(1,"NOUT");tiles=1;k=1;if($value$plusargs("TILES=%d",tiles));if($value$plusargs("K=%d",k));
 wsrc=0;round=0;oen=0;mmode=0;wbase=0;ts=0;ks=0;js=0;xbase=0;xks=0;xjs=0;xcs=0;wcs=0;obase=0;ots=0;ojs=0;split=0;
 if($value$plusargs("WSRC=%d",wsrc));if($value$plusargs("ROUND=%d",round));if($value$plusargs("OEN=%d",oen));if($value$plusargs("MMODE=%d",mmode));
 if($value$plusargs("WBASE=%d",wbase));if($value$plusargs("TS=%d",ts));if($value$plusargs("KS=%d",ks));if($value$plusargs("JS=%d",js));
 if($value$plusargs("XBASE=%d",xbase));if($value$plusargs("XKS=%d",xks));if($value$plusargs("XJS=%d",xjs));if($value$plusargs("XCS=%d",xcs));
 if($value$plusargs("WCS=%d",wcs));if($value$plusargs("OBASE=%d",obase));if($value$plusargs("OTS=%d",ots));if($value$plusargs("OJS=%d",ojs));if($value$plusargs("SPLIT=%d",split));
 repeat(5)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);go=1;go_cyc=cycle;@(negedge ck);go=0;
 repeat(6000)@(negedge ck);
 $display("DONE ncap=%0d",ncap);$finish;
end
endmodule
