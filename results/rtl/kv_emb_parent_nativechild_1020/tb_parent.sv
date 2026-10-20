`timescale 1ns/1ps
module tb_parent;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=1;reg [98:0] ctx=0;reg slot=0;reg[72:0] ctl=0;
 reg[298:0] a=0,b=0,c=0,d=0;
 wire nv,ov,ns,os,nf,of;wire[547:0] np,op;wire[17:0] nt,ot;wire[15:0] ne,oe;
 qkd_kvs_emb_ctx_n32child dut(.ck(ck),.rst_n(rst_n),.i_ctx(ctx),.d2d__emb_tx_slot(slot),.i_ctl(ctl),.i_hroot_WS(a),.i_hroot_WN(b),.i_hroot_ES(c),.i_hroot_EN(d),.rowtx__emb_tx_v(nv),.rowtx__emb_tx_payload(np),.px_st(ns),.px_tok(nt),.px_tep(ne),.emb_fault(nf));
 qkd_kvs_emb_ctx_bound_reference #(.NATIVE32(1),.PIPE_JOIN(1)) gold(.ck(ck),.rst_n(rst_n),.i_ctx(ctx),.d2d__emb_tx_slot(slot),.i_ctl(ctl),.i_hroot_WS(a),.i_hroot_WN(b),.i_hroot_ES(c),.i_hroot_EN(d),.rowtx__emb_tx_v(ov),.rowtx__emb_tx_payload(op),.px_st(os),.px_tok(ot),.px_tep(oe),.emb_fault(of));
 integer checks=0,errors=0,beats=0,starts=0,words=0,warm=0,seed=17193;
 reg initialized=0;
 always @(negedge ck) begin
  if(!rst_n)warm=0;else warm=warm+1;
  if(initialized && warm>0)begin
   checks++;
   // Identity and payload fields are meaningful on their registered valid.
   if({nv,ns,nf}!=={ov,os,of} || ((nv||ov) && np!==op) ||
      ((ns||os) && {nt,ne}!=={ot,oe}))begin errors++;if(errors<8)$display("DIFF parent t=%0t n=%b/%b o=%b/%b",$time,nv,nf,ov,of);end
   if(nv)beats++;if(ns)starts++;if(dut.w_v)words++;
   if(dut.u_ctx.pending_valid[4] !== dut.u_ctx.pending_valid[0])
    $fatal(1,"FAIL parent selector copy not mature before use");
  end
 end
 task tick;begin @(negedge ck);#0.01;end endtask
 task quiet;begin ctx=0;slot=0;ctl=0;a=0;b=0;c=0;d=0;end endtask
 task reset;begin quiet();rst_n=0;repeat(7)tick();initialized=1;rst_n=1;repeat(30)tick();end endtask
 function automatic[98:0] record(input integer tk,input integer ep);
  record={1'b1,1'b1,5'd0,4'd12,6'd63,16'(ep),5'd0,2'd0,16'(ep),6'd0,18'(tk),13'd0,6'd0};
 endfunction
 function automatic[255:0] payload(input integer tk,input integer beat);
  for(integer j=0;j<8;j++)payload[j*32+:32]=32'(tk*113+beat*997+j);
 endfunction
 task row(input integer tk,input integer ep,input integer gaps);
  integer n,guard;reg[298:0] rec;
  begin
   // One contiguous compiler calendar supplies 128 code halves + one scale.
   ctl={1'b1,2'd1,38'd0,8'd129,16'd20,8'd0};tick();ctl=0;repeat(4)tick();
   ctx=record(tk,ep);guard=0;
   while(!gold.px_st && guard<100)begin tick();guard++;end
   if(guard==100)$fatal(1,"FAIL parent no admitted context");
   ctx=0;guard=0;
   while(!gold.u_join.slot && guard<100)begin tick();guard++;end
   if(guard==100)$fatal(1,"FAIL parent no calendar slot");
   for(n=0;n<129;n++)begin
    rec={16'(ep),1'(n==128),1'(n%2),6'(n/2),18'(tk),(n==128?256'h3f80:payload(tk,n)),1'b1};
    a=0;b=0;c=0;d=0;
    case(n%4)0:a=rec;1:b=rec;2:c=rec;3:d=rec;endcase
    tick();
   end
   a=0;b=0;c=0;d=0;repeat(25)tick();
   for(n=0;n<65;n++)begin slot=1;tick();slot=0;if(gaps)repeat(n%gaps)tick();end
   slot=0;repeat(20)tick();
   if(nf)$fatal(1,"FAIL parent legal row fault token=%0d",tk);
  end
 endtask
 initial begin
  // Permit independent random power-up state before a real reset assertion.
  repeat(3)tick();
  reset();row(17,41,0);row(19,42,3);
  reset();row(221,7,2);
  // Repeated held owner, unrelated kind, malformed owner, and cold reset.
  ctx=record(221,7);repeat(20)tick();ctx[91:88]=13;repeat(10)tick();
  reset();ctx=record(42,3);ctx[26:21]=1;repeat(20)tick();
  reset();row(991,108,0);
  slot=1;tick();slot=0;repeat(20)tick();
  if(!nf)$fatal(1,"FAIL parent missing 66th-slot fault");
  reset();ctx=record(777,123);repeat(100)tick();
  // No return words: row stays open after the 66-edge minimum gap.
  ctx=record(778,124);repeat(30)tick();
  if(!nf)$fatal(1,"FAIL parent missing open-row overlap fault");
  // Abort an armed row, holding the valid owner through reset and first use.
  ctx=record(881,127);rst_n=0;repeat(7)tick();rst_n=1;repeat(100)tick();
  if(nf)$fatal(1,"FAIL parent held-context cold first-use fault");
  quiet();repeat(15)tick();
  if(checks<900||beats<260||starts<4||words<260)$fatal(1,"FAIL parent coverage checks=%0d beats=%0d starts=%0d words=%0d",checks,beats,starts,words);
  if(errors)$fatal(1,"FAIL parent mismatches=%0d",errors);
  $display("PASS EMB_PARENT_NATIVECHILD checks=%0d beats=%0d starts=%0d words=%0d",checks,beats,starts,words);$finish;
 end
endmodule
