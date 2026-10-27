`timescale 1ns/1ps
// Source CFG7 + qbank-S transport composition. Arithmetic is covered separately
// by qxpq_go_boundary_bench.sh; this vehicle proves dated GO lowering only.
module tb_qxpq_go_calendar;
reg clk=0; always #0.5 clk=~clk;
reg rst=0; reg [14:0] oldlc=0,newlc=0;
reg [14:0] oldwords[0:299],newwords[0:299];
string oldfile,newfile;
wire [11:0] aa,ba; wire [6:0] ace,bce;wire [53:0] acfg,bcfg;
wire ago,bgo;wire [1:0] ast,bst,atag,btag;
`define SEQ(PORT,LC,ADDR,CE,CFG,GO,ST,TAG) \
 ot_s81_cfg7_seq #(.PHW(10),.PQ(1),.LAYOUT(1),.PINREG(1)) PORT( \
 .clk(clk),.rst_n(rst),.lc(LC),.a(ADDR),.ce0(CE[0]),.ce1(CE[1]),.ce2(CE[2]),.ce3(CE[3]),.ce4(CE[4]),.ce5(CE[5]),.ce6(CE[6]), \
 .q0(48'd1),.q1(48'd1),.q2(48'd1),.q3(48'd1),.q4(48'd1),.q5(48'd1),.q6(48'd1),.cfg(CFG),.go_e(GO),.st(ST),.ef(2'b11),.go_tag(TAG));
`SEQ(oldseq,oldlc,aa,ace,acfg,ago,ast,atag)
`SEQ(newseq,newlc,ba,bce,bcfg,bgo,bst,btag)
reg [282:0] xs0=0;reg [265:0] xs1=0;
wire [53:0] aqcfg,bqcfg;wire aqgo,bqgo;wire [282:0] aqx0,bqx0;wire [265:0] aqx1,bqx1;
dsfd_qbank_S abank(.ck(clk),.rs(rst),.i_cfg(acfg),.i_go(ago),.i_x0(xs0),.i_x1(xs1),.o_cfg(aqcfg),.o_go(aqgo),.o_x0(aqx0),.o_x1(aqx1));
dsfd_qbank_S bbank(.ck(clk),.rs(rst),.i_cfg(bcfg),.i_go(bgo),.i_x0(xs0),.i_x1(xs1),.o_cfg(bqcfg),.o_go(bqgo),.o_x0(bqx0),.o_x1(bqx1));
// Exactly the GO/TAG capture in the actual _gb wrapper; its separate RSTP
// relay is already present in both native element profiles and adds no delta.
reg gbgo=0;reg[1:0] gbtag=0;
always@(posedge clk or negedge rst) if(!rst) gbgo<=0;else gbgo<=bqgo;
always@(posedge clk) gbtag<=btag;
integer edgeidx, errors=0,gos=0,cfgs=0,readychecks=0;
initial begin
 if(!$value$plusargs("OLD=%s",oldfile)||!$value$plusargs("NEW=%s",newfile)) $fatal(1,"calendar files missing");
 $readmemh(oldfile,oldwords);$readmemh(newfile,newwords);
 for(edgeidx=0;edgeidx<300;edgeidx=edgeidx+1)begin
  @(negedge clk);rst=(edgeidx>=12);oldlc=oldwords[edgeidx];newlc=newwords[edgeidx];
  xs0=283'(edgeidx*37);xs1=266'(edgeidx*71);
  #0.01;
  if(edgeidx>20)begin
   if(aqcfg!==bqcfg||aqx0!==bqx0||aqx1!==bqx1||aa!==ba||ace!==bce)begin errors=errors+1;$display("DATE_OR_PAYLOAD_DIFF %0d",edgeidx);end
   if(aqgo!==gbgo)begin errors=errors+1;$display("GO_DATE_DIFF %0d legacy%0d gb%0d",edgeidx,aqgo,gbgo);end
   if(aqgo)begin gos=gos+1;if(atag!==gbtag)begin errors=errors+1;$display("TAG_DIFF %0d",edgeidx);end end
   if(acfg[53])cfgs=cfgs+1;
   if(ast[1]||bst[1])begin errors=errors+1;$display("SEQ_FAULT %0d old%0d new%0d",edgeidx,ast,bst);end
  end
  if(edgeidx==60||edgeidx==184)begin
   readychecks=readychecks+1;
   if(oldseq.u_impl.pend_x||oldseq.u_impl.ld_run_x||oldseq.u_impl.c_v||oldseq.u_impl.cfg_go_x)begin errors=errors+1;$display("LEGAL_BOUND_NOT_READY %0d",edgeidx);end
  end
 end
 if(gos!=2||cfgs!=50||readychecks!=2)begin errors=errors+1;$display("VACUOUS gos%0d cfgs%0d ready%0d",gos,cfgs,readychecks);end
 if(errors)begin $display("GB_GO_CALENDAR FAIL errors%0d",errors);$fatal(1,"miter");end
 $display("GB_GO_CALENDAR PASS gos%0d cfgs%0d ready%0d",gos,cfgs,readychecks);$finish;
end
endmodule
