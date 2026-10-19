`timescale 1ns/1ps
module banked_class_case #(parameter SVG=1,PREL=1,MUT=0,W=SVG?135:173,XW=SVG?47:5,TW=62+XW,QW=(W+15)/16)(output reg finished=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;reg[10:0]cfg_addr=0,start_base=0;reg[255:0]cfg_data=0;reg[11:0]start_limit=0;reg[15:0]start_loops=0;reg[XW-1:0]start_ctx=0;
 wire cw0,cw1;wire[9:0]ca;wire[255:0]cd;wire[TW-1:0]rq0,rq1,t0,t1;wire[W-1:0]r0,r1;wire[QW-1:0]ok0,ok1;
 wire[W-1:0]oldapp,newapp;wire ov,nv,oa,na,od,nd,ofault,nfault,cls,cv;
 generate if(SVG)begin:g_svg
 banked_app_reference_svg #(.PREL(PREL)) refapp(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx[45:0]),.app(oldapp),.app_v(ov),.active(oa),.done(od),.fault(ofault));
 ot_smh_banked_svg_central #(.PREL(PREL),.XW(47),.CLASS_ENABLE(1),.CLASS_MUT(MUT)) dut(.*,.cfg0_we(cw0),.cfg1_we(cw1),.bank_cfg_addr(ca),.bank_cfg_data(cd),.request0(rq0),.request1(rq1),.row0(r0),.row1(r1),.ok0(ok0),.ok1(ok1),.token0(t0),.token1(t1),.programme(newapp),.programme_v(nv),.active(na),.done(nd),.fault(nfault),.command_class_observe(cls),.command_context_valid_observe(cv),.command_envelope());
 end else begin:g_xc
 banked_app_reference_xc #(.PREL(PREL)) refapp(.*,.app(oldapp),.app_v(ov),.active(oa),.done(od),.fault(ofault));
 ot_smh_banked_xc_central #(.PREL(PREL),.CLASS_ENABLE(1),.CLASS_MUT(MUT)) dut(.*,.cfg0_we(cw0),.cfg1_we(cw1),.bank_cfg_addr(ca),.bank_cfg_data(cd),.request0(rq0),.request1(rq1),.row0(r0),.row1(r1),.ok0(ok0),.ok1(ok1),.token0(t0),.token1(t1),.cmd_ext(newapp[108:0]),.kv_desc(newapp[172:109]),.active(na),.done(nd),.fault(nfault),.command_class_observe(cls),.command_context_valid_observe(cv),.command_envelope());
 assign nv=0;
 end endgenerate
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(0)) b0(.clk(clk),.rst_n(rst_n),.cfg_we(cw0),.cfg_addr(ca),.cfg_data(cd),.read_token(rq0),.row(r0),.word_ok(ok0),.row_token(t0));
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(1)) b1(.clk(clk),.rst_n(rst_n),.cfg_we(cw1),.cfg_addr(ca),.cfg_data(cd),.read_token(rq1),.row(r1),.word_ok(ok1),.row_token(t1));
 // Independent old calendar provides context/word association; old qualified
 // application R/C provides every expected payload bit (including mrel).
 wire[W-1:0]refword;wire[XW-1:0]refctx;wire refv;wire[31:0]reford;
 ot_smh_calendar_static_x #(.W(W),.XW(XW)) oldcal(.*,.calendar(refword),.calendar_ctx(refctx),.calendar_iter(),.calendar_lastit(),.calendar_v(refv),.ordinal(reford),.active(),.done(),.fault());
 reg class_r,class_c,valid_r,valid_c;
 wire rc=SVG?refctx[XW-1]:refctx[4];wire fl=SVG?refctx[2]:refctx[0];
 always @(posedge clk)begin class_r<=refv?rc:0;class_c<=class_r;if(PREL&&refv&&reford==0&&fl)class_c<=rc;end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin valid_r<=0;valid_c<=0;end else begin valid_r<=refv;valid_c<=valid_r;if(PREL&&refv&&reford==0&&fl)valid_c<=1;end
 wire ec=PREL?class_c:class_r,ev=MUT==4?1'b0:(PREL?valid_c:valid_r);
 reg[W-1:0]aq[0:1];reg cq[0:1],vq[0:1],dq[0:1],fq[0:1];reg semantic_fault=0;reg[W-1:0]consume_word=0;reg consume_valid=0,consume_class=0;
 integer warm=0,cycle=0,checked=0,completed=0,magic_seen=0,inject_seen=0;
 // Consume the previously launched expected pins at this edge, exactly like
 // the native semantic checker. Core/app fault is separately shifted2.
 always @(posedge clk)begin
 if(!rst_n)semantic_fault<=0;
 else if(!SVG&&consume_word[108:101]==8'ha2&&(!consume_valid||consume_word[100:98]==3||consume_word[100]!=consume_class))semantic_fault<=1;
 #1;cycle=cycle+1;if(cycle>30000)$fatal(1,"CLASS_FAIL watchdog");
 if(!rst_n)begin warm=0;consume_word=0;consume_valid=0;consume_class=0;for(integer j=0;j<2;j=j+1)begin aq[j]=0;cq[j]=0;vq[j]=0;dq[j]=0;fq[j]=0;end end
 else begin
 if(warm>=14)begin
  if(newapp!==aq[1]||cls!==cq[1]||cv!==vq[1]||nd!==dq[1]||nfault!==(fq[1]||(!SVG&&semantic_fault)))
   $fatal(1,"CLASS_FAIL SVG=%0d PREL=%0d MUT=%0d cycle=%0d cls=%b/%b valid=%b/%b fault=%b/%b",SVG,PREL,MUT,cycle,cls,cq[1],cv,vq[1],nfault,fq[1]||(!SVG&&semantic_fault));
  checked=checked+1;if(nd)completed=completed+1;
  if(!SVG&&newapp[108:101]==8'ha2)magic_seen=magic_seen+1;
  if(SVG&&newapp[28])inject_seen=inject_seen+1;
 end
 consume_word=aq[1];consume_valid=vq[1];consume_class=cq[1];
 aq[1]=aq[0];cq[1]=cq[0];vq[1]=vq[0];dq[1]=dq[0];fq[1]=fq[0];aq[0]=oldapp;cq[0]=ec;vq[0]=ev;dq[0]=od;fq[0]=ofault;warm=warm+1;
 end end
 function automatic[255:0]word(input integer a,mode);
 reg[255:0]z;begin z=0;z[255:240]=16'hc7a1;z[234:224]=11'(a);
 if(SVG)begin z[25]=1;z[29]=1;z[22:11]=12'(a);z[9:7]=3'(a);z[6:0]=7'(a);z[39:30]=10'(a);z[83]=1;z[106:101]=6'(a);z[116:107]=10'(a);z[117]=1;z[134:119]=16'hda71;z[118]=1;end
 else begin z[108:101]=8'ha2;z[100:98]=3'(mode);z[97:0]=98'(a*1347+573);z[172:109]=64'(a*9173+721);end
 word=z;end endfunction
 task automatic idle(input integer n);repeat(n)@(negedge clk);endtask
 task automatic reset;begin @(negedge clk);rst_n=0;cfg_we=0;start_v=0;idle(4);rst_n=1;idle(16);end endtask
 task automatic install(input integer mode);begin
 for(integer a=1022;a<1030;a=a+1)begin @(negedge clk);cfg_we=1;cfg_addr=11'(a);cfg_data=word(a,mode);end
 @(negedge clk);cfg_we=0;idle(8);end endtask
 task automatic run(input integer mode,dc,mrel,format_launch);
 integer target;reg[XW-1:0]ctx;begin
 ctx=0;if(SVG)begin ctx[46]=1'(dc);ctx[2]=1'(format_launch);ctx[1:0]=2'(mode);end else ctx={3'(mode),1'(mrel),1'(format_launch)};
 target=completed+1;@(negedge clk);start_base=1022;start_limit=1030;start_loops=3;start_ctx=ctx;start_v=1;@(negedge clk);start_v=0;wait(completed==target);idle(8);end endtask
 initial begin reset();
 // All8literal modes, including invalid3, bankcrossing and loopedcommands.
 for(integer mode=0;mode<8;mode=mode+1)begin install(mode);run(mode,mode>>2,0,0);if(!SVG&&mode==3&&!nfault)$fatal(1,"CLASS_FAIL invalid3 missed");reset();end
 // Every legal descriptor mode rewrites an opposite-class literal at mrel.
 for(integer mode=0;mode<8;mode=mode+1)if(mode!=3)begin install(mode^4);run(mode,mode>>2,1,0);reset();end
 // Genuine mismatch: dense descriptor, attention literal (postmrel off).
 install(4);run(0,0,0,0);if(!SVG&&!nfault)$fatal(1,"CLASS_FAIL mismatch missed");reset();
 // Alternating descriptor class + injectedformat in an empty previousCslot.
 install(4);run(4,1,0,1);reset();install(0);run(0,0,0,1);reset();
 $display("BANKED_CLASS_PROFILE_PASS SVG=%0d PREL=%0d checked=%0d magic=%0d inject=%0d",SVG,PREL,checked,magic_seen,inject_seen);finished=1;end
endmodule
module tb_banked_class #(parameter MUT=0);
 wire[3:0]finished;
 banked_class_case #(.SVG(1),.PREL(1),.MUT(MUT)) s1(.finished(finished[0]));
 banked_class_case #(.SVG(1),.PREL(0),.MUT(MUT)) s0(.finished(finished[1]));
 banked_class_case #(.SVG(0),.PREL(1),.MUT(MUT)) x1(.finished(finished[2]));
 banked_class_case #(.SVG(0),.PREL(0),.MUT(MUT)) x0(.finished(finished[3]));
 initial begin wait(&finished);$display("BANKED_CLASS PASS modes0..7 mrel format nativefaultedge1 profiles4");$finish;end
endmodule
