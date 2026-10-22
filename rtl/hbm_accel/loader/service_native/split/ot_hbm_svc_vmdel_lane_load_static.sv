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
// HBMc/TILES3 10-22 (m9 TT -219.3 / b9 -161.0: owned -> block_ready_c -> load_cmd_ok -> issue -> u_payload r_ce_in, ~890 ps
// with ~450 ps of long wire between the central control and the PC macros):
//  SHPRE=1 (0 edges): the command shape checks (group < NPC, ln/sub/offset/format ranges) are pure functions of load_cmd_i,
//   computed in the pin-flop stage and registered beside load_cmd (shape_*_q == f(load_cmd) on every edge): exact.
//  RPIPE=1 (+1 edge, COORD 12:20 accepted): the payload read port (r_ce / r_addr) is registered in a kept per-PC module
//   beside its macro; every consumer of the read data (raw group select, out_v/slot/group, the load capture/convert/
//   scatter/mask command pipes, lv/lc) moves one edge later, so dq / load_dq / load_out_v / load_dest_* are +1 edge;
//   full/pcbad/block_ready/busy/fault and the write port are unchanged.
module ot_hbm_svc_vmdel_lane_load_static #(parameter integer NPC = 4, MUT = 0, WCE_SPEC = 0, SHPRE = 0, RPIPE = 0) (
 input wire clk,rst_n,input wire [2:0] bank_id,
 input wire begin_v_i,begin_bank_i,input wire [15:0] begin_epoch_i,
 input wire start_i,start_bank_i,input wire [15:0] start_epoch_i,start_base_sector_i,
 input wire [NPC-1:0] fill_v_i,fill_bank_i,input wire [6*NPC-1:0] fill_slot_i,input wire [16*NPC-1:0] fill_epoch_i,input wire [256*NPC-1:0] fill_data_i,
 input wire [7:0] full0_all,full1_all,pcbad_all,
 output reg full0,full1,pcbad,
 output reg [1:0] block_ready,output reg busy,output reg fault,
 input wire load_v_i,input wire [61:0] load_cmd_i,
 output reg [2:0] load_dest_bank,output reg [1:0] load_dest_q,
 output reg [280:0] load_dq,output wire load_out_v,
 output reg [280:0] dq
);
 // ---- input pin-flop band: one flop per input pin, no logic, no async clear
 reg rst_s;
 wire[7:0]reset_copy;
 for(genvar r=0;r<8;r=r+1)begin:reset_roots
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(2000+r)) u(.clk(clk),.d(rst_n),.q(reset_copy[r]));
 end
 reg load_v;reg [61:0] load_cmd;
 wire load_bank_epoch,start_bank_epoch;
 (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(2300)) u_load_epoch_bank(.clk(clk),.d(load_cmd_i[0]),.q(load_bank_epoch));
 (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(2301)) u_start_epoch_bank(.clk(clk),.d(start_bank_i),.q(start_bank_epoch));
 always @(posedge clk)begin load_v<=load_v_i;load_cmd<=load_cmd_i;end
 // SHPRE: shape checks of the command on its way into the pin flop (input-to-reg slack 394 ps at m9)
 wire [2:0] lf_i=load_cmd_i[32:30]; wire [3:0] ln_i=load_cmd_i[55:52];
 // m11 (HBMc/TILES4): m10 census refused load_cmd_i[30..32] at 33-37 loads (22 capture + 2 format copies + pin flop
 // + abc spreading the format decode over the shape adders).  The format decode ends on kept nets (abc boundary), so
 // each raw format bit drives only the three decode terms; same function.
 (* keep="true" *) wire lf_e4_i=lf_i==0||lf_i==5; (* keep="true" *) wire lf_e2_i=lf_i==1;
 (* keep="true" *) wire lf_bad_i=lf_i==3||lf_i==7;
 wire [5:0] esz_i=lf_e4_i?6'd4:lf_e2_i?6'd2:6'd1;
 wire shape_com_i=load_cmd_i[18:17]<NPC&&ln_i<=8&&{1'b0,load_cmd_i[51:49]}+ln_i<=8&&
  {1'b0,load_cmd_i[29:25]}+ln_i*esz_i<=32&&!lf_bad_i;
 (* keep="true" *) reg shape_cmd_q,shape_load_q;
 always @(posedge clk)begin shape_cmd_q<=shape_com_i&&(ln_i!=0||load_cmd_i[56]);shape_load_q<=shape_com_i&&ln_i!=0;end
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
  if(!reset_copy[0]) begin block_ready<=0;busy<=0;fault<=0;dq[280]<=0; end
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
               start_epoch==(start_bank_epoch?epoch1:epoch0) && !landing_fault;
 wire raw_issue=running || start_ok;
 wire [2:0] lf=load_cmd[32:30];
 wire [3:0] ln=load_cmd[55:52];
 wire [5:0] esz=(lf==0||lf==5)?6'd4:lf==1?6'd2:6'd1;
 wire shape_cmd=(SHPRE!=0)?shape_cmd_q:(load_cmd[18:17]<NPC&&(ln!=0||load_cmd[56])&&ln<=8&&{1'b0,load_cmd[51:49]}+ln<=8&&
 {1'b0,load_cmd[29:25]}+ln*esz<=32&&lf!=3&&lf!=7);
 wire shape_load=(SHPRE!=0)?shape_load_q:(load_cmd[18:17]<NPC&&ln!=0&&ln<=8&&{1'b0,load_cmd[51:49]}+ln<=8&&
 {1'b0,load_cmd[29:25]}+ln*esz<=32&&lf!=3&&lf!=7);
 // round 5 (b11r4 census: the load_bank_epoch copy selected the 16-bit epoch mux of both compares, 34 loads): compare the
 // command epoch with BOTH bank epochs on kept nets; load_bank_epoch then selects one bit.  Same function.
 (* keep="true" *) wire lc_eq0=load_cmd[16:1]==epoch0; (* keep="true" *) wire lc_eq1=load_cmd[16:1]==epoch1;
 (* keep="true" *) wire lc_epoch_eq=load_bank_epoch?lc_eq1:lc_eq0;   // round 6: b11r5 still 34 (abc duplicated the select into both cones)
 wire command_ok=load_v&&!raw_issue&&owned[load_cmd[0]]&&
 block_ready_c[load_cmd[0]]&&lc_epoch_eq&&
 shape_cmd&&!landing_fault;
 wire load_ok=command_ok&&ln!=0;
 wire release_only=command_ok&&ln==0;
 // HBMc/TILES 10-22 (H.STA.DMA.LOAD, routes m5 TT -191.5 / m7 TT -265.3 at the payload CE pins): the read CE
 // no longer waits for start_ok in series with the command checks. command_ok = !raw_issue && load_cmd_ok, so
 // raw_issue || (command_ok && ln!=0) == raw_issue || (load_cmd_ok && ln!=0): the two validations run in parallel.
 // Identical function (every edge, valid or malformed); no read is enabled that the old expression did not enable.
 wire load_cmd_ok=load_v&&owned[load_cmd[0]]&&
 block_ready_c[load_cmd[0]]&&lc_epoch_eq&&
 shape_load&&!landing_fault;
 wire issue=raw_issue||load_cmd_ok;
 // Address selection does not wait for ownership/shape validation. Read CE
 // still requires load_ok; conflicting or malformed requests set sticky fault
 // and cannot produce a valid output. Raw-only schedules keep their old path.
 // m11/b11 round 4 (b11r3 census: running = busy_c flop at 33 loads): the address selects and the raw request read a
 // hierarchy-kept copy of running with the same next state (cannot be merged with running).  Same value every edge.
 wire running_n=!reset_copy[2] ? 1'b0 : start_ok ? 1'b1 : (running && slot_q==63 && group_q==GLAST) ? 1'b0 : running;
 wire running_a;
 (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(2500),.S(1)) u_running_a(.clk(clk),.d(running_n),.q(running_a));
 wire rb=load_v?load_cmd[0]:(running_a ? bank_r : start_bank);
 wire [1:0] rg=load_v?load_cmd[18:17]:(running_a ? group_q : 2'd0);
 wire [5:0] rs=load_v?load_cmd[24:19]:(running_a ? slot_q : 6'd0);
 // A bank requested for reading cannot accept a fill on this edge. This
 // hazard check deliberately precedes read validation: valid schedules are
 // unchanged, and an invalid conflicting request already latches fault.
 // After such a fault, rejected fills and their counter/pcbad side effects
 // can differ from the old implementation. No invalid read or output is
 // enabled; complete ownership/epoch/full/shape checks remain above.
 wire raw_request=running_a||start;
 wire raw_request_bank=running_a?bank_r:start_bank;
 wire clear_bank=begin_v && !owned[begin_bank] && !(lstart && start_bank==begin_bank);
 always @(posedge clk) if(!reset_copy[1])begin bad<=0;end
 else if(start)begin
  if(!aperture_ok || running)bad<=1;
  else base_q<=start_base_sector;
 end
 // m11 (HBMc/TILES4): m11 census found the epoch0/epoch1 load enable at 34/33 loads (abc shared the begin-accept term
 // with the owned/sticky/start cones).  Each epoch's write enable is the same condition as before (out of reset, begin_v,
 // bank free and not being started, begin_bank selects it), ended on a kept net that drives only its 16 enables.
 // m11 round 3: the kept net was still buffered to 33 pins (census counts through buffers; each enable bit maps to a
 // 2-pin AO mux).  Each epoch's enable now ends in two hierarchy-kept AND gates, one per byte (same function).
 (* keep="true" *) wire ep0_acc=reset_copy[2]&&begin_v&&!begin_bank; (* keep="true" *) wire ep0_free=!(owned[0]||(lstart&&start_bank==1'b0));
 (* keep="true" *) wire ep1_acc=reset_copy[2]&&begin_v&&begin_bank;  (* keep="true" *) wire ep1_free=!(owned[1]||(lstart&&start_bank==1'b1));
 wire [1:0] ep0_we,ep1_we;
 for(genvar h=0;h<2;h=h+1)begin:ep_en
  (* keep_hierarchy="yes" *) ot_hbm_dma_and2 #(.COPY_ID(h))   u0(.a(ep0_acc),.b(ep0_free),.y(ep0_we[h]));
  (* keep_hierarchy="yes" *) ot_hbm_dma_and2 #(.COPY_ID(2+h)) u1(.a(ep1_acc),.b(ep1_free),.y(ep1_we[h]));
  always @(posedge clk) begin if(ep0_we[h])epoch0[8*h+:8]<=begin_epoch[8*h+:8]; if(ep1_we[h])epoch1[8*h+:8]<=begin_epoch[8*h+:8]; end
 end
 always @(posedge clk) begin
  if(!reset_copy[2]) begin
   owned<=0;running<=0;bank_r<=0;slot_q<=0;
   sticky<=0;out_v<=0;
  end else begin
   out_v<=raw_issue && !landing_fault;
   if(load_v&&!command_ok)sticky<=1;
   if(command_ok&&load_cmd[56])owned[load_cmd[0]]<=0;
   if(begin_v) begin
    if(owned[begin_bank] || (lstart && start_bank==begin_bank)) sticky<=1;
    else owned[begin_bank]<=1;   // m11: epoch0/1 writes moved to their kept enables below (same condition)
   end
   if(lstart && !start_ok) sticky<=1;
   if(start_ok) begin running<=1;bank_r<=start_bank;slot_q<=6'd0;end
   if(running) begin
    if(slot_q==63 && group_q==GLAST) begin running<=0;owned[bank_r]<=0;end
    else if(group_q==GLAST)begin slot_q<=slot_q+1'b1;end

   end
  end
 end
 always @(posedge clk)begin
  if(!reset_copy[5])group_q<=0;
  else if(start_ok)group_q<=1;
  else if(running&&!(slot_q==63&&group_q==GLAST))group_q<=(group_q==GLAST)?2'd0:group_q+1'b1;
  if(!reset_copy[6])begin out_group<=0;out_slot<=0;end
  else begin out_group<=rg;out_slot<=rs;end
 end
 // RPIPE: the read data arrives one edge later; out_v / out_slot / out_group / raw group select follow it
 reg out_v1; reg [5:0] out_slot1; reg [1:0] out_group1,rg1; reg [15:0] base_q1;
 always @(posedge clk)begin
  if(!reset_copy[2])out_v1<=0;else out_v1<=out_v;
  if(!reset_copy[6])begin out_group1<=0;out_slot1<=0;end else begin out_group1<=out_group;out_slot1<=out_slot;end
  rg1<=rg;base_q1<=base_q;
 end
 wire out_v_e=(RPIPE!=0)?out_v1:out_v; wire [5:0] out_slot_e=(RPIPE!=0)?out_slot1:out_slot;
 wire [1:0] out_group_e=(RPIPE!=0)?out_group1:out_group; wire [1:0] rg_e=(RPIPE!=0)?rg1:rg;
 wire [15:0] base_e=(RPIPE!=0)?base_q1:base_q;   // sector of a beat = base of its block, one edge later too
 wire[NPC*2-1:0]local_lstart,local_start_ok,local_raw_done,local_load_release;
 for(genvar c=0;c<NPC*2;c=c+1)begin:window_decode
  (* keep_hierarchy="yes" *) ot_hbm_dma_window_decode #(.NPC(NPC),.COPY_ID(c)) u(
   .start(start),.base(start_base_sector),.bad(bad),.running(running),.owned(owned),.ready(block_ready_c),
   .clk(clk),.start_bank_i(start_bank_i),.epoch(start_epoch),.epoch0(epoch0),.epoch1(epoch1),
   .landing_fault(landing_fault),.slot(slot_q),.group_id(group_q),
   .command_ok(command_ok),.release_flag(load_cmd[56]),.load_release(local_load_release[c]),
   .lstart(local_lstart[c]),.start_ok(local_start_ok[c]),.raw_done(local_raw_done[c]));
 end
 // ---- the four PCs of this lane ----
 wire [256*NPC-1:0] macro_data; wire [NPC-1:0] f0,f1,bad_v;
 genvar g;
 generate for(g=0;g<NPC;g=g+1)begin:pc
  // HBMc/TILES 10-22 (m8 gate: fill_ok -> seen / n0 / n1 / w_ce -131..-149 ps through the cross-slice seen OR):
  // the seen8 slices update their own seen bits from the seen-free fill_base and their own lookup (only the slice of
  // fs[5:3] can hit, so this equals fill_ok); full = &seen (== n[6]: n counted distinct accepted writes, cleared and
  // reset with seen) and the sticky fill fault is kept per slice (each fill belongs to exactly one slice).
  wire fb_epoch;
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(2400+g)) u_epoch_bank(.clk(clk),.d(fill_bank_i[g]),.q(fb_epoch));
  wire[7:0]seen_part,clear_counts0,clear_counts1,full0_part,full1_part,pbad_part; wire fill_base;
  for(genvar part=0;part<8;part=part+1)begin:seen_slice
   wire unused_clear0,unused_clear1;
   (* keep_hierarchy="yes" *) ot_hbm_dma_seen8 #(.COPY_ID(g*8+part),.BLOCK(part)) u(.clk(clk),.rst_n(rst_n),
    .begin_v_i(begin_v_i),.begin_bank_i(begin_bank_i),.start_bank_i(start_bank_i),.fill_bank_i(fill_bank_i[g]),.fill_slot_i(fill_slot_i[g*6+:6]),
    .load_bank_i(load_cmd_i[0]),.lstart(local_lstart[(g*8+part)/4]),.start_ok(local_start_ok[(g*8+part)/4]),.raw_done(local_raw_done[(g*8+part)/4]),
    .load_release(local_load_release[(g*8+part)/4]),.fill_v_i(fill_v_i[g]),.fill_base(fill_base),.seen_current(seen_part[part]),.clear0(clear_counts0[part]),.clear1(clear_counts1[part]),
    .full0(full0_part[part]),.full1(full1_part[part]),.pbad(pbad_part[part]));
  end
  wire fb=fill_bank[g]; wire [5:0] fs=fill_slot[g*6+:6];
  wire [15:0] ep=fb_epoch?epoch1:epoch0;
  wire seen_current=|seen_part;
  wire fill_hazard=(load_v&&load_cmd[0]==fb)||(raw_request&&raw_request_bank==fb);
  assign fill_base=fill_v[g] && owned[fb] && fill_epoch[g*16+:16]==ep && !fill_hazard && !landing_fault;
  // WCE_SPEC=1 (fallback): the payload write enable does not wait for the cross-slice duplicate check -- a malformed
  // duplicate fill (which latches pbad -> pcbad -> landing fault) may overwrite its slot; valid schedules unchanged.
  wire fill_ok=fill_base && (WCE_SPEC!=0 || !seen_current);
  // n counts accepted (always distinct, !seen) writes, so &seen == (n==64) == n[6]: a registered full flag
  assign f0[g]=&full0_part; assign f1[g]=&full1_part; assign bad_v[g]=|pbad_part;
  wire r_ce,r_ce_c=issue && !landing_fault && rg==g; wire [6:0] r_addr,r_addr_c={rb,rs};
  if(RPIPE!=0)begin:g_rport
   (* keep_hierarchy="yes" *) ot_hbm_dma_rport u_rport(.clk(clk),.ce_i(r_ce_c),.addr_i(r_addr_c),.ce(r_ce),.addr(r_addr));
  end else begin:g_rdirect
   assign r_ce=r_ce_c; assign r_addr=r_addr_c;
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_payload (
   .clk(clk),.r_ce_in(r_ce),.r_addr_in(r_addr),.rd_out(macro_data[g*256+:256]),
   .w_ce_in(fill_ok),.w_addr_in({fb,fs}),.wd_in(fill_data[g*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 // cross-lane status output flops
 always @(posedge clk)
  if(!rst_s) begin full0<=0;full1<=0;pcbad<=0; end
  else begin full0<=&f0;full1<=&f1;pcbad<=|bad_v; end
 // decoded constant-index group select (no runtime part-select)
 wire [255:0] sel;
 for(genvar part=0;part<16;part=part+1)begin:raw_slice
   wire[NPC*16-1:0] d;
   for(genvar pcid=0;pcid<NPC;pcid=pcid+1)assign d[pcid*16+:16]=macro_data[pcid*256+part*16+:16];
   (* keep_hierarchy="yes" *) ot_hbm_dma_raw_select #(.NPC(NPC),.COPY_ID(part)) u(.clk(clk),.group_i(rg_e),.d(d),.q(sel[part*16+:16]));
 end
 wire [15:0]sector0=(NPC==4)?base_e+{5'b0,out_slot_e,out_group_e,3'b0}:base_e+{6'b0,out_slot_e,out_group_e[0],3'b0};
 // Static read commands carry exact source ownership and output destination. No arbitration.
 reg lv0,lv1,lv2,lv3,lv4;reg[61:0]lc0,lc1,lc2,lc3,lc4;
 always @(posedge clk)begin
  if(!reset_copy[3])begin lv0<=0;lv1<=0;lv2<=0;lv3<=0;lv4<=0;end
  else begin lv0<=load_ok;lv1<=lv0;lv2<=lv1;lv3<=lv2;lv4<=lv3;end
  lc0<=load_cmd;lc1<=lc0;lc2<=lc1;lc3<=lc2;lc4<=lc3;
 end
 wire lv_e=(RPIPE!=0)?lv4:lv3; wire [61:0] lc_e=(RPIPE!=0)?lc4:lc3;
 always @(posedge clk)begin
  load_dest_bank<=lc_e[59:57];load_dest_q<=lc_e[61:60];
  load_dq[279:264]<=lc_e[48:33];
  if(!reset_copy[4])load_dq[280]<=0;else load_dq[280]<=lv_e&&!fault_c;
 end
 assign load_out_v=load_dq[280];
 wire[175:0]capture_cmd;
 wire[41:0]scatter_cmd;
 // m11 round 3: with RPIPE the 22 capture copies share their first stage per group of 6 (4 input flops instead of 22 on
 // load_cmd_i[32:25]; the census refused [30..32] at 33-36).  Same 1+RPIPE edges per copy.
 if(RPIPE!=0)begin:g_cap_tree
  wire[31:0]cap_pre;
  for(genvar g=0;g<4;g=g+1)begin:cap_pre_root
   (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(8),.COPY_ID(2400+g),.S(1)) u(.clk(clk),.d({load_cmd_i[32:30],load_cmd_i[29:25]}),.q(cap_pre[g*8+:8]));
  end
  for(genvar c=0;c<22;c=c+1)begin:cap_root
   (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(8),.COPY_ID(c),.S(RPIPE)) u(.clk(clk),.d(cap_pre[(c/6)*8+:8]),.q(capture_cmd[c*8+:8]));
  end
 end else begin:g_cap_flat
  for(genvar c=0;c<22;c=c+1)begin:cap_root
   (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(8),.COPY_ID(c),.S(1+RPIPE)) u(.clk(clk),.d({load_cmd_i[32:30],load_cmd_i[29:25]}),.q(capture_cmd[c*8+:8]));
  end
 end
 for(genvar c=0;c<6;c=c+1)begin:scatter_root
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(7),.COPY_ID(8+c),.S(1+RPIPE)) u(.clk(clk),.d({load_cmd_i[55:52],load_cmd_i[51:49]}),.q(scatter_cmd[c*7+:7]));
 end
 wire[2047:0]source_copies;
 for(genvar c=0;c<8;c=c+1)begin:source_copy
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(256),.COPY_ID(3000+c)) u(.clk(clk),.d(sel),.q(source_copies[c*256+:256]));
 end
 wire[5:0]fmt_copies;
 for(genvar c=0;c<2;c=c+1)begin:format_copy
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(3),.COPY_ID(3100+c),.S(1+RPIPE)) u(.clk(clk),.d(load_cmd_i[32:30]),.q(fmt_copies[c*3+:3]));
 end
 wire[1023:0]normalized;
 for(genvar c=0;c<512;c=c+1)begin:capture
  (* keep_hierarchy="yes" *) ot_hbm_dma_capture_pair #(.COPY_ID(c),.WORD((c%128)/16),.PAIR(c%16)) u(.clk(clk),.cmd_i(capture_cmd[(c/24)*8+:8]),.source(source_copies[(c/64)*256+:256]),.q(normalized[c*2+:2]));
 end
 wire[255:0]word_data;
 for(genvar w=0;w<8;w=w+1)for(genvar half=0;half<4;half=half+1)begin:convert_word
  (* keep_hierarchy="yes" *) ot_hbm_dma_convert_part #(.COPY_ID(w*4+half),.PART(half),.MUT(MUT)) u(.clk(clk),.fmt_i(fmt_copies[((w*4+half)/16)*3+:3]),.raw(normalized[half*256+w*32+:32]),.q(word_data[w*32+half*8+:8]));
 end
 for(genvar c=0;c<128;c=c+1)begin:scatter
  (* keep_hierarchy="yes" *) ot_hbm_dma_scatter_pair #(.COPY_ID(c),.WORD(c/16),.PAIR(c%16)) u(.clk(clk),.dest_i(scatter_cmd[(c/24)*7+:7]),.d(word_data),.q(load_dq[8+c*2+:2]));
 end
 wire[63:0]mask_cmd;
 for(genvar b=0;b<8;b=b+1)begin:mask
  (* keep_hierarchy="yes" *) ot_hbm_dma_mask #(.COPY_ID(b),.WORD(b),.X(RPIPE)) u(.clk(clk),.d({load_cmd_i[55:52],load_cmd_i[51:49]}),.q(load_dq[b]));
 end
 assign dq_c={out_v_e && !fault_c,sector0[15:3],bank_q,sel,8'hff};
endmodule

(* keep_hierarchy="yes" *)
module ot_hbm_dma_raw_select #(parameter NPC=2,COPY_ID=0)(input wire clk,input wire[1:0]group_i,input wire[NPC*16-1:0]d,output reg[15:0]q);
 (* keep="true" *)reg[1:0]group_q;
 always @(posedge clk)group_q<=group_i;
 always @*begin q=0;for(integer g=0;g<NPC;g=g+1)if(group_q==g)q=q|d[g*16+:16];end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_cmd_copy #(parameter W=8,COPY_ID=0,S=1)(input wire clk,input wire[W-1:0]d,output reg[W-1:0]q);
 if(S>1)begin:g_pre
  (* keep="true" *) reg[W-1:0]p[0:S-2];
  always @(posedge clk)begin p[0]<=d;for(integer i=1;i<S-1;i=i+1)p[i]<=p[i-1];q<=p[S-2];end
 end else begin:g_one
  always @(posedge clk)q<=d;
 end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_and2 #(parameter COPY_ID=0)(input wire a,input wire b,output wire y);
 assign y=a&b;
endmodule
// RPIPE read port: r_ce / r_addr registered beside the payload macro (HBMc/TILES3 10-22)
(* keep_hierarchy="yes" *)
module ot_hbm_dma_rport(input wire clk,input wire ce_i,input wire[6:0]addr_i,output reg ce,output reg[6:0]addr);
 always @(posedge clk)begin ce<=ce_i;addr<=addr_i;end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_capture_pair #(parameter COPY_ID=0,WORD=0,PAIR=0)(input wire clk,input wire[7:0]cmd_i,input wire[255:0]source,output reg[1:0]q);
 (* keep="true" *)reg[7:0]cmd;
 (* keep="true" *)reg[7:0]lo;
 (* keep="true" *)reg[3:0]hi;
 reg valid;
 // m11: size ends on a kept net (m10 census: capture[504] cmd[7] QN 33 loads after abc spread the decode into the
 // byte_index adder / valid compare); same function.
 (* keep="true" *) wire[2:0]size=(cmd[7:5]==0||cmd[7:5]==5)?3'd4:cmd[7:5]==1?3'd2:3'd1;
 wire[6:0]byte_index={2'd0,cmd[4:0]}+7'(WORD*size)+7'(PAIR/4);
 reg[1:0]selected;
 always @*begin
 selected=0;
 for(integer b=0;b<32;b=b+1)selected=selected|({2{lo[b%8]&&hi[b/8]}}&source[b*8+(PAIR%4)*2+:2]);
 end
 always @(posedge clk)begin
 cmd<=cmd_i;lo<=8'b1<<byte_index[2:0];hi<=4'b1<<byte_index[4:3];
 valid<=byte_index<32&&PAIR<size*4;
 q<=valid?selected:2'b00;
 end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_convert_part #(parameter COPY_ID=0,PART=0,MUT=0)(input wire clk,input wire[2:0]fmt_i,input wire[31:0]raw,output reg[7:0]q);
 (* keep="true" *)reg[2:0]fmt,f0,f1;
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction

 function automatic [31:0] decode_word(input [31:0] raw,input [2:0] fmt);
 begin
 case(fmt)
  1:decode_word={raw[15:0],16'd0};
  2:decode_word=e4m3_f(raw[7:0]);
  4:decode_word=i8_f(raw[7:0]);
  6:decode_word=raw[7:0]==255?32'h7fc00000:raw[7:0]==0?32'h00400000:{1'b0,raw[7:0],23'd0};
  default:decode_word=raw;
 endcase
 end
 endfunction

 wire[31:0]result=decode_word(raw,fmt);
 always @(posedge clk)begin
 f0<=fmt_i;f1<=f0;fmt<=f1;
 q<=result[PART*8+:8]^((MUT==1&&fmt==1&&PART==2)?8'h01:8'h00);
 end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_scatter_pair #(parameter COPY_ID=0,WORD=0,PAIR=0)(input wire clk,input wire[6:0]dest_i,input wire[255:0]d,output reg[1:0]q);
 (* keep="true" *)reg[6:0]p0,p1,p2,p3;
 integer src;
 always @*src=WORD-p3[2:0];
 always @(posedge clk)begin p0<=dest_i;p1<=p0;p2<=p1;p3<=p2;q<=(WORD>=p3[2:0]&&WORD<p3[2:0]+p3[6:3])?2'(d>>(src*32+PAIR*2)):2'b00;end
endmodule
(* keep_hierarchy="yes" *)
module ot_hbm_dma_mask #(parameter COPY_ID=0,WORD=0,X=0)(input wire clk,input wire[6:0]d,output reg q);
 (* keep="true" *)reg[6:0]p0,p1,p2,p3,p4,p5;
 wire[6:0]pl=(X!=0)?p5:p4;
 always @(posedge clk)begin p0<=d;p1<=p0;p2<=p1;p3<=p2;p4<=p3;p5<=p4;q<=WORD>=pl[2:0]&&WORD<pl[2:0]+pl[6:3];end
endmodule


(* keep_hierarchy="yes" *)
module ot_hbm_dma_seen8 #(parameter COPY_ID=0,BLOCK=0)(
 input wire clk,rst_n,begin_v_i,begin_bank_i,start_bank_i,fill_bank_i,
 input wire[5:0]fill_slot_i,input wire load_bank_i,lstart,start_ok,raw_done,load_release,fill_v_i,fill_base,
 output wire seen_current,clear0,clear1,full0,full1,output reg pbad);
 (* keep="true" *)reg rs,bv,bb,sb,fb,lb,rb,fv;
 (* keep="true" *)reg[5:0]fs;
 (* keep="true" *)reg[1:0]owned;
 reg[7:0]seen0,seen1;
 wire clear_bank=bv&&!owned[bb]&&!(lstart&&sb==bb);
 // this slice's own accepted fill (== the lane's fill_ok restricted to block BLOCK: only this slice can hit)
 wire own_ok=fill_base&&fs[5:3]==BLOCK&&!seen_current;
 always @(posedge clk)begin
 rs<=rst_n;fv<=fill_v_i;bv<=begin_v_i;bb<=begin_bank_i;sb<=start_bank_i;fb<=fill_bank_i;fs<=fill_slot_i;lb<=load_bank_i;
 if(!rs)owned<=0;
 else begin
 if(clear_bank)owned[bb]<=1;
 if(start_ok)rb<=sb;
 if(raw_done)owned[rb]<=0;
 if(load_release)owned[lb]<=0;
 end
 if(!rs)seen0<=0;
 else if(clear_bank&&!bb)seen0<=0;
 else if(own_ok&&!fb)seen0[fs[2:0]]<=1;
 if(!rs)seen1<=0;
 else if(clear_bank&&bb)seen1<=0;
 else if(own_ok&&fb)seen1[fs[2:0]]<=1;
 if(!rs)pbad<=0;
 else if(fv&&fs[5:3]==BLOCK&&!own_ok)pbad<=1;
 end
 assign clear0=clear_bank&&!bb;assign clear1=clear_bank&&bb;
 assign full0=&seen0;assign full1=&seen1;
 assign seen_current=(fs[5:3]==BLOCK)&&(fb?seen1[fs[2:0]]:seen0[fs[2:0]]);
endmodule


(* keep_hierarchy="yes" *)
module ot_hbm_dma_window_decode #(parameter NPC=2,COPY_ID=0)(
 input wire clk,start_bank_i,start,bad,running,landing_fault,
 input wire[15:0]base,epoch,epoch0,epoch1,input wire[1:0]owned,ready,
 input wire[5:0]slot,input wire[1:0]group_id,input wire command_ok,release_flag,
 output wire lstart,start_ok,raw_done,load_release);
 // Three same-edge pin captures bound the status and two byte comparisons.
 wire[2:0]bank;
 for(genvar b=0;b<3;b=b+1)begin:bank_copy
  (* keep_hierarchy="yes" *) ot_hbm_dma_cmd_copy #(.W(1),.COPY_ID(3000+COPY_ID*3+b)) u(
   .clk(clk),.d(start_bank_i),.q(bank[b]));
 end
 wire aperture_ok=base[4:0]==0&&base[12:0]<=13'(8192-512*NPC)&&(!base[15]||base[14:13]==0);
 assign lstart=start&&aperture_ok&&!bad;
 assign start_ok=lstart&&!running&&owned[bank[0]]&&ready[bank[0]]&&
   epoch[7:0]==(bank[1]?epoch1[7:0]:epoch0[7:0])&&
   epoch[15:8]==(bank[2]?epoch1[15:8]:epoch0[15:8])&&!landing_fault;
 assign load_release=command_ok&&release_flag;
 assign raw_done=running&&slot==63&&group_id==NPC-1;
endmodule

`default_nettype wire
