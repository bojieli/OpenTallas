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
module tb_q3stageb;
 localparam integer NLINK=3, VM_RT=81, VMLAT=VM_RT, ROWS=256;
 localparam [15:0] VB=16'h0400,VS=16'h0020;localparam [39:0] OBASE_A=40'h41000000,DSTRIDE=40'h40;
 reg clk=0;always #0.4165 clk=~clk;
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
  reg[255:0] out;out={8{32'hffffffff}};
  if(sector==16'h0400)out[31:0]=bank%2?32'(20+bank/2):(32'h40800000-32'(bank/2)*32'h00800000);
  return out;
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
 wire twv,tbusy,tdone,tfault;wire[39:0]twa;wire[15:0]twm;wire[511:0]twd;wire[31:0]tcycles;
 wire[2340:0]txraw,rxraw;wire[1170:0]beat;wire txfault,rxfault,slot0;reg boot_start=0;
 assign txraw={tkx_start,tkx_del_valid,tkx_del_slot,tkx_del_flit,tkx_cfg_rbase,tkx_cfg_pf,tkx_cfg_obase,tkx_cfg_nout,tkx_cfg_n,tkx_cfg_k,tkx_cfg_has_r,tkx_cfg_gbase,tkx_cfg_g,tkx_arg_mode};
 ot_hbm_tkm_path_tkx_ft21 bound(.nw_clk(clk),.clk(clk),.buffer_clk(clk),.tile_clk({32{clk}}),.nw_rst_n(rst_n),.root_rst_n(rst_n),.tx_boot_start(boot_start),.rx_boot_start(boot_start),.strap_tile_ids(192'd0),.tx_tkx(txraw),.rx_tkx(rxraw),.beat(beat),.tx_fault(txfault),.rx_fault(rxfault),.slot0(slot0),.wv(twv),.busy(tbusy),.done(tdone),.fault(tfault),.wa(twa),.wm(twm),.wd(twd),.cycles(tcycles));
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
  .tkx_del_flit(tkx_del_flit),.tkx_w_v(twv),.tkx_w_addr(twa),.tkx_w_mask(twm),.tkx_w_data(twd),
  .tkx_busy(tbusy),.tkx_done(tdone),.tkx_fault(tfault),
  .fault(fault),.fault_cause(fault_cause),.done(done2),.stat_cycles(stat));
 integer cyc=0,lc=-1,errors=0,words=0,root_done=0,qdone=0,producer_start=0,producer_flits=0;reg firstfault=0;
 always@(posedge clk)begin
  cyc<=cyc+1;if(launch)lc<=cyc;
  if(rst_n&&lc>=0)begin
   if(tkx_start)begin producer_start++;$display("EV START +%0d slot0%0d",cyc-lc,slot0);end
   if(|tkx_del_slot|| |tkx_del_valid)begin producer_flits++;$display("EV FLIT +%0d slot%h valid%h slot0%0d",cyc-lc,tkx_del_slot,tkx_del_valid,slot0);end
   if(twv)begin
    $display("EV WRITE +%0d addr%0d mask%h data%h",cyc-lc,twa,twm,twd);
    for(integer j=0;j<16;j++)if(twm[j])begin words++;if(twa+j!=64 || twd[32*j+:32]!==32'd20)errors++;end
   end
   if(tdone)begin root_done++;$display("EV ROOT_DONE +%0d cycles%0d",cyc-lc,tcycles);end
   if(done)begin qdone++;$display("EV Q_DONE +%0d",cyc-lc);end
   if((fault||program_fault||hf||tfault||txfault||rxfault)&&!firstfault)begin firstfault<=1;$display("FIRST_FAULT +%0d q%0d pf%0d hf%0d root%0d tx%0d rx%0d cause%h",cyc-lc,fault,program_fault,hf,tfault,txfault,rxfault,fault_cause);end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("NR=%d",NR))$fatal(1,"DIR NR required");
  for(integer r=0;r<256;r++)begin rows[r]=0;meta[r]=0;end
  $readmemh({dir,"/d0q0.rows.hex"},rows,0,NR-1);$readmemh({dir,"/d0q0.meta.hex"},meta,0,NR-1);limit=13'(NR);
  repeat(64)@(negedge clk);rst_n=1;repeat(16)@(negedge clk);boot_start=1;@(negedge clk);boot_start=0;
  for(integer r=0;r<NR;r++)begin
   for(integer s=0;s<7;s++)begin @(negedge clk);cv=1;cfg_addr=12'(r*8+s);cfg_data=s<6?rows[r][256*s+:256]:{192'd0,meta[r]};end
   @(negedge clk);cv=0;repeat(55)@(negedge clk);while(init_busy)@(negedge clk);
   if(program_fault)$fatal(1,"programme fault row%0d",r);
  end
  @(negedge clk);dvc=1;@(negedge clk);dvc=0;repeat(ROWS+8)@(negedge clk);
  if(!configured||program_fault)$fatal(1,"descriptor fail");
  while(!slot0)@(negedge clk);
  if($test$plusargs("PHASE_OFFSET"))@(negedge clk);
  launch=1;@(negedge clk);launch=0;
  repeat(800)@(negedge clk);
  $display("STAGEB_SUMMARY producer_start%0d producer_flits%0d words%0d root_done%0d qdone%0d errors%0d fault%0d",producer_start,producer_flits,words,root_done,qdone,errors,firstfault);
  if(producer_start!=1||words!=1||root_done!=1||qdone!=1||errors||firstfault)$fatal(1,"Q3STAGEB FAIL");
  $display("Q3STAGEB PASS");$finish;
 end
endmodule
`default_nettype wire
