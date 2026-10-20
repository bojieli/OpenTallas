`timescale 1ns/1ps
// QW-N59-5 (10-20) Q.STA.N59.1 -- Q-READY AGE certificate of the hardened native59 split.
// The die schedule (QW-QREADY, codex/qwen-qready-programme-1019) delivers the W5 Q words to native59.dd_i over a 20-edge
// path (age 20) and admits the CMD / q_slot from a compiled calendar against native59's INTERNAL Q write -> Q read
// relation (dd_i Q word -> qseen / q_committed at the request -> SRAM read at q_slot).  The split must keep that relation
// in the bank: bank ports dd_i / q_slot at BOFF 0, service ports SOFF later, outputs ROFF later.
// This bench = the DV programme of tb_qfd_native59_dv_service (r1 reference qfd_native59_dv_service_r1 SAFE 2 EMB_RELAY 1)
// with the 64-word Q burst shifted +QSHIFT edges toward the CMD (+QSHIFT=n plusarg), the split (n59_split_shadow) in
// lockstep at every edge INCLUDING fault behaviour.  +QLATE=1 = timing mutant: only the Q-kind dd words reach the split
// one edge late (a 21-edge Q path); it must FAIL lockstep at the r1 boundary shift.
// Lines: N59QAGE r1 ... (per run), N59QAGE_LOCKSTEP_PASS / N59QAGE_LOCKSTEP_FAIL.  Driver: run_n59_qage.sh.
module tb_n59_qage #(parameter integer MUT=0,BAD_Q=0,SAFE=2,LATE_PREFETCH=0,EMBR=1,SPLIT_MUT=0,QB_MUT=0,LP_MUT=0,SPL_SOFF=3,SPL_BOFF=0,SPL_ROFF=4)(input wire clk);
 integer QSHIFT=0,QLATE=0;
 initial begin if(!$value$plusargs("QSHIFT=%d",QSHIFT))QSHIFT=0;if(!$value$plusargs("QLATE=%d",QLATE))QLATE=0;end
 // EMBR (QW-N59-3 safe4): DUT EMB_RELAY; the embedding words land one edge later (cmd+7..+71), group 0 unchanged
 localparam integer HEADS=1;
 localparam[379:0]TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 localparam[58:0]TAG={16'd9,6'd1,18'd50994,13'd255,6'd0};
 localparam[17:0]ETOK=18'd123457;localparam[15:0]EEP=16'd77;
 reg[31:0]cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 wire rst_n=cyc>=4;
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
 function automatic [31:0] qval(input integer e);qval=32'(e)*32'h9E3779B1+32'h3F800007;endfunction
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
 localparam integer QD0B=44,CMD=122,QS0=126,RX0=160,VIS=210,STS=211,CMP=213,FILL=220,CORE=290,EMB=292;
 integer c,i,j,ll,pp,g,w;
 reg context_v,q_committed,kvslot,xslot,qslot,txslot,rxslot,rxv,visibility_slot,complete_slot;
 reg[5:0]stage;reg[17:0]token,position;reg[379:0]cmd;reg[62:0]issue;
 reg[1:0]kvindex;reg[4:0]qb,tb,rb;reg[3:0]tk,rk;
 reg[63:0]we;reg[1535:0]wa;reg[2047:0]wd;reg[523:0]q;reg[547:0]rxdata,dd;
 // provider stimulus
 reg pw_v,pw_scale,fill_begin,core_start;reg[5:0]pw_idx;reg[511:0]pw_data;
 always @*begin
  c=cyc;
  context_v=(c==5);q_committed=(c>=110);kvslot=0;xslot=0;qslot=0;txslot=0;rxslot=0;rxv=0;visibility_slot=0;complete_slot=0;
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
  // NEW: Q as 64 dd words, permuted element order
  if(c>=QD0B+QSHIFT&&c<QD0B+QSHIFT+64&&!(BAD_Q!=0&&c==QD0B+QSHIFT+17))begin
   j=c-(QD0B+QSHIFT);dd[547]=1;dd[546:545]=2'd0;dd[544:537]=8'hff;
   for(ll=0;ll<8;ll=ll+1)begin dd[345+24*ll+:24]=24'(qperm(8*j+ll));dd[89+32*ll+:32]=qval(qperm(8*j+ll));end
  end
  if(c>=112&&c<119)begin i=c-112;kvslot=i<4;kvindex=2'(i);xslot=i>=3;end
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
 // ------------------------------------------------------------------ NEW DUT + the real embedding provider
 wire safe_qslot=(SAFE==2&&LATE_PREFETCH==0)?(cyc>=QS0-1&&cyc<QS0+31):qslot;
 wire[4:0]safe_qbeat=(SAFE==2&&LATE_PREFETCH==0)?5'(cyc-(QS0-1)):qb;
 wire[519:0]dr;wire n_tv,n_done,n_fault;wire[58:0]n_xid;wire[1:0]n_xg;wire[523:0]n_x3;wire[547:0]n_td;wire[94:0]n_ret;
 wire e_cre,e_sre;wire[23:0]e_caddr;wire[17:0]e_saddr;wire[511:0]e_cq;wire[15:0]e_sq;wire p_fault;
`ifdef N59_R1
 qfd_native59_dv_service_r1 #(.MUT(MUT),.SAFE(SAFE),.EMB_RELAY(EMBR))dut(
 .ck(clk),.rst_n(rst_n),
`else
 qfd_native59_dv_service #(.MUT(MUT),.SAFE(SAFE))dut(
 .ck(clk),.ck_fmt(clk),.ck_qbuf(clk),.rst_n(rst_n),
`endif
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .dd_i(dd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
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

 // mutant: Q-kind dd words to the split one edge late (KV words unchanged)
 reg[547:0]dd_q1=0;
 always @(posedge clk)dd_q1<=(dd[547]&&dd[546:545]==2'd0)?dd:548'd0;
 wire[547:0]dd_s=(QLATE!=0)?((dd[547]&&dd[546:545]==2'd0)?548'd0:dd)|dd_q1:dd;
 // QW-N59-4: lockstep shadow of the hardened split (n59_split_shadow) against the reference DUT above
 integer sh_mism,sh_cmp;
 n59_split_shadow #(.NU(1),.MU_SEQ0(14'd0),.MCTX(0),.EMBR(EMBR),.MUT(SPLIT_MUT),.QB_MUT(QB_MUT),.LP_MUT(LP_MUT),.SOFF(SPL_SOFF),.BOFF(SPL_BOFF),.ROFF(SPL_ROFF))shadow(
 .ck(clk),.rst_n(rst_n),.cmp_en(1'b1),.host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),.layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),.dd_i(dd_s),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),.q_slot(safe_qslot),.q_slot_beat(safe_qbeat),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.emb_code_q(e_cq),.emb_scale_q(e_sq),.visibility_slot(visibility_slot),.complete_slot(complete_slot),
 .r_x3(n_x3),.r_x3_identity(n_xid),.r_x3_generation(n_xg),.r_native_tx_v(n_tv),.r_native_tx_payload(n_td),.r_dr_o(dr),.r_emb_code_re(e_cre),.r_emb_code_addr(e_caddr),.r_emb_scale_re(e_sre),.r_emb_scale_addr(e_saddr),.r_completed(n_done),.r_native_ret(n_ret),.r_fault(n_fault),.mism(sh_mism),.compared(sh_cmp));


 // reference observations: last Q dd word edge, request edge, q_committed rise, fault / completion
 integer last_q=-1,req_e=-1,qc_e=-1,flt_e=-1,done_e=-1,qtf_e=-1;
 always @(posedge clk)if(rst_n)begin
  if(dd[547]&&dd[546:545]==2'd0)last_q<=cyc;
  if(dut.u_core.request_slot&&req_e<0)req_e<=cyc;
  if(dut.u_core.q_committed&&qc_e<0)qc_e<=cyc;
  if(dut.u_core.qtag_fault&&qtf_e<0)qtf_e<=cyc;
  if(n_fault&&flt_e<0)flt_e<=cyc;
  if(n_done&&done_e<0)done_e<=cyc;
 end
 always @(posedge clk)if(cyc==EMB+80)begin
  $display("N59QAGE r1 QSHIFT %0d QLATE %0d last_q_dd %0d q_committed %0d request %0d qtag_fault %0d fault %0d done %0d age_req_minus_lastq %0d split_mism %0d compared %0d",
           QSHIFT,QLATE,last_q,qc_e,req_e,qtf_e,flt_e,done_e,req_e-last_q,sh_mism,sh_cmp);
  if(sh_mism!=0||sh_cmp<100)begin $display("N59QAGE_LOCKSTEP_FAIL QSHIFT %0d QLATE %0d: %0d of %0d edges differ",QSHIFT,QLATE,sh_mism,sh_cmp);$fatal(1);end
  $display("N59QAGE_LOCKSTEP_PASS QSHIFT %0d QLATE %0d: %0d edges, split == r1 (SOFF %0d BOFF %0d ROFF %0d) incl. fault",QSHIFT,QLATE,sh_cmp,SPL_SOFF,SPL_BOFF,SPL_ROFF);
  $finish;
 end
endmodule
