`timescale 1ns/1ps
// KVJ-F 2026-10-17 (stub audit K-1, coordinator 0da): the landing V response -> its REAL consumer, the 16 PV16 V ports.
// DUT = the static-join template's own edges (tools/qwen_kv_die/kv_static.py template(), kv_die.py _pv144_buses):
//   32 x qkd_static_kv_landing_seg_h (the HIERARCHICAL segment: row_h3 / lane_h4 / relay_h2 are its CLOSED children,
//        cycle-identical to the flat seg) on their cfg straps, and
//   16 x qkd_pv16_vport (r6, DQ / RT parameters), port vport_<st>_<k> = vport[4*stack + k]:
//        landing group g of stack st (g = 2k + parity) -> vport k side `parity`:
//            land.vreq_{valid,t}        <- vport.vq<parity>_{valid,t}
//            vport.in<parity>_{valid,vflag,t,epoch,d} <- land.rsp_{valid,v,t,epoch,data}
//   (the SAME rsp bus also carries the group's K rows to its K issuer: the V port must ignore every K word).
// Stimulus: the 128 PCs' corrected returns (real 128x256 SRAM model inside each landing lane), K rows of every group
// for t < CTX, then both PV16 pairs' w16 request walk at T = 8192 driven on the V ports' pr faces (the pairs' requests).
// Checks: every K row on the landing rsp at LAT 8 (K side unchanged), every V row at the V port output: valid / t /
// epoch / 1,024 data bits on its edge (OL = DQ + RT + 3 edges after the pr pin), 8,192 V rows, no landing / vport
// fault.  RT (vq register -> rsp at the in pins) of the direct (relay-free) join = 1 + the seg's VREQ latency 8 = 9:
// the vport r5/r6 contract's 'landing 8 + relays' (kv_die.py pv_vport_timing, KVJ-E VPORT_RT_LANDING) is one edge short
// for the static seg (RT 8 faults every slot; RT_ADJ -1 below).  Die joins with r relay stages: RT = 9 + r.
// Negative controls (must FAIL): JOIN_MUT 1 = the two sides of every port swapped (group 2k+1 on in0), 2 = vq faces
// swapped (V gets of group 2k sent to 2k+1); VP_MUT = the vport's own mutants (1 sel, 2 quarter swap, 3 K/V flag
// ignored, 4 wrong group, 5 epoch side); RT_ADJ = RT off by the given edges.
module tb_static_landing_vport;
 parameter integer CTX=8192;
 parameter integer DQ=0;
 parameter integer RT=9;           // MEASURED here for the abutted join: vq register -> landing pin capture (1) + seg LAT 8
 parameter integer RT_ADJ=0;
 parameter integer JOIN_MUT=0;
 parameter integer VP_MUT=0;
 parameter integer SEGH=1;          // 1: qkd_static_kv_landing_seg_h (closed hierarchy); 0: the flat seg (same cycles)
 localparam integer LAT=8;          // landing seg K request -> rsp (VMAP 1 / VREQ 1 / PHYS)
 localparam integer OL=DQ+RT+3;     // vport pr pin -> out pins
 integer klen[0:31],kord[0:31][0:255],ktot=0;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst=0,arm=0;
 reg [31:0] put=0,rq=0;
 reg [9:0] sec[0:31];reg [13:0] tt[0:31];
 reg [1023:0] wd[0:31];
 reg [3:0] ap[0:31];reg [39:0] as[0:31];
 reg [15:0] prv=0;reg [13:0] prt[0:15];
 wire [31:0] ov,ff,outv;wire [1023:0] od[0:31];wire [13:0] ot[0:31];wire [15:0] oe[0:31];
 wire [31:0] vqv;wire [13:0] vqt[0:31];   // per GROUP: the V get its port drives
 wire [15:0] vq0v,vq1v;wire [13:0] vq0t[0:15],vq1t[0:15];
 wire [15:0] pv,pf;wire [13:0] pt[0:15];wire [15:0] pe[0:15];wire [511:0] plo[0:15],phi[0:15];
 integer errors=0,kseen=0,vseen=0,cycles=0,vreq=0;
 function automatic [13:0] kt(input integer i,s,e);
  kt=14'(((i>>3)&15)*512+s*128+((i>>7)&1)*64+(i&7)*8+e);
 endfunction
 function automatic [9:0] js(input integer t,v);
  js={1'(v),1'b0,1'((t>>6)&1),4'((t>>9)&15),3'((v!=0)?((t>>1)&7):((t>>3)&7))};
 endfunction
 function automatic [13:0] vt(input integer o,s,e);
  vt=14'(((o>>4)&15)*512+s*128+((o>>3)&1)*64+(e>>1)*16+(o&7)*2+(e&1));
 endfunction
 function automatic [1023:0] pattern(input integer t,v);
  for(integer j=0;j<32;j=j+1)pattern[32*j+:32]=32'h19e30000^(32'(t)*32'h9e3779b9)^(32'(v)<<31)^32'(j*71);
 endfunction
 genvar g,k;
 generate for(g=0;g<32;g=g+1)begin:groups
  wire [5:0] ol;
  localparam integer ST=g/8, GI=g%8, VP=4*ST+GI/2, PAR=GI%2;
  // the vq face this group's vreq is joined to (JOIN_MUT 2: the port's other side)
  localparam integer QPAR=(JOIN_MUT==2)?1-PAR:PAR;
  assign vqv[g]=(QPAR==0)?vq0v[VP]:vq1v[VP];
  assign vqt[g]=(QPAR==0)?vq0t[VP]:vq1t[VP];
  if(SEGH!=0)begin:g_h
  qkd_static_kv_landing_seg_h #(.MUT(0),.HOP_MUT(0))dut(
   .ck(ck),.ck_p0(ck),.ck_p1(ck),.ck_p2(ck),.ck_p3(ck),.ck_r0(ck),.ck_r3(ck),.rst_n(rst),.cfg_stack(2'(ST)),.cfg_group(3'(GI)),
   .arm(arm),.epoch(16'd7),.layer(6'd3),
   .expected_put({4{put[g]}}),.expected_sector({4{sec[g]}}),.actual_valid(ap[g]),.actual_sector(as[g]),
   .actual_epoch({4{16'd7}}),.actual_layer({4{6'd3}}),.actual_data(wd[g]),
   .req_valid(rq[g]),.req_t(tt[g]),.req_v(1'b0),.req_epoch(16'd7),.req_layer(6'd3),
   .vreq_valid(vqv[g]),.vreq_t(vqt[g]),
   .rsp_valid(ov[g]),.rsp_data(od[g]),.rsp_t(ot[g]),.rsp_v(outv[g]),.rsp_epoch(oe[g]),.rsp_layer(ol),.fault(ff[g]));
  end else begin:g_f
  qkd_static_kv_landing_seg #(.MUT(0),.HOP_MUT(0))dut(
   .ck(ck),.rst_n(rst),.cfg_stack(2'(ST)),.cfg_group(3'(GI)),.arm(arm),.epoch(16'd7),.layer(6'd3),
   .expected_put({4{put[g]}}),.expected_sector({4{sec[g]}}),.actual_valid(ap[g]),.actual_sector(as[g]),
   .actual_epoch({4{16'd7}}),.actual_layer({4{6'd3}}),.actual_data(wd[g]),
   .req_valid(rq[g]),.req_t(tt[g]),.req_v(1'b0),.req_epoch(16'd7),.req_layer(6'd3),
   .vreq_valid(vqv[g]),.vreq_t(vqt[g]),
   .rsp_valid(ov[g]),.rsp_data(od[g]),.rsp_t(ot[g]),.rsp_v(outv[g]),.rsp_epoch(oe[g]),.rsp_layer(ol),.fault(ff[g]));
  end
 end
 for(k=0;k<16;k=k+1)begin:ports
  // side s of port k (stack k/4, lane k%4) = landing group 8*(k/4) + 2*(k%4) + s (JOIN_MUT 1: sides swapped)
  localparam integer G0=8*(k/4)+2*(k%4)+((JOIN_MUT==1)?1:0), G1=8*(k/4)+2*(k%4)+((JOIN_MUT==1)?0:1);
  qkd_pv16_vport #(.MUT(VP_MUT),.DQ(DQ),.RT(RT+RT_ADJ))vp(
   .ck(ck),.rst_n(rst),.pr_valid(prv[k]),.pr_t(prt[k]),
   .vq0_valid(vq0v[k]),.vq0_t(vq0t[k]),.vq1_valid(vq1v[k]),.vq1_t(vq1t[k]),
   .in0_valid(ov[G0]),.in0_vflag(outv[G0]),.in0_t(ot[G0]),.in0_epoch(oe[G0]),.in0_d(od[G0]),
   .in1_valid(ov[G1]),.in1_vflag(outv[G1]),.in1_t(ot[G1]),.in1_epoch(oe[G1]),.in1_d(od[G1]),
   .out_valid(pv[k]),.out_t(pt[k]),.out_epoch(pe[k]),.out_v_lo(plo[k]),.out_v_hi(phi[k]),.fault(pf[k]));
 end endgenerate
 // expectations: K at the landing rsp (LAT after the K request pin), V at the V port output (OL after the pr pin)
 localparam integer D=32;
 reg [31:0] kexp[0:D];reg [13:0] kexpt[0:D][0:31];
 reg [15:0] vexp[0:D];reg [13:0] vexpt[0:D][0:15];
 always @(posedge ck)begin
  cycles++;
  if(!rst)for(integer d=0;d<=D;d=d+1)begin kexp[d]<=0;vexp[d]<=0;end
  else begin
   kexp[0]<=rq;vexp[0]<=prv;
   for(integer n=0;n<32;n=n+1)kexpt[0][n]<=tt[n];
   for(integer n=0;n<16;n=n+1)vexpt[0][n]<=prt[n];
   for(integer d=1;d<=D;d=d+1)begin
    kexp[d]<=kexp[d-1];vexp[d]<=vexp[d-1];
    for(integer n=0;n<32;n=n+1)kexpt[d][n]<=kexpt[d-1][n];
    for(integer n=0;n<16;n=n+1)vexpt[d][n]<=vexpt[d-1][n];
   end
  end
  #0.001;
  if(rst)begin
   for(integer n=0;n<32;n=n+1)begin
    // K words: on the rsp bus at LAT, kind K, exact; V words on the rsp bus are checked at the V port
    if(kexp[LAT][n]&&!(ov[n]&&!outv[n]&&ot[n]===kexpt[LAT][n]&&od[n]===pattern(kexpt[LAT][n],0)))begin
     if(errors<8)$display("BAD K row c%0d group%0d t%0d",cycles,n,kexpt[LAT][n]);errors++;end
    if(kexp[LAT][n])kseen++;
    if(ov[n]&&!outv[n]&&!kexp[LAT][n])begin if(errors<8)$display("BAD stray K word c%0d group%0d",cycles,n);errors++;end
   end
   if(pv!==vexp[OL])begin if(errors<8)$display("BAD V port valid c%0d actual%h expected%h",cycles,pv,vexp[OL]);errors++;end
   for(integer n=0;n<16;n=n+1)if(pv[n])begin
    vseen++;
    if(pt[n]!==vexpt[OL][n]||pe[n]!==16'd7||{phi[n],plo[n]}!==pattern(vexpt[OL][n],1))begin
     if(errors<8)$display("BAD V row c%0d port%0d t%0d expected t%0d",cycles,n,pt[n],vexpt[OL][n]);errors++;
    end
   end
  end
 end
 task automatic idle;
  put=0;rq=0;prv=0;
  for(integer g=0;g<32;g=g+1)begin ap[g]=0;as[g]=0;end
 endtask
 task automatic loadrow(input integer g,o,v);
  automatic integer t=v?vt(o,g/8,g%8):kt(o,g/8,g%8);
  put[g]=1;sec[g]=js(t,v);ap[g]=4'hf;as[g]={4{sec[g]}};wd[g]=pattern(t,v);
 endtask
 integer nexto[0:31];
 initial begin
  for(integer n=0;n<32;n=n+1)begin sec[n]=0;tt[n]=0;wd[n]=0;ap[n]=0;as[n]=0;end
  for(integer n=0;n<16;n=n+1)prt[n]=0;
  repeat(8)@(negedge ck);rst=1;repeat(8)@(negedge ck);arm=1;@(negedge ck);arm=0;repeat(4)@(negedge ck);
  // K phase (the shared rsp bus: K words pass the V ports, which must ignore them)
  for(integer g=0;g<32;g=g+1)begin klen[g]=0;for(integer p=0;p<256;p=p+1)begin automatic integer i=((p>>3)&1)*128+(p>>4)*8+(p&7);
   if(kt(i,g/8,g%8)<CTX)begin kord[g][klen[g]]=i;klen[g]=klen[g]+1;end end ktot=ktot+klen[g];end
  for(integer i=0;i<64;i=i+1)begin idle();for(integer g=0;g<32;g=g+1)if(i<klen[g])loadrow(g,kord[g][i],0);@(negedge ck);end
  for(integer i=0;i<256;i=i+1)begin
   idle();for(integer g=0;g<32;g=g+1)if(i<klen[g])begin rq[g]=1;tt[g]=kt(kord[g][i],g/8,g%8);if(i+64<klen[g])loadrow(g,kord[g][i+64],0);end
   @(negedge ck);
  end
  idle();repeat(8)@(negedge ck);
  // V phase: rows 0..63 of every group resident, then the w16 walk of both pairs on the V ports' request faces
  for(integer i=0;i<64;i=i+1)begin idle();for(integer g=0;g<32;g=g+1)loadrow(g,i,1);@(negedge ck);end
  for(integer g=0;g<32;g=g+1)nexto[g]=0;
  for(integer q=0;q<16*33;q=q+1)begin
   idle();
   for(integer p=0;p<2;p=p+1)for(integer wp=0;wp<8;wp=wp+1)begin
    automatic integer l=(wp&3)+4*(((q>>4)^(wp>>2))&1);
    automatic integer n=(q>>4)-(l>>2);
    automatic integer t=256*n+128*p+16*l+(q&15);
    if(n>=0&&t<8192)begin
     automatic integer s=(t>>7)&3, lane=(t>>4)&3, v=4*s+lane;
     automatic integer g=8*s+2*lane+(t&1);
     automatic integer o=(((t>>9)&15)<<4)|(((t>>6)&1)<<3)|((t>>1)&7);
     if(prv[v])begin $display("BAD two requests on V port %0d edge q%0d",v,q);errors++;end
     if(o!=nexto[g])begin $display("BAD group %0d ordinal %0d expected %0d",g,o,nexto[g]);errors++;end
     nexto[g]=o+1;vreq++;
     prv[v]=1;prt[v]=14'(t);if(o+64<256)loadrow(g,o+64,1);
    end
   end
   @(negedge ck);
  end
  if(vreq!=8192)begin $display("BAD V gets %0d",vreq);errors++;end
  idle();repeat(OL+12)@(negedge ck);
  if((|ff)||(|pf)||errors||kseen!=ktot||vseen!=8192)begin
   $display("FAIL landing_vport krows%0d/%0d vrows%0d errors%0d landing_fault%h vport_fault%h join_mut%0d vp_mut%0d rt%0d",
            kseen,ktot,vseen,errors,ff,pf,JOIN_MUT,VP_MUT,RT+RT_ADJ);$fatal(1);end
  $display("PASS landing_vport ctxK%0d groups32 vports16 krows%0d vrows%0d K_lat%0d V_pr_to_out%0d DQ%0d RT%0d segh%0d cycles%0d",
           CTX,kseen,vseen,LAT,OL,DQ,RT,SEGH,cycles);$finish;
 end
endmodule
