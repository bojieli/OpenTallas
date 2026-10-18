`default_nettype none
// HBM-B-RTL1 2026-10-17 (owner 0do, plan (b) d4g): ot_hbm_svc_vmdel_lane with NPC PC slots per lane.
// d4f: a stack's 8 SM groups (vmks k, PCs 4k..4k+3) fill the 8 delivery lanes of its W slice only; lane b holds the 4 PCs
// of vmks 0,2,4,6 (b < 4) or 1,3,5,7 (b >= 4) and delivers a 64-slot x 4-group block (2048 sectors) into bank b.  In plan
// (b) each 4-SM quadrant fills its OWN 8 banks from its own 4 SM groups (16 PCs): 16 PCs / 8 lanes = 2 PCs per lane, so
// the lane is NPC = 2: slot g of lane b = vmks (2g + b/4) of the quadrant, controller lane b%4 (the d4f rule restricted
// to the quadrant's 4 SM groups).  NPC = 4 is ot_hbm_svc_vmdel_lane statement for statement (same pins, same timing).
// NPC = 2 differences (compiler contract): the group counter runs 0..1; a block is 64 slots x 2 groups = 128 dq beats =
// 1024 sectors (was 2048); beat sector = base + slot*8*NPC + group*8 (NPC 2: slot*16, was slot*32); aperture: base 32-
// sector aligned and base <= 8192 - 512*NPC (NPC 2: 7168, was 6144); block_ready = both slots full.  Delivery start, LAT 2,
// STATUS_LAT 2, the 8-lane full/pcbad status ring, begin/start/epoch rules and faults are unchanged.  Static schedule:
// the compiler issues start only when block_ready (checked, fault otherwise); no credits, no ready, no retry.
// Bench: tb_hbm_svc_vmdel_lane_n_lockstep.sv (NPC 2 lane vs the d4f NPC 4 lane on the same fills).
// Original history (unchanged mechanics) follows.
module ot_hbm_svc_vmdel_lane_n #(parameter integer NPC = 4) (
 input wire clk,rst_n,input wire [2:0] bank_id,
 input wire begin_v_i,begin_bank_i,input wire [15:0] begin_epoch_i,
 input wire start_i,start_bank_i,input wire [15:0] start_epoch_i,start_base_sector_i,
 input wire [NPC-1:0] fill_v_i,fill_bank_i,input wire [6*NPC-1:0] fill_slot_i,input wire [16*NPC-1:0] fill_epoch_i,input wire [256*NPC-1:0] fill_data_i,
 input wire [7:0] full0_all,full1_all,pcbad_all,
 output reg full0,full1,pcbad,
 output reg [1:0] block_ready,output reg busy,output reg fault,
 output reg [280:0] dq
);
 // ---- input pin-flop band: one flop per input pin, no logic, no async clear
 reg rst_s;
 reg begin_v,begin_bank,start,start_bank; reg [15:0] begin_epoch,start_epoch,start_base_sector;
 reg [NPC-1:0] fill_v,fill_bank; reg [6*NPC-1:0] fill_slot; reg [16*NPC-1:0] fill_epoch; reg [256*NPC-1:0] fill_data;
 initial if(NPC!=2&&NPC!=4)$fatal(1,"ot_hbm_svc_vmdel_lane_n: NPC 2 or 4");
 localparam [1:0] GLAST=2'(NPC-1);
 localparam [12:0] APMAX=13'(8192-512*NPC);
 reg [7:0] full0_p,full1_p,pcbad_p; reg [2:0] bank_q;
 always @(posedge clk) begin
  rst_s<=rst_n;
  begin_v<=begin_v_i;start<=start_i;fill_v<=fill_v_i;
  begin_bank<=begin_bank_i;begin_epoch<=begin_epoch_i;start_bank<=start_bank_i;start_epoch<=start_epoch_i;
  start_base_sector<=start_base_sector_i;fill_bank<=fill_bank_i;fill_slot<=fill_slot_i;fill_epoch<=fill_epoch_i;fill_data<=fill_data_i;
  full0_p<=full0_all;full1_p<=full1_all;pcbad_p<=pcbad_all;bank_q<=bank_id;
 end
 // ---- body (clk), synchronous reset from rst_s
 wire [1:0] block_ready_c; wire busy_c,fault_c; wire [280:0] dq_c;
 always @(posedge clk)
  if(!rst_s) begin block_ready<=0;busy<=0;fault<=0;dq[280]<=0; end
  else begin block_ready<=block_ready_c;busy<=busy_c;fault<=fault_c;dq[280]<=dq_c[280]; end
 always @(posedge clk) dq[279:0]<=dq_c[279:0];
 // Flush the status loop before releasing it after reset. The plain capture
 // flops can still contain the sender's pre-reset status on the body's reset
 // edge; that stale fault must not be recirculated into the new image.
 reg status_live;
 always @(posedge clk) status_live<=rst_s;
 // STATUS_LAT=2 (sender output flop + receiver pin flop), reduction after capture.
 wire full0_q=status_live && (&full0_p), full1_q=status_live && (&full1_p), pcbad_q=status_live && (|pcbad_p);
 reg [1:0] owned; reg [15:0] epoch0,epoch1,base_q; reg running,bank_r,sticky,bad,out_v;
 reg [5:0] slot_q,out_slot; reg [1:0] group_q,out_group;
 wire landing_fault=sticky || pcbad_q;
 assign fault_c=bad||landing_fault;
 assign busy_c=running;
 assign block_ready_c={owned[1] && full1_q,owned[0] && full0_q};
 wire aperture_ok=start_base_sector[4:0]==0 && start_base_sector[12:0]<=APMAX &&
                  (!start_base_sector[15] || start_base_sector[14:13]==0);
 wire lstart=start && aperture_ok && !bad;
 wire start_ok=lstart && !running && owned[start_bank] && block_ready_c[start_bank] &&
               start_epoch==(start_bank?epoch1:epoch0) && !landing_fault;
 wire issue=running || start_ok;
 wire rb=running ? bank_r : start_bank;
 wire [1:0] rg=running ? group_q : 2'd0;
 wire [5:0] rs=running ? slot_q : 6'd0;
 wire clear_bank=begin_v && !owned[begin_bank] && !(lstart && start_bank==begin_bank);
 always @(posedge clk) if(!rst_s)begin base_q<=0;bad<=0;end
 else if(start)begin
  if(!aperture_ok || running)bad<=1;
  else base_q<=start_base_sector;
 end
 always @(posedge clk) begin
  if(!rst_s) begin
   owned<=0;epoch0<=0;epoch1<=0;running<=0;bank_r<=0;slot_q<=0;
   sticky<=0;group_q<=0;out_group<=0;out_v<=0;out_slot<=0;
  end else begin
   out_v<=issue && !landing_fault;out_slot<=rs;out_group<=rg;
   if(begin_v) begin
    if(owned[begin_bank] || (lstart && start_bank==begin_bank)) sticky<=1;
    else begin owned[begin_bank]<=1;if(begin_bank)epoch1<=begin_epoch;else epoch0<=begin_epoch;end
   end
   if(lstart && !start_ok) sticky<=1;
   if(start_ok) begin running<=1;bank_r<=start_bank;slot_q<=6'd0;group_q<=2'd1;end
   if(running) begin
    if(slot_q==63 && group_q==GLAST) begin running<=0;owned[bank_r]<=0;end
    else if(group_q==GLAST)begin slot_q<=slot_q+1'b1;group_q<=0;end
    else group_q<=group_q+1'b1;
   end
  end
 end
 // ---- the four PCs of this lane ----
 wire [256*NPC-1:0] macro_data; wire [NPC-1:0] f0,f1,bad_v;
 genvar g;
 generate for(g=0;g<NPC;g=g+1)begin:pc
  reg [63:0] seen0,seen1; reg [6:0] n0,n1; reg pbad;
  wire fb=fill_bank[g]; wire [5:0] fs=fill_slot[g*6+:6];
  wire [15:0] ep=fb?epoch1:epoch0;
  wire [63:0] seen_fb=fb?seen1:seen0;
  wire fill_ok=fill_v[g] && owned[fb] && fill_epoch[g*16+:16]==ep && !seen_fb[fs] && !(issue && rb==fb) && !landing_fault;
  // n counts accepted (always distinct, !seen) writes, so &seen == (n==64) == n[6]: a registered full flag
  assign f0[g]=n0[6]; assign f1[g]=n1[6]; assign bad_v[g]=pbad;
  // seen: unreset (cleared by the bank's accepted begin before any fill of that bank can be accepted)
  always @(posedge clk) begin
   if(clear_bank && !begin_bank) seen0<=0;
   else if(fill_ok && !fb) seen0[fs]<=1;
   if(clear_bank && begin_bank) seen1<=0;
   else if(fill_ok && fb) seen1[fs]<=1;
  end
  always @(posedge clk)begin
   if(!rst_s)begin n0<=0;n1<=0;pbad<=0;end
   else begin
    if(clear_bank && !begin_bank)n0<=0;
    if(clear_bank && begin_bank)n1<=0;
    if(fill_v[g]&&!fill_ok)pbad<=1;
    if(fill_ok && !fb)n0<=n0+1'b1;
    if(fill_ok && fb)n1<=n1+1'b1;
   end
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_payload (
   .clk(clk),.r_ce_in(issue && !landing_fault && rg==g),.r_addr_in({rb,rs}),.rd_out(macro_data[g*256+:256]),
   .w_ce_in(fill_ok),.w_addr_in({fb,fs}),.wd_in(fill_data[g*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 // cross-lane status output flops
 always @(posedge clk)
  if(!rst_s) begin full0<=0;full1<=0;pcbad<=0; end
  else begin full0<=&f0;full1<=&f1;pcbad<=|bad_v; end
 // decoded constant-index group select (no runtime part-select)
 wire [255:0] sel;
 if(NPC==4)begin:sel4
  assign sel=({256{out_group==2'd0}}&macro_data[0+:256])|({256{out_group==2'd1}}&macro_data[256+:256])|
             ({256{out_group==2'd2}}&macro_data[512+:256])|({256{out_group==2'd3}}&macro_data[768+:256]);
 end else begin:sel2
  assign sel=({256{out_group[0]==1'b0}}&macro_data[0+:256])|({256{out_group[0]==1'b1}}&macro_data[256+:256]);
 end
 wire [15:0] sector0=(NPC==4)?base_q+{5'b0,out_slot,out_group,3'b0}:base_q+{6'b0,out_slot,out_group[0],3'b0};
 assign dq_c={out_v && !fault_c,sector0[15:3],bank_q,sel,8'hff};
endmodule
`default_nettype wire
