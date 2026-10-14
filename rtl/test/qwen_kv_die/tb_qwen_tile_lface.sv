`timescale 1ns/1ps
// Actual CEXT2 ctl + RPS1/SPLIT1 children, all25 logical child clocks coherent.
module xcache_actual_tile #(parameter integer XLOCAL=0)(
 input wire cc,input wire rst_n,input wire [15:0] tid,input wire go,
 input wire [378:0] ib,input wire [127:0] xl,output wire [3:0] xr,
 output wire [95:0] xa,output wire [20:0] epoch,output wire [511:0] tout,
 output wire tv,output wire fault
);
 wire [69:0] req;wire [2047:0] rqr;wire [3127:0] ld;wire [583:0] lq;
 wire [71:0] le;wire vd,nf;wire [129:0] rm;reg [2659:0] rd=0;
 genvar i;generate for(i=0;i<8;i=i+1) begin assign le[9*i+:9]=lq[73*i+64+:9];end endgenerate
`ifdef XCACHE_TP8
 generate if(XLOCAL==0) begin:choice_ref
 ot_qwen_tile_ctl_tp8_ref ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end else begin:choice
 ot_qwen_tile_ctl_tp8 ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
 end endgenerate
`else
 ot_qwen_tile_ctl #(.XLOCAL(XLOCAL)) ctl(.clk(cc),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.xl(xl),.fault(fault),.cx_xre(xr),.cx_xaddr(xa),.cx_xepoch(epoch),.cx_rreq(req),.cx_rqr(rqr),.cx_ld(ld),.cx_lerr(le),.cx_tvd(vd),.cx_nfault(nf));
`endif
 ot_qwen_tile_kids #(.CODE_BANKS(5),.RPS(0),.MCLK(1),.SPLIT(1)) kids(.clk(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),.rst_n(rst_n),.cx_rreq(req),.cx_rq(),.cx_rqr(rqr),.cx_ld(ld),.cx_lq(lq),.cx_td(512'd0),.cx_tvd(vd),.cx_nfault(nf),.n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(tout),.t_vout(tv),.rom_req_m(rm),.rom_rd(rd));
 integer p,l;always @(posedge cc) for(p=0;p<10;p=p+1) if(rm[13*p+12]) begin
  rd[266*p+:266]<=0;
  for(l=0;l<32;l=l+1) rd[266*p+8*l+:8]<=8'(rm[13*p+:12]+32*(p/5)+l+3*tid+1);
 end
endmodule
// r5 (2026-10-14) tb_qwen_tile_lface: the ACTUAL GT3072 control + CLOSED children with registered admission/credit
// faces (ot_qwen_rom_tile_nkt_tp8_core_lface) in lockstep with the historical reference tile, its query identity and
// numeric words STREAMED through two live-clock queues (ot_qwen_live_credit_queue) whose REGISTERED credits drive
// the coherent family clock enable through LAT-1 live stages.  Checks: every request/epoch/context/version against
// the independent reference, every numeric word, the accepted descriptor bundle (one output stage later), once-only
// in-order delivery of every query tuple and numeric word through the queues, no overflow / credit / admission
// fault, and completion after long consumer stalls that STOP the core clock (including with an admission ACK in
// flight): no deadlock.  Prints the base-edge cost against the mailbox bench (4,568 base edges, same 6 ops).
module tb_qwen_tile_lface;
 parameter integer MUT=0,QMUT=0,LAT=2,DEPTH=5,STALL=1,ALL_SPLITS=0;
 localparam integer TARGET_GT=3072;
 `define REF_ME ref_tile.choice_ref.ctl.u_logic.u_me
 localparam integer QW=1+40+4+96+21+16+32;
 reg [378:0] native_ib[0:3];
 reg incoming=0,expected_mode=0;reg [15:0] current_ctx=0,expected_ctx=0,offered_ctx=0;reg [31:0] expected_ver=0;wire read_mode;wire [15:0] read_ctx;wire [31:0] read_ver;wire op_accept,core_idle;wire [15:0] accepted_ctx;wire [31:0] accepted_ver;wire [378:0] accepted_ib;reg [378:0] expected_accepted_ib=0,exp_ib_d=0;reg accepted_valid=0,accepted_valid_d=0;integer accepts=0,metadata_checks=0,descriptor_checks=0;reg [95:0] load_key=0;reg [15:0] load_ctx=0;reg [31:0] load_ver=0;integer mode_checks=0,resident_checks=0;
 reg clk=0;always #5 clk=~clk;
 wire [39:0] query_seq;wire query_fault,query_issue_v,accept_toggle,admission_fault;reg accept_ack=0;integer base_edges=0;reg [39:0] next_query=0;
 // ---- live queues + registered family enable ----
 wire [1:0] credit;wire en;wire qv,nv;wire [QW-1:0] qt;wire [511:0] nt;wire qfault,nfault;reg ready=1;
 reg allow=1,gate=1;wire hit;always @(negedge clk) gate<=allow&&hit&&en;
 wire cc=clk&&gate;
 reg rst_n=0,go=0,clear=0,lv=0,j_repeat=1;
 reg [15:0] tid=0;reg [378:0] ib=0;reg [20:0] load_epoch=0;
 reg [127:0] lx=0;wire [127:0] cache_x;
 wire [3:0] cr,unused_r;wire [95:0] ca,unused_a;wire [20:0] ep,unused_e;
 wire [511:0] rt,ct;wire rv,cv,rf,cf,cachefault;
 reg [95:0] oracle_addr=0;reg [3:0] oracle_req=0;reg [20:0] oracle_epoch=0;
 reg [127:0] held_ref=0;reg [127:0] raw_ref;
 ot_qwen_live_family_enable #(.N(2),.STAGES(LAT-1)) u_en(.base_clk(clk),.rst_n(rst_n),.credit_q(credit),.run(1'b1),.en(en));
 ot_qwen_live_credit_queue #(.W(QW),.DEPTH(DEPTH),.LAT(LAT),.MUT(QMUT)) u_qq(.base_clk(clk),.rst_n(rst_n),.core_en(gate),
  .produce_v(query_issue_v),.produce_tuple({read_mode,query_seq,cr,ca,ep,read_ctx,read_ver}),.credit_q(credit[0]),
  .consume_ready(ready),.consume_v(qv),.consume_tuple(qt),.fault(qfault));
 ot_qwen_live_credit_queue #(.W(512),.DEPTH(DEPTH),.LAT(LAT),.MUT(QMUT)) u_nq(.base_clk(clk),.rst_n(rst_n),.core_en(gate),
  .produce_v(cv),.produce_tuple(ct),.credit_q(credit[1]),
  .consume_ready(ready),.consume_v(nv),.consume_tuple(nt),.fault(nfault));
 // ---- bench expectation FIFOs (filled from the lockstep-checked core edge, drained by the live pops) ----
 reg [QW-1:0] qexp[0:65535];reg [511:0] nexp[0:4095];integer qw=0,qr=0,nw=0,nr=0,stall_left=0,credit_pause=0,ack_pause=0,max_q=0;
 function automatic [31:0] xv(input [23:0] a);
  xv=32'h3f800000 | (((a*24'd7919)^24'h123456)&23'h7fffff);
 endfunction
 integer l;always @* begin
  raw_ref=held_ref;
  if(|oracle_req) for(integer z=0;z<4;z=z+1) raw_ref[32*z+:32]=xv(oracle_addr[24*z+:24]);
 end
 xcache_actual_tile #(.XLOCAL(0)) ref_tile(cc,rst_n,tid,go,ib,raw_ref,unused_r,unused_a,unused_e,rt,rv,rf);
 wire [127:0] response;
 ot_qwen_rom_tile_nkt_tp8_core_lface #(.MUT(MUT)) u_core(
  .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),
  .rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.x_response(response),
  .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(ct),.t_vout(cv),.fault(cf),
  .cx_xre(cr),.cx_xaddr(ca),.cx_xepoch(ep),.op_context(offered_ctx),.vm_version(32'(100+offered_ctx)),.cx_xjrepeat(read_mode),.cx_xcontext(read_ctx),.cx_xversion(read_ver),.cx_op_accept(op_accept),.cx_accepted_context(accepted_ctx),.cx_accepted_version(accepted_ver),.cx_core_idle(core_idle),.cx_accepted_ib(accepted_ib),.accept_ack_toggle(accept_ack),.accept_transport_fence(1'b0),.cx_accept_toggle(accept_toggle),.cx_admission_fault(admission_fault),.cx_issue_last(),.cx_query_seq(query_seq),.cx_query_fault(query_fault),.cx_query_issue_v(query_issue_v));
 ot_qwen_xcache_context32 cache(
  .load_clk(clk),.core_clk(cc),.rst_n(rst_n),.clear(clear),
  .live_j_repeat(j_repeat),.read_j_repeat(read_mode),.load_j_repeat(xjs==0),
  .load_v(lv),.load_epoch(load_epoch),.read_epoch(ep),.load_context(load_ctx),.read_context(read_ctx),
  .load_version(load_ver),.read_version(read_ver),.load_addr(load_key),.read_addr(ca),
  .load_x(lx),.read_v(cr),.hit(hit),.q_x(response),.fault(cachefault));
 // ---- live side: ACK return, consumer with stalls, pops checked against the expectation FIFOs ----
 reg last_accept_toggle=0;
 always @(posedge clk)begin
  base_edges=base_edges+1;
  if(!rst_n)begin accept_ack<=0;stall_left=0;ready<=1;last_accept_toggle=0;end
  else begin
   accept_ack<=accept_toggle;
   // Consumer stall schedule: periodic short stalls plus a long stall started at every op acceptance, so the core
   // clock stops with queries in flight and with the admission ACK still travelling (ack_q not yet updated).
   if(STALL && accept_toggle!=last_accept_toggle)stall_left=97;
   last_accept_toggle=accept_toggle;
   if(stall_left>0)stall_left=stall_left-1;
   ready<=!STALL || (stall_left==0 && base_edges%23<17);
   if(!gate && allow && hit)begin credit_pause=credit_pause+1;if(u_core.u_ctl.ack_q!=accept_ack)ack_pause=ack_pause+1;end
   if(u_qq.count>max_q)max_q=u_qq.count;
   if(u_qq.pop)begin
    if(qr>=qw)$fatal(1,"live query pop without an issued query");
    if(qt!==qexp[qr%65536])$fatal(1,"live query tuple mismatch at %0d: got %h expected %h",qr,qt,qexp[qr%65536]);
    qr=qr+1;
   end
   if(u_nq.pop)begin
    if(nr>=nw)$fatal(1,"live numeric pop without a produced word");
    if(nt!==nexp[nr%4096])$fatal(1,"live numeric word mismatch at %0d",nr);
    nr=nr+1;
   end
   #1;if(qfault||nfault)$fatal(1,"live queue overflow fault (credit loop broken) q=%0d n=%0d",qfault,nfault);
  end
 end
 integer checks=0,requests=0,misses=0,edges=0,ops=0;
 always @(posedge cc) begin
  edges=edges+1;
  if(!rst_n) begin accepted_valid<=0;accepted_valid_d<=0;oracle_req<=0;next_query=0;expected_mode<=0;expected_ctx<=0;expected_ver<=0;end
  else begin
   if(`REF_ME.go && `REF_ME.ready)begin
    expected_accepted_ib<=ref_tile.choice_ref.ctl.u_logic.ib_i;accepted_valid<=1;
   end
   exp_ib_d<=expected_accepted_ib;accepted_valid_d<=accepted_valid;
   expected_mode<=(`REF_ME.xjs_r==0);expected_ctx<=current_ctx;expected_ver<=32'(100+current_ctx);
   for(l=0;l<4;l=l+1) begin
    oracle_req[l]<=`REF_ME.active && (((`REF_ME.gb+l)>>`REF_ME.split_r)<(TARGET_GT>>`REF_ME.split_r));
    oracle_addr[24*l+:24]<=`REF_ME.xc+((`REF_ME.gb+l)&((1<<`REF_ME.split_r)-1))*`REF_ME.xcs_r;
   end
   oracle_epoch<={`REF_ME.k,`REF_ME.j};
  end
  if(|oracle_req) held_ref<=raw_ref;
  #1;
  if(rst_n) begin
   if(op_accept)next_query=0;
   if(|cr)begin
    if(!query_issue_v || query_seq!==next_query)$fatal(1,"streamed query identity missing or not monotonic");
    next_query=next_query+1;
    qexp[qw%65536]={read_mode,query_seq,cr,ca,ep,read_ctx,read_ver};qw=qw+1;
   end else if(query_issue_v)$fatal(1,"streamed query identity without request");
   if(query_fault||admission_fault)$fatal(1,"query/admission fault");
   if(cr!==oracle_req || (|cr) && (ca!==oracle_addr || ep!==oracle_epoch)) $fatal(1,"actual tile request/epoch mismatch op=%0d",ops);
   if(accepted_valid_d && (MUT!=2))begin
    descriptor_checks=descriptor_checks+1;
    if(accepted_ib!==exp_ib_d)$fatal(1,"production acceptedIB lifetime mismatch");
   end
   if(|cr) begin
    requests=requests+1;
    if(read_mode!==expected_mode || read_ctx!==expected_ctx || read_ver!==expected_ver)$fatal(1,"production request metadata mismatch");
    metadata_checks=metadata_checks+1;
   end
   if(op_accept)begin
    accepts=accepts+1;
    if(accepted_ctx!==current_ctx || accepted_ver!==32'(100+current_ctx))$fatal(1,"production accepted context mismatch");
   end
   if(rv!==cv || rv && rt!==ct) $fatal(1,"actual CEXT2 arithmetic mismatch op=%0d edge=%0d",ops,edges);
   if(cv)begin nexp[nw%4096]=ct;nw=nw+1;end
   if(rf!==cf || cachefault) $fatal(1,"actual tile/cache fault op=%0d",ops);
   if(rv) checks=checks+1;
  end
 end
 integer op,t,k,j,a,kc,tiles,sp,xjs,xb,nout,xks,xcs,w;
 task automatic drain;begin
  // Every issued query and every produced word must leave through the live queues; a stopped core clock that never
  // restarts (deadlock) trips the bound.
  w=0;while((qr!=qw || nr!=nw || `REF_ME.active) && w<20000)begin @(negedge clk);w=w+1;end
  if(w>=20000)$fatal(1,"DEADLOCK: queues/core did not drain (qr=%0d qw=%0d nr=%0d nw=%0d gate=%b en=%b)",qr,qw,nr,nw,gate,en);
 end endtask
 initial begin
  $readmemh("native_profiles.hex",native_ib);
  repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
  for(op=0;op<6+(ALL_SPLITS?16:0);op=op+1) begin
   if(op>=6) begin allow=1;rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);qr=0;qw=0;nr=0;nw=0;end
   current_ctx=16'(op+1);offered_ctx=current_ctx;incoming=0;allow=0;repeat(2) @(negedge clk);clear=1;@(negedge clk);clear=0;
   case(op)
    0:begin tid=0;sp=9;kc=8;tiles=1;nout=768;xjs=0;end
    1:begin tid=127;sp=8;kc=2;tiles=3;nout=4096;xjs=0;end
    2:begin tid=512;sp=7;kc=32;tiles=1;nout=3072;xjs=0;end
    3:begin tid=767;sp=8;kc=6;tiles=3;nout=4096;xjs=0;end
    4:begin tid=511;sp=11;kc=3;tiles=1;nout=16;xjs=17;end
    5:begin tid=703;sp=7;kc=9;tiles=2;nout=4096;xjs=29;end
    default:begin tid=0;sp=op-6;kc=2;tiles=1;nout=128;xjs=5;end
   endcase
   xb=4096+op*10000;xks=1;xcs=kc;
   if(op==5 || op>=6) begin
    xb=24'hFED123;xks=24'hC7D8E9;xjs=24'hABCDE7;xcs=24'hFACE91;
   end
   j_repeat=(xjs==0);
   ib={18'(nout),18'(tiles),18'(kc),1'b0,24'd0,24'(kc*8),24'd8,24'd1,24'(xb),24'(xks),24'(xjs),24'(xcs),3'd0,4'(sp),24'd0,1'b1,24'd0,24'd8,24'd1,1'b0,1'b1,1'b0,1'b0,24'd0};
   if(op<4) begin
    ib=native_ib[op];
    case(op) 0:xb=4096;1:xb=50672;2:xb=4096;3:xb=55280;endcase
   end
   for(k=0;k<kc;k=k+1) for(j=0;j<(j_repeat?1:8);j=j+1) begin
    load_ctx=current_ctx;load_ver=32'(100+current_ctx);load_epoch={18'(k),3'(j)};
    for(l=0;l<4;l=l+1) begin a=xb+((4*tid+l)&((1<<sp)-1))*xcs+k*xks+j*xjs;lx[32*l+:32]=xv(24'(a));load_key[24*l+:24]=24'(a);end
    lv=1;@(negedge clk);
   end
   lv=0;allow=1;repeat(8) @(negedge clk);go=1;wait(op_accept);@(negedge clk);go=0;
   for(t=0;t<3*kc*tiles*8+300 || `REF_ME.active;t=t+1) begin
    if(t>200000)$fatal(1,"DEADLOCK: op %0d did not finish",op);
    if(op==5 && t==20) begin clear=1;@(negedge clk);clear=0;end
    if(!hit) begin
     misses=misses+1;load_epoch=ep;
     for(l=0;l<4;l=l+1) lx[32*l+:32]=xv(ca[24*l+:24]);
     load_ctx=read_ctx;load_ver=read_ver;load_key=ca;lv=1;repeat(3) @(negedge clk);lv=0;
    end
    if(op==5 && !incoming && |cr && ep[2:0]==6 && ep[20:3]==0)begin
     incoming=1;j_repeat=1;ib=native_ib[0];offered_ctx=current_ctx+16'h4000;mode_checks=mode_checks+1;
     allow=0;repeat(2)@(negedge clk);
     load_ctx=current_ctx+16'h4000;load_ver=read_ver+1;load_key=ca;load_epoch=ep;
     lx=128'h40000000400000004000000040000000;lv=1;@(negedge clk);lv=0;
     #1;if(hit)$fatal(1,"resident context/version reused for old request");
     resident_checks=resident_checks+1;
     load_ctx=read_ctx;load_ver=read_ver;
     for(l=0;l<4;l=l+1)lx[32*l+:32]=xv(ca[24*l+:24]);
     lv=1;@(negedge clk);lv=0;
    end
    allow=(t%13!=7 && t%13!=8);@(negedge clk);
   end
   allow=1;drain;repeat(8) @(negedge clk);ops=ops+1;
   if(op==2) begin rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);qr=0;qw=0;nr=0;nw=0;end
  end
  if(metadata_checks<600 || accepts<6 || descriptor_checks<600)$fatal(1,"production metadata coverage missing");
  if(resident_checks!=1)$fatal(1,"missing resident context/version overlap coverage");
  if(mode_checks!=1)$fatal(1,"missing actual j6 mode-overlap coverage");
  if(requests<600 || checks!=680+(ALL_SPLITS?256:0) || misses<4) $fatal(1,"coverage actualrequests=%0d arithmetic=%0d misses=%0d",requests,checks,misses);
  if(STALL && (credit_pause<100 || ack_pause<1))$fatal(1,"stopped-clock coverage missing credit_pause=%0d ack_pause=%0d",credit_pause,ack_pause);
  $display("LFACE LAT=%0d DEPTH=%0d STALL=%0d base_edges=%0d core_edges=%0d credit_paused_base_edges=%0d paused_with_ack_in_flight=%0d max_query_queue=%0d (mailbox bench: 4568 base edges, 871 pending edges)",LAT,DEPTH,STALL,base_edges,edges,credit_pause,ack_pause,max_q);
  $display("PASS lface registered faces GT%0d ops=%0d arithmetic=%0d requests=%0d misses=%0d streamed_queries=%0d streamed_words=%0d no_fault no_deadlock",TARGET_GT,ops,checks,requests,misses,requests,checks);$finish;
 end
endmodule

// Bench-only synchronous hash model for the actual RPS0 hard-ROM interfaces.
// Both reference and candidate instantiate the real rpair leaf and this model.
module ot_rom_4096x266_m8(input wire clk,input wire ce_in,input wire [11:0] addr_in,output reg [265:0] rd_out);
 integer l;always @(posedge clk) if(ce_in) begin
  rd_out<=0;
  for(l=0;l<32;l=l+1) rd_out[8*l+:8]<=8'(addr_in+l+1);
 end
endmodule
