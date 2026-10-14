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
module tb_qwen_xcache_grouped_parent;
 parameter integer MUT=0,ALL_SPLITS=0;
`ifdef XCACHE_TP8
 localparam integer TARGET_GT=3072;
 `define REF_ME ref_tile.choice_ref.ctl.u_logic.u_me
`else
 localparam integer TARGET_GT=6144;
 `define REF_ME ref_tile.ctl.u_logic.u_me
`endif
 reg [378:0] native_ib[0:3];
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
 ot_qwen_tile_tp8_cached_grouped dut_cached(
  .clk_ctl(cc),.clk_rp({5{cc}}),.clk_sl({8{cc}}),.clk_node(cc),.clk_tx_group(cc),.clk_rqr({2{cc}}),
  .clk_cache(cc),.load_clk(clk),.rst_n(rst_n),.tile_id(tid),.ib_go(go),.ib(ib),
  .clear(clear),.j_repeat(j_repeat),.load_v(lv),.load_epoch(load_epoch),.load_x(lx),
  .n_a(512'd0),.n_b(512'd0),.n_va(1'b0),.n_y(),.n_vy(),.t_out(ct),.t_vout(cv),
  .core_fault(cf),.cache_fault(cachefault),.cache_hit(hit),.x_re(cr),.x_addr(ca),.x_epoch(ep));

 integer checks=0,requests=0,misses=0,edges=0,ops=0;
 always @(posedge cc) begin
  edges=edges+1;
  if(!rst_n) oracle_req<=0;
  else begin
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
   if(|cr) requests=requests+1;
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
   allow=0;repeat(2) @(negedge clk);clear=1;@(negedge clk);clear=0;
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
    load_epoch={18'(k),3'(j)};
    for(l=0;l<4;l=l+1) begin a=xb+((4*tid+l)&((1<<sp)-1))*xcs+k*xks+j*xjs;lx[32*l+:32]=xv(24'(a));end
    lv=1;@(negedge clk);
   end
   lv=0;allow=1;repeat(8) @(negedge clk);go=1;@(negedge clk);go=0;
   for(t=0;t<kc*tiles*8+180;t=t+1) begin
    if(op==5 && t==20) begin clear=1;@(negedge clk);clear=0;end
    if(!hit) begin
     misses=misses+1;load_epoch=ep;
     for(l=0;l<4;l=l+1) lx[32*l+:32]=xv(ca[24*l+:24]);
     lv=1;repeat(3) @(negedge clk);lv=0;
    end
    allow=(t%13!=7 && t%13!=8);@(negedge clk);
   end
   allow=1;repeat(8) @(negedge clk);ops=ops+1;
   if(op==2) begin go=1;@(negedge clk);go=0;repeat(5) @(negedge clk);rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);end
  end
  if(requests<600 || checks!=680+(ALL_SPLITS?256:0) || misses<4) $fatal(1,"coverage actualrequests=%0d arithmetic=%0d misses=%0d",requests,checks,misses);
  $display("PASS actual grouped cached parent GT%0d NW18 ops=%0d arithmetic=%0d requests=%0d misses=%0d XLOCAL=1 IREG_XL_bypass_only=1 ME_EXTRA=8 indexed_entries=32 coherent19roots=1 raw_split_fault_diagnostics=%0d",TARGET_GT,ops,checks,requests,misses,ALL_SPLITS);$finish;
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
