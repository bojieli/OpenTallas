`timescale 1ns/1ps
`default_nettype none
// Full eight actual quadrant parents: 2 SW q3 (native KMAX2048) +6 q2.
// Boundary SU stimulus only. All internal issuers, SRAMs, switches, CRC rails,
// ring stops, VM writers and inactive TKM hardware are the actual RTL.
module tb_hfd_coll_static_allgather;
 localparam integer CFGN=3402;
 reg clk=0,rst_n=0,start=0;always #0.5 clk=~clk;
 reg [36:0]cfg[0:7];reg[36:0]cfgmem[0:8*CFGN-1];
 wire[7:0]busy,done,fault;
 wire[1:0]inj_rd[0:7];wire[31:0]inj_idx[0:7];wire[1023:0]inj_data[0:7];
 wire[3:0]del_v[0:7];wire[2179:0]del_d[0:7];wire[159:0]del_addr[0:7];
 wire[2:0]txv[0:7],rxv[0:7];wire[1787:0]txf[0:7],rxf[0:7];
 wire[279:0]cw[0:7],ccw[0:7];
 wire[9:0]dbg_src[0:7];wire[15:0]dbg_dst[0:7];wire[7:0]dbg_cause[0:7];
 wire[29:0]dbg_link[0:7];wire[5:0]dbg_pc[0:7];wire[31:0]dbg_it[0:7];
 integer mut=0,checked=0,errors=0,fault_edges=0,first_fault=-1,p=-9;
 bit seen[0:7][0:1][0:95];string dir;
 function automatic integer cwprev(input integer q);case(q)0:return 2;1:return 0;3:return 1;default:return 3;endcase endfunction
 function automatic integer ccwprev(input integer q);case(q)0:return 1;1:return 3;3:return 2;default:return 0;endcase endfunction
 function automatic[511:0] payload(input integer die,input integer q,input integer idx);
  reg[511:0]v;
  for(integer l=0;l<16;l=l+1)v[l*32+:32]=32'hfeed0000^(32'(die)*32'h15162123)^(32'(q)*32'h83761045)^(32'(idx)*32'h99172353)^(32'(l)*32'hba590723);
  return v;
 endfunction
 function automatic[544:0] expected(input integer die,input integer q,input integer idx);
  return {1'b1,8'hff,8'(die),16'(idx),payload(die,q,idx)};
 endfunction
 function automatic[31:0] crc(input[563:0]body);
  reg[31:0]c;c='1;
  for(integer b=563;b>=0;b=b-1)c={c[30:0],1'b0}^((c[31]^body[b])?32'h04c11db7:32'b0);
  return c;
 endfunction
 for(genvar e=0;e<8;e=e+1)begin:g_q
  localparam integer D=e/4,Q=e%4,OTHER=(1-D)*4+Q;
  wire[159:0]inj_addr;wire[2:0]retry;wire[135:0]vmrq;wire[2247:0]vmkq;
  reg[1023:0]su_pipe[0:10];
  // Registered request edge P -> declared source capture edge P+12.
  // Eleven external producer registers plus consumer sampling edge; metadata
  // valid/identity independently follows the actual parent pipeline.
  always @(posedge clk)begin
   for(integer j=0;j<2;j=j+1)begin
    su_pipe[0][j*512+:512]<=payload(D,Q,int'(inj_idx[e][j*16+:16]))^
      ((mut==1 && e==0 && j==0 && inj_idx[e][15:0]==14)?512'b1:512'b0);
   end
   for(integer l=1;l<11;l=l+1)su_pipe[l]<=su_pipe[l-1];
  end
  assign inj_data[e]=su_pipe[10];
  reg[2:0]wire_v[0:4];reg[1787:0]wire_f[0:4];
  always @(posedge clk)begin
   if(!rst_n)begin for(integer l=0;l<5;l=l+1)wire_v[l]<=0;end
   else begin
    wire_v[0]<=txv[OTHER];wire_f[0]<=txf[OTHER];
    for(integer l=1;l<5;l=l+1)begin wire_v[l]<=wire_v[l-1];wire_f[l]<=wire_f[l-1];end
   end
  end
  assign rxv[e]=wire_v[4];assign rxf[e]=wire_f[4];
  if(Q==0)begin:g_sw
   ot_hfd_coll_q3_static dut(.rst_n(rst_n),.clk_control(clk),.clk_issue({4{clk}}),.clk_qslots({2{clk}}),
    .clk_ring({17{clk}}),.clk_vmwrite(clk),.clk_link({15{clk}}),.clk_tkm({34{clk}}),.qid(2'(Q)),
    .hgi_start(start),.hgi_start_pc(6'b0),.program_cfg(cfg[e]),.hgi_busy(busy[e]),.hgi_done(done[e]),.hgi_fault(),
    .inj_rd(inj_rd[e]),.inj_idx(inj_idx[e]),.hgi_inj_addr(inj_addr),.inj_d(inj_data[e]),
    .del_valid(del_v[e]),.del_flit(del_d[e]),.hgi_del_obase(del_addr[e]),
    .rc_v(1'b0),.rc_tag(3'b0),.rc_d(256'b0),.rr_v(),.rr_tag(),.rr_d(),
    .phy_up(3'b111),.tx_pin_v(txv[e]),.tx_pin_flit(txf[e]),.rx_pin_v(rxv[e]),.rx_pin_flit(rxf[e]),.retry_requested(retry),
    .pr_cw_i(cw[D*4+cwprev(Q)]),.pr_ccw_i(ccw[D*4+ccwprev(Q)]),.pr_cw_o(cw[e]),.pr_ccw_o(ccw[e]),
    .vm_rq(vmrq),.vm_rr(2056'b0),.vm_kq(vmkq),.fault(fault[e]),.done(),.stat_cycles());
   assign dbg_src[e]=dut.u_q.source_v;assign dbg_dst[e]=dut.u_q.dest_v;
   assign dbg_cause[e]={3'b0,dut.u_q.protocol_fault,dut.u_q.slot_cause};
   assign dbg_link[e]=dut.u_q.link_cause;assign dbg_pc[e]=dut.u_q.uop_pc;assign dbg_it[e]=dut.u_q.iteration;
  end else begin:g_other
   assign txv[e][2]=0;assign txf[e][1787:1192]=0;
   ot_hfd_coll_q2_static dut(.rst_n(rst_n),.clk_control(clk),.clk_issue({4{clk}}),.clk_qslots({2{clk}}),
    .clk_ring({17{clk}}),.clk_vmwrite(clk),.clk_link({10{clk}}),.qid(2'(Q)),
    .hgi_start(start),.hgi_start_pc(6'b0),.program_cfg(cfg[e]),.hgi_busy(busy[e]),.hgi_done(done[e]),.hgi_fault(),
    .inj_rd(inj_rd[e]),.inj_idx(inj_idx[e]),.hgi_inj_addr(inj_addr),.inj_d(inj_data[e]),
    .del_valid(del_v[e]),.del_flit(del_d[e]),.hgi_del_obase(del_addr[e]),
    .rc_v(1'b0),.rc_tag(3'b0),.rc_d(256'b0),.rr_v(),.rr_tag(),.rr_d(),
    .phy_up(2'b11),.tx_pin_v(txv[e][1:0]),.tx_pin_flit(txf[e][1191:0]),.rx_pin_v(rxv[e][1:0]),.rx_pin_flit(rxf[e][1191:0]),.retry_requested(retry[1:0]),
    .pr_cw_i(cw[D*4+cwprev(Q)]),.pr_ccw_i(ccw[D*4+ccwprev(Q)]),.pr_cw_o(cw[e]),.pr_ccw_o(ccw[e]),
    .vm_rq(vmrq),.vm_rr(2056'b0),.vm_kq(vmkq),.fault(fault[e]),.done(),.stat_cycles());
   assign dbg_src[e]={1'b0,dut.u_q.source_v};assign dbg_dst[e]={1'b0,dut.u_q.dest_v};
   assign dbg_cause[e]={3'b0,dut.u_q.protocol_fault,dut.u_q.slot_cause};
   assign dbg_link[e]={10'b0,dut.u_q.link_cause};assign dbg_pc[e]=dut.u_q.uop_pc;assign dbg_it[e]=dut.u_q.iteration;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing DIR");
  if($value$plusargs("MUT=%d",mut))begin end
  $readmemh({dir,"/all.cfg.hex"},cfgmem);
  // Runtime program mutations reuse the identical actual hierarchy/binary.
  if(mut==2)cfgmem[25*54+1+11]=cfgmem[25*54+1+11]^(37'b1<<22); // rdslot7->6
  if(mut==3)cfgmem[12*54+1]=cfgmem[12*54+1]^37'b1; // missing SU0 capture
  for(integer e=0;e<8;e=e+1)begin
   cfg[e]=0;for(integer d=0;d<2;d=d+1)for(integer f=0;f<96;f=f+1)seen[e][d][f]=0;
  end
  repeat(8)@(negedge clk);rst_n=1;
  for(integer c=0;c<CFGN;c=c+1)begin
   for(integer e=0;e<8;e=e+1)cfg[e]=cfgmem[e*CFGN+c];
   @(negedge clk);
  end
  for(integer e=0;e<8;e=e+1)cfg[e]=0;
  repeat(3)@(negedge clk);
  if(|fault)$fatal(1,"configuration fault mask%h",fault);
  start=1;@(posedge clk);#0.01;@(negedge clk);start=0;
  for(integer off=1;off<=90;off=off+1)begin
   @(posedge clk);#0.01;p=off-4;
   if(|fault)begin fault_edges=fault_edges+1;if(first_fault<0)first_fault=p;end
   if(mut==0 && |fault)begin
    for(integer e=0;e<8;e=e+1)$display("FAULT e%0d P%0d pc%0d it%0d src%h dst%h cause%h link%h",e,p,dbg_pc[e],dbg_it[e],dbg_src[e],dbg_dst[e],dbg_cause[e],dbg_link[e]);
    $fatal(1,"native schedule fault P%0d mask%h",p,fault);
   end
   if(done!==((off==82)?8'hff:8'b0))$fatal(1,"issuer done timeline off%0d done%h",off,done);
   if(mut<2)for(integer e=0;e<8;e=e+1)begin
    if(inj_rd[e]!==((p>=0&&p<48)?2'b11:2'b00))$fatal(1,"request timeline e%0d P%0d",e,p);
    for(integer lane=0;lane<4;lane=lane+1)begin
     bit ev;integer origin,idx,base;
     base=lane<2?14:31;ev=p>=base&&p<base+48;
     if(del_v[e][lane]!==ev)$fatal(1,"delivery timeline e%0d lane%0d P%0d got%0d",e,lane,p,del_v[e][lane]);
     if(ev)begin
      origin=lane<2?e/4:1-e/4;idx=(e%4)*96+2*(p-base)+(lane%2);
      if(del_d[e][lane*545+:545]!==expected(origin,e%4,idx))errors=errors+1;
      if(seen[e][origin][idx-(e%4)*96])$fatal(1,"duplicate");
      seen[e][origin][idx-(e%4)*96]=1;checked=checked+1;
      if(del_addr[e][lane*40+:40]!==40'(32'h10000+(e%4)*32'h4000+lane*32'h1000))$fatal(1,"delivery base");
     end
    end
    for(integer rail=0;rail<3;rail=rail+1)begin
     bit ev;ev=rail<2&&p>=21&&p<69;
     if(txv[e][rail]!==ev)$fatal(1,"TX timeline e%0d rail%0d P%0d got%0d",e,rail,p,txv[e][rail]);
     if(ev && txf[e][rail*596+564+:32]!==crc(txf[e][rail*596+:564]))$fatal(1,"native TX CRC");
    end
   end
   @(negedge clk);
  end
  if(mut==0)begin
   if(checked!=1536||errors||fault_edges)$fatal(1,"scoreboard checked%0d errors%0d faultedges%0d",checked,errors,fault_edges);
   for(integer e=0;e<8;e=e+1)for(integer d=0;d<2;d=d+1)for(integer f=0;f<96;f=f+1)if(!seen[e][d][f])$fatal(1,"missing");
   $display("ALLGATHER_NATIVE PASS parents8 q3x2_K2048 q2x6 G2 PF384 quarter96 flits%0d lastP78 rows63 wire5",checked);
  end else begin
   if(mut==1 && (errors==0 || fault_edges))$fatal(1,"payload mutant escaped or unexpected protocol failure");
   if(mut>=2 && fault_edges==0)$fatal(1,"reservation mutant escaped");
   $display("ALLGATHER_MUTANT PASS kind%0d errors%0d fault_edges%0d first_fault_P%0d",mut,errors,fault_edges,first_fault);
  end
  $finish;
 end
endmodule
`default_nettype wire
