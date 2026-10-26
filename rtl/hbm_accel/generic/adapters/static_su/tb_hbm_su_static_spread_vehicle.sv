`timescale 1ns/1ps
`default_nettype none
// Static SU VM transport vehicle: the compiler's per-quarter-spread calendar (tools/hbm_static/su_f2_spread.py)
// executed edge by edge on real RTL: 4 quarters x ot_hbm_su_static_vm_ports (4 bank-pair port groups each, GEO-H)
// -> ot_hbm_vm_lg_static_split SU near station (read return 10, write done 7) -> 32 ot_vms_bank_static
// (96 real 1024x256 SRAM macro models, SECDED). No credits/ready: the bench drives every request on its compiled
// edge and checks (a) zero port/LG/bank faults, (b) every read returns exactly +10 with the exact expected sector,
// (c) every write is done exactly +7, (d) per-record VM transport windows equal the compiler's, (e) the final image
// read back from every touched sector equals the compiler's final image. Preload and readback are unmeasured.
// MUT_PG=1: port groups drop the per-quarter spread (SID bits) -> must FAIL. MUT_LG=1: LG write-mux mutant -> FAIL.
// The LG local read/write selects come from the VM calendar programme image (cal_rd/cal_wr, set from the compiled
// calendar events), never from the SU ports. MUT_CAL=1: the calendar omits one SU read slot (quarter 1) -> FAIL.
module tb_hbm_su_static_spread_vehicle;
 parameter integer MUT_PG=0,MUT_LG=0,MUT_CAL=0,MAXPRE=32768,MAXEV=32768,MAXREC=64;
 // Adopted floorplan T_band2__npg4_s5 (main 952c5933c): all four quarters 4 bank-pair groups (BANK_GROUP 0x33221100);
 // the superseded v15/D 5-group SW/SE map (SWSE_NPG 5, 0x43322110) stays reachable via -P parameter overrides.
 parameter integer SWSE_NPG=4;
 parameter [31:0] SWSE_BANK_GROUP=32'h3322_1100;
 localparam integer RR=10,WR=7;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [8*17-1:0] su_rq[0:3];reg [8*281-1:0] su_wq[0:3];
 reg [7:0] cal_rd[0:3],cal_wr[0:3];integer cal_cut=0;
 wire [8*257-1:0] su_rr[0:3];wire [7:0] su_w_done[0:3];
 wire [4:0] pg_fault[0:3];wire [7:0] lg_fault[0:3];
 wire [32*18-1:0] status;
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [8*17-1:0] lrq,nrq;wire [8*281-1:0] lwq,nwq;wire [7:0] ndone,ldone;
  wire [8*257-1:0] nrr,lrr;
  localparam integer NPG=(q<2)?SWSE_NPG:4;
  wire [NPG-1:0] pf;
  assign pg_fault[q]=5'(pf);
  ot_hbm_su_static_vm_ports #(.QID(q),.READ_RETURN(RR),.WRITE_RETURN(WR),.MUT(MUT_PG),.NPG(NPG),
   .BANK_GROUP((q<2)?SWSE_BANK_GROUP:32'h3322_1100)) ports(
   .pg_clk({NPG{clk}}),.rst_n(rst_n),.su_rq(su_rq[q]),.su_wq(su_wq[q]),.su_rr(su_rr[q]),.su_w_done(su_w_done[q]),
   .lg_rq(lrq),.lg_wq(lwq),.lg_rr(lrr),.lg_w_done(ldone),.fault(pf));
  ot_hbm_vm_lg_static_split #(.READ_RETURN(RR),.WRITE_RETURN(WR),.MUT(MUT_LG)) lg(
   .clk({8{clk}}),.rst_n(rst_n),.local_rq(lrq),.far_rq(136'd0),.local_wq(lwq),.far_wq(2248'd0),
   .local_read(cal_rd[q]),.local_write(cal_wr[q]),.near_rq(nrq),.near_wq(nwq),.near_rr(nrr),.near_w_done(ndone),
   .local_rr(lrr),.far_rr(),.local_w_done(ldone),.far_w_done(),.bank_fault(lg_fault[q]));
  for(genvar b=0;b<8;b=b+1)begin:g_b
   wire [3*257-1:0] rr3;
   ot_vms_bank_static #(.RG(3),.WG(1)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
    .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),.rq({34'd0,nrq[b*17+:17]}),.rr(rr3),
    .wq(nwq[b*281+:281]),.wq_done(ndone[b]),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
    .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[(q*8+b)*18+:18]));
   assign nrr[b*257+:257]=rr3[0+:257];
  end
 end
 reg [31:0] nimg[0:2];
 reg [275:0] pre[0:MAXPRE-1];reg [275:0] fin[0:MAXPRE-1];
 reg [327:0] ev[0:MAXEV-1];reg [63:0] win[0:MAXREC-1];
 integer npre,nev,nrec,errors=0,cycle=0,reads=0,writes=0,i,q,b;
 // expected returns, indexed by absolute edge modulo 64
 reg exp_r[0:63][0:31];reg exp_w[0:63][0:31];reg [255:0] exp_d[0:63][0:31];reg [7:0] exp_k[0:63][0:31];
 reg [31:0] first_seen[0:MAXREC-1],last_seen[0:MAXREC-1];
 integer t0=-1;reg measuring=0,checking=1;
 task clear;begin for(q=0;q<4;q=q+1)begin su_rq[q]=0;su_wq[q]=0;cal_rd[q]=0;cal_wr[q]=0;end end endtask
 // drive one sector request for the edge being prepared (request sampled at the coming posedge = 'cycle')
 task put(input reg w,input integer qq,input reg[15:0] sec,input reg[7:0] m,input reg[255:0] d,input integer k,input reg chk);
  integer bb;begin
   bb=sec[2:0];
   if(w)begin
    if(su_wq[qq][bb*281+280])begin $display("ERR double write q%0d b%0d edge %0d",qq,bb,cycle);errors=errors+1;end
    su_wq[qq][bb*281+:281]={1'b1,sec,d,m};cal_wr[qq][bb]=1'b1;
    exp_w[(cycle+WR)%64][qq*8+bb]=1;exp_k[(cycle+WR)%64][qq*8+bb]=8'(k);
   end else begin
    if(su_rq[qq][bb*17+16])begin $display("ERR double read q%0d b%0d edge %0d",qq,bb,cycle);errors=errors+1;end
    su_rq[qq][bb*17+:17]={1'b1,sec};
    if(MUT_CAL!=0&&qq==1&&cal_cut==0&&chk)cal_cut=1;else cal_rd[qq][bb]=1'b1;
    exp_r[(cycle+RR)%64][qq*8+bb]=chk;exp_d[(cycle+RR)%64][qq*8+bb]=d;exp_k[(cycle+RR)%64][qq*8+bb]=8'(k);
    if(!chk)exp_r[(cycle+RR)%64][qq*8+bb]=1'b1;
   end
  end
 endtask
 // advance one edge and check everything visible after it
 task tick;integer s,k,slot;begin
  @(posedge clk);#2;
  slot=cycle%64;
  if(rst_n)begin
   for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)begin
    s=q*8+b;
    if(su_rr[q][b*257+256]!==exp_r[slot][s])begin
     if(errors<10)$display("ERR read return phase edge %0d q%0d b%0d got %b exp %b",cycle,q,b,su_rr[q][b*257+256],exp_r[slot][s]);errors=errors+1;
    end else if(exp_r[slot][s])begin
     reads=reads+1;
     if(checking&&su_rr[q][b*257+:256]!==exp_d[slot][s])begin
      if(errors<10)$display("ERR read data edge %0d q%0d b%0d rec %0d got %h exp %h",cycle,q,b,exp_k[slot][s],su_rr[q][b*257+:64],exp_d[slot][s][63:0]);errors=errors+1;
     end
     if(measuring)begin k=exp_k[slot][s];if(last_seen[k]<cycle-t0)last_seen[k]=cycle-t0;end
    end
    if(su_w_done[q][b]!==exp_w[slot][s])begin
     if(errors<10)$display("ERR write done phase edge %0d q%0d b%0d",cycle,q,b);errors=errors+1;
    end else if(exp_w[slot][s])begin
     writes=writes+1;
     if(measuring)begin k=exp_k[slot][s];if(last_seen[k]<cycle-t0)last_seen[k]=cycle-t0;end
    end
    exp_r[slot][s]=0;exp_w[slot][s]=0;
   end
  end
  cycle=cycle+1;@(negedge clk);
 end endtask
 integer ptr,k;reg [8*512-1:0] stem;
 reg [7:0] pend[0:31];
 initial begin
  if(!$value$plusargs("stem=%s",stem))$fatal(1,"+stem=<image path stem> required");
  $readmemh($sformatf("%0s_n.mem",stem),nimg);npre=nimg[0];nev=nimg[1];nrec=nimg[2];
  if(npre>MAXPRE||nev>MAXEV||nrec>MAXREC)$fatal(1,"vehicle image exceeds bench arrays");
  $readmemh($sformatf("%0s_pre.mem",stem),pre);$readmemh($sformatf("%0s_ev.mem",stem),ev);
  $readmemh($sformatf("%0s_final.mem",stem),fin);$readmemh($sformatf("%0s_win.mem",stem),win);
  for(i=0;i<64;i=i+1)for(b=0;b<32;b=b+1)begin exp_r[i][b]=0;exp_w[i][b]=0;end
  for(i=0;i<MAXREC;i=i+1)begin first_seen[i]=32'hffffffff;last_seen[i]=0;end
  clear();repeat(6)tick();rst_n=1;repeat(2)tick();
  // ---- preload (unmeasured): each bank one full-sector write per edge
  ptr=0;
  while(ptr<npre)begin
   clear();for(b=0;b<32;b=b+1)pend[b]=0;
   // simple greedy: walk forward, take the first unserved sector of each bank
   for(i=ptr;i<npre;i=i+1)begin
    q=pre[i][275:272];b=q*8+pre[i][258:256];
    if(pre[i][275:272]!==4'hf&&!pend[b])begin
     put(1,q,pre[i][271:256],8'hff,pre[i][255:0],0,1);pend[b]=1;pre[i][275:272]=4'hf;
    end
    if(i>ptr+40000)i=npre;
   end
   tick();
   while(ptr<npre&&pre[ptr][275:272]==4'hf)ptr=ptr+1;
  end
  clear();repeat(RR+4)tick();
  // ---- the compiled calendar, edge for edge
  t0=cycle;measuring=1;ptr=0;
  while(ptr<nev)begin
   clear();
   while(ptr<nev&&ev[ptr][327:296]==32'(cycle-t0))begin
    k=ev[ptr][295:288];
    put(ev[ptr][287:284]!=0,ev[ptr][283:280],ev[ptr][279:264],ev[ptr][263:256],ev[ptr][255:0],k,1);
    if(first_seen[k]>cycle-t0)first_seen[k]=cycle-t0;
    ptr=ptr+1;
   end
   if(ptr<nev&&ev[ptr][327:296]<32'(cycle-t0))$fatal(1,"calendar not sorted at event %0d",ptr);
   tick();
  end
  clear();repeat(RR+4)tick();measuring=0;
  // ---- final readback (unmeasured): every touched sector equals the compiler's final image
  ptr=0;for(i=0;i<npre;i=i+1)pre[i][275:272]=fin[i][275:272];
  while(ptr<npre)begin
   clear();for(b=0;b<32;b=b+1)pend[b]=0;
   for(i=ptr;i<npre&&i<ptr+40000;i=i+1)begin
    q=pre[i][275:272];b=q*8+fin[i][258:256];
    if(q!=15&&!pend[b])begin put(0,q,fin[i][271:256],8'hff,fin[i][255:0],0,1);pend[b]=1;pre[i][275:272]=4'hf;end
   end
   tick();
   while(ptr<npre&&pre[ptr][275:272]==4'hf)ptr=ptr+1;
  end
  clear();repeat(RR+4)tick();
  // ---- verdict
  for(i=0;i<4;i=i+1)if(pg_fault[i]!==0||lg_fault[i]!==0)begin $display("ERR fault quarter %0d pg=%b lg=%b",i,pg_fault[i],lg_fault[i]);errors=errors+1;end
  if(status!==0)begin $display("ERR bank status %h",status);errors=errors+1;end
  for(k=0;k<nrec;k=k+1)begin
   $display("RECORD %0d window measured %0d..%0d = %0d edges, compiler %0d..%0d",k,first_seen[k],last_seen[k],
            last_seen[k]-first_seen[k],win[k][63:32],win[k][31:0]);
   if(first_seen[k]!==win[k][63:32]||last_seen[k]!==win[k][31:0])begin $display("ERR record %0d window",k);errors=errors+1;end
  end
  if(errors)$fatal(1,"SU_SPREAD_VEHICLE FAIL errors=%0d reads=%0d writes=%0d",errors,reads,writes);
  $display("SU_SPREAD_VEHICLE PASS preload=%0d events=%0d records=%0d reads=%0d writes=%0d calendar_edges=%0d quarters=4 port_groups=%0d(SW/SE %0d) lg_leaves=32 banks=32 srams=96",
           npre,nev,nrec,reads,writes,ev[nev-1][327:296]+1,8+2*SWSE_NPG,SWSE_NPG);
  $finish;
 end
endmodule
`default_nettype wire
