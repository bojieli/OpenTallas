`timescale 1ns/1ps
// Typed DQ protocol equivalence; original every-bit bench is preserved unchanged.
// The actual VM consumer treats valid=0 as an idle slot. Its 64-bank/192-SRAM
// non-interference proof is tb_vm_delivery_invalid_payload.sv. Metadata and
// control still compare every cycle; all 256 payload bits compare on every
// valid beat, and an unknown valid/payload fails closed.
// Lockstep equivalence: monolithic ot_hbm_svc_static_vm_delivery vs the physical split (HBM-V15-HARDEN 10-15).
// Directed-random legal traffic (begin, per-PC fills of both banks, compiler starts at legal and illegal bases) mixed
// with protocol violations (duplicate/epoch-wrong fills, early starts, begin conflicts). All control and valid-beat bits, every cycle.
module tb_hbm_svc_vmdel_protocol_equiv;
 parameter integer SEED=1, CYCLES=60000, LAT=2;  // LAT: split interface latency (v3 lane pin registers: 2)
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,begin_v=0,begin_bank=0,start=0,start_bank=0;
 reg [15:0] begin_epoch=0,start_epoch=0,start_base_sector=0;
 reg [31:0] fill_v=0,fill_bank=0;reg [191:0] fill_slot=0;reg [511:0] fill_epoch=0;reg [8191:0] fill_data=0;
 wire [1:0] br_a,br_b;wire [2247:0] dq_a,dq_b;wire busy_a,busy_b,fault_a,fault_b;
 ot_hbm_svc_static_vm_delivery ref_i(.clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.block_ready(br_a),
  .start(start),.start_bank(start_bank),.start_epoch(start_epoch),.start_base_sector(start_base_sector),.dq(dq_a),.busy(busy_a),.fault(fault_a));
 ot_hbm_svc_static_vm_delivery_split_native dut(.clk_lane({8{clk}}),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
  .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),.block_ready(br_b),
  .start(start),.start_bank(start_bank),.start_epoch(start_epoch),.start_base_sector(start_base_sector),.dq(dq_b),.busy(busy_b),.fault(fault_b));
 integer seed=SEED,cyc,p,checks=0,starts=0,valid_dq=0,faults_seen=0,resets=0,completes=0;
 reg [15:0] ep[0:1]; reg [6:0] nxt[0:31][0:1]; reg [1:0] opened; integer viol_at=-1,fault_run=0; reg v; reg run_bank=0; reg open_pend=0; 
 function integer rnd(input integer n); rnd=$unsigned($random(seed))%n; endfunction
 // reference outputs delayed LAT cycles; the first LAT cycles after each reset release compare nothing (the split's
 // output registers still hold their reset value while the reference already shows its post-reset state)
 reg [2251:0] hist [0:7]; integer since_rst=0, h;
 wire [2251:0] ref_now={br_a,dq_a,busy_a,fault_a};
 wire [2251:0] ref_del=(LAT==0)?ref_now:hist[LAT-1];
 always @(negedge clk) begin
  if(!rst_n) since_rst=0; else since_rst=since_rst+1;
 end
 always @(posedge clk) begin for(h=7;h>0;h=h-1) hist[h]<=hist[h-1]; hist[0]<=ref_now; end
 always @(negedge clk) if(rst_n && since_rst>LAT) begin
  checks=checks+1;
  if(ref_del[2251:2250]!==br_b||ref_del[1:0]!=={busy_b,fault_b})
   $fatal(1,"DELIVERY_PROTOCOL control mismatch cycle=%0d LAT=%0d",cyc,LAT);
  for(integer b=0;b<8;b=b+1)begin:OBSERVE_DQ
   reg [280:0] want,got;
   want=ref_del[2+b*281+:281];got=dq_b[b*281+:281];
   if(want[280]!==1'b0&&want[280]!==1'b1)$fatal(1,"DELIVERY_PROTOCOL unknown valid");
   if(want[280:264]!==got[280:264]||want[7:0]!==got[7:0]||
      (want[280]&&want[263:8]!==got[263:8]))
    $fatal(1,"DELIVERY_PROTOCOL beat mismatch cycle=%0d lane=%0d LAT=%0d valid=%b/%b",cyc,b,LAT,want[280],got[280]);
   if(want[280]&&((^want[263:8]===1'bx)||(^got[263:8]===1'bx)))
    $fatal(1,"DELIVERY_PROTOCOL unknown valid payload");
  end
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
  $display("DELIVERY_PROTOCOL PASS LAT=%0d seed=%0d cycles=%0d checks=%0d starts=%0d dq_valid_lanes=%0d fault_cycles=%0d resets=%0d",
           LAT,seed,CYCLES,checks,starts,valid_dq,faults_seen,resets);
  $finish;
 end
endmodule
