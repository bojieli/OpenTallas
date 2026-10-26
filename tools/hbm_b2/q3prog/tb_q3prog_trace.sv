`timescale 1ns/1ps
`default_nettype none
// TOK-HBM q3prog stage A (2026-10-25): actual COLL.ARGMAX_MERGE static programme (tools/hbm_coll_static/argmax_rows.py,
// --start-reg --arg-pr-source: the edge core's argmax_m_tp192_pr contract) on the ACTUAL five-core q3 producer assembly
// (ot_hbm_q3_producer_native, NLINK3 TP192 VM_RT81 ROWS256) or its adopted SYNC_INPUT copy (`DUT = ..._native__q3sync).
// Adapted from rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_v8x_argmax.sv (native host F20 programming 7 frames a
// row + 55-edge drain, descriptor scan, launch, VM read group at 7 + VM_RT, golden FP32 total-order winner scoreboard).
// Sequence: cold reset -> run A (programme + launch, scored) -> run B (relaunch of the LOADED programme, scored; the
// target's contract: a fresh reset is required to install a programme, frames to complete rows fault) -> run W
// (relaunch, WARM reset +WARMAT edges after launch, held +HOLD) -> run C (full programme + launch after the reset, scored). Every output port is written to +TRACE on every edge it changes
// (trace form: one engine per model; legacy vs sync traces are compared offline by tools/hbm_b2/q3prog/trace_compare.py).
// Only declared boundary models: VM read group (vm_rq/vm_rr), every other off-assembly input idle (ARGMAX uses none).
`ifndef DUT
`define DUT ot_hbm_q3_producer_native
`endif
module tb_q3prog_trace;
 localparam integer NLINK=3, VM_RT=81, VMLAT=VM_RT, ROWS=256;
 localparam [15:0] VB=16'h0400,VS=16'h0020;localparam [39:0] OBASE_A=40'h41000000,DSTRIDE=40'h40;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,launch=0,cv=0,dvc=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;reg [12:0] limit=0;
 wire configured,init_busy,program_fault,busy,done,hf,fault;wire [15:0] fault_cause;
 reg [1535:0] rows[0:255];reg [63:0] meta[0:255];
 integer NR=0,P=1,MAXC=100000,drain_extra=0,WARMAT=150,HOLD=64;
 string dir,tracef;integer tfd;
 function automatic [31:0] mix(input [31:0] x);
  reg [31:0] h;h=x*32'h9e3779b1;h=h^(h>>15);h=h*32'h85ebca6b;h=h^(h>>13);return h;
 endfunction
 function automatic [31:0] cand_value(input integer p,input integer r);
  reg [31:0] h;h=mix(32'(p*131+r+7));
  if(r==(p*7)%96 || r==(p*7+13)%96)return 32'h42280000;
  if(p==3 && r==5)return 32'h7fc00000;
  if(p==4 && r==40)return 32'h7f800000;
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
 function automatic [255:0] vmword(input integer bank,input [15:0] sector);
  reg [255:0] v;
  for(integer l=0;l<8;l=l+1)v[l*32+:32]=32'h7a110000^(32'(bank)*32'h1b873593)^(32'(sector)*32'hcc9e2d51)^(32'(l)*32'he6546b64);
  return v;
 endfunction
 function automatic [255:0] vmbank(input integer bank,input [15:0] sector);
  integer p,r;
  if(bank%2==0 && sector>=VB)begin
   p=int'(sector-VB)/int'(VS);r=4*(int'(sector-VB)%int'(VS))+bank/2;
   return {192'd0,cand_id(p,r),cand_value(p,r)};
  end
  return vmword(bank,sector);
 endfunction
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;
 wire [3:0] del_v;wire [2179:0] del_d;wire [159:0] del_a;
 wire [NLINK-1:0] txv,retry;wire [NLINK*612-1:0] txf;
 wire [135:0] vm_rq;wire [2055:0] vm_rr;wire [2247:0] kq;
 wire rrv;wire [2:0] rrt;wire [255:0] rrd;wire [279:0] cwo,ccwo;wire [31:0] stat;wire done2;
 wire [57:0] isa_ring;wire [255:0] isa_lp_data;wire [1:0] ag_v;wire [3:0] ag_src;wire [5:0] ag_tag;wire [511:0] ag_d;
 wire tkx_start,tkx_arg_mode,tkx_cfg_has_r;wire [11:0] tkx_cfg_n;wire [12:0] tkx_cfg_k,tkx_cfg_nout;
 wire [7:0] tkx_cfg_g,tkx_cfg_gbase;wire [15:0] tkx_cfg_pf;wire [39:0] tkx_cfg_obase,tkx_cfg_rbase;
 wire [3:0] tkx_del_slot,tkx_del_valid;wire [2179:0] tkx_del_flit;
 localparam integer VD=7+VMLAT;
 reg [135:0] vmp[0:VD-1];
 // the VM read group is off-assembly (HBM bank boundary model): its pipe is cleared by reset like the die's VM leaf
 always @(posedge clk)begin vmp[0]<=rst_n?vm_rq:136'd0;for(integer s=1;s<VD;s=s+1)vmp[s]<=rst_n?vmp[s-1]:136'd0;end
 for(genvar b=0;b<8;b=b+1)begin:g_bank
  assign vm_rr[b*257+:257]=vmp[VD-1][b*17+16]?{1'b1,vmbank(b,vmp[VD-1][b*17+:16])}:257'd0;
 end
 `DUT dut(.rst_n(rst_n),.qid(2'd0),
  .clk_program(clk),.clk_control(clk),.clk_vmasm({16{clk}}),.clk_upipe({16{clk}}),.clk_issue(clk),
  .clk_qslots({(NLINK+8+18){clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),.clk_vmwrite({16{clk}}),
  .clk_link({(5*NLINK){clk}}),
  .cfg_v(cv),.cfg_target(8'd52),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dvc),.desc_base(12'd0),.desc_limit(limit),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),
  .hgi_busy(busy),.hgi_done(done),.hgi_fault(hf),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(1024'd0),
  .del_valid(del_v),.del_flit(del_d),.hgi_del_obase(del_a),
  .rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),.rr_v(rrv),.rr_tag(rrt),.rr_d(rrd),
  .phy_up({NLINK{1'b1}}),.tx_pin_v(txv),.tx_pin_flit(txf),.rx_pin_v({NLINK{1'b0}}),.rx_pin_flit({(NLINK*612){1'b0}}),
  .retry_requested(retry),.pr_cw_i(280'd0),.pr_ccw_i(280'd0),.pr_cw_o(cwo),.pr_ccw_o(ccwo),
  .isa_ring(isa_ring),.isa_lp_data(isa_lp_data),
  .ra_lp_we(1'b0),.ra_lp_tag(3'd0),.ra_lp_data(256'd0),
  .ra_state_read_add(1'b0),.ra_state_read_tx(1'b0),.ra_state_read_rr(1'b0),
  .ra_state_add_tag(3'd0),.ra_state_tx_tag(3'd0),.ra_state_rr_tag(3'd0),
  .ra_state_add_src(2'd0),.ra_state_add_rhs_acc(1'b0),.ra_state_tx_acc(1'b0),.ra_add_v(1'b0),.ra_add_tag(3'd0),
  .ra_add_src(2'd0),.ra_add_rhs_acc(1'b0),.ra_tx_inject(2'd0),.ra_tx_forward(2'd0),.ra_tx_tag(3'd0),
  .ra_tx_dst(2'd0),.ra_tx_result(1'b0),.ra_tx_acc(1'b0),.ra_tx_gather(1'b0),.ra_tx_ttl(4'd0),
  .ra_rx_slot(2'd0),.ra_rx_kind(4'd0),.ra_rx_src(4'd0),.ra_rx_tag(6'd0),.ra_rr_local(1'b0),.ra_rr_local_tag(3'd0),
  .ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),
  .vm_rq(vm_rq),.vm_rr(vm_rr),.vm_kq(kq),
  .tkx_start(tkx_start),.tkx_arg_mode(tkx_arg_mode),.tkx_cfg_n(tkx_cfg_n),.tkx_cfg_k(tkx_cfg_k),.tkx_cfg_nout(tkx_cfg_nout),
  .tkx_cfg_g(tkx_cfg_g),.tkx_cfg_gbase(tkx_cfg_gbase),.tkx_cfg_pf(tkx_cfg_pf),.tkx_cfg_obase(tkx_cfg_obase),
  .tkx_cfg_rbase(tkx_cfg_rbase),.tkx_cfg_has_r(tkx_cfg_has_r),.tkx_del_slot(tkx_del_slot),.tkx_del_valid(tkx_del_valid),
  .tkx_del_flit(tkx_del_flit),.tkx_w_v(1'b0),.tkx_w_addr(40'd0),.tkx_w_mask(16'd0),.tkx_w_data(512'd0),
  .tkx_busy(1'b0),.tkx_done(1'b0),.tkx_fault(1'b0),
  .fault(fault),.fault_cause(fault_cause),.done(done2),.stat_cycles(stat));
 // ---------------- trace (every output port, field order = TRACE_FIELDS header) ----------------
 `define TRF {configured,init_busy,program_fault,busy,done,hf,inj_rd,inj_idx,inj_addr,del_v,del_d,del_a,rrv,rrt,rrd,txv,txf,retry,cwo,ccwo,isa_ring,isa_lp_data,ag_v,ag_src,ag_tag,ag_d,vm_rq,kq,tkx_start,tkx_arg_mode,tkx_cfg_n,tkx_cfg_k,tkx_cfg_nout,tkx_cfg_g,tkx_cfg_gbase,tkx_cfg_pf,tkx_cfg_obase,tkx_cfg_rbase,tkx_cfg_has_r,tkx_del_slot,tkx_del_valid,tkx_del_flit,fault,fault_cause,done2,stat}
 localparam integer TW=$bits(`TRF);
 reg [TW-1:0] prev_t;integer cyc=0;
 always @(negedge clk)begin
  if(cyc==0 || `TRF!==prev_t)$fdisplay(tfd,"%0d %0d %h",cyc,rst_n,`TRF);
  prev_t<=`TRF;
 end
 // ---------------- scoreboard (per run) ----------------
 integer launch_cyc=-1,cnt=0,first_del=-1,last_del=-1,data_errors=0,addr_errors=0,stray=0,fault_first=-1;
 integer done_cyc=-1,done_count=0,first_vm=-1,first_tkx_arg=-1,tkx_v_edges=0;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(launch)launch_cyc<=cyc;
  if(rst_n)begin
   if((fault||program_fault||hf) && fault_first<0)begin fault_first<=cyc;
    $display("FAULT cyc%0d fault%0d program_fault%0d hgi_fault%0d cause%h",cyc,fault,program_fault,hf,fault_cause);end
   if(done)begin done_cyc<=cyc;done_count<=done_count+1;end
   if(launch_cyc>=0 && first_vm<0 && |{vm_rq[16],vm_rq[33],vm_rq[50],vm_rq[67],vm_rq[84],vm_rq[101],vm_rq[118],vm_rq[135]})
    first_vm<=cyc;
   if(launch_cyc>=0 && |tkx_del_valid)begin tkx_v_edges<=tkx_v_edges+1;if(first_tkx_arg<0)first_tkx_arg<=cyc;end
   for(integer k=0;k<4;k=k+1)if(del_v[k])begin
    if(k!=0 || cnt>=P)stray=stray+1;
    else begin
     reg [544:0] want;
     want={1'b1,8'hff,8'd0,16'd0,480'd0,winner_id(cnt)};
     if(del_d[544:0]!==want)begin data_errors=data_errors+1;
      if(data_errors<8)$display("ARG_MISMATCH pos%0d cyc%0d got id%0d want id%0d",cnt,cyc,del_d[31:0],want[31:0]);end
     if(del_a[39:0]!==OBASE_A+40'(cnt)*DSTRIDE)begin addr_errors=addr_errors+1;
      if(addr_errors<4)$display("ADDR_MISMATCH pos%0d got%h want%h",cnt,del_a[39:0],OBASE_A+40'(cnt)*DSTRIDE);end
     if(first_del<0)first_del<=cyc;
     last_del<=cyc;cnt=cnt+1;
    end
   end
  end
 end
 task automatic clear_sb;
  launch_cyc=-1;cnt=0;first_del=-1;last_del=-1;data_errors=0;addr_errors=0;stray=0;fault_first=-1;
  done_cyc=-1;done_count=0;first_vm=-1;first_tkx_arg=-1;tkx_v_edges=0;
 endtask
 integer fails=0;
 task automatic program_and_launch(input string run);
  for(integer r=0;r<NR;r=r+1)begin
   for(integer s=0;s<7;s=s+1)begin
    @(negedge clk);cv=1;cfg_addr=12'(r*8+s);cfg_data=s<6?rows[r][s*256+:256]:{192'd0,meta[r]};
   end
   @(negedge clk);cv=0;
   repeat(55)@(negedge clk);
   for(integer w=0;w<8 && init_busy;w=w+1)begin @(negedge clk);if(r==0)drain_extra=w+1;end
   if(init_busy || program_fault)begin
    $display("Q3PROG FAIL run %s host row %0d drain (init_busy%0d program_fault%0d)",run,r,init_busy,program_fault);
    $fclose(tfd);$finish;end
  end
  @(negedge clk);dvc=1;@(negedge clk);dvc=0;repeat(ROWS+8)@(negedge clk);
  if(!configured || program_fault)begin
   $display("Q3PROG FAIL run %s descriptor configured%0d program_fault%0d",run,configured,program_fault);$fclose(tfd);$finish;end
  clear_sb();
  @(negedge clk);launch=1;@(negedge clk);launch=0;
 endtask
 task automatic relaunch(input string run);
  if(!configured || program_fault || init_busy)begin
   $display("Q3PROG FAIL run %s relaunch configured%0d program_fault%0d init_busy%0d",run,configured,program_fault,init_busy);
   $fclose(tfd);$finish;end
  clear_sb();
  @(negedge clk);launch=1;@(negedge clk);launch=0;
 endtask
 task automatic score(input string run,input integer t0);
  $display("Q3PROG_MEASURE run %s P%0d NR%0d host_programme_edges%0d drain55+%0d launch_to_first_vm_rq%0d launch_to_first_tkx_lane%0d tkx_lane_edges%0d launch_to_first_delivery%0d launch_to_last_delivery%0d done%0d positions%0d/%0d data_err%0d addr_err%0d stray%0d fault_first%0d",
   run,P,NR,launch_cyc-t0,drain_extra,first_vm<0?-1:first_vm-launch_cyc,first_tkx_arg<0?-1:first_tkx_arg-launch_cyc,tkx_v_edges,
   first_del<0?-1:first_del-launch_cyc,last_del<0?-1:last_del-launch_cyc,done_cyc<0?-1:done_cyc-launch_cyc,
   cnt,P,data_errors,addr_errors,stray,fault_first<0?-1:fault_first-launch_cyc);
  if(cnt==P && data_errors==0 && addr_errors==0 && stray==0 && fault_first<0 && done_count==1 && done_cyc>last_del)
   $display("Q3PROG RUN %s PASS",run);
  else begin $display("Q3PROG RUN %s FAIL",run);fails=fails+1;end
 endtask
 initial begin : main
  integer t0;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing +DIR");
  if(!$value$plusargs("TRACE=%s",tracef))$fatal(1,"missing +TRACE");
  void'($value$plusargs("P=%d",P));void'($value$plusargs("MAXC=%d",MAXC));
  void'($value$plusargs("WARMAT=%d",WARMAT));void'($value$plusargs("HOLD=%d",HOLD));
  if(!$value$plusargs("NR=%d",NR))$fatal(1,"missing +NR");
  tfd=$fopen(tracef,"w");
  $fdisplay(tfd,"# TRACE_FIELDS configured:1 init_busy:1 program_fault:1 busy:1 done:1 hf:1 inj_rd:2 inj_idx:32 inj_addr:160 del_v:4 del_d:2180 del_a:160 rrv:1 rrt:3 rrd:256 txv:%0d txf:%0d retry:%0d cwo:280 ccwo:280 isa_ring:58 isa_lp_data:256 ag_v:2 ag_src:4 ag_tag:6 ag_d:512 vm_rq:136 kq:2248 tkx_start:1 tkx_arg_mode:1 tkx_cfg_n:12 tkx_cfg_k:13 tkx_cfg_nout:13 tkx_cfg_g:8 tkx_cfg_gbase:8 tkx_cfg_pf:16 tkx_cfg_obase:40 tkx_cfg_rbase:40 tkx_cfg_has_r:1 tkx_del_slot:4 tkx_del_valid:4 tkx_del_flit:2180 fault:1 fault_cause:16 done2:1 stat:32 TW=%0d",
   NLINK,NLINK*612,NLINK,TW);
  for(integer r=0;r<256;r=r+1)begin rows[r]='0;meta[r]='0;end
  $readmemh({dir,"/d0q0.rows.hex"},rows,0,NR-1);$readmemh({dir,"/d0q0.meta.hex"},meta,0,NR-1);
  $display("Q3PROG config NLINK%0d VM_RT%0d ROWS%0d P%0d NR%0d WARMAT%0d HOLD%0d TW%0d",NLINK,VM_RT,ROWS,P,NR,WARMAT,HOLD,TW);
  limit=13'(NR);
  // cold reset, run A
  repeat(64)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  t0=cyc;program_and_launch("A");
  while(done_count==0 && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(16)@(negedge clk);score("A",t0);
  // run B: relaunch the loaded programme (no reset), scored
  t0=cyc;relaunch("B");
  while(done_count==0 && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(16)@(negedge clk);score("B",t0);
  // run W: relaunch, warm reset mid-run
  t0=cyc;relaunch("W");
  repeat(WARMAT)@(negedge clk);
  $display("Q3PROG WARM_RESET cyc%0d launch+%0d delivered%0d",cyc,cyc-launch_cyc,cnt);
  rst_n=0;repeat(HOLD)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  // run C after the warm reset
  t0=cyc;program_and_launch("C");
  while(done_count==0 && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(16)@(negedge clk);score("C",t0);
  $display("Q3PROG %s runs A,B,C fails%0d end_cyc%0d",fails==0?"PASS":"FAIL",fails,cyc);
  $fclose(tfd);$finish;
 end
endmodule
`default_nettype wire
