`timescale 1ns/1ps
// Lockstep equivalence: monolithic ot_hbm_svc_static_vm_delivery vs the physical split (HBM-V15-HARDEN 10-15).
// Directed-random legal traffic (begin, per-PC fills of both banks, compiler starts at legal and illegal bases) mixed
// with protocol violations (duplicate/epoch-wrong fills, early starts, begin conflicts). Every output bit, every cycle.
module tb_hbm_svc_vmdel_split_equiv;
 parameter integer SEED=1, CYCLES=60000;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,begin_v=0,begin_bank=0,start=0,start_bank=0;
 reg [15:0] begin_epoch=0,start_epoch=0,start_base_sector=0;
 reg [31:0] fill_v=0,fill_bank=0;reg [191:0] fill_slot=0;reg [511:0] fill_epoch=0;reg [8191:0] fill_data=0;
 wire [1:0] br_a,br_b;wire [2247:0] dq_a,dq_b;wire busy_a,busy_b,fault_a,fault_b;
 ot_hbm_svc_static_vm_delivery ref_i(.clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.block_ready(br_a),
  .start(start),.start_bank(start_bank),.start_epoch(start_epoch),.start_base_sector(start_base_sector),.dq(dq_a),.busy(busy_a),.fault(fault_a));
 ot_hbm_svc_static_vm_delivery_split dut(.clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.block_ready(br_b),
  .start(start),.start_bank(start_bank),.start_epoch(start_epoch),.start_base_sector(start_base_sector),.dq(dq_b),.busy(busy_b),.fault(fault_b));
 integer seed=SEED,cyc,p,checks=0,starts=0,valid_dq=0,faults_seen=0,resets=0,completes=0;
 reg [15:0] ep[0:1]; reg [6:0] nxt[0:31][0:1]; reg [1:0] opened; integer viol_at=-1,fault_run=0; reg v; reg run_bank=0; reg open_pend=0; 
 function integer rnd(input integer n); rnd=$unsigned($random(seed))%n; endfunction
 always @(negedge clk) if(rst_n) begin
  checks=checks+1;
  if({br_a,dq_a,busy_a,fault_a}!=={br_b,dq_b,busy_b,fault_b})
   $fatal(1,"SPLIT_EQUIV mismatch cycle=%0d br %b/%b busy %b/%b fault %b/%b dq_diff_bank=%0d",cyc,br_a,br_b,busy_a,busy_b,fault_a,fault_b,
          (dq_a[280:0]!==dq_b[280:0])?0:(dq_a[561:281]!==dq_b[561:281])?1:9);
  for(integer b=0;b<8;b=b+1) if(dq_a[b*281+280]) valid_dq=valid_dq+1;
  if(fault_a) faults_seen=faults_seen+1;
 end
 initial begin
  if(!$value$plusargs("seed=%d",seed)) seed=SEED;
  opened=0;
  for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
   @(negedge clk);
   begin_v=0;start=0;fill_v=0;
   fault_run=fault_a?fault_run+1:0;
   v=(cyc==viol_at);
   if(!rst_n) begin rst_n=(rnd(4)!=0); opened=0; for(p=0;p<32;p=p+1)begin nxt[p][0]=0;nxt[p][1]=0;end
     viol_at=(rnd(3)==0)?cyc+1+rnd(3000):-1; end
   else if(fault_run>40 || rnd(20000)==0) begin rst_n=0; resets=resets+1; end
   else begin
    // begin: mostly on a closed bank, sometimes a conflict
    if((!opened[0]&&!(busy_a&&run_bank==0)||!opened[1]&&!(busy_a&&run_bank==1))&&rnd(20)==0 || v&&rnd(4)==0) begin
     begin_bank=v?rnd(2):(!opened[0]?0:1); begin_epoch=$random(seed); if(!v && busy_a && run_bank==begin_bank) begin_bank=!begin_bank;
     begin_v=1;
     if(!opened[begin_bank]) begin ep[begin_bank]=begin_epoch; open_pend=1; end
    end
    // fills: each PC independently, next slot of an opened bank, occasional violations
    for(p=0;p<32;p=p+1) if(rnd(3)!=0) begin
     fill_bank[p]=rnd(2); if(!v&&!opened[fill_bank[p]]) fill_bank[p]=!fill_bank[p];
     fill_slot[p*6+:6]=(v&&rnd(8)==0)?rnd(64):nxt[p][fill_bank[p]][5:0];
     fill_epoch[p*16+:16]=(v&&rnd(8)==0)?$random(seed):ep[fill_bank[p]];
     fill_data[p*256+:256]={8{$random(seed)}};
     if(opened[fill_bank[p]] && nxt[p][fill_bank[p]]<64 || v&&rnd(8)==0) begin
      fill_v[p]=1; if(nxt[p][fill_bank[p]]<64) nxt[p][fill_bank[p]]=nxt[p][fill_bank[p]]+1;
     end
    end
    if(open_pend) begin opened[begin_bank]=1; for(p=0;p<32;p=p+1) nxt[p][begin_bank]=0; open_pend=0; end
    // compiler start: when a block is ready (legal), sometimes early / bad base
    if((br_a!=0 && !busy_a && rnd(4)==0) || v&&rnd(2)==0) begin
     start=1; start_bank=br_a[1]?1:br_a[0]?0:rnd(2); start_epoch=(v&&rnd(3)==0)?$random(seed):ep[start_bank];
     start_base_sector=(v&&rnd(3)==0)?$random(seed):{rnd(2)==0?3'b000:3'b100,rnd(193)>192?13'd0:13'(rnd(193)*32)};
     starts=starts+1;
     if(br_a[start_bank]) begin opened[start_bank]=0; run_bank=start_bank; completes=completes+1; end
    end
   end
  end
  $display("SPLIT_EQUIV PASS seed=%0d cycles=%0d checks=%0d starts=%0d dq_valid_lanes=%0d fault_cycles=%0d resets=%0d",
           seed,CYCLES,checks,starts,valid_dq,faults_seen,resets);
  $finish;
 end
endmodule
