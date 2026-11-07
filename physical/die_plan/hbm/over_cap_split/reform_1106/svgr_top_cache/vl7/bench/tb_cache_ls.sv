`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-87 vL7 lock-step bench: ot_svgr_cache136_native new form (WDEC/GSEL/GREP from defines) vs the vL6 kit copy
// (renamed ot_svgr_cache136_native_ref), PACKED136=1 RW_SRAM=1 WPIPE=1 (the vL6 kit setting, P1=1 CACHE_RW_SRAM=1).
// Stimulus is protocol-steered from the REFERENCE instance's registers (both see identical inputs), with injection of
// bad sector index, wrong epoch, missing / extra sector, bad read / retire / open, read-retire-open collisions, resets.
// Every output port compared every edge with !==.
`ifndef WDEC
`define WDEC 0
`endif
`ifndef GS
`define GS 0
`endif
`ifndef GR
`define GR 1
`endif
`ifndef NCYC
`define NCYC 200000
`endif
`ifndef SEED
`define SEED 1
`endif
`ifndef WP
`define WP 1
`endif
module tb;
 reg clk=0,rst_n=0;
 reg open_v,open_bank;reg[15:0]open_epoch;reg[6:0]open_count;reg[9:0]open_tag_base;
 reg[3:0]sector_v;reg[95:0]sector_index;reg[63:0]sector_epoch;reg[1023:0]sector_data;
 reg read_v,read_bank;reg[15:0]read_epoch;reg[5:0]read_row;reg[9:0]read_tag;
 reg retire_v,retire_bank;reg[15:0]retire_epoch;
 wire[1:0]br_a,bo_a,br_b,bo_b;wire busy_a,busy_b,f_a,f_b;wire[1098:0]op_a,op_b;
 ot_svgr_cache136_native_ref #(.PACKED136(1),.RW_SRAM(1),.WPIPE(`WP)) ref_i(.clk(clk),.rst_n(rst_n),
  .open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),.open_tag_base(open_tag_base),
  .sector_v(sector_v),.sector_index(sector_index),.sector_epoch(sector_epoch),.sector_data(sector_data),
  .read_v(read_v),.read_bank(read_bank),.read_epoch(read_epoch),.read_row(read_row),.read_tag(read_tag),
  .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),
  .block_ready(br_a),.bank_owned(bo_a),.busy(busy_a),.fault(f_a),.out_packet(op_a));
 ot_svgr_cache136_native #(.PACKED136(1),.RW_SRAM(1),.WPIPE(`WP),.WDECOUPLE(`WDEC),.GSEL(`GS),.GREP(`GR)) dut_i(.clk(clk),.rst_n(rst_n),
  .open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),.open_tag_base(open_tag_base),
  .sector_v(sector_v),.sector_index(sector_index),.sector_epoch(sector_epoch),.sector_data(sector_data),
  .read_v(read_v),.read_bank(read_bank),.read_epoch(read_epoch),.read_row(read_row),.read_tag(read_tag),
  .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),
  .block_ready(br_b),.bank_owned(bo_b),.busy(busy_b),.fault(f_b),.out_packet(op_b));
 // reference state used only to steer stimulus
 wire r_run=ref_i.g_on.running,r_st=ref_i.g_on.sticky,r_lb=ref_i.g_on.load_bank;
 wire[8:0]r_rcv=ref_i.g_on.received;wire[2:0]r_exp=ref_i.g_on.expected_sectors;wire[15:0]r_lep=ref_i.g_on.load_epoch;
 wire[1:0]r_own=ref_i.g_on.owned;
 integer seed=`SEED,cyc=0,mism=0,i,k,nreset=0,nfault=0,nrowwr=0,nreadok=0,nopen=0,nretire=0,ninj=0,nmm_w=0,since_fault=0,ncmp=0;
 integer nwdiff=0,nrows=0,nrp3=0;
 reg[31:0] rr;
 function [31:0] rnd;input integer dummy;begin rnd=$random(seed);end endfunction
 always #5 clk=~clk;
 task drive;begin
  // defaults: protocol-correct
  open_v=0;open_bank=rnd(0);open_epoch=rnd(0);open_count=1+(rnd(0)&63);open_tag_base=rnd(0);
  sector_v=0;sector_index=0;sector_epoch=0;
  for(k=0;k<32;k=k+1)sector_data[k*32+:32]=rnd(0);
  read_v=0;read_bank=rnd(0);read_epoch=0;read_row=rnd(0);read_tag=0;retire_v=0;retire_bank=rnd(0);retire_epoch=0;
  rr=rnd(0);
  // sectors: the expected pattern, with injections
  if(r_run&&!r_st)begin
   for(k=0;k<4;k=k+1)begin
    sector_v[k]=(k<r_exp);sector_index[k*24+:24]=r_rcv+k;sector_epoch[k*16+:16]=r_lep;
   end
   if((rr&4095)<3)begin ninj=ninj+1;sector_index[(rnd(0)&3)*24+:24]=rnd(0)&16'hffff;end         // bad index
   else if((rr&4095)<5)begin ninj=ninj+1;sector_epoch[(rnd(0)&3)*16+:16]=rnd(0);end              // wrong epoch
   else if((rr&4095)<7)begin ninj=ninj+1;sector_v[rnd(0)&3]=0;end                                 // missing sector
   else if((rr&4095)<8)begin ninj=ninj+1;sector_v[rnd(0)&3]=1;end                                 // extra sector
   else if((rr&4095)<10)begin ninj=ninj+1;for(k=0;k<4;k=k+1)sector_index[k*24+:24]=r_rcv+k-((rnd(0)&1)?16:0);end // aliased index (present clash)
   else if((rr&4095)<11)begin ninj=ninj+1;for(k=0;k<4;k=k+1)sector_index[k*24+:24]=r_rcv+k+16;end // index +16 (same slot)
  end else if((rr&4095)<2)begin ninj=ninj+1;sector_v=rnd(0);end                                 // sector while idle
  // open: when idle, a free bank, mostly legal
  if(!r_run&&(rnd(0)&7)==0)begin
   open_v=1;open_bank=(r_own==2'b01)?1:(r_own==2'b10)?0:rnd(0);
   if((rnd(0)&15)==0)open_count=(rnd(0)&1)?0:65+(rnd(0)&63);   // illegal count
   if((rnd(0)&63)==0)begin ninj=ninj+1;open_bank=~open_bank;end
  end else if((rnd(0)&1023)==0)begin ninj=ninj+1;open_v=1;end   // open while running
  // read: of a ready bank, correct tag/epoch mostly
  if((rnd(0)&3)==0)begin
   read_bank=rnd(0);read_row=rnd(0)%((ref_i.g_on.count[read_bank]==0)?1:ref_i.g_on.count[read_bank]);
   read_epoch=ref_i.g_on.epoch[read_bank];read_tag=ref_i.g_on.tags[{read_bank,read_row}];
   if(ref_i.g_on.ready[read_bank]||(rnd(0)&255)==0)read_v=1;
   if((rnd(0)&511)==0)begin ninj=ninj+1;read_tag=read_tag^1;end
   if((rnd(0)&511)==0)begin ninj=ninj+1;read_epoch=read_epoch^16'h8000;end
   if((rnd(0)&511)==0)begin ninj=ninj+1;read_row=6'd63;end
  end
  // retire: an owned, loaded bank
  if((rnd(0)&15)==0)begin
   retire_bank=rnd(0);retire_epoch=ref_i.g_on.epoch[retire_bank];
   if(r_own[retire_bank]&&!(r_run&&r_lb==retire_bank)&&ref_i.g_on.ready[retire_bank])retire_v=1;
   if((rnd(0)&255)==0)begin retire_v=1;ninj=ninj+1;end
   if(retire_v&&read_v&&read_bank==retire_bank&&(rnd(0)&7)!=0)read_v=0; // collisions only sometimes
   if((rnd(0)&255)==0)begin retire_epoch=retire_epoch^1;end
  end
 end endtask
 initial begin
  drive;rst_n=0;repeat(3)@(posedge clk);#1 rst_n=1;
  while(cyc<`NCYC)begin
   @(negedge clk);drive;
   // reset: after a fault, or rarely mid-run (also reset asserted mid-cycle = async)
   if(r_st)since_fault=since_fault+1;
   if((r_st&&since_fault>(rnd(0)&63))||(rnd(0)%20000)==0)begin
    #2 rst_n=0;nreset=nreset+1;since_fault=0;#2 rst_n=1;
   end
   #1;
   if(ref_i.g_on.open_ok&&rst_n)nopen=nopen+1;
   if(rst_n&&r_run&&!r_st)for(k=0;k<4;k=k+1)if(sector_v[k]&&(sector_epoch[k*16+:16]!=r_lep||sector_index[k*24+:24]!=r_rcv+k||ref_i.g_on.present[(r_rcv+k)%16]))nmm_w=nmm_w+1;
   if(rst_n&&ref_i.g_on.row_slot&&!ref_i.g_on.sticky)nrows=nrows+1;
   if(rst_n&&ref_i.g_on.row_slot&&!ref_i.g_on.sticky&&ref_i.g_on.record_phase==3)nrp3=nrp3+1;
   @(posedge clk);#1;
   cyc=cyc+1;ncmp=ncmp+1;
   if(br_a!==br_b||bo_a!==bo_b||busy_a!==busy_b||f_a!==f_b||op_a!==op_b)begin
    mism=mism+1;
`ifdef STOPMM
    if(mism==1)begin $display("FIRST_MISMATCH cyc=%0d",cyc);$display("RESULT_MUT caught=1 cyc=%0d",cyc);$finish;end
`endif
    if(mism<=5)$display("MISMATCH cyc=%0d br %b/%b bo %b/%b busy %b/%b f %b/%b opv %b/%b opd_eq %0d",cyc,br_a,br_b,bo_a,bo_b,busy_a,busy_b,f_a,f_b,op_a[1098],op_b[1098],op_a===op_b);
   end
   if(f_a&&!r_st)nfault=nfault+1;
   if(ref_i.g_on.w_q)nrowwr=nrowwr+1;
   if(ref_i.g_on.out_valid&&!f_a)nreadok=nreadok+1;
  end
  $display("RESULT wdec=%0d gsel=%0d grep=%0d wpipe=%0d seed=%0d cycles=%0d compared_edges=%0d ports=block_ready,bank_owned,busy,fault,out_packet[1098:0] (1105 bits) mismatches=%0d resets=%0d injections=%0d row_writes=%0d reads_ok=%0d opens=%0d mismatch_sector_writes=%0d row_slots=%0d row_slots_rp3=%0d",
   `WDEC,`GS,`GR,`WP,`SEED,cyc,ncmp,mism,nreset,ninj,nrowwr,nreadok,nopen,nmm_w,nrows,nrp3);
  $finish;
 end
 // count sticky rises in ref for the summary
 reg pst=0;integer nsticky=0;always @(posedge clk)begin if(ref_i.g_on.sticky&&!pst)nsticky=nsticky+1;pst<=ref_i.g_on.sticky;end
 final $display("STICKY_RISES %0d",nsticky);
endmodule
`default_nettype wire
