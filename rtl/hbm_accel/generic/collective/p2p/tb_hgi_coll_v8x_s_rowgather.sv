`timescale 1ns/1ps
`default_nettype none
// HBM-TAPS 11-12 (DO_NOT_COUNT): P-row COLL.ROW_GATHER (tools/hbm_coll_static/row_gather_rows.py --vm-rt VM_RT) on the
// ACTUAL q3bc SW COLL parent ot_hfd_coll_q3_hard_v8x_s #(NLINK 3, TP, VM_RT, ROWS 256): native HOST programming (F20
// frames, 55-edge row drain, descriptor scan of ROWS rows), the 256-row issuer (v7, or ISS2E ot_hgi_coll_issuer_m256v8e
// under -DOT_COLL_ISSUER256_ISS2E), qslots, links with native SRAM/CRC, SU delivery lanes 0..2.
// SPMD loopback (as tb_hgi_coll_q_static_host_v4_rows NE=2, q3 only): each rail's RX pin is its OWN TX pin W edges
// earlier. Valid because every die runs the identical compiled programme on a data-independent static calendar, so the
// peer's TX pin sequence equals this die's (the scoreboard expects sender = this die).
// Declared boundary models only (same as the host_v4 rows bench): SU inject read data (index pin observed P+1, eleven
// registers, data stable for the INJLAT 12 capture), the COLL VM read group at the d4g budget (request pin cycle n ->
// response visible n + 7 + VM_RT, the v8x argmax bench model), the wire; rc / ring A / TKM-x idle.
// Scoreboard (independent of the programme words): delivered flit j of lane k: payload = SU port k data of list index
// IDX0_k + j (k < 2) or VM sector VM_S0 + j bank pair 1:0 (k = 2), header {valid, 0xff, sender 0, idx/0xa5a5},
// address OBASE + k*R*64 + (j / R)*RS + (j % R)*64; exactly P*R flits a lane, one done after the last delivery, no fault.
module tb_hgi_coll_v8x_s_rowgather #(parameter integer NLINK=3, TP=192, VM_RT=81, ROWS=256);
 localparam [39:0] OBASE=40'h40000000, RS=40'h60000;
 localparam [15:0] IDX0_0=16'h0100, IDX0_1=16'h4100, VM_S0=16'h0200;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,launch=0,cv=0,dvc=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;reg [12:0] limit=0;
 wire configured,init_busy,program_fault,busy,done,hf,fault;wire [15:0] fault_cause;
 reg [1535:0] rows[0:255];reg [63:0] meta[0:255];
 integer NR=0,P=1,R=8,W=20,MAXC=200000,drain_extra=0;
 string dir;
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
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;wire [1023:0] inj_d;
 wire [3:0] del_v;wire [2179:0] del_d;wire [159:0] del_a;
 wire [NLINK-1:0] txv,retry,rxv;wire [NLINK*612-1:0] txf,rxf;
 wire [135:0] vm_rq;wire [2055:0] vm_rr;wire [2247:0] kq;
 wire rrv;wire [2:0] rrt;wire [255:0] rrd;wire [279:0] cwo,ccwo;wire [31:0] stat;wire done2;
 wire [57:0] isa_ring;wire [255:0] isa_lp_data;wire [1:0] ag_v;wire [3:0] ag_src;wire [5:0] ag_tag;wire [511:0] ag_d;
 wire tkx_start,tkx_arg_mode,tkx_cfg_has_r;wire [11:0] tkx_cfg_n;wire [12:0] tkx_cfg_k,tkx_cfg_nout;
 wire [7:0] tkx_cfg_g,tkx_cfg_gbase;wire [15:0] tkx_cfg_pf;wire [39:0] tkx_cfg_obase,tkx_cfg_rbase;
 wire [3:0] tkx_del_slot,tkx_del_valid;wire [2179:0] tkx_del_flit;
 integer cyc=0,launch_cyc=-1;
 // SU inject boundary model: index pin observed P+1, eleven registers, data stable for the P+12 capture
 reg [15:0] sidx0[0:10],sidx1[0:10];
 always @(posedge clk)begin
  sidx0[0]<=inj_idx[15:0];sidx1[0]<=inj_idx[31:16];
  for(integer s=1;s<11;s=s+1)begin sidx0[s]<=sidx0[s-1];sidx1[s]<=sidx1[s-1];end
 end
 assign inj_d={payload_su(0,0,1,sidx1[10]),payload_su(0,0,0,sidx0[10])};
 // COLL VM read group at the d4g budget: response visible 7 + VM_RT cycles after the request pin
 localparam integer VD=7+VM_RT;
 reg [135:0] vmp[0:VD-1];
 always @(posedge clk)begin vmp[0]<=vm_rq;for(integer s=1;s<VD;s=s+1)vmp[s]<=vmp[s-1];end
 for(genvar b=0;b<8;b=b+1)begin:g_bank
  assign vm_rr[b*257+:257]=vmp[VD-1][b*17+16]?{1'b1,vmword(0,0,b,vmp[VD-1][b*17+:16])}:257'd0;
 end
 // SPMD loopback wire: rx pin in cycle t = own tx pin in cycle t-W
 reg [NLINK-1:0] hv[0:1023];reg [NLINK*612-1:0] hfl[0:1023];
 always @(posedge clk)begin hv[cyc%1024]<=txv;hfl[cyc%1024]<=txf;end
 assign rxv=(cyc>=W)?hv[(cyc-W)%1024]:'0;
 assign rxf=hfl[(cyc-W+1024)%1024];
 ot_hfd_coll_q3_hard_v8x_s #(.NLINK(NLINK),.TP(TP),.VM_RT(VM_RT),.ROWS(ROWS)) dut(.rst_n(rst_n),.qid(2'd0),
  .clk_program(clk),.clk_control(clk),.clk_vmasm({16{clk}}),.clk_upipe({16{clk}}),.clk_issue(clk),
  .clk_qslots({(NLINK+8+18){clk}}),.clk_ring({17{clk}}),.clk_reduce({33{clk}}),.clk_arg(clk),.clk_vmwrite({16{clk}}),
  .clk_link({(5*NLINK){clk}}),
  .cfg_v(cv),.cfg_target(8'd52),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(dvc),.desc_base(12'd0),.desc_limit(limit),.desc_loops(16'd1),.launch_v(launch),
  .program_configured(configured),.program_init_busy(init_busy),.program_fault(program_fault),
  .hgi_busy(busy),.hgi_done(done),.hgi_fault(hf),
  .inj_rd(inj_rd),.inj_idx(inj_idx),.hgi_inj_addr(inj_addr),.inj_d(inj_d),
  .del_valid(del_v),.del_flit(del_d),.hgi_del_obase(del_a),
  .rc_v(1'b0),.rc_tag(3'd0),.rc_d(256'd0),.rr_v(rrv),.rr_tag(rrt),.rr_d(rrd),
  .phy_up({NLINK{1'b1}}),.tx_pin_v(txv),.tx_pin_flit(txf),.rx_pin_v(rxv),.rx_pin_flit(rxf),
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
 // ---------------- scoreboard ----------------
 integer cnt[0:3],first_del[0:3],last_del[0:3];
 integer errors=0,addr_errors=0,data_errors=0,stray=0,fault_first=-1,done_cyc=-1,done_count=0,first_tx=-1,first_rx=-1;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(launch)launch_cyc<=cyc;
  if(rst_n)begin
   if((fault||program_fault||hf) && fault_first<0)begin fault_first<=cyc;
    $display("FAULT cyc%0d fault%0d program_fault%0d hgi_fault%0d cause%h",cyc,fault,program_fault,hf,fault_cause);end
   if(done)begin done_cyc<=cyc;done_count<=done_count+1;end
   if(|txv && first_tx<0)first_tx<=cyc;
   if(|rxv && first_rx<0)first_rx<=cyc;
   for(integer k=0;k<4;k=k+1)if(del_v[k])begin
    if(k>=NLINK)stray=stray+1;
    else begin
     integer j,p,f;reg [544:0] want;reg [39:0] wa;
     j=cnt[k];p=j/R;f=j%R;
     if(k<2)want={1'b1,8'hff,8'd0,16'((k==0?IDX0_0:IDX0_1)+16'(j)),payload_su(0,0,k,16'((k==0?IDX0_0:IDX0_1)+16'(j)))};
     else want={1'b1,8'hff,8'd0,16'ha5a5,vmword(0,0,1,VM_S0+16'(j)),vmword(0,0,0,VM_S0+16'(j))};
     wa=OBASE+40'(k)*40'(R)*40'd64+40'(p)*RS+40'(f)*40'd64;
     if(j>=P*R)stray=stray+1;
     else begin
      if(del_d[k*545+:545]!==want)begin data_errors=data_errors+1;
       if(data_errors<4)$display("DATA_MISMATCH lane%0d j%0d cyc%0d got%h want%h",k,j,cyc,del_d[k*545+512+:33],want[544:512]);end
      if(del_a[k*40+:40]!==wa)begin addr_errors=addr_errors+1;
       if(addr_errors<4)$display("ADDR_MISMATCH lane%0d j%0d (pos%0d flit%0d) cyc%0d got%h want%h",k,j,p,f,cyc,del_a[k*40+:40],wa);end
     end
     if(first_del[k]<0)first_del[k]<=cyc;
     last_del[k]<=cyc;cnt[k]<=cnt[k]+1;
    end
   end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing +DIR");
  void'($value$plusargs("P=%d",P));void'($value$plusargs("R=%d",R));void'($value$plusargs("W=%d",W));
  void'($value$plusargs("MAXC=%d",MAXC));
  if(!$value$plusargs("NR=%d",NR))$fatal(1,"missing +NR");
  if(NR<1 || NR>256)$fatal(1,"NR 1..256");
  if(W<1||W>1000)$fatal(1,"wire edges 1..1000");
  for(integer k=0;k<4;k=k+1)begin cnt[k]=0;first_del[k]=-1;last_del[k]=-1;end
  for(integer r=0;r<256;r=r+1)begin rows[r]='0;meta[r]='0;end
  $readmemh({dir,"/d0q0.rows.hex"},rows,0,NR-1);$readmemh({dir,"/d0q0.meta.hex"},meta,0,NR-1);
  $display("ROWGATHER_V8XS config NLINK%0d TP%0d VM_RT%0d ROWS%0d P%0d R%0d W%0d NR%0d",NLINK,TP,VM_RT,ROWS,P,R,W,NR);
  limit=13'(NR);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(integer r=0;r<NR;r=r+1)begin
   for(integer s=0;s<7;s=s+1)begin
    @(negedge clk);cv=1;cfg_addr=12'(r*8+s);cfg_data=s<6?rows[r][s*256+:256]:{192'd0,meta[r]};
   end
   @(negedge clk);cv=0;
   repeat(55)@(negedge clk);
   for(integer w=0;w<8 && init_busy;w=w+1)begin @(negedge clk);if(r==0)drain_extra=w+1;end
   if(init_busy || program_fault)begin
    $display("ROWGATHER_ROWS FAIL host row %0d drain (init_busy%0d program_fault%0d)",r,init_busy,program_fault);$finish;end
  end
  @(negedge clk);dvc=1;@(negedge clk);dvc=0;repeat(ROWS+8)@(negedge clk);
  if(!configured || program_fault)begin
   $display("ROWGATHER_ROWS FAIL descriptor validation configured%0d program_fault%0d",configured,program_fault);$finish;end
  @(negedge clk);launch=1;@(negedge clk);launch=0;
  while(done_count==0 && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(W+64)@(negedge clk);
  for(integer k=0;k<NLINK;k=k+1)begin
   if(cnt[k]!=P*R)errors=errors+1;
   $display("LANE %0d delivered%0d/%0d first_del%0d last_del%0d",k,cnt[k],P*R,first_del[k]-launch_cyc,last_del[k]-launch_cyc);
  end
  if(done_count!=1)errors=errors+1;
  for(integer k=0;k<NLINK;k=k+1)if(done_cyc>=0 && done_cyc<=last_del[k])errors=errors+1;
  $display("ROWGATHER_ROWS_MEASURE P%0d R%0d W%0d first_tx%0d first_rx%0d last_delivery%0d done%0d data_err%0d addr_err%0d stray%0d fault_first%0d",
   P,R,W,first_tx-launch_cyc,first_rx-launch_cyc,last_del[0]-launch_cyc,done_cyc<0?-1:done_cyc-launch_cyc,data_errors,addr_errors,stray,
   fault_first<0?-1:fault_first-launch_cyc);
  if(errors==0 && data_errors==0 && addr_errors==0 && stray==0 && fault_first<0)
   $display("ROWGATHER_ROWS PASS P%0d R%0d W%0d NLINK%0d TP%0d VM_RT%0d ROWS%0d rows%0d",P,R,W,NLINK,TP,VM_RT,ROWS,NR);
  else $display("ROWGATHER_ROWS FAIL P%0d errors%0d data%0d addr%0d stray%0d done_count%0d fault_first%0d",P,errors,data_errors,
   addr_errors,stray,done_count,fault_first<0?-1:fault_first-launch_cyc);
  $finish;
 end
endmodule
`default_nettype wire
