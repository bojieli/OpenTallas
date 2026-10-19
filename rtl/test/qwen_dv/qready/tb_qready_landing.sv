`timescale 1ns/1ps
// tb_qfd_native59_dv_service -- Q-N59 (10-17) equivalence bench, cycle-driven (Verilator, C++ clock; no delays).
// Two DUTs on one clock and one compiled timeline:
//   OLD qfd_native59_compute_service fed exactly as tb_qfd_native59_ar520_component does it: the SU64 64-lane KV writes
//       with their native_issue, the VM Q export words at q_slot, and the VM's SRAM write-consume pins (declared model).
//   NEW qfd_native59_dv_service fed the SAME payloads as W5 slice D2D words: each 64-lane KV write as 8 dd words of 8
//       lanes (kind 2 V / 1 K, same lane addresses and FP32 values), Q as 64 dd words (kind 0) of 8 elements in a
//       permuted element order before the request; no native_issue / q / write_commit pins.
// Checks (bit-exact):
//   x3 words + identity + generation, native_tx_payload sequence, and the attention result words: identical sequences,
//   NEW exactly one edge (x3, tx) / two edges (dr_o vs vm_ar: + the dr_o pin flop) after OLD; native_ret(NEW, t+1) ==
//   native_ret(OLD, t) every cycle (except commit_count, which follows the physical landing edge; final 32 checked); completion one edge later; both fault-free; the Q tx beats also equal the
//   independent element values (beat b lane j = element 16b+j).
//   Embedding (G9): a real qfd_embedding_word_provider is filled (token/epoch/64 code words/BF16 scale), core_start,
//   then the EMB native_cmd; dr_o must carry 65 group-1 words on consecutive edges starting exactly 6 edges after the
//   command pin: beat k = code word k (k 0..63), then beat 0 = {496'd0, scale}; provider and DUT fault-free.
// BAD_Q=1: one Q dd word is never sent -> NEW must fault and never complete (schedule violation, no stall).
// Pass line: N59DV_PASS ...; any failure prints N59DV_FAIL and $fatal.
module tb_qready_landing #(parameter integer MUT=0,BAD_Q=0,SAFE=0,LATE_PREFETCH=0,IDEAL_CONTROL=0)(input wire clk);
 localparam integer HEADS=1;
 localparam[379:0]TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 localparam[58:0]TAG={16'd9,6'd1,18'd50994,13'd255,6'd0};
 localparam[17:0]ETOK=18'd123457;localparam[15:0]EEP=16'd77;
 reg[31:0]cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 wire rst_n=cyc>=1596;
 // Original real-stage Q words retain their measured spacing, offset64 for the bench-only context.
 // IDEAL_CONTROL uses K6/E15 for a lawful zero-delay clock control, never the production K2/E19 contract.
 // Transport and service proof only: no deployment programme/request admission is claimed.
 reg[547:0]qdd_source[0:4999];reg[31:0]qgold[0:511];
 reg[1023:0]qfile,gfile;
 initial begin
  if(!$value$plusargs("QDD=%s",qfile)||!$value$plusargs("QGOLD=%s",gfile))$fatal(1,"QDD/QGOLD required");
  $readmemh(qfile,qdd_source);$readmemh(gfile,qgold);
 end
 wire[547:0]qwire[0:26];wire[25:0]qclk,qepoch;wire lane_fault;
 assign qwire[0]=qdd_source[cyc];
 genvar qh;
 generate for(qh=0;qh<25;qh=qh+1)begin:qhop
  ot_qfd_lane_st #(.W(548),.FIRST(qh==0)) u_hop(
   .ck(qh==0?clk:qclk[qh-1]),.en(qh==0?(cyc>=1266):qepoch[qh-1]),
   .a(qwire[qh]),.b(qwire[qh+1]),.eb(qepoch[qh]),.ck_o(qclk[qh]));
 end endgenerate
 ot_qfd_land #(.W(548),.FIRST(0))u_land(.ckf(qclk[24]),.ea(qepoch[24]),.i(qwire[25]),
  .ck(clk),.rs(rst_n),.k(IDEAL_CONTROL?3'd6:3'd2),.o(qwire[26]),.fault(lane_fault));

 // ------------------------------------------------------------------ payload functions (old bench)
 function automatic [7:0] code(input integer k,input integer h,input integer d);
  integer x;begin x=(k*91+h*37+d)%254;if(x>=127)x=x+1;code=x[7:0];end
 endfunction
 function automatic [31:0] decode(input [7:0] b);
  reg [3:0] e;reg [2:0] m;begin e=b[6:3];m=b[2:0];
   if(e!=0)decode={b[7],8'(e+120),m,20'd0};
   else if(m[2])decode={b[7],8'd120,m[1:0],21'd0};
   else if(m[1])decode={b[7],8'd119,m[0],22'd0};
   else if(m[0])decode={b[7],8'd118,23'd0};
   else decode={b[7],31'd0};
  end
 endfunction
 function automatic [23:0] address(input integer k,input integer d);
  integer p;begin p=255;
   if(k==0)address=24'(((p/16)*128+d)*16+p%16);
   else address=24'(HEADS*1048576+p*128+d);end
 endfunction
 function automatic [31:0] qval(input integer e);qval=qgold[e];endfunction
 function automatic [31:0] rval(input integer b,input integer j);rval=32'(b*16+j)*32'h85EBCA6B+32'h1234567;endfunction
 function automatic integer qperm(input integer n);qperm=(n*37+11)%512;endfunction
 function automatic [511:0] erow(input integer w);
  integer j;begin for(j=0;j<16;j=j+1)erow[32*j+:32]=32'(w*16+j)*32'hC2B2AE35^32'(ETOK);end
 endfunction
 function automatic integer eperm(input integer n);eperm=(n*29+5)%64;endfunction
 localparam[15:0]ESCALE=16'h3E80;
 // ------------------------------------------------------------------ timeline
 // KV write groups: cycle, kind (1 V / 0 K), dim base
 function automatic integer wgrp(input integer c);
  wgrp=(c==9)?0:(c==17)?1:(c==26)?2:(c==35)?3:-1;endfunction
 function automatic integer wkind(input integer g);wkind=(g<2)?1:0;endfunction
 function automatic integer wbase(input integer g);wbase=(g==1||g==3)?64:0;endfunction
 localparam integer QD0=44,CMD=200,QS0=204,RX0=240,VIS=290,STS=291,CMP=293,FILL=300,CORE=370,EMB=372;
 integer c,i,j,ll,pp,g,w;
 reg context_v,q_committed,kvslot,xslot,qslot,txslot,rxslot,rxv,visibility_slot,complete_slot;
 reg[5:0]stage;reg[17:0]token,position;reg[379:0]cmd;reg[62:0]issue;
 reg[1:0]kvindex;reg[4:0]qb,tb,rb;reg[3:0]tk,rk;
 reg[63:0]we;reg[1535:0]wa;reg[2047:0]wd;reg[523:0]q;reg[547:0]rxdata,dd;
 // provider stimulus
 reg pw_v,pw_scale,fill_begin,core_start;reg[5:0]pw_idx;reg[511:0]pw_data;
 always @*begin
  c=cyc-1600;
  context_v=(c==5);q_committed=(c>=174);kvslot=0;xslot=0;qslot=0;txslot=0;rxslot=0;rxv=0;visibility_slot=0;complete_slot=0;
  stage=(c>=QS0)?6'd3:6'd1;token=(c>=QS0)?18'd42:18'd50994;position=(c>=QS0)?18'd8191:18'd255;
  cmd=0;issue=0;kvindex=0;qb=0;tb=0;rb=0;tk=0;rk=0;we=0;wa=0;wd=0;q=0;rxdata=0;dd=0;
  pw_v=0;pw_scale=0;fill_begin=0;core_start=0;pw_idx=0;pw_data=0;
  // OLD: native issue one edge before each write burst
  if(c==8)issue={address(1,0),2'd2,18'd128,18'd1,1'b1};
  if(c==25)issue={address(0,0),2'd2,18'd64,18'd1,1'b1};
  if(c==34)issue={address(0,64),2'd2,18'd64,18'd1,1'b1};
  g=wgrp(c);
  if(g>=0)begin
   we=64'hffffffffffffffff;
   for(ll=0;ll<64;ll=ll+1)begin pp=(ll*17)%64;wa[24*ll+:24]=address(wkind(g),wbase(g)+pp);wd[32*ll+:32]=decode(code(wkind(g),0,wbase(g)+pp));end
  end
  // NEW: the same 64 lanes as 8 dd words on the 8 edges from the OLD write edge
  for(i=0;i<4;i=i+1)begin
   w=(i==0)?9:(i==1)?17:(i==2)?26:35;
   if(c>=w&&c<w+8)begin
    j=c-w;dd[547]=1;dd[546:545]=(wkind(i)==1)?2'd2:2'd1;dd[544:537]=8'hff;
    for(ll=0;ll<8;ll=ll+1)begin pp=((8*j+ll)*17)%64;
     dd[345+24*ll+:24]=address(wkind(i),wbase(i)+pp);dd[89+32*ll+:32]=decode(code(wkind(i),0,wbase(i)+pp));end
   end
  end
  if(c>=178&&c<185)begin i=c-178;kvslot=i<4;kvindex=2'(i);xslot=i>=3;end
  if(c==CMD)cmd=TEMPLATE;
  if(c==CMD+1)begin txslot=1;tk=1;tb=0;end
  if(c>=QS0&&c<QS0+33)begin
   i=c-QS0;qslot=i<32;qb=5'(i);
   if(i<32)begin q[523]=1;q[522:520]=3'd1;q[516:512]=5'(i);for(j=0;j<16;j=j+1)q[32*j+:32]=qval(16*i+j);end
   txslot=i>0;tk=2;tb=5'(i-1);
  end
  if(c>=RX0&&c<RX0+33)begin
   i=c-RX0;rxv=i<32;rxslot=i<32;rk=3;rb=5'(i);
   rxdata[547:512]={5'd0,4'd3,6'd0,16'd9,5'(i)};for(j=0;j<16;j=j+1)rxdata[32*j+:32]=rval(i,j);
  end
  if(c==VIS)visibility_slot=1;
  if(c==STS)begin rxv=1;rxslot=1;rk=4;rb=0;rxdata={5'd0,4'd4,6'd0,16'd9,5'd0,507'd0,5'b01001};end
  if(c==CMP)complete_slot=1;
  // embedding provider fill: FILL, gap, scale header, 64 code words (permuted), then core_start, then EMB command
  if(c==FILL)fill_begin=1;
  if(c==FILL+2)begin pw_v=1;pw_scale=1;pw_data={496'd0,ESCALE};end
  if(c>=FILL+3&&c<FILL+67)begin pw_v=1;pw_idx=6'(eperm(c-FILL-3));pw_data=erow(eperm(c-FILL-3));end
  if(c==CORE)core_start=1;
  if(c==EMB)cmd={4'hE,ETOK,357'd0,1'b0};
 end
 // ------------------------------------------------------------------ OLD DUT + its declared VM commit-pin model
 wire[519:0]vm_ar;wire o_qe,o_qs,o_tv,o_done,o_fault;wire[58:0]o_xid;wire[1:0]o_xg;wire[523:0]o_x3;wire[547:0]o_td;wire[94:0]o_ret;
 reg[7:0]pending=0;reg[4:0]pbeat[0:7];integer pi;
 always @(posedge clk)begin pending<={pending[6:0],vm_ar[519]};pbeat[0]<=vm_ar[516:512];for(pi=1;pi<8;pi=pi+1)pbeat[pi]<=pbeat[pi-1];end
 reg[38:0]raw_v;reg[311:0]raw_line;reg[623:0]raw_mask;
 always @*begin raw_v=0;raw_line=0;raw_mask=0;
  if(pending[7])begin raw_v[7+pbeat[7]]=1;raw_line[8*(7+pbeat[7])+:8]=8'd49;raw_mask[16*(7+pbeat[7])+:16]=16'hffff;end
 end
 qfd_native59_compute_service old(
 .ck_context(clk),.ck_service(clk),.ck_format(clk),.ck_record(clk),.ck_qtag(clk),.ck_x3(clk),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd[0]?cmd:380'd0),
 .native_issue(issue),.kv_we(we),.kv_waddr(wa),.kv_wdata(wd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
 .x3(o_x3),.x3_identity(o_xid),.x3_generation(o_xg),.vm_q_epoch(o_qe),.vm_q_start(o_qs),.q_committed(q_committed),.q_fault(1'b0),.q(q),
 .q_slot(qslot),.q_slot_beat(qb),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(o_tv),.native_tx_payload(o_td),
 .native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.vm_ar(vm_ar),
 .write_commit_v(raw_v),.write_commit_line(raw_line),.write_commit_mask(raw_mask),.visibility_slot(visibility_slot),
 .complete_slot(complete_slot),.completed(o_done),.native_ret(o_ret),.fault(o_fault));
 // ------------------------------------------------------------------ NEW DUT + the real embedding provider
 // Source-side sys_face request advanced1, through the exact two-edge pin landing.
 wire qs_source=(c>=QS0-3+LATE_PREFETCH&&c<QS0+29+LATE_PREFETCH);
 wire[4:0]qb_source=5'(c-(QS0-3+LATE_PREFETCH));
 wire safe_qslot;wire[4:0]safe_qbeat;wire qs_fault,qb_fault;
 ot_qfd_land #(.W(1),.FIRST(1))u_qs(.ckf(clk),.ea(cyc>=21),.i(qs_source),.ck(clk),.rs(rst_n),.k(3'd3),.o(safe_qslot),.fault(qs_fault));
 ot_qfd_land #(.W(5),.FIRST(1))u_qb(.ckf(clk),.ea(cyc>=21),.i(qb_source),.ck(clk),.rs(rst_n),.k(3'd3),.o(safe_qbeat),.fault(qb_fault));
 wire[547:0]dd_landed=qwire[26][547]?qwire[26]:dd;
 wire[519:0]dr;wire n_tv,n_done,n_fault;wire[58:0]n_xid;wire[1:0]n_xg;wire[523:0]n_x3;wire[547:0]n_td;wire[94:0]n_ret;
 wire e_cre,e_sre;wire[23:0]e_caddr;wire[17:0]e_saddr;wire[511:0]e_cq;wire[15:0]e_sq;wire p_fault;
 qfd_native59_dv_service #(.MUT(MUT),.SAFE(SAFE))dut(
 .ck(clk),.ck_fmt(clk),.ck_qbuf(clk),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .dd_i(dd_landed),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
 .x3(n_x3),.x3_identity(n_xid),.x3_generation(n_xg),
 .q_slot(safe_qslot),.q_slot_beat(safe_qbeat),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(n_tv),.native_tx_payload(n_td),
 .native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr),
 .emb_code_re(e_cre),.emb_code_addr(e_caddr),.emb_scale_re(e_sre),.emb_scale_addr(e_saddr),.emb_code_q(e_cq),.emb_scale_q(e_sq),
 .visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(n_done),.native_ret(n_ret),.fault(n_fault));
 qfd_embedding_word_provider prov(.ck(clk),.rst_n(rst_n),.word_v(pw_v),.word_data(pw_data),.word_token(ETOK),.word_index(pw_idx),
 .word_scale(pw_scale),.word_epoch(EEP),.expected_word_slot(pw_v),.expected_token(ETOK),.expected_word(pw_idx),.expected_scale(pw_scale),
 .expected_epoch(EEP),.fill_begin(fill_begin),.fill_token(ETOK),.fill_epoch(EEP),.core_start(core_start),.core_token(ETOK),.core_epoch(EEP),
 .embed_code_re(e_cre),.embed_code_addr(e_caddr),.embed_code_q(e_cq),.embed_scale_re(e_sre),.embed_scale_addr(e_saddr),.embed_scale_q(e_sq),
 .fault(p_fault));
 // ------------------------------------------------------------------ recorders and comparisons
 reg[583:0]ox3[0:7];reg[31:0]ox3c[0:7];integer nox3=0,nnx3=0;
 reg[547:0]otx[0:63];reg[31:0]otxc[0:63];integer notx=0,nntx=0;
 reg[519:0]oar[0:63];reg[31:0]oarc[0:63];integer noar=0,nnar=0,nemb=0;
 integer errs=0,o_done_c=-1,n_done_c=-1;reg[94:0]o_ret_d=0;
 integer k;reg[511:0]exq;
 integer nqw=0,nqr=0;reg[2:0]faultseen=0;reg[511:0]seen_q=0;integer sl,sa;
 always @(posedge clk)if(rst_n)begin
  if({lane_fault,qs_fault,qb_fault}!=faultseen)begin $display("QLANDING_FAULT cycle%0d data%0d qs%0d qb%0d",cyc,lane_fault,qs_fault,qb_fault);err("production forwarded landing fault");faultseen={lane_fault,qs_fault,qb_fault};end
  if(qwire[26][547])begin
   nqw=nqw+1;if(nqw==1)$display("QTRACE_FIRST cycle%0d",cyc);
   if(qwire[26]!==qdd_source[cyc-(IDEAL_CONTROL?16:20)])err("Q landing differs from selected age (GEN20/control16)");
   for(sl=0;sl<8;sl=sl+1)if(qwire[26][537+sl])begin
    sa=qwire[26][345+24*sl+:24];
    if(sa>=512||seen_q[sa]||qwire[26][89+32*sl+:32]!==qgold[sa])err("landed Q seat coverage/data");
    seen_q[sa]=1;
   end
  end
  if(safe_qslot)begin
   nqr=nqr+1;if(nqr==1)$display("QREQUEST_FIRST cycle%0d beat%0d",cyc,safe_qbeat);
   if(c!=QS0-1+LATE_PREFETCH+safe_qbeat)err("Q request landing is not source+2 edges");
  end
 end

 task automatic err(input [8*64-1:0] what);begin errs=errs+1;if(errs<12)$display("N59DV_ERR cycle %0d: %0s",cyc,what);end endtask
 always @(posedge clk)if(rst_n)begin
  o_ret_d<=o_ret;
  // commit_count [93:78] moves with the physical landing edge (LAND_EDGES, not the old VM pins): checked at the end
  if(cyc>1605&&({n_ret[94],n_ret[77:0]}!=={o_ret_d[94],o_ret_d[77:0]}))err("native_ret(NEW,t+1) != native_ret(OLD,t)");
  if(o_x3[523])begin ox3[nox3]<={o_xg,o_xid,o_x3};ox3c[nox3]<=cyc;nox3<=nox3+1;end
  if(n_x3[523])begin
   if(nnx3>=nox3||{n_xg,n_xid,n_x3}!==ox3[nnx3]||cyc!=ox3c[nnx3]+1)err("x3 word differs from OLD (or not +1 edge)");
   if(n_xid!==TAG||n_xg!=2'd1)err("x3 identity");
   nnx3<=nnx3+1;
  end
  if(o_tv)begin otx[notx]<=o_td;otxc[notx]<=cyc;notx<=notx+1;end
  if(n_tv)begin
   if(nntx>=notx||n_td!==otx[nntx]||cyc!=otxc[nntx]+1)err("native_tx_payload differs from OLD (or not +1 edge)");
   if(n_td[542:539]==4'd2)begin
    for(k=0;k<16;k=k+1)exq[32*k+:32]=qval(16*n_td[516:512]+k);
    if(n_td[511:0]!==exq)err("Q beat != element values (packing)");
   end
   nntx<=nntx+1;
  end
  if(vm_ar[519])begin oar[noar]<=vm_ar;oarc[noar]<=cyc;noar<=noar+1;end
  if(dr[519]&&!dr[518])begin
   if(nnar>=noar||dr!==oar[nnar]||cyc!=oarc[nnar]+2)err("dr_o group 0 differs from OLD vm_ar (or not +2 edges)");
   for(k=0;k<16;k=k+1)exq[32*k+:32]=rval(nnar,k);
   if(dr[511:0]!==exq||dr[516:512]!=5'(nnar))err("attention result data/beat");
   nnar<=nnar+1;
  end
  if(dr[519]&&dr[518])begin
   if(cyc!=1600+EMB+6+nemb)err("embedding word not on its static edge");
   if(nemb<64)begin if(dr[517:512]!=6'(nemb)||dr[511:0]!==erow(nemb))err("embedding code word");end
   else if(dr[517:512]!=0||dr[511:0]!=={496'd0,ESCALE})err("embedding scale word");
   nemb<=nemb+1;
  end
  if(o_done)o_done_c<=cyc;
  if(n_done)n_done_c<=cyc;
  if(o_fault&&cyc<1600+EMB)err("OLD fault");
  if(p_fault)err("provider fault");
 end
 always @(posedge clk)if(cyc==1600+EMB+80)begin
  if(BAD_Q!=0)begin
   if(!n_fault||n_done_c!=-1)begin $display("N59DV_FAIL BAD_Q: missing Q seat did not fault / still completed");$fatal(1);end
   $display("N59DV_PASS BAD_Q missing Q dd word -> sticky fault, no completion");$finish;
  end else begin
   if(n_fault)err("NEW fault");
   if(nqw!=64||nqr!=32||!(&seen_q))err("Q trace or request coverage");
   if(o_done_c<0||n_done_c!=o_done_c+1)err("completion edge");
   if(n_ret[93:78]!=16'd32||o_ret[93:78]!=16'd32)err("commit count");
   if(nox3!=4||nnx3!=4||notx!=33||nntx!=33||noar!=32||nnar!=32||nemb!=65)err("counts");
   if(errs!=0)begin
    $display("N59DV_FAIL errors=%0d x3 %0d/%0d tx %0d/%0d ar %0d/%0d emb %0d done %0d/%0d fault %0d",errs,nox3,nnx3,notx,nntx,noar,nnar,nemb,o_done_c,n_done_c,n_fault);
    $fatal(1);
   end
   $display("QREADY_LANDING_PASS 512 actual seats 32 requests Qage%0d/QSage2, IDEAL_CONTROL%0d production_bound=false",IDEAL_CONTROL?16:20,IDEAL_CONTROL);
   $display("N59DV_PASS x3=%0d tx=%0d(1 CMD+32 Q) ar=%0d bit-exact vs OLD (+1/+1/+2 edges), native_ret every edge, done %0d->%0d, emb group-1 words=%0d at cmd+6..+70",
            nnx3,nntx,nnar,o_done_c,n_done_c,nemb);
   $finish;
  end
 end
endmodule
