`timescale 1ns/1ps
// Lockstep equivalence of ot_hbm_svc_static_pc (counted block_ready, HBM-V15-HARDEN 10-15) against the previous
// all_seen form (ot_hbm_svc_static_pc_ref, renamed copy of the prior source). Directed-random opens, staged fills,
// scheduled reads, prefetch/write-back commands with randomly delayed PHY responses, retires and violations; every
// output bit compared every cycle.
module tb_hbm_svc_pc_ready_equiv;
 parameter integer CYCLES=40000;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg open_v=0,open_bank=0;reg [15:0] open_epoch=0;reg [6:0] open_count=0;
 reg fill_v=0,fill_bank=0;reg [15:0] fill_epoch=0;reg [5:0] fill_slot=0;reg [255:0] fill_data=0;
 reg read_v=0,read_bank=0;reg [15:0] read_epoch=0;reg [5:0] read_slot=0;
 reg retire_v=0,retire_bank=0;reg [15:0] retire_epoch=0;
 reg cmd_v=0,cmd_write=0,cmd_bank=0;reg [15:0] cmd_epoch=0;reg [29:0] cmd_addr=0,cmd_step=0;
 reg k_rdy=0,k_wr_done=0,kr_v=0;reg [16:0] kr_tag=0;reg [3:0] kr_beat=0;reg [255:0] kr_data=0;
 wire [1:0] br_a,br_b,bo_a,bo_b;wire ov_a,ov_b,busy_a,busy_b,done_a,done_b,fault_a,fault_b;
 wire [255:0] od_a,od_b,kw_a,kw_b;wire kv_a,kv_b,kwe_a,kwe_b,krr_a,krr_b;wire [29:0] ka_a,ka_b;wire [3:0] kl_a,kl_b;
 wire [16:0] kt_a,kt_b;wire [31:0] ks_a,ks_b;
 ot_hbm_svc_static_pc_ref ref_i(.clk(clk),.rst_n(rst_n),.open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_epoch(fill_epoch),.fill_slot(fill_slot),.fill_data(fill_data),
  .read_v(read_v),.read_bank(read_bank),.read_epoch(read_epoch),.read_slot(read_slot),.out_v(ov_a),.out_data(od_a),
  .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),.cmd_v(cmd_v),.cmd_write(cmd_write),.cmd_bank(cmd_bank),
  .cmd_epoch(cmd_epoch),.cmd_addr(cmd_addr),.cmd_step(cmd_step),.block_ready(br_a),.bank_owned(bo_a),.busy(busy_a),.done(done_a),.fault(fault_a),
  .k_v(kv_a),.k_rdy(k_rdy),.k_addr(ka_a),.k_len(kl_a),.k_tag(kt_a),.k_we(kwe_a),.k_wdata(kw_a),.k_wstrb(ks_a),.k_wr_done(k_wr_done),
  .kr_v(kr_v),.kr_rdy(krr_a),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 ot_hbm_svc_static_pc dut(.clk(clk),.rst_n(rst_n),.open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_epoch(fill_epoch),.fill_slot(fill_slot),.fill_data(fill_data),
  .read_v(read_v),.read_bank(read_bank),.read_epoch(read_epoch),.read_slot(read_slot),.out_v(ov_b),.out_data(od_b),
  .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),.cmd_v(cmd_v),.cmd_write(cmd_write),.cmd_bank(cmd_bank),
  .cmd_epoch(cmd_epoch),.cmd_addr(cmd_addr),.cmd_step(cmd_step),.block_ready(br_b),.bank_owned(bo_b),.busy(busy_b),.done(done_b),.fault(fault_b),
  .k_v(kv_b),.k_rdy(k_rdy),.k_addr(ka_b),.k_len(kl_b),.k_tag(kt_b),.k_we(kwe_b),.k_wdata(kw_b),.k_wstrb(ks_b),.k_wr_done(k_wr_done),
  .kr_v(kr_v),.kr_rdy(krr_b),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 integer seed=7,cyc,checks=0,readies=0,dones=0,faults=0,reads=0,fault_run=0;
 reg [15:0] ep[0:1]; reg [6:0] cnt[0:1]; reg [6:0] nxt[0:1]; reg [1:0] own; reg viol;
 function integer rnd(input integer n); rnd=$unsigned($random(seed))%n; endfunction
 always @(negedge clk) if(rst_n) begin
  checks=checks+1;
  if({br_a,bo_a,ov_a,od_a,busy_a,done_a,fault_a,kv_a,ka_a,kl_a,kt_a,kwe_a,kw_a,ks_a,krr_a}!==
     {br_b,bo_b,ov_b,od_b,busy_b,done_b,fault_b,kv_b,ka_b,kl_b,kt_b,kwe_b,kw_b,ks_b,krr_b})
   $fatal(1,"PC_READY_EQUIV mismatch cycle=%0d br %b/%b busy %b/%b fault %b/%b",cyc,br_a,br_b,busy_a,busy_b,fault_a,fault_b);
  if(br_a!=0) readies=readies+1; if(done_a) dones=dones+1; if(fault_a) faults=faults+1; if(ov_a) reads=reads+1;
 end
 initial begin
  if(!$value$plusargs("seed=%d",seed)) seed=7;
  own=0; viol=0;
  for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
   @(negedge clk);
   open_v=0;fill_v=0;read_v=0;retire_v=0;cmd_v=0;k_wr_done=0;kr_v=0;
   fault_run=fault_a?fault_run+1:0;
   if(!rst_n) begin rst_n=1; own=0; viol=(rnd(4)==0); end
   else if(fault_run>20 || rnd(30000)==0) rst_n=0;
   else begin
    k_rdy=(rnd(3)!=0);
    // PHY side: answer an outstanding read request after a random delay, ack writes
    if(krr_a && rnd(3)==0) begin kr_v=1; kr_tag=(viol&&rnd(50)==0)?$random(seed):kt_a; kr_beat=0; kr_data={8{$random(seed)}}; end
    if(kwe_a && kv_a && k_rdy || busy_a && rnd(4)==0) k_wr_done=(rnd(2)==0) && (kwe_a || !viol ? 1 : rnd(2));
    if(!busy_a && rnd(25)==0) begin
     open_bank=rnd(2);
     if(!own[open_bank] || viol&&rnd(10)==0) begin
      open_v=1; open_epoch=$random(seed); open_count=(viol&&rnd(20)==0)?rnd(128):1+rnd(64);
      if(!own[open_bank]) begin own[open_bank]=1; ep[open_bank]=open_epoch; cnt[open_bank]=open_count; nxt[open_bank]=0; end
     end
    end
    if(!open_v && rnd(2)==0) begin
     fill_bank=rnd(2);
     if(own[fill_bank] && nxt[fill_bank]<cnt[fill_bank] && !(busy_a)) begin
      fill_v=1; fill_slot=nxt[fill_bank]; nxt[fill_bank]=nxt[fill_bank]+1;
      fill_epoch=(viol&&rnd(40)==0)?$random(seed):ep[fill_bank]; fill_data={8{$random(seed)}};
      if(viol&&rnd(40)==0) fill_slot=rnd(64);
     end
    end
    if(rnd(4)==0) begin read_bank=rnd(2); if(br_a[read_bank] || viol&&rnd(30)==0) begin
      read_v=1; read_epoch=ep[read_bank]; read_slot=rnd(cnt[read_bank]==0?1:cnt[read_bank]); end end
    if(!busy_a && !fill_v && !read_v && rnd(40)==0) begin
     cmd_bank=rnd(2); cmd_write=br_a[cmd_bank]?1:0;
     if(own[cmd_bank] && (cmd_write || nxt[cmd_bank]==0) || viol&&rnd(10)==0) begin
      cmd_v=1; cmd_epoch=ep[cmd_bank]; cmd_addr={$random(seed)}<<5; cmd_step=(1+rnd(8))<<5;
      if(!cmd_write) nxt[cmd_bank]=cnt[cmd_bank];
      if(cmd_write) own[cmd_bank]=0;
     end
    end
    if(!busy_a && !cmd_v && !fill_v && !read_v && rnd(60)==0) begin
     retire_bank=rnd(2); if(own[retire_bank] && br_a[retire_bank] || viol&&rnd(5)==0) begin
      retire_v=1; retire_epoch=ep[retire_bank]; own[retire_bank]=0; end
    end
   end
  end
  $display("PC_READY_EQUIV PASS cycles=%0d checks=%0d ready_cycles=%0d dones=%0d reads=%0d fault_cycles=%0d",CYCLES,checks,readies,dones,reads,faults);
  $finish;
 end
endmodule
