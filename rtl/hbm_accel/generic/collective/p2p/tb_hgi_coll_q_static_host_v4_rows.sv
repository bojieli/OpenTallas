`timescale 1ns/1ps
`default_nettype none
// P-row COLL.ROW_GATHER on the ACTUAL die-bound native V4 quadrants: two dies x {q3 SW host_v4 QID0, q2 host_v4
// QID1} = four actual parents (program target, issuer + 3 program SRAMs, qslots, ring, reduce, ARG/TKM on q3,
// writer, ALL-input-capture endpoints with native SRAM/CRC). Die d's quadrant q rail k is wired to die 1-d's
// quadrant q rail k through a W-edge pin-to-pin delay (the 453-cycle off-die PHY/package crossing stand-in; SPMD:
// both dies run the same compiled programme, so the peer is the real RTL, not a replay).
// Declared boundary models only: SU inject read data (G-CIL-INJ: the die leaves inj_d unbound; request pins are
// observed P+1, data stable before the P+12 capture), the COLL VM read group (bank sample P+1, response P+8), and
// the wire. rc_* is tied idle (G-CIL-RC: the ring is not used by ROW_GATHER and r_lp_we stays 0).
// The scoreboard's reference is independent of the programme words: expected payload, header and delivery
// address of the j-th delivered flit of every lane follow from the sender's identity and (position, flit) = j / R.
module tb_hgi_coll_q_static_host_v4_rows #(parameter integer NE=4);
 // NE 4: two dies x {q3, q2}, die d's rails wired to die 1-d's. NE 2 (SPMD loopback): ONE die {q3, q2}; each parent's
 // RX pin is its OWN TX pin W edges earlier. Valid because both dies run the identical compiled programme on a
 // data-independent static calendar, so the peer's TX pin sequence equals this die's (only the payload's sender
 // identity differs; the scoreboard expects the sender = this die). Halves the build (the q3 TKM elaborates ~124 GB).
 localparam [39:0] OBASE=40'h40000000, RS=40'h60000;
 localparam [15:0] IDX0_0=16'h0100, IDX0_1=16'h4100, VM_S0=16'h0200;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,launch=0;
 reg [3:0] cv=0,dvc=0;
 reg [11:0] cfg_addr[0:3];reg [255:0] cfg_data[0:3];reg [12:0] limit[0:3];
 wire [3:0] configured,init_busy,program_fault,busy,done,fault;
 reg [1535:0] rows[0:3][0:63];reg [63:0] meta[0:3][0:63];
 reg [1535:0] rtmp[0:63];reg [63:0] mtmp[0:63];
 integer NR[0:3];
 integer P=1,R=8,W=20,MAXC=200000,OP=0; // OP 0 ROW_GATHER, 1 ARGMAX_MERGE (q3 ARG fold)
 // ARGMAX operands (argmax_rows.py placement, mirrored here): rank r of position p is VM line VB+p*VS+r/4,
 // pair lane r%4 = banks {2j+1,2j}; the low bank's words 0/1 carry (value FP32, id U32)
 localparam [15:0] VB=16'h0400,VS=16'h0020;localparam [39:0] OBASE_A=40'h41000000,DSTRIDE=40'h40;
 function automatic [31:0] mix(input [31:0] x);
  reg [31:0] h;h=x*32'h9e3779b1;h=h^(h>>15);h=h*32'h85ebca6b;h=h^(h>>13);return h;
 endfunction
 function automatic [31:0] cand_value(input integer p,input integer r);
  reg [31:0] h;h=mix(32'(p*131+r+7));
  if(r==(p*7)%96 || r==(p*7+13)%96)return 32'h42280000;        // tie at the maximum: lower id must win
  if(p==3 && r==5)return 32'h7fc00000;                             // NaN orders after every number
  if(p==4 && r==40)return 32'h7f800000;                            // +inf is a number and wins
  return {h[0],8'(120+h[3:1]),h[26:4]};
 endfunction
 function automatic [31:0] cand_id(input integer p,input integer r);return 32'(1000*p+(r*37)%96);endfunction
 function automatic [31:0] okey(input [31:0] v);
  if(v[30:0]==0)return 32'h80000000;return v[31]?~v:(v|32'h80000000);
 endfunction
 function automatic isnan(input [31:0] v);return v[30:23]==8'hff && v[22:0]!=0;endfunction
 function automatic [31:0] winner_id(input integer p);
  reg [31:0] bv,bi,v,i;
  bv=cand_value(p,0);bi=cand_id(p,0);
  for(integer r=1;r<96;r=r+1)begin
   reg take;v=cand_value(p,r);i=cand_id(p,r);
   if(isnan(v)!=isnan(bv))take=isnan(bv);
   else if(isnan(v))take=i<bi;
   else if(okey(v)!=okey(bv))take=okey(v)>okey(bv);
   else take=i<bi;
   if(take)begin bv=v;bi=i;end
  end
  return bi;
 endfunction
 function automatic [255:0] vmbank(input integer die,input integer q,input integer bank,input [15:0] sector);
  integer p,r;
  if(OP==1 && bank%2==0 && sector>=VB)begin
   p=int'(sector-VB)/int'(VS);r=4*(int'(sector-VB)%int'(VS))+bank/2;
   return {192'd0,cand_id(p,r),cand_value(p,r)};
  end
  return vmword(die,q,bank,sector);
 endfunction
 string dir;
 wire [1:0] inj_rd[0:3];wire [31:0] inj_idx[0:3];wire [159:0] inj_addr[0:3];wire [1023:0] inj_d[0:3];
 wire [3:0] del_v[0:3];wire [2179:0] del_d[0:3];wire [159:0] del_a[0:3];
 wire [2:0] txv[0:3];wire [1835:0] txf[0:3];wire [2:0] rxv[0:3];wire [1835:0] rxf[0:3];
 wire [135:0] vm_rq[0:3];wire [2055:0] vm_rr[0:3];
 integer cyc=0,launch_cyc=-1;
 // pin history of every parent's TX (the wire's shift register)
 reg [2:0] hv[0:3][0:1023];reg [1835:0] hfl[0:3][0:1023];
 always @(posedge clk)for(integer e=0;e<NE;e=e+1)begin hv[e][cyc%1024]<=txv[e];hfl[e][cyc%1024]<=txf[e];end
 function automatic integer gidx(input integer q,input integer k);return q==0?k:3+k;endfunction
 function automatic [511:0] payload_su(input integer die,input integer q,input integer port,input [15:0] idx);
  reg [511:0] v;
  for(integer l=0;l<16;l=l+1)v[l*32+:32]=32'h5eed0000^(32'(die)*32'h15162123)^(32'(q)*32'h83761045)^
    (32'(port)*32'h2c1b3c6d)^(32'(idx)*32'h99172353)^(32'(l)*32'hba590723);
  return v;
 endfunction
 function automatic [255:0] vmword(input integer die,input integer q,input integer bank,input [15:0] sector);
  reg [255:0] v;
  for(integer l=0;l<8;l=l+1)v[l*32+:32]=32'h7a110000^(32'(die)*32'h297a2d39)^(32'(q)*32'h6b43a9b5)^
    (32'(bank)*32'h1b873593)^(32'(sector)*32'hcc9e2d51)^(32'(l)*32'he6546b64);
  return v;
 endfunction
 // ---------------- four actual parents ----------------
 for(genvar e=0;e<NE;e=e+1)begin:g_p
  localparam integer D=e/2,Q=e%2,PEER=(NE==2)?e:(e^2);
  wire [2:0] retry;wire [279:0] cwo,ccwo;wire [2247:0] kq;wire rrv;wire [2:0] rrt;wire [255:0] rrd;wire [31:0] stat;
  wire hf;
  // SU inject boundary model: index pin observed P+1, eleven registers, data stable for the P+12 capture
  reg [15:0] sidx0[0:10],sidx1[0:10];
  always @(posedge clk)begin
   sidx0[0]<=inj_idx[e][15:0];sidx1[0]<=inj_idx[e][31:16];
   for(integer s=1;s<11;s=s+1)begin sidx0[s]<=sidx0[s-1];sidx1[s]<=sidx1[s-1];end
  end
  assign inj_d[e]={payload_su(D,Q,1,sidx1[10]),payload_su(D,Q,0,sidx0[10])};
  // COLL VM read-group boundary model: request pin sampled P+1, response register visible P+8
  reg [135:0] vmp[0:6];
  always @(posedge clk)begin vmp[0]<=vm_rq[e];for(integer s=1;s<7;s=s+1)vmp[s]<=vmp[s-1];end
  for(genvar b=0;b<8;b=b+1)begin:g_bank
   assign vm_rr[e][b*257+:257]=vmp[6][b*17+16]?{1'b1,vmbank(D,Q,b,vmp[6][b*17+:16])}:257'd0;
  end
  // Off-die crossing stand-in: rx pin in cycle t = peer tx pin in cycle t-W
  assign rxv[e]=(cyc>=W)?hv[PEER][(cyc-W)%1024]:3'b0;
  assign rxf[e]=hfl[PEER][(cyc-W+1024)%1024];
  if(Q==0)begin:g_q3
   ot_hfd_coll_q3_static_host_v4 #(.QID(2'd0)) dut(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
    .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),.clk_tkm({34{clk}}),.clk_vmwrite(clk),
    .clk_link({15{clk}}),.cfg_v(cv[e]),.cfg_target(8'd52),.cfg_addr(cfg_addr[e]),.cfg_data(cfg_data[e]),
    .desc_v(dvc[e]),.desc_base(12'd0),.desc_limit(limit[e]),.desc_loops(16'd1),.launch_v(launch),
    .program_configured(configured[e]),.program_init_busy(init_busy[e]),.program_fault(program_fault[e]),
    .hgi_busy(busy[e]),.hgi_done(done[e]),.hgi_fault(hf),
    .inj_rd(inj_rd[e]),.inj_idx(inj_idx[e]),.hgi_inj_addr(inj_addr[e]),.inj_d(inj_d[e]),
    .del_valid(del_v[e]),.del_flit(del_d[e]),.hgi_del_obase(del_a[e]),
    .rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),.rr_v(rrv),.rr_tag(rrt),.rr_d(rrd),
    .phy_up(3'b111),.tx_pin_v(txv[e]),.tx_pin_flit(txf[e]),.rx_pin_v(rxv[e]),.rx_pin_flit(rxf[e]),.retry_requested(retry),
    .pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
    .vm_rq(vm_rq[e]),.vm_rr(vm_rr[e]),.vm_kq(kq),.fault(fault[e]),.done(),.stat_cycles(stat));
  end else begin:g_q2
   assign txv[e][2]=1'b0;assign txf[e][1835:1224]='0;
   ot_hfd_coll_q2_static_host_v4 #(.QID(2'd1)) dut(.rst_n(rst_n),.clk_program(clk),.clk_control(clk),.clk_issue({4{clk}}),
    .clk_qslots({2{clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_vmwrite(clk),
    .clk_link({10{clk}}),.cfg_v(cv[e]),.cfg_target(8'd53),.cfg_addr(cfg_addr[e]),.cfg_data(cfg_data[e]),
    .desc_v(dvc[e]),.desc_base(12'd0),.desc_limit(limit[e]),.desc_loops(16'd1),.launch_v(launch),
    .program_configured(configured[e]),.program_init_busy(init_busy[e]),.program_fault(program_fault[e]),
    .hgi_busy(busy[e]),.hgi_done(done[e]),.hgi_fault(hf),
    .inj_rd(inj_rd[e]),.inj_idx(inj_idx[e]),.hgi_inj_addr(inj_addr[e]),.inj_d(inj_d[e]),
    .del_valid(del_v[e]),.del_flit(del_d[e]),.hgi_del_obase(del_a[e]),
    .rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),.rr_v(rrv),.rr_tag(rrt),.rr_d(rrd),
    .phy_up(2'b11),.tx_pin_v(txv[e][1:0]),.tx_pin_flit(txf[e][1223:0]),.rx_pin_v(rxv[e][1:0]),.rx_pin_flit(rxf[e][1223:0]),
    .retry_requested(retry[1:0]),.pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
    .vm_rq(vm_rq[e]),.vm_rr(vm_rr[e]),.vm_kq(kq),.fault(fault[e]),.done(),.stat_cycles(stat));
  end
 end
 // ---------------- scoreboard and event log ----------------
 integer cnt[0:3][0:3],first_del[0:3][0:3],last_del[0:3][0:3];
 integer errors=0,addr_errors=0,data_errors=0,stray=0,fault_first=-1,done_cyc[0:3],done_count[0:3];
 integer first_inj[0:3],first_tx[0:3],first_rx[0:3];
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(launch)launch_cyc<=cyc;
  if(rst_n)for(integer e=0;e<NE;e=e+1)begin
   integer npt,S,Q;
   npt=(e%2==0)?3:2;S=(NE==2)?e/2:1-e/2;Q=e%2;
   if((fault[e]||program_fault[e]) && fault_first<0)fault_first<=cyc;
   if(done[e])begin done_cyc[e]<=cyc;done_count[e]<=done_count[e]+1;end
   if(|inj_rd[e] && first_inj[e]<0)first_inj[e]<=cyc;
   if(|txv[e] && first_tx[e]<0)first_tx[e]<=cyc;
   if(|rxv[e] && first_rx[e]<0)first_rx[e]<=cyc;
   for(integer k=0;k<4;k=k+1)if(del_v[e][k])begin
    if(OP==1)begin
     integer j;reg [544:0] want;
     j=cnt[e][k];
     want={1'b1,8'hff,8'(e/2),16'd0,480'd0,winner_id(j)};
     if(k!=0 || Q!=0 || j>=P)stray=stray+1;
     else begin
      if(del_d[e][k*545+:545]!==want)begin data_errors=data_errors+1;
       if(data_errors<8)$display("ARG_MISMATCH e%0d pos%0d cyc%0d got id%0d want id%0d",e,j,cyc,del_d[e][31:0],want[31:0]);end
      if(del_a[e][39:0]!==OBASE_A+40'(j)*DSTRIDE)begin addr_errors=addr_errors+1;
       if(addr_errors<4)$display("ADDR_MISMATCH e%0d pos%0d got%h",e,j,del_a[e][39:0]);end
     end
     if(first_del[e][k]<0)first_del[e][k]<=cyc;
     last_del[e][k]<=cyc;cnt[e][k]<=cnt[e][k]+1;
    end else
    if(k>=npt)stray=stray+1;
    else begin
     integer j,p,f;reg [544:0] want;reg [39:0] wa;
     j=cnt[e][k];p=j/R;f=j%R;
     if(k<2)want={1'b1,8'hff,8'(S),16'((k==0?IDX0_0:IDX0_1)+16'(j)),payload_su(S,Q,k,16'((k==0?IDX0_0:IDX0_1)+16'(j)))};
     else want={1'b1,8'hff,8'(S),16'ha5a5,vmword(S,Q,1,VM_S0+16'(j)),vmword(S,Q,0,VM_S0+16'(j))};
     wa=OBASE+40'(gidx(Q,k))*40'(R)*40'd64+40'(p)*RS+40'(f)*40'd64;
     if(j>=P*R)stray=stray+1;
     else begin
      if(del_d[e][k*545+:545]!==want)begin data_errors=data_errors+1;
       if(data_errors<4)$display("DATA_MISMATCH e%0d lane%0d j%0d cyc%0d got%h want%h",e,k,j,cyc,del_d[e][k*545+512+:33],want[544:512]);end
      if(del_a[e][k*40+:40]!==wa)begin addr_errors=addr_errors+1;
       if(addr_errors<4)$display("ADDR_MISMATCH e%0d lane%0d j%0d (pos%0d flit%0d) cyc%0d got%h want%h",e,k,j,p,f,cyc,del_a[e][k*40+:40],wa);end
     end
     if(first_del[e][k]<0)first_del[e][k]<=cyc;
     last_del[e][k]<=cyc;cnt[e][k]<=cnt[e][k]+1;
    end
   end
  end
 end
 integer expect_total;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing +DIR");
  if($value$plusargs("P=%d",P))begin end
  if($value$plusargs("R=%d",R))begin end
  if($value$plusargs("W=%d",W))begin end
  if($value$plusargs("MAXC=%d",MAXC))begin end
  if($value$plusargs("OP=%d",OP))begin end
  if(!$value$plusargs("NRQ3=%d",NR[0])||!$value$plusargs("NRQ2=%d",NR[1]))$fatal(1,"missing +NRQ3/+NRQ2");
  NR[2]=NR[0];NR[3]=NR[1];
  if(W<1||W>1000)$fatal(1,"wire edges 1..1000");
  for(integer e=0;e<NE;e=e+1)begin
   string nm;nm=$sformatf("%s/d%0dq%0d",dir,e/2,e%2);
   for(integer r=0;r<64;r=r+1)begin rtmp[r]='0;mtmp[r]='0;end
   $readmemh({nm,".rows.hex"},rtmp,0,NR[e]-1);$readmemh({nm,".meta.hex"},mtmp,0,NR[e]-1);
   for(integer r=0;r<64;r=r+1)begin rows[e][r]=rtmp[r];meta[e][r]=mtmp[r];end
   limit[e]=13'(NR[e]);cfg_addr[e]=0;cfg_data[e]=0;
   done_cyc[e]=-1;done_count[e]=0;first_inj[e]=-1;first_tx[e]=-1;first_rx[e]=-1;
   for(integer k=0;k<4;k=k+1)begin cnt[e][k]=0;first_del[e][k]=-1;last_del[e][k]=-1;end
  end
  repeat(4)@(negedge clk);rst_n=1;
  // Native HOST F20 programming: seven frames a row, then the fixed 55-edge drain reservation (no polling)
  for(integer r=0;r<64;r=r+1)if(r<NR[0]||r<NR[1])begin
   for(integer s=0;s<7;s=s+1)begin
    @(negedge clk);
    for(integer e=0;e<NE;e=e+1)begin
     cv[e]=r<NR[e];cfg_addr[e]=12'(r*8+s);
     cfg_data[e]=s<6?rows[e][r][s*256+:256]:{192'd0,meta[e][r]};
    end
   end
   @(negedge clk);cv=0;
   repeat(55)@(negedge clk);
   if(|init_busy || |program_fault)$fatal(1,"host row %0d drain did not finish on its reserved edge",r);
  end
  @(negedge clk);dvc=4'((1<<NE)-1);@(negedge clk);dvc=0;repeat(66)@(negedge clk);
  if(configured[NE-1:0]!==NE'((1<<NE)-1) || |program_fault)$fatal(1,"descriptor validation configured%b fault%b",configured,program_fault);
  @(negedge clk);launch=1;@(negedge clk);launch=0;
  while(!(done_count[0]&&done_count[1]&&(NE==2||(done_count[2]&&done_count[3]))) && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(8)@(negedge clk);
  expect_total=0;
  for(integer e=0;e<NE;e=e+1)begin
   integer npt;npt=(e%2==0)?3:2;
   expect_total=expect_total+npt*P*R;
   for(integer k=0;k<npt;k=k+1)begin
    if(cnt[e][k]!=P*R)errors=errors+1;
    $display("LANE e%0d die%0d q%0d lane%0d delivered%0d first_del%0d last_del%0d",e,e/2,e%2,k,cnt[e][k],
     first_del[e][k]-launch_cyc,last_del[e][k]-launch_cyc);
   end
   $display("PARENT e%0d die%0d q%0d first_inj_pin%0d first_tx_pin%0d first_rx_pin%0d done%0d done_count%0d",e,e/2,e%2,
    first_inj[e]-launch_cyc,first_tx[e]-launch_cyc,first_rx[e]-launch_cyc,done_cyc[e]-launch_cyc,done_count[e]);
   if(done_count[e]!=1)errors=errors+1;
  end
  begin
   integer lastq3,lastq2,firstq3;
   lastq3=-1;lastq2=-1;firstq3=-1;
   for(integer e=0;e<NE;e=e+1)for(integer k=0;k<3;k=k+1)if(last_del[e][k]>=0)begin
    if(e%2==0 && last_del[e][k]-launch_cyc>lastq3)lastq3=last_del[e][k]-launch_cyc;
    if(e%2==1 && last_del[e][k]-launch_cyc>lastq2)lastq2=last_del[e][k]-launch_cyc;
   end
   for(integer e=0;e<NE;e=e+1)if(done_cyc[e]>=0 && done_cyc[e]<=last_del[e][0])errors=errors+1;
   if(OP==1)$display("ARGMAX_ROWS_MEASURE P%0d launch_to_last_delivery q3=%0d positions%0d/%0d data_err%0d addr_err%0d stray%0d fault_first%0d",
    P,lastq3,cnt[0][0]+(NE==4?cnt[2][0]:0),(NE/2)*P,data_errors,addr_errors,stray,fault_first<0?-1:fault_first-launch_cyc);
   $display("ROWGATHER_ROWS_MEASURE P%0d R%0d W%0d launch_to_last_delivery q3=%0d q2=%0d die=%0d delivered%0d/%0d data_err%0d addr_err%0d stray%0d fault_first%0d",
    P,R,W,lastq3,lastq2,lastq3>lastq2?lastq3:lastq2,cnt[0][0]+cnt[0][1]+cnt[0][2]+cnt[1][0]+cnt[1][1]+(NE==4?cnt[2][0]+cnt[2][1]+cnt[2][2]+cnt[3][0]+cnt[3][1]:0),
    expect_total,data_errors,addr_errors,stray,fault_first<0?-1:fault_first-launch_cyc);
  end
  if(errors==0 && data_errors==0 && addr_errors==0 && stray==0 && fault_first<0)
   $display("%s PASS P%0d R%0d W%0d parents%0d q3x%0d q2x%0d",OP==1?"ARGMAX_ROWS":"ROWGATHER_ROWS",P,R,W,NE,NE/2,NE/2);
  else $display("%s FAIL P%0d errors%0d data%0d addr%0d stray%0d fault_first%0d",OP==1?"ARGMAX_ROWS":"ROWGATHER_ROWS",P,errors,data_errors,addr_errors,stray,
   fault_first<0?-1:fault_first-launch_cyc);
  $finish;
 end
endmodule
`default_nettype wire
