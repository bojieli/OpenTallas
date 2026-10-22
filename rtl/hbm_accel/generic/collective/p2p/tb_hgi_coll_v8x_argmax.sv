`timescale 1ns/1ps
`default_nettype none
// HBM-ARGMAX (10-19, coordinator HANDOFF 0kj): COLL.ARGMAX_MERGE P-row static programme (tools/hbm_coll_static/
// argmax_rows.py --vm-rt VM_RT --rows ROWS --npt NLINK) on the ACTUAL d4g SW COLL parent ot_hfd_coll_q3_hard_v8x
// #(NLINK, TP, VM_RT, ROWS): native HOST programming through the programme target (F20 frames, 55-edge row drain,
// descriptor scan of ROWS rows), the 256-row issuer (ROWS 256: 4 x 64-row macros a bank, 8-bit pc), the VM_RT protocol
// leaf (ot_hgi_coll_ctl_v5r_*), qslots, the native ARGMAX unit, SU delivery lane 0.
// Declared boundary models only: the COLL VM read group at the parent's vm_rq / vm_rr pins with the d4g budget
// round trip (request pin visible in cycle n -> response visible in cycle n + 7 + VMLAT; VMLAT = VM_RT: the die pads every
// bank lane to the scalar budget), inj_d / rc / ring A / TKM-x / links idle (ARGMAX uses none of them).
// Scoreboard (independent of the programme words): delivery j on SU lane 0 = {valid, 0xff, sender 0, 0, winner id of
// position j} at address OBASE + j * DSTRIDE, exactly P deliveries, one done after the last delivery, no fault.
// The candidates (argmax_rows.py operand placement) include ties at the maximum (lower id wins), NaN (orders after every
// number) and +inf (wins): the reference is the golden FP32 total order with id tie-break.
module tb_hgi_coll_v8x_argmax #(parameter integer NLINK=2, TP=192, VM_RT=74, ROWS=256, VMLAT=VM_RT);
 localparam [15:0] VB=16'h0400,VS=16'h0020;localparam [39:0] OBASE_A=40'h41000000,DSTRIDE=40'h40;
 localparam integer PW=(ROWS>128)?8:(ROWS>64)?7:6;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,launch=0,cv=0,dvc=0;
 reg [11:0] cfg_addr=0;reg [255:0] cfg_data=0;reg [12:0] limit=0;
 wire configured,init_busy,program_fault,busy,done,hf,fault;wire [15:0] fault_cause;
 reg [1535:0] rows[0:255];reg [63:0] meta[0:255];
 integer NR=0,P=1,MAXC=100000,drain_extra=0;
 string dir;
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
 function automatic [255:0] vmword(input integer bank,input [15:0] sector);
  reg [255:0] v;
  for(integer l=0;l<8;l=l+1)v[l*32+:32]=32'h7a110000^(32'(bank)*32'h1b873593)^(32'(sector)*32'hcc9e2d51)^(32'(l)*32'he6546b64);
  return v;
 endfunction
 // rank r of position p is VM line VB+p*VS+r/4, pair lane r%4 = banks {2j+1,2j}; the low bank's words 0/1 = (value, id)
 function automatic [255:0] vmbank(input integer bank,input [15:0] sector);
  integer p,r;
  if(bank%2==0 && sector>=VB)begin
   p=int'(sector-VB)/int'(VS);r=4*(int'(sector-VB)%int'(VS))+bank/2;
   return {192'd0,cand_id(p,r),cand_value(p,r)};
  end
  return vmword(bank,sector);
 endfunction
 // ---------------- the actual parent ----------------
 wire [1:0] inj_rd;wire [31:0] inj_idx;wire [159:0] inj_addr;
 wire [3:0] del_v;wire [2179:0] del_d;wire [159:0] del_a;
 wire [NLINK-1:0] txv,retry;wire [NLINK*612-1:0] txf;
 wire [135:0] vm_rq;wire [2055:0] vm_rr;wire [2247:0] kq;
 wire rrv;wire [2:0] rrt;wire [255:0] rrd;wire [279:0] cwo,ccwo;wire [31:0] stat;wire done2;
 wire [57:0] isa_ring;wire [255:0] isa_lp_data;wire [1:0] ag_v;wire [3:0] ag_src;wire [5:0] ag_tag;wire [511:0] ag_d;
 wire tkx_start,tkx_arg_mode,tkx_cfg_has_r;wire [11:0] tkx_cfg_n;wire [12:0] tkx_cfg_k,tkx_cfg_nout;
 wire [7:0] tkx_cfg_g,tkx_cfg_gbase;wire [15:0] tkx_cfg_pf;wire [39:0] tkx_cfg_obase,tkx_cfg_rbase;
 wire [3:0] tkx_del_slot,tkx_del_valid;wire [2179:0] tkx_del_flit;
 // COLL VM read group at the d4g budget: response visible 7 + VMLAT cycles after the request pin
 localparam integer VD=7+VMLAT;
 reg [135:0] vmp[0:VD-1];
 always @(posedge clk)begin vmp[0]<=vm_rq;for(integer s=1;s<VD;s=s+1)vmp[s]<=vmp[s-1];end
 for(genvar b=0;b<8;b=b+1)begin:g_bank
  assign vm_rr[b*257+:257]=vmp[VD-1][b*17+16]?{1'b1,vmbank(b,vmp[VD-1][b*17+:16])}:257'd0;
 end
 ot_hfd_coll_q3_hard_v8x #(.NLINK(NLINK),.TP(TP),.VM_RT(VM_RT),.ROWS(ROWS)) dut(.rst_n(rst_n),.qid(2'd0),
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
 // ---------------- scoreboard ----------------
 integer cyc=0,launch_cyc=-1,cnt=0,first_del=-1,last_del=-1,data_errors=0,addr_errors=0,stray=0,fault_first=-1;
 integer done_cyc=-1,done_count=0,first_vm=-1,first_vm_rr=-1;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(launch)launch_cyc<=cyc;
  if(rst_n)begin
   if((fault||program_fault||hf) && fault_first<0)begin fault_first<=cyc;
    $display("FAULT cyc%0d fault%0d program_fault%0d hgi_fault%0d cause%h",cyc,fault,program_fault,hf,fault_cause);end
   if(done)begin done_cyc<=cyc;done_count<=done_count+1;end
   if(launch_cyc>=0 && first_vm<0 && |{vm_rq[16],vm_rq[33],vm_rq[50],vm_rq[67],vm_rq[84],vm_rq[101],vm_rq[118],vm_rq[135]})
    first_vm<=cyc;
   for(integer k=0;k<4;k=k+1)if(del_v[k])begin
    if(k!=0 || cnt>=P)stray=stray+1;
    else begin
     reg [544:0] want;
     want={1'b1,8'hff,8'd0,16'd0,480'd0,winner_id(cnt)};
     if(del_d[544:0]!==want)begin data_errors=data_errors+1;
      if(data_errors<8)$display("ARG_MISMATCH pos%0d cyc%0d got id%0d want id%0d hdr got%h want%h",cnt,cyc,
       del_d[31:0],want[31:0],del_d[544:512],want[544:512]);end
     if(del_a[39:0]!==OBASE_A+40'(cnt)*DSTRIDE)begin addr_errors=addr_errors+1;
      if(addr_errors<4)$display("ADDR_MISMATCH pos%0d got%h want%h",cnt,del_a[39:0],OBASE_A+40'(cnt)*DSTRIDE);end
     if(first_del<0)first_del<=cyc;
     last_del<=cyc;cnt=cnt+1;
    end
   end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"missing +DIR");
  void'($value$plusargs("P=%d",P));void'($value$plusargs("MAXC=%d",MAXC));
  if(!$value$plusargs("NR=%d",NR))$fatal(1,"missing +NR");
  if(NR<1 || NR>256)$fatal(1,"NR 1..256");
  for(integer r=0;r<256;r=r+1)begin rows[r]='0;meta[r]='0;end
  $readmemh({dir,"/d0q0.rows.hex"},rows,0,NR-1);$readmemh({dir,"/d0q0.meta.hex"},meta,0,NR-1);
  $display("ARGMAX_V8X config NLINK%0d TP%0d VM_RT%0d VMLAT%0d ROWS%0d PW%0d P%0d NR%0d",NLINK,TP,VM_RT,VMLAT,ROWS,PW,P,NR);
  limit=13'(NR);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  // native HOST F20 programming: seven frames a row, then the fixed 55-edge drain reservation (no polling)
  for(integer r=0;r<NR;r=r+1)begin
   for(integer s=0;s<7;s=s+1)begin
    @(negedge clk);cv=1;cfg_addr=12'(r*8+s);cfg_data=s<6?rows[r][s*256+:256]:{192'd0,meta[r]};
   end
   @(negedge clk);cv=0;
   repeat(55)@(negedge clk);
   // the v8 fj leaf registers the host frame and the target's busy face (+2 edges against host_v4): bounded wait
   for(integer w=0;w<8 && init_busy;w=w+1)begin @(negedge clk);if(r==0)drain_extra=w+1;end
   if(init_busy || program_fault)begin
    $display("ARGMAX_ROWS FAIL host row %0d drain (init_busy%0d program_fault%0d)",r,init_busy,program_fault);$finish;end
  end
  // descriptor: the target scans every row of the programme memory (ROWS + 2 edges reserved)
  $display("ARGMAX_V8X host drain 55+%0d edges a row",drain_extra);
  @(negedge clk);dvc=1;@(negedge clk);dvc=0;repeat(ROWS+8)@(negedge clk);
  if(!configured || program_fault)begin
   $display("ARGMAX_ROWS FAIL descriptor validation configured%0d program_fault%0d",configured,program_fault);$finish;end
  @(negedge clk);launch=1;@(negedge clk);launch=0;
  while(done_count==0 && cyc-launch_cyc<MAXC)@(negedge clk);
  repeat(16)@(negedge clk);
  $display("ARGMAX_ROWS_MEASURE P%0d VM_RT%0d ROWS%0d NR%0d launch_to_first_vm_rq%0d launch_to_last_delivery%0d done%0d positions%0d/%0d data_err%0d addr_err%0d stray%0d fault_first%0d",
   P,VM_RT,ROWS,NR,first_vm<0?-1:first_vm-launch_cyc,last_del<0?-1:last_del-launch_cyc,done_cyc<0?-1:done_cyc-launch_cyc,
   cnt,P,data_errors,addr_errors,stray,fault_first<0?-1:fault_first-launch_cyc);
  if(cnt==P && data_errors==0 && addr_errors==0 && stray==0 && fault_first<0 && done_count==1 && done_cyc>last_del)
   $display("ARGMAX_ROWS PASS P%0d NLINK%0d TP%0d VM_RT%0d ROWS%0d rows%0d",P,NLINK,TP,VM_RT,ROWS,NR);
  else $display("ARGMAX_ROWS FAIL P%0d delivered%0d data%0d addr%0d stray%0d done_count%0d fault_first%0d",P,cnt,data_errors,
   addr_errors,stray,done_count,fault_first<0?-1:fault_first-launch_cyc);
  $finish;
 end
endmodule
`default_nettype wire
