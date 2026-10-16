`timescale 1ns/1ps
`default_nettype none
// tb_hbm_su_collport (H-NETLIST/suport 2026-10-16): one SU quarter's COLL joins on REAL RTL: 4 x ot_hbm_su_static_pgslice
// (COLLPORT=1, MULTIRATE=1, real pinned banks / SRAM models), ot_hbm_su_static_qcore (COLLPORT=1) and
// ot_hbm_su_static_cxport. The bench is COLL (stream) and the SU programme (serial) only.
// Clocks: quantum 1 ns, stream period 3, serial 4, phase-zero epoch at t=120 (first stream edge p=0, serial n=0).
// Phases checked:
//   DELIVERY  4 lanes / stream edge (active phases), lane j -> slice j (obase[5:4]=j), random half/row/data; model.
//   INJECT    random 2-lane requests on active phases; inj_d checked at EXACTLY P+INJ_RET against the model
//             (and 0 on every other edge for lanes without a request).
//   RED_CARRY red_sv/red_tag/red_x driven at the cxport pins (the qcore reducer output contract): CW words + EMIT
//             (with and without LATE); rc_v must pulse exactly at the computed stream edge with the words, 0 elsewhere.
//   RR        rr pulses for emitted tags; the qcore RF sector is read back through RF class 0 and compared.
//   SFU ro    ro_v/ro_x at the cxport stream pins; SFU-source red_cmd (osel=1, lane[6]=1) at E = ceil((3A+3)/4);
//             qcore's reducer operand register rc_x at E+1 must equal ro_x[lane].
// Plusargs: +COLLIDE (inject and drain on one group in one edge: fault MUST latch), +PHASE2 (SU-bound valid at stream
// phase 2: fault MUST latch). Positive run: fault must stay 0.
// MUT_CX / MUT_PG / MUT_QC select the leaf mutants (bench must FAIL).
module tb_hbm_su_collport #(parameter integer QID=1, INJ_RET=11, SD=0, MUT_CX=0, MUT_PG=0, MUT_QC=0, NINJ=400, NDEL=600)();
 localparam integer B39=(QID==0);
 reg clk_s=0, clk_q=0, rst=0;
 // phase-zero clocks: rising stream edges at 3p, serial at 4n (t from 0)
 initial begin clk_s=1; forever begin #1.5 clk_s=~clk_s; end end
 initial begin clk_q=1; forever begin #2 clk_q=~clk_q; end end
 // ------------------------------------------------------------------ DUT
 reg [1:0] inj_rd=0; reg [159:0] inj_addr=0; wire [1023:0] inj_d;
 reg [3:0] del_valid=0; reg [2179:0] del_flit=0; reg [159:0] del_obase=0;
 wire rc_v; wire [2:0] rc_tag; wire [255:0] rc_d;
 reg rr_v=0; reg [2:0] rr_tag=0; reg [255:0] rr_d=0;
 reg red_sv=0; reg [31:0] red_tag=0, red_x=0;
 reg [15:0] ro_v=0; reg [511:0] ro_x=0;
 reg [73:0] red_cmd=0; reg [53:0] rf_rd_cmd=0;
 reg [4*78-1:0] vmw_cmd=0;
 wire [11:0] red_sel={red_cmd[73],red_cmd[72:70],red_cmd[7],red_cmd[6:0]};
 wire [4*1024-1:0] inj_q; wire [7:0] dw_v; wire [71:0] dw_row; wire [4095:0] dw_d;
 wire rr_wv; wire [4:0] rr_wa; wire [255:0] rr_wd; wire [31:0] sfu_x;
 wire [4*32-1:0] slice_x; wire [4*32-1:0] rf_bword; wire [4*9-1:0] rf_bcmd; wire [255:0] rf_dsec;
 wire cx_fault, core_fault; wire [3:0] sl_fault;
 ot_hbm_su_static_cxport #(.QID(QID),.B39_NOOP(B39),.INJ_RET(INJ_RET),.SD(SD),.MUT(MUT_CX)) u_cx(
  .clk_s(clk_s),.clk_q(clk_q),.rst_n(rst),.inj_rd(inj_rd),.inj_addr(inj_addr),.inj_d(inj_d),
  .del_valid(del_valid),.del_flit(del_flit),.del_obase(del_obase),.rc_v(rc_v),.rc_tag(rc_tag),.rc_d(rc_d),
  .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.inj_q(inj_q_d),.dw_v(dw_v),.dw_row(dw_row),.dw_d(dw_d),
  .red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),
  .ro_v(ro_v),.ro_x(ro_x),.red_sel(red_sel),.sfu_x(sfu_x),.fault(cx_fault));
 // SD serial relay stages on inj_q (die relays are plain register copies)
 wire [4*1024-1:0] inj_q_d;
 if(SD==0)begin:g_sd0 assign inj_q_d=inj_q; end
 else begin:g_sd
  reg [4*1024-1:0] r [0:SD-1];
  always @(posedge clk_q) begin r[0]<=inj_q; for(integer t=1;t<SD;t=t+1) r[t]<=r[t-1]; end
  assign inj_q_d=r[SD-1];
 end
 for(genvar g=0;g<4;g=g+1)begin:g_sl
  ot_hbm_su_static_pgslice #(.QID(QID),.G(g),.READ_RETURN(10),.WRITE_RETURN(7),.FETCH_EXTRA_EDGES(2),.MLAT(4),.ALAT(3),
   .LEAF(1),.MUT(MUT_PG),.MULTIRATE(1),.COLLPORT(1)) u_slice(
   .pg_clk(clk_s),.clk_lane({256{clk_q}}),.clk_insert({128{clk_q}}),.rst_lane_n({32{rst}}),.clk_bcast({4{clk_q}}),
   .rst_bcast_n({4{rst}}),.clk_bank({32{clk_q}}),.clk_bank_macro({192{clk_q}}),.clk_ctl(clk_q),.clk_side({6{clk_q}}),
   .rst_n(rst),.bridge_rst_n(rst),.control(1742'd0),.vmr_cmd(60'd0),.vmw_cmd(vmw_cmd[78*g+:78]),
   .rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),.red_sel(red_sel),.slice_x(slice_x[32*g+:32]),
   .lg_rq(),.lg_wq(),.lg_rr(514'd0),.lg_w_done(2'd0),.fault(sl_fault[g]),
   .inj_rd(inj_rd),.inj_addr(inj_addr),.inj_q(inj_q[1024*g+:1024]),
   .dw_v(dw_v[2*g+:2]),.dw_row(dw_row[18*g+:18]),.dw_d(dw_d[1024*g+:1024]));
 end
 ot_hbm_su_static_qcore #(.MUT(MUT_QC),.COLLPORT(1)) u_core(.clk_rf({64{clk_q}}),.clk_ctl(clk_q),.clk_red(clk_q),.rst_n(rst),
  .rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),.rf_drain_cmd(2'd0),.slice_x(slice_x),.rf_wv(4'd0),.rf_wa(32'd0),.rf_wd(128'd0),
  .rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),.red_sv(),.red_tag(),.red_x(),.red_rf_v(),
  .rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),.sfu_x(sfu_x),.fault(core_fault));
 wire any_fault = cx_fault | core_fault | (|sl_fault);
 // ------------------------------------------------------------------ epoch bookkeeping
 integer p=-1, n=-1;                  // index of the last stream / serial edge (epoch counted)
 always @(posedge clk_s) if(rst) p<=p+1;
 always @(posedge clk_q) if(rst) n<=n+1;
 function automatic integer s2q(input integer a); s2q=(3*a+3+3)/4; endfunction   // ceil((3a+3)/4)
 function automatic integer q2s(input integer m); q2s=(4*m+3+2)/3; endfunction   // ceil((4m+3)/3)
 // ------------------------------------------------------------------ model
 reg [31:0] mem [0:127][0:511];
 reg [8:0] wrow_seen [0:127];
 integer errors=0, checks=0;
 task automatic err(input string s); begin errors=errors+1; if(errors<20) $display("ERR t=%0t p=%0d n=%0d %s",$time,p,n,s); end endtask
 // expected inj_d per stream edge
 reg [1023:0] exp_inj [0:8191]; reg exp_has [0:8191];
 // ------------------------------------------------------------------ helpers
 function automatic [39:0] saddr(input integer lane, input integer row); saddr={22'd0,2'(QID),9'(row),7'(lane)}; endfunction
 integer seed=1;
 integer ph2=0, collide=0;
 initial begin
  if($test$plusargs("PHASE2")) ph2=1;
  if($test$plusargs("COLLIDE")) collide=1;
  for(integer i=0;i<8192;i=i+1) exp_has[i]=0;
  for(integer l=0;l<128;l=l+1) for(integer r=0;r<512;r=r+1) mem[l][r]=32'hx;
  #119.5 rst=1;
 end
 // drive on stream edges (after the edge: COLL registers at edge P)
 integer stage=0;                     // 0 delivery, 1 inject, 2 rc/rr/sfu, 3 done
 integer dcount=0, icount=0;
 reg [8:0] drows [0:15]; integer ndrows=8;
 initial for(integer i=0;i<16;i=i+1) drows[i]=9'(i*37+5);
 always @(posedge clk_s) if(rst) begin : drive
  integer pn, ph;
  pn=p+1; ph=pn%4;                    // pn = index of THIS edge
  inj_rd<=0; del_valid<=0; rr_v<=0; ro_v<=0;
  // the value registered at edge P is captured by the SU at A=P+1: allowed iff (P+1)%4 != 2
  if(pn>20 && ((pn+1)%4)!=2) begin
   if(stage==0) begin
    reg [3:0] dv; reg [2179:0] df; reg [159:0] ob;
    dv=0; df=0; ob=0;
    for(integer j=0;j<4;j=j+1) if($urandom(seed)%4!=0) begin
     integer half, row, base;
     half=$urandom%2; row=drows[$urandom%ndrows]; base=64*half+16*j;
     dv[j]=1; ob[40*j+:40]=saddr(base,row);
     df[545*j+544]=1'b1; df[545*j+512+:16]=16'(dcount);
     for(integer w=0;w<16;w=w+1) begin df[545*j+32*w+:32]=$urandom; mem[base+w][row]=df[545*j+32*w+:32]; end
    end
    del_valid<=dv; del_flit<=df; del_obase<=ob; dcount=dcount+1;
    if(dcount>=NDEL) stage=1;
   end else if(stage==1 && pn>20+NDEL*2) begin
    reg [1:0] rd; reg [159:0] ad; reg [1023:0] ex; integer at;
    rd=0; ad=0; ex=0;
    for(integer j=0;j<2;j=j+1) if($urandom%5!=0) begin
     integer lane, row, lane2, row2, b39;
     lane=8*($urandom%16); row=drows[$urandom%ndrows];
     lane2=(lane+8)%128; row2=row+((lane+8)/128);
     if(row2>511) row2=row;
     b39=(B39!=0) && ($urandom%4==0);
     rd[j]=1;
     ad[80*j+:40]=saddr(lane,row)|(b39?40'h80_0000_0000:40'd0);
     ad[80*j+40+:40]=saddr(lane2,row2);
     if(b39) begin
      // IDX lane: SU drives 0; its hi address names a group the other lane may read at another row
      ad[80*j+40+:40]=saddr(8*(j==0?3:5),(row+1)%512);
     end else
      for(integer w=0;w<8;w=w+1) begin ex[512*j+32*w+:32]=mem[lane+w][row]; ex[512*j+256+32*w+:32]=mem[lane2+w][row2]; end
    end
    // avoid two sectors on one group at different rows (a compiler rule; RTL faults)
    begin : grpchk
     reg ok; ok=1;
     for(integer a=0;a<4;a=a+1) for(integer b=a+1;b<4;b=b+1)
      if(rd[a/2] && rd[b/2] && !(B39 && ad[80*(a/2)+39]) && !(B39 && ad[80*(b/2)+39]) &&
         ad[40*a+3+:4]==ad[40*b+3+:4] && ad[40*a+7+:9]!=ad[40*b+7+:9]) ok=0;
     if(!ok) rd=0;
    end
    if(rd!=0 || 1) begin
     inj_rd<=rd; inj_addr<=ad;
     at=pn+INJ_RET; exp_inj[at%8192]=ex; exp_has[at%8192]=1;
    end
    icount=icount+1;
    if(icount>=NINJ) stage=2;
   end
  end
  if(ph2 && pn==60) begin del_valid<=4'b0001; del_obase<=saddr(0,1); del_flit[544]<=1'b1; end   // captured at phase 2
 end
 // inject check: value after edge q equals expectation registered for q
 always @(posedge clk_s) if(rst) begin
  #0.2;
  if(exp_has[p%8192]) begin
   checks=checks+1;
   if(inj_d!==exp_inj[p%8192]) err($sformatf("inj_d mismatch at P+INJ_RET (lane0 lo got %h exp %h)",inj_d[31:0],exp_inj[p%8192][31:0]));
   exp_has[p%8192]=0;
  end
 end
 // +COLLIDE: a drain of slice 1 port 0 group (h=0,hi=0) row 5 in the same serial edge as an inject of that group
 // (inject captured at A=4k -> serial 3k+1; drain vmw_cmd presented for serial edge 3k+1)
 initial if(collide) begin
  wait(stage==1); @(posedge clk_s);
  @(posedge clk_s); while(((p+2)%4)!=0) @(posedge clk_s);
  // this edge P: request captured at A=P+1 (phase 0) -> serial s2q(A)
  inj_rd<=2'b01; inj_addr<={40'd0,saddr(8*2,5)};      // group g=2 -> slice 1, h=0, hi=0
  begin : dr
   integer ns; ns=s2q(p+2);
   wait(n==ns-1); #0.1;
   vmw_cmd[78*1+:39]<={1'b1,1'b0,1'b0,9'd5,16'd0,8'hff}; @(posedge clk_q); #0.1; vmw_cmd<=0;
  end
 end
 // ------------------------------------------------------------------ stage 2: RED_CARRY, RR, SFU ro
 // reducer scalar sequence at the cxport pins on serial edges; expected rc pulse stream edge computed from the epoch map
 integer rc_exp_edge [0:15]; reg [258:0] rc_exp [0:15]; integer nrc=0, rc_seen=0;
 reg [255:0] rr_exp [0:7];
 initial begin : stage2
  reg [255:0] words; integer s, m, pe, late, tag;
  wait(stage==2);
  repeat(40) @(posedge clk_q);
  for(integer e=0;e<6;e=e+1) begin
   tag=e; late=(e%2); words=0;
   for(integer w=0;w<8;w=w+1) begin
    @(posedge clk_q); #0.1;
    red_sv<=1; red_x<=$urandom;
    red_tag<=32'h200 | (w<<10) | ((w==7)<<13) | (tag<<14) | (late<<17) | ((e%8)<<18) | ((e%4)<<21) | (1<<23);
    #0.01; words[32*w+:32]=red_x;
    if(w==7) begin
     // captured at the next serial edge s (= n+1), processed at s+1 = m
     m=n+2; pe=q2s(m)+late;
     rc_exp_edge[nrc]=pe; rc_exp[nrc]={3'(tag),words}; nrc=nrc+1;
    end
   end
   @(posedge clk_q); #0.1; red_sv<=0; red_tag<=0;
   repeat(3) @(posedge clk_q);
  end
 end
 always @(posedge clk_s) if(rst) begin
  #0.2;
  if(rc_v) begin
   if(rc_seen>=nrc || rc_exp_edge[rc_seen]!=p) err($sformatf("rc_v at unexpected edge %0d (exp %0d)",p,rc_seen<nrc?rc_exp_edge[rc_seen]:-1));
   else if({rc_tag,rc_d}!==rc_exp[rc_seen]) err("rc tag/data mismatch");
   checks=checks+1; rc_seen=rc_seen+1;
  end
 end
 // rr: after the rc's, return 4 results (tags 0..3) and read their RF sectors back
 initial begin : rrphase
  wait(stage==2); wait(rc_seen==6); repeat(10) @(posedge clk_s);
  for(integer t=0;t<4;t=t+1) begin
   reg [255:0] d;
   while(((p+2)%4)==2) @(posedge clk_s);
   for(integer w=0;w<8;w=w+1) d[32*w+:32]=$urandom;
   #0.1; rr_v<=1; rr_tag<=3'(t); rr_d<=d; rr_exp[t]=d;
   @(posedge clk_s); #0.1; rr_v<=0;
   repeat(3) @(posedge clk_s);
  end
  repeat(10) @(posedge clk_q);
  // read back: RF word addr = {row2, bank6}, sector s, row r -> banks 8s..8s+7; class 0 command one edge before
  for(integer t=0;t<4;t=t+1) for(integer w=0;w<8;w=w+1) begin
   integer bank, row, k;
   bank=8*(t%8)+w; row=t%4;
   @(posedge clk_q); #0.1; rf_rd_cmd[8:0]<={1'b1,2'(row),6'(bank)}; k=n+1;
   @(posedge clk_q); #0.1; rf_rd_cmd[8:0]<=0;
   wait(n==k+3); #0.1;
   checks=checks+1;
   if(rf_bword[31:0]!==rr_exp[t][32*w+:32]) err($sformatf("RF rr word t%0d w%0d got %h exp %h",t,w,rf_bword[31:0],rr_exp[t][32*w+:32]));
  end
  stage=3;
 end
 // SFU ro: ro at stream edge P (captured A=P+1), SFU red_cmd at serial E=ceil((3A+3)/4), rc_x checked at E+1
 initial begin : sfu
  wait(stage==3);
  for(integer t=0;t<12;t=t+1) begin
   reg [511:0] x; integer A, E, lane;
   @(posedge clk_s); while(((p+2)%4)==2) @(posedge clk_s);
   for(integer w=0;w<16;w=w+1) x[32*w+:32]=$urandom;
   lane=$urandom%16; A=p+2;
   #0.1; ro_v<=16'hffff; ro_x<=x;
   @(posedge clk_s); #0.1; ro_v<=0; ro_x<=0;
   E=s2q(A);
   wait(n==E-1); #0.1; red_cmd<={1'b1,3'd1,10'd0,10'd0,10'd0,32'd0,1'b1,1'b1,2'b00,4'(lane)};
   @(posedge clk_q); #0.1; red_cmd<=0;
   @(posedge clk_q); #0.1;
   checks=checks+1;
   if(u_core.rc_x!==x[32*lane+:32]) err($sformatf("SFU reducer operand lane %0d got %h exp %h",lane,u_core.rc_x,x[32*lane+:32]));
   repeat(4) @(posedge clk_q);
  end
  repeat(20) @(posedge clk_q);
  if(collide||ph2) begin
   if(any_fault) $display("SU_COLLPORT PASS negative control faulted (cx %0d core %0d slices %b)",cx_fault,core_fault,sl_fault);
   else begin $display("SU_COLLPORT FAIL negative control did not fault"); $fatal(1,"SU_COLLPORT gate rejected"); end
   $finish;
  end
  if(errors==0 && !any_fault && checks>NINJ/2 && rc_seen==6)
   $display("SU_COLLPORT PASS QID=%0d INJ_RET=%0d SD=%0d checks=%0d deliveries=%0d injects=%0d rc=%0d",QID,INJ_RET,SD,checks,dcount,icount,rc_seen);
  else begin
   $display("SU_COLLPORT FAIL errors=%0d fault(cx %0d core %0d slices %b) checks=%0d rc=%0d",errors,cx_fault,core_fault,sl_fault,checks,rc_seen);
   $fatal(1,"SU_COLLPORT gate rejected");
  end
  $finish;
 end
 initial begin #2000000; $display("SU_COLLPORT FAIL timeout stage=%0d",stage); $fatal(1,"SU_COLLPORT gate rejected"); end
endmodule
`default_nettype wire
