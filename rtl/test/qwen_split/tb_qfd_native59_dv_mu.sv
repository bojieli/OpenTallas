`timescale 1ns/1ps
// tb_qfd_native59_dv_mu -- MU-DQ-D2DUSER (10-19) bench: the D2D attention user tag on the compute die.
// DUT4 = qfd_native59_dv_service #(NU 4) runs NOP attention operations of 4 users back to back on one compiled timeline
// (one operation per P edges, the calendar's mixed-user order: u0L0 u1L0 u0L1 u2L0 u0L2 u3L0 u0L3 u1L1, then the next
// tokens).  Each op is driven at the service's pins exactly as the die drives them: the head context (layer_context_v /
// stage / token / position with the head-start user on position[17:16], qfd_tt_ctlm_dv native_pos), the slice dd words
// (K/V of the op's position, Q of the op), the D2D slots (CMD, Q x 32, RESULT x 32, STATUS) and the HOST face (user 0's
// epoch / tag only, held across filler ops as the closed face holds it).
// The bench is the KV die's seam: every CMD / Q record the DUT emits must carry the epoch the KV die expects for that
// user-step (MU convention {seq14, user2}: the HOST allocator's per-user sequence SEQ0 + n, n = the user's token index),
// the op's layer and beat; the KV side answers RESULT x 32 + STATUS with ITS epoch for the op (the record endpoint must
// accept them -> returns matched).  Per op: 1 CMD + 32 Q out (tags checked on every beat), 32 dr result words with the
// op's data, one completion, KVN x3 identity epoch = the op's.  No fault anywhere.
// DUT1 = the same block at NU 1, fed user 0's ops only (filler windows idle): during every user-0 op DUT4's tx records,
// dr words and x3 words equal DUT1's on the same edges (user 0 = single user).
// Cases: RET_BAD=1 the KV side answers user 2's op with user tag 1 -> DUT4 must fault and that op must not complete.
//        MUT 5 (m7, = MU-TOK-KV's m7) user 3's CMD/Q carry user tag 0;  MUT 6 the filler sequence never advances  -> FAIL.
// Pass line N59MU_PASS ...; failure N59MU_FAIL ... and exit != 0.
module tb_qfd_native59_dv_mu #(parameter integer MUT=0,RET_BAD=0)(input wire clk);
 localparam integer NOP=14,P=240,B0=10;
 localparam[13:0]SEQ0=14'd9;
 localparam[379:0]TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg[31:0]cyc=0;
 always @(posedge clk)cyc<=cyc+1;
 wire rst_n=cyc>=4;
 // ------------------------------------------------------------------ the op list (user, layer); n = the user's token index
 integer op_u[0:NOP-1],op_l[0:NOP-1],op_n[0:NOP-1],op_n0[0:NOP-1];
 integer ii,cnt[0:3],last0;
 initial begin
  op_u[0]=0;op_l[0]=0; op_u[1]=1;op_l[1]=0; op_u[2]=0;op_l[2]=1; op_u[3]=2;op_l[3]=0; op_u[4]=0;op_l[4]=2;
  op_u[5]=3;op_l[5]=0; op_u[6]=0;op_l[6]=3; op_u[7]=1;op_l[7]=1; op_u[8]=0;op_l[8]=0; op_u[9]=2;op_l[9]=1;
  op_u[10]=1;op_l[10]=0; op_u[11]=3;op_l[11]=1; op_u[12]=0;op_l[12]=1; op_u[13]=3;op_l[13]=0;
  for(ii=0;ii<4;ii=ii+1)cnt[ii]=-1;
  last0=0;
  for(ii=0;ii<NOP;ii=ii+1)begin
   if(op_l[ii]==0)cnt[op_u[ii]]=cnt[op_u[ii]]+1;
   op_n[ii]=cnt[op_u[ii]];
   if(op_u[ii]==0)last0=op_n[ii];
   op_n0[ii]=last0;
  end
 end
 function automatic [17:0] otok(input integer u,input integer n);otok=18'(1000+5000*u+n);endfunction
 function automatic [17:0] opos(input integer u,input integer n);opos=18'(255+64*u+n);endfunction
 function automatic [15:0] kv_epoch(input integer u,input integer n);kv_epoch={SEQ0+14'(n),2'(u)};endfunction
 // ------------------------------------------------------------------ payload functions (as tb_qfd_native59_dv_service)
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
 function automatic [23:0] address(input integer k,input integer d,input integer p);
  if(k==0)address=24'(((p/16)*128+d)*16+p%16);
  else address=24'(1048576+p*128+d);
 endfunction
 function automatic [31:0] qval(input integer e,input integer o);qval=32'(e)*32'h9E3779B1+32'h3F800007+32'(o)*32'h01000193;endfunction
 function automatic [31:0] rval(input integer b,input integer j,input integer o);rval=32'(b*16+j)*32'h85EBCA6B+32'h1234567^32'(o*977);endfunction
 function automatic integer qperm(input integer n);qperm=(n*37+11)%512;endfunction
 function automatic integer wkind(input integer g);wkind=(g<2)?1:0;endfunction
 function automatic integer wbase(input integer g);wbase=(g==1||g==3)?64:0;endfunction
 // ------------------------------------------------------------------ stimulus (combinational in cyc)
 integer c,k,r,i,j,ll,pp,w,u,lay,n;
 reg context_v,kvslot,xslot,qslot,txslot,rxslot,rxv,visibility_slot,complete_slot,in_op;
 reg[5:0]stage;reg[17:0]token,position;reg[379:0]cmd;
 reg[1:0]kvindex;reg[4:0]qb,tb,rb;reg[3:0]tk,rk;reg[547:0]rxdata,dd;
 reg[15:0]he;reg[58:0]htag;reg[15:0]kep;
 always @*begin
  c=cyc;k=(c>=B0)?(c-B0)/P:0;r=(c>=B0)?(c-B0)%P:-1;in_op=(c>=B0)&&k<NOP;
  if(!in_op)k=NOP-1;
  u=op_u[k];lay=op_l[k];n=op_n[k];
  context_v=0;kvslot=0;xslot=0;qslot=0;txslot=0;rxslot=0;rxv=0;visibility_slot=0;complete_slot=0;
  cmd=0;kvindex=0;qb=0;tb=0;rb=0;tk=0;rk=0;rxdata=0;dd=0;
  stage=6'(lay+1);token=otok(u,n);position={2'(u),opos(u,n)[15:0]};
  // HOST face: user 0's current token context only (held across filler ops)
  he={SEQ0+14'(op_n0[k]),2'd0};htag={he,6'd0,otok(0,op_n0[k]),opos(0,op_n0[k])[12:0],6'd0};
  kep=kv_epoch(u,n);if(RET_BAD!=0&&u==2)kep={kep[15:2],2'd1};
  if(in_op)begin
   if(r==5)context_v=1;
   for(i=0;i<4;i=i+1)begin
    w=(i==0)?9:(i==1)?17:(i==2)?26:35;
    if(r>=w&&r<w+8)begin
     j=r-w;dd[547]=1;dd[546:545]=(wkind(i)==1)?2'd2:2'd1;dd[544:537]=8'hff;
     for(ll=0;ll<8;ll=ll+1)begin pp=((8*j+ll)*17)%64;
      dd[345+24*ll+:24]=address(wkind(i),wbase(i)+pp,int'(opos(u,n)));dd[89+32*ll+:32]=decode(code(wkind(i),k,wbase(i)+pp));end
    end
   end
   if(r>=44&&r<108)begin
    j=r-44;dd[547]=1;dd[546:545]=2'd0;dd[544:537]=8'hff;
    for(ll=0;ll<8;ll=ll+1)begin dd[345+24*ll+:24]=24'(qperm(8*j+ll));dd[89+32*ll+:32]=qval(qperm(8*j+ll),k);end
   end
   if(r>=112&&r<119)begin i=r-112;kvslot=i<4;kvindex=2'(i);xslot=i>=3;end
   if(r==122)cmd=TEMPLATE;
   if(r==123)begin txslot=1;tk=1;tb=0;end
   if(r>=126&&r<159)begin i=r-126;qslot=i<32;qb=5'(i);txslot=i>0;tk=2;tb=5'(i-1);end
   if(r>=160&&r<192)begin
    i=r-160;rxv=1;rxslot=1;rk=3;rb=5'(i);
    rxdata[547:512]={5'd0,4'd3,6'(lay),kep,5'(i)};for(j=0;j<16;j=j+1)rxdata[32*j+:32]=rval(i,j,k);
   end
   if(r==210)visibility_slot=1;
   if(r==211)begin rxv=1;rxslot=1;rk=4;rb=0;rxdata={5'd0,4'd4,6'(lay),kep,5'd0,507'd0,5'b01001};end
   if(r==213)complete_slot=1;
  end
 end
 // DUT1 sees user 0's ops only (every pin idle in a filler window)
 wire m0=(u==0);
 // ------------------------------------------------------------------ DUTs
 wire[519:0]dr4,dr1;wire tv4,tv1,dn4,dn1,f4,f1;wire[58:0]xid4,xid1;wire[1:0]xg4,xg1;wire[523:0]x34,x31;wire[547:0]td4,td1;wire[94:0]ret4,ret1;
 qfd_native59_dv_service #(.MUT(MUT),.NU(4),.MU_SEQ0(SEQ0))dut4(
 .ck(clk),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(he),.host_tag(htag),.host_generation(2'd1),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .dd_i(dd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
 .x3(x34),.x3_identity(xid4),.x3_generation(xg4),
 .q_slot(qslot),.q_slot_beat(qb),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(tv4),.native_tx_payload(td4),
 .native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr4),
 .emb_code_re(),.emb_code_addr(),.emb_scale_re(),.emb_scale_addr(),.emb_code_q(512'd0),.emb_scale_q(16'd0),
 .visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(dn4),.native_ret(ret4),.fault(f4));
 qfd_native59_dv_service #(.NU(1))dut1(
 .ck(clk),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(he),.host_tag(htag),.host_generation(2'd1),
 .layer_context_v(context_v&&m0),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(m0?cmd:380'd0),
 .dd_i(m0?dd:548'd0),.kv_word_slot(kvslot&&m0),.kv_word_index(kvindex),.kv_x3_slot(xslot&&m0),
 .x3(x31),.x3_identity(xid1),.x3_generation(xg1),
 .q_slot(qslot&&m0),.q_slot_beat(qb),.tx_slot(txslot&&m0),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(tv1),.native_tx_payload(td1),
 .native_rx_v(rxv&&m0),.native_rx_payload(m0?rxdata:548'd0),.rx_slot(rxslot&&m0),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr1),
 .emb_code_re(),.emb_code_addr(),.emb_scale_re(),.emb_scale_addr(),.emb_code_q(512'd0),.emb_scale_q(16'd0),
 .visibility_slot(visibility_slot&&m0),.complete_slot(complete_slot&&m0),.completed(dn1),.native_ret(ret1),.fault(f1));
 // ------------------------------------------------------------------ the KV seam checks
 integer errs=0,tagerr=0,nrec[0:3],ncmd[0:3],nq[0:3],nres[0:NOP-1],ndone[0:NOP-1],nx3[0:NOP-1],nid=0,first_fault=-1;
 integer ko,ro,b,q;reg[511:0]exq;reg[15:0]ee;
 initial for(q=0;q<4;q=q+1)begin nrec[q]=0;ncmd[q]=0;nq[q]=0;end
 initial for(q=0;q<NOP;q=q+1)begin nres[q]=0;ndone[q]=0;nx3[q]=0;end
 task automatic err(input [8*72-1:0] what);begin errs=errs+1;if(errs<16)$display("N59MU_ERR cycle %0d op %0d: %0s",cyc,ko,what);end endtask
 always @(posedge clk)if(rst_n&&cyc>=B0)begin
  // outputs at this edge belong to the op of the current cycle (every DUT output is < P/2 edges after its slot)
  ko=(cyc-B0)/P;ro=(cyc-B0)%P;if(ko>=NOP)ko=NOP-1;
  ee=kv_epoch(op_u[ko],op_n[ko]);
  if(tv4)begin
   if(td4[547:543]!=0||td4[538:533]!=6'(op_l[ko])||(td4[542:539]!=4'd1&&td4[542:539]!=4'd2))err("tx record kind / layer");
   if(td4[532:517]!=ee)begin tagerr=tagerr+1;
    if(tagerr<8)$display("N59MU_TAG_ERR cycle %0d op %0d user %0d kind %0d beat %0d epoch %04h want %04h",cyc,ko,op_u[ko],td4[542:539],td4[516:512],td4[532:517],ee);end
   if(td4[542:539]==4'd1)ncmd[op_u[ko]]=ncmd[op_u[ko]]+1;
   if(td4[542:539]==4'd2)begin
    nq[op_u[ko]]=nq[op_u[ko]]+1;
    for(b=0;b<16;b=b+1)exq[32*b+:32]=qval(16*td4[516:512]+b,ko);
    if(td4[511:0]!==exq)err("Q beat data");
   end
   nrec[op_u[ko]]=nrec[op_u[ko]]+1;
  end
  if(dr4[519]&&!dr4[518])begin
   for(b=0;b<16;b=b+1)exq[32*b+:32]=rval(dr4[516:512],b,ko);
   if(dr4[511:0]!==exq)err("attention result word (returns not matched to the op)");
   nres[ko]=nres[ko]+1;
  end
  if(x34[523])begin if(xid4[58:43]!=ee||xid4[36:19]!=otok(op_u[ko],op_n[ko]))err("KVN x3 identity epoch / token");nx3[ko]=nx3[ko]+1;end
  if(dn4)ndone[ko]=ndone[ko]+1;
  if(f4&&first_fault<0)begin first_fault=cyc;$display("N59MU_FAULT first at cycle %0d op %0d user %0d",cyc,ko,op_u[ko]);end
  if(f1)err("DUT1 (NU 1) fault");
  // user 0 = single user: DUT4 == DUT1 on every edge of a user-0 op
  if(op_u[ko]==0&&ro>0)begin
   if(tv4!==tv1||(tv4&&td4!==td1))err("user-0 tx record != NU 1");
   if(dr4!==dr1)err("user-0 dr word != NU 1");
   if(x34!==x31||(x34[523]&&{xg4,xid4}!=={xg1,xid1}))err("user-0 x3 != NU 1");
   if(dn4!==dn1)err("user-0 completion != NU 1");
   nid=nid+1;
  end
 end
 integer s0,s1;
 always @(posedge clk)if(cyc==B0+NOP*P+20)begin
  s0=0;s1=0;
  for(q=0;q<NOP;q=q+1)begin
   if(RET_BAD==0||op_u[q]!=2)begin if(nres[q]!=32||ndone[q]!=1||nx3[q]!=4)s0=s0+1;end
   else if(ndone[q]!=0)s1=s1+1;
  end
  if(RET_BAD!=0)begin
   if(first_fault<0||s1!=0||ko<0)begin $display("N59MU_FAIL RET_BAD: wrong-user RESULT did not fault (fault %0d) or the op completed (%0d)",first_fault,s1);$fatal(1);end
   $display("N59MU_PASS RET_BAD user-2 RESULT with user tag 1 -> sticky fault at %0d, no completion",first_fault);$finish;
  end else begin
   if(f4)err("DUT4 fault");
   if(tagerr!=0)err("user tags");
   if(s0!=0)err("per-op results / completion / KVN counts");
   for(q=0;q<4;q=q+1)if(ncmd[q]==0||nq[q]!=32*ncmd[q])err("CMD / Q counts per user");
   if(errs!=0)begin
    $display("N59MU_FAIL errors=%0d tag_errors=%0d first_fault=%0d records u0..3 %0d/%0d/%0d/%0d",errs,tagerr,first_fault,nrec[0],nrec[1],nrec[2],nrec[3]);
    $fatal(1);
   end
   $display("N59MU_PASS ops=%0d users=4 CMD u0..3 %0d/%0d/%0d/%0d Q %0d/%0d/%0d/%0d (every beat tagged {seq,user}); results 32/op matched, 1 completion/op, KVN identity tagged; user-0 == NU 1 on %0d edges",
            NOP,ncmd[0],ncmd[1],ncmd[2],ncmd[3],nq[0],nq[1],nq[2],nq[3],nid);
   $finish;
  end
 end
endmodule
