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
module tb_qwen_xcache_accepted_ib;
 parameter integer MUT=0,ALL_SPLITS=0;
`ifdef XCACHE_TP8
 localparam integer TARGET_GT=3072;
 `define REF_ME ref_tile.choice_ref.ctl.u_logic.u_me
`else
 localparam integer TARGET_GT=6144;
 `define REF_ME ref_tile.ctl.u_logic.u_me
`endif
 reg [378:0] native_ib[0:3];
 reg incoming=0,expected_mode=0;reg [15:0] current_ctx=0,expected_ctx=0,offered_ctx=0;reg [31:0] expected_ver=0;wire read_mode;wire [15:0] read_ctx;wire [31:0] read_ver;wire op_accept,core_idle;wire [15:0] accepted_ctx;wire [31:0] accepted_ver;wire [378:0] accepted_ib;reg [378:0] expected_accepted_ib=0;reg accepted_valid=0;integer accepts=0,metadata_checks=0,descriptor_checks=0;reg [95:0] load_key=0;reg [15:0] load_ctx=0;reg [31:0] load_ver=0;integer mode_checks=0,resident_checks=0;
 reg clk=0;always #5 clk=~clk;
 reg allow=1,gate=1;wire hit;always @(negedge clk) gate<=allow&&hit;
 wire cc=clk&&gate;
 reg rst_n=0,go=0,clear=0,lv=0,j_repeat=1;
 reg [15:0] tid=0;reg [378:0] ib=0;reg [20:0] load_epoch=0;
 reg [127:0] lx=0;wire [127:0] cache_x;reg [127:0] stale_x=0;always @(posedge cc) stale_x<=cache_x;
 wire [3:0] cr,unused_r;wire [95:0] ca,unused_a;wire [20:0] ep,unused_e;
 wire [511:0] rt,ct;wire rv,cv,rf,cf,cachefault;
 reg [95:0] oracle_addr=0;reg [3:0] oracle_req=0;reg [20:0] oracle_epoch=0;
 reg [127:0] held_ref=0;reg [127:0] raw_ref;
 function automatic [31:0] xv(input [23:0] a);
  xv=32'h3f800000 | (((a*24'd7919)^24'h123456)&23'h7fffff);
 endfunction
 integer l;always @* begin
  raw_ref=held_ref;
  if(|oracle_req) for(integer z=0;z<4;z=z+1) raw_ref[32*z+:32]=xv(oracle_addr[24*z+:24]);
 end
 xcache_actual_tile #(.XLOCAL(0)) ref_tile(cc,rst_n,tid,go,ib,raw_ref,unused_r,unused_a,unused_e,rt,rv,rf);
 generate if(MUT==1)begin:old_source
 assign read_mode=expected_mode;assign read_ctx=expected_ctx;assign read_ver=expected_ver;assign op_accept=0;assign accepted_ctx=0;assign accepted_ver=0;assign core_idle=0;assign accepted_ib=0;
 ot_qwen_tile_tp8_cached_split dut_cached(
  .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),
  .clk_cache(cc),.load_clk(clk),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),
  .clear(clear),.j_repeat(j_repeat),.load_v(lv),.load_epoch(load_epoch),.load_x(lx),
  .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(ct),.t_vout(cv),
  .core_fault(cf),.cache_fault(cachefault),.cache_hit(hit),.x_re(cr),.x_addr(ca),.x_epoch(ep));
 end else begin:repair
 wire [127:0] response;
 ot_qwen_rom_tile_nkt_tp8_core_ctx u_core(
  .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx({8{cc}}),.clk_rqr({2{cc}}),
  .rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),.x_response(response),
  .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(ct),.t_vout(cv),.fault(cf),
  .cx_xre(cr),.cx_xaddr(ca),.cx_xepoch(ep),.op_context(offered_ctx),.vm_version(32'(100+offered_ctx)),.cx_xjrepeat(read_mode),.cx_xcontext(read_ctx),.cx_xversion(read_ver),.cx_op_accept(op_accept),.cx_accepted_context(accepted_ctx),.cx_accepted_version(accepted_ver),.cx_core_idle(core_idle),.cx_accepted_ib(accepted_ib));
 ot_qwen_xcache_context32 #(.MUT_LIVE_MODE(MUT==2),.MUT_RESIDENT(MUT==3)) cache(
  .load_clk(clk),.core_clk(cc),.rst_n(rst_n),.clear(clear),
  .live_j_repeat(j_repeat),.read_j_repeat(read_mode),.load_j_repeat(xjs==0),
  .load_v(lv),.load_epoch(load_epoch),.read_epoch(ep),.load_context(load_ctx),.read_context(read_ctx),
  .load_version(load_ver),.read_version(read_ver),.load_addr(load_key),.read_addr(ca),
  .load_x(lx),.read_v(cr),.hit(hit),.q_x(response),.fault(cachefault));
 end endgenerate

 integer checks=0,requests=0,misses=0,edges=0,ops=0;
 always @(posedge cc) begin
  edges=edges+1;
  if(!rst_n) begin accepted_valid<=0;oracle_req<=0;expected_mode<=0;expected_ctx<=0;expected_ver<=0;end
  else begin
   if(`REF_ME.go && `REF_ME.ready)begin
    expected_accepted_ib<=ref_tile.choice_ref.ctl.u_logic.ib_i;accepted_valid<=1;
   end
   // Capture pre-update request mode/context on the same actual address edge.
   expected_mode<=(`REF_ME.xjs_r==0);expected_ctx<=current_ctx;expected_ver<=32'(100+current_ctx);
   // Independent production reference state, not candidate request reuse.
   for(l=0;l<4;l=l+1) begin
    oracle_req[l]<=`REF_ME.active && (((`REF_ME.gb+l)>>`REF_ME.split_r)<(TARGET_GT>>`REF_ME.split_r));
    oracle_addr[24*l+:24]<=`REF_ME.xc+((`REF_ME.gb+l)&((1<<`REF_ME.split_r)-1))*`REF_ME.xcs_r;
   end
   oracle_epoch<={`REF_ME.k,`REF_ME.j};
  end
  if(|oracle_req) held_ref<=raw_ref;
  #1;
  if(rst_n) begin
   if(cr!==oracle_req || (|cr) && (ca!==oracle_addr || ep!==oracle_epoch)) $fatal(1,"actual tile request/epoch mismatch op=%0d",ops);
   if(MUT!=1 && accepted_valid && (MUT!=4 || incoming))begin
    descriptor_checks=descriptor_checks+1;
    if(accepted_ib!==expected_accepted_ib)$fatal(1,"production acceptedIB lifetime mismatch");
   end
   if(|cr) begin
    requests=requests+1;
    if(MUT!=1 && (read_mode!==expected_mode || read_ctx!==expected_ctx || read_ver!==expected_ver))$fatal(1,"production request metadata mismatch");
    if(MUT!=1)metadata_checks=metadata_checks+1;
   end
   if(MUT!=1 && op_accept)begin
    accepts=accepts+1;
    if(accepted_ctx!==current_ctx || accepted_ver!==32'(100+current_ctx))$fatal(1,"production accepted context mismatch");
   end
   if(rv!==cv || rv && rt!==ct) $fatal(1,"actual CEXT2 arithmetic mismatch op=%0d edge=%0d",ops,edges);
   if(rf!==cf || cachefault) $fatal(1,"actual tile/cache fault op=%0d",ops);
   if(rv) checks=checks+1;
  end
 end
 integer op,t,k,j,a,kc,tiles,sp,xjs,xb,nout,xks,xcs;
 initial begin
`ifdef XCACHE_TP8
  $readmemh("native_profiles.hex",native_ib);
`endif
  repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
  for(op=0;op<6+(ALL_SPLITS?16:0);op=op+1) begin
   if(op>=6) begin allow=1;rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);end
   current_ctx=16'(op+1);offered_ctx=current_ctx;incoming=0;allow=0;repeat(2) @(negedge clk);clear=1;@(negedge clk);clear=0;
   case(op)
    0:begin tid=0;sp=9;kc=8;tiles=1;nout=768;xjs=0;end
    1:begin tid=127;sp=8;kc=2;tiles=3;nout=4096;xjs=0;end
    2:begin tid=(TARGET_GT==3072)?512:768;sp=7;kc=32;tiles=1;nout=3072;xjs=0;end
    3:begin tid=(TARGET_GT==3072)?767:1535;sp=8;kc=6;tiles=3;nout=4096;xjs=0;end
    4:begin tid=511;sp=11;kc=3;tiles=1;nout=16;xjs=17;end
    5:begin tid=(TARGET_GT==3072)?703:1023;sp=7;kc=9;tiles=2;nout=4096;xjs=29;end
    default:begin tid=0;sp=op-6;kc=2;tiles=1;nout=128;xjs=5;end
   endcase
   xb=4096+op*10000;xks=1;xcs=kc;
   if(op==5 || op>=6) begin
    xb=24'hFED123;xks=24'hC7D8E9;xjs=24'hABCDE7;xcs=24'hFACE91;
   end
   j_repeat=(xjs==0);
   ib={18'(nout),18'(tiles),18'(kc),1'b0,24'd0,24'(kc*8),24'd8,24'd1,24'(xb),24'(xks),24'(xjs),24'(xcs),3'd0,4'(sp),24'd0,1'b1,24'd0,24'd8,24'd1,1'b0,1'b1,1'b0,1'b0,24'd0};
`ifdef XCACHE_TP8
   if(op<4) begin
    ib=native_ib[op];
    case(op) 0:xb=4096;1:xb=50672;2:xb=4096;3:xb=55280;endcase
   end
`endif
   for(k=0;k<kc;k=k+1) for(j=0;j<(j_repeat?1:8);j=j+1) begin
    load_ctx=current_ctx;load_ver=32'(100+current_ctx);load_epoch={18'(k),3'(j)};
    for(l=0;l<4;l=l+1) begin a=xb+((4*tid+l)&((1<<sp)-1))*xcs+k*xks+j*xjs;lx[32*l+:32]=xv(24'(a));load_key[24*l+:24]=24'(a);end
    lv=1;@(negedge clk);
   end
   lv=0;allow=1;repeat(8) @(negedge clk);go=1;@(negedge clk);go=0;
   for(t=0;t<kc*tiles*8+180;t=t+1) begin
    if(op==5 && t==20) begin clear=1;@(negedge clk);clear=0;end
    if(!hit) begin
     misses=misses+1;load_epoch=ep;
     for(l=0;l<4;l=l+1) lx[32*l+:32]=xv(ca[24*l+:24]);
     load_ctx=read_ctx;load_ver=read_ver;load_key=ca;lv=1;repeat(3) @(negedge clk);lv=0;
    end
    if(op==5 && !incoming && |cr && ep[2:0]==6 && ep[20:3]==0)begin
     // Offer a next descriptor with xjs0 while its GO is held externally.
     // Old actual request j6 remains pending; only latest external mode changes.
     incoming=1;j_repeat=1;ib=native_ib[0];offered_ctx=current_ctx+16'h4000;mode_checks=mode_checks+1;
     if(MUT!=1)begin
      allow=0;repeat(2)@(negedge clk);
      load_ctx=current_ctx+16'h4000;load_ver=read_ver+1;load_key=ca;load_epoch=ep;
      lx=128'h40000000400000004000000040000000;lv=1;@(negedge clk);lv=0;
      #1;if(MUT!=2 && hit)$fatal(1,"resident context/version reused for old request");
      resident_checks=resident_checks+1;
      load_ctx=read_ctx;load_ver=read_ver;
      for(l=0;l<4;l=l+1)lx[32*l+:32]=xv(ca[24*l+:24]);
      lv=1;@(negedge clk);lv=0;
     end
    end
    if(MUT==2 && incoming && |cr && !hit)$fatal(1,"live mode lost old pending request");
    allow=(t%13!=7 && t%13!=8);@(negedge clk);
   end
   allow=1;repeat(8) @(negedge clk);ops=ops+1;
   if(op==2) begin go=1;@(negedge clk);go=0;repeat(5) @(negedge clk);rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);end
  end
  if(MUT==0 && (metadata_checks<600 || accepts<6 || descriptor_checks<600))$fatal(1,"production metadata coverage missing");
  if(MUT==0 && resident_checks!=1)$fatal(1,"missing resident context/version overlap coverage");
  if(mode_checks!=1)$fatal(1,"missing actual j6 mode-overlap coverage");
  if(requests<600 || checks!=680+(ALL_SPLITS?256:0) || misses<4) $fatal(1,"coverage actualrequests=%0d arithmetic=%0d misses=%0d",requests,checks,misses);
  $display("PASS production acceptedIB and request ports GT%0d NW18 ops=%0d arithmetic=%0d requests=%0d misses=%0d XLOCAL=1 IREG_XL_bypass_only=1 ME_EXTRA=8 indexed_entries=32 coherent26roots=1 raw_split_fault_diagnostics=%0d",TARGET_GT,ops,checks,requests,misses,ALL_SPLITS);$finish;
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
