`timescale 1ns/1ps
module tb_qwen_xcache_core;
 parameter integer MUT=0,MEM_EXTRA=0;
 reg clk=0;always #5 clk=~clk;
 reg allow=1,gate=1;always @(negedge clk) gate<=allow&&hit;
 wire cc=clk&&gate;
 reg rst_n=0,go=0,clear=0,lv=0;
 reg [7:0] slot=0;reg [95:0] la=0;reg [127:0] lx=0;
 reg [15:0] nout=768,tiles=1,kc=8;reg [3:0] sp=9;
 reg [23:0] xb=4096,xks=1,xjs=0,xcs=8;
 reg [31:0] gb=0;
 wire [3:0] rr,cr;wire [95:0] ra,ca;
 reg [127:0] rx=0;wire [127:0] cx;
 wire [511:0] rt,ct;wire rv,cv,rf,cf,hit,cachefault,readyr,readyc;
 reg [511:0] wrq=0;
 wire [127:0] rfeed,cfeed;wire [511:0] wfeed;
 generate if(MEM_EXTRA==0) begin
  assign rfeed=rx;assign cfeed=cx;assign wfeed=wrq;
 end else begin:delayed
  reg [127:0] rp[0:MEM_EXTRA-1],cp[0:MEM_EXTRA-1];reg [511:0] wp[0:MEM_EXTRA-1];integer z;
  always @(posedge cc) begin
   rp[0]<=rx;cp[0]<=cx;wp[0]<=wrq;
   for(z=1;z<MEM_EXTRA;z=z+1) begin rp[z]<=rp[z-1];cp[z]<=cp[z-1];wp[z]<=wp[z-1];end
  end
  assign rfeed=rp[MEM_EXTRA-1];assign cfeed=cp[MEM_EXTRA-1];assign wfeed=wp[MEM_EXTRA-1];
 end endgenerate
 wire wr,ww;wire [23:0] wa,cwa;
 function automatic [31:0] xv(input [23:0] a);
  xv=32'h3f800000 | (((a*24'd7919)^24'h123456)&23'h7fffff);
 endfunction
 // Runtime address tags come from production x_addr, not a copied issue loop.
 ot_qwen_xcache_seam #(.MUT_ADDR(MUT)) cache(clk,cc,rst_n,clear,lv,slot,la,lx,cr,ca,hit,cx,cachefault);
`define CORE(P,Q) \
 ot_qwen_w12_matvec_part #(.W(16),.G(4),.GT(3072),.PART(1),.NW(16),.SMIN(6),.INT8_WEIGHT(1),.GBASE_PORT(1),.FAST_ISSUE(1),.MEM_EXTRA(MEM_EXTRA)) P ( \
 .clk(cc),.rst_n(rst_n),.go(go),.ready(ready``P),.idle(),.i_nout(nout),.i_tiles(tiles),.i_k(kc),.i_wsrc(1'b0), \
 .i_wbase(24'd0),.i_ts(24'd64),.i_ks(24'd8),.i_js(24'd1),.i_xbase(xb),.i_xks(xks),.i_xjs(xjs),.i_xcs(xcs), \
 .i_jsh(3'd0),.i_split(sp),.i_wcs(24'd0),.i_round(1'b1),.i_obase(24'd0),.i_ots(24'd8),.i_ojs(24'd1), \
 .i_mmode(1'b0),.i_oen(1'b1),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(24'd0), \
 .wrom_re(P``w),.wrom_addr(P``wa),.wrom_q(wfeed),.scale_re(),.scale_gre(),.scale_addr(),.scale_q(1024'd0), \
 .kv_re(),.kv_addr(),.kv_q(2048'd0),.x_re(P``r),.x_addr(P``a),.x_q(Q), \
 .ov(),.o_we(),.o_addr(),.o_mask(),.o_data(),.am_idx(),.am_val(),.am_any(),.mx_we(),.mx_addr(),.mx_mask(),.mx_data(), \
 .progress(),.fault(P``f),.i_gbase(gb),.t_in(512'd0),.t_fault_in(1'b0),.t_out(P``t),.t_vout(P``v),.t_fault(),.active_o());
 wire rw,cw;wire [23:0] rwa;
 `CORE(r,rfeed)
 `CORE(c,cfeed)
 integer l,edges=0,checks=0,ops=0,misses=0;
 always @(posedge cc) begin
  edges<=edges+1;
  for(l=0;l<4;l=l+1) if(rr[l]) rx[32*l+:32]<=xv(ra[24*l+:24]);
  if(rw) for(l=0;l<64;l=l+1) wrq[8*l+:8]<=8'(rwa+l+1);
  #1;
  if(rst_n) begin
   if(rr!==cr || (|rr)&&ra!==ca) $fatal(1,"production x request mismatch");
   if(rv!==cv || rv && rt!==ct) $fatal(1,"production matvec output mismatch op=%0d edge=%0d",ops,edges);
   if(rf!==cf || cachefault) $fatal(1,"core/cache fault op=%0d",ops);
   if(rv) checks=checks+1;
  end
 end
 integer op,t,k,j,a,limit;
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  for(op=0;op<6;op=op+1) begin
   allow=0;@(negedge clk);@(negedge clk);clear=1;@(negedge clk);clear=0;
   gb=(op==5)?2044:4*(op*127%512);
   xb=4096+op*10000;xks=1;
   case(op)
    0:begin sp=9;kc=8;tiles=1;nout=768;xjs=0;end
    1:begin sp=8;kc=2;tiles=3;nout=4096;xjs=0;end
    2:begin sp=7;kc=32;tiles=1;nout=3072;xjs=0;end
    3:begin sp=8;kc=6;tiles=3;nout=4096;xjs=0;end
    4:begin sp=11;kc=3;tiles=1;nout=16;xjs=17;end
    5:begin sp=6;kc=9;tiles=2;nout=4096;xjs=29;end
   endcase
   xcs=kc;
   // Loader materializes address/value records; DUT lookup is driven solely
   // by real production requests. Arbitrary j stride gets8 entries per k.
   for(k=0;k<kc;k=k+1) for(j=0;j<(xjs?8:1);j=j+1) begin
    for(l=0;l<4;l=l+1) begin
     a=xb+((gb+l)&((1<<sp)-1))*xcs+k*xks+j*xjs;
     la[24*l+:24]=24'(a);lx[32*l+:32]=xv(a);
    end
    slot=8'(k*(xjs?8:1)+j);lv=1;@(negedge clk);
   end
   lv=0;allow=1;repeat(2) @(negedge clk);go=1;@(negedge clk);go=0;
   // Whole core and response clocks pause together; loader clock keeps going.
   for(t=0;t<kc*tiles*8+120;t=t+1) begin
    if(op==5 && t==20) begin clear=1;@(negedge clk);clear=0;end
    if(!hit) begin
     // Bounded miss fallback: freeze entire core until this exact request's
     // operands have arrived. Loader is independent of the frozen clock.
     misses=misses+1;la=ca;
     for(l=0;l<4;l=l+1) lx[32*l+:32]=xv(ca[24*l+:24]);
     slot=0;lv=1;repeat(3) @(negedge clk);lv=0;
    end
    allow=(t%13!=7 && t%13!=8);@(negedge clk);
   end
   allow=1;repeat(4) @(negedge clk);ops=ops+1;
   if(op==2) begin
    // Reset an actual in-flight production instruction, then start fresh.
    go=1;@(negedge clk);go=0;repeat(5) @(negedge clk);
    rst_n=0;repeat(3) @(negedge clk);rst_n=1;
   end
  end
  if(misses<4) $fatal(1,"insufficient loader miss fallback coverage %0d",misses);
  if(checks!=680) $fatal(1,"missing actual arithmetic outputs got=%0d expected=680",checks);
  $display("PASS production-core-cache ops=%0d arithmetic_outputs=%0d core_edges=%0d native_qkv_o_gu_down=4 SMAX11=1 arbitrary_xjs=2 wholecore_stalls=1 instructionclear=1 midop_reset=1 reactive_misses=%0d MEM_EXTRA=%0d",ops,checks,edges,misses,MEM_EXTRA);$finish;
 end
endmodule
