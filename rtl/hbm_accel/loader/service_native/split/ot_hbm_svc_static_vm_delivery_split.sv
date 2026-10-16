`default_nettype none
// HBM-V15-HARDEN 2026-10-15: structural physical partition of ot_hbm_svc_static_vm_delivery
// (one quadrant: 32 PC landing SRAMs + 8-bank dq stream into the VM).
//
// Why: the monolithic leaf puts 8,960 fill pins on one face (pin_fit 124 % of slots), spans > 600 um on one clock
// root and needs a runtime-indexed 2,048-bit group mux.  v1 (separate control leaf) failed its gate on
// combinational feed-through (start -> issue, pc_fault -> dq_v: in->out -57.9 ps): a control leaf between
// lanes is a leaf->ctl->leaf round trip every cycle.
// v2 (this file): ONE lane leaf type, hardened once, eight per quadrant. Each lane holds the four PCs that feed VM
// bank b (PC b, 8+b, 16+b, 24+b), their real 128x256 SRAMs, the local 4:1 group select and dq[b], AND a replica of
// the small begin/start/aperture/owned/epoch/running state (identical inputs -> identical state in every lane).
// The only cross-lane signals are three registered status bits per lane (all-64-slots-full per bank, PC fault),
// fanned out by the wires-only parent to every lane: one lane->lane hop per cycle, launched from flops.
// v5: launched from an output flop AND captured in a pin flop at every lane (cross-lane status latency 2 edges,
// reference STATUS_LAT=2).
// v3: lane pin registers on every input and output (+2 cycles interface latency, II=1); every output bit equals the
// monolithic module delayed exactly 2 cycles (lockstep bench tb_hbm_svc_vmdel_split_equiv.sv, LAT=2); no credit,
// ready or retry added. Lane 0 drives block_ready/busy/fault.
// Sector = base + slot*32 + group*8 + bank: base is aligned32 (aperture check), so the bank adds no carry and each
// lane appends its 3-bit bank index (port bank_id, a declared die constant per instance).
module ot_hbm_svc_static_vm_delivery_split (
 input wire clk,rst_n,begin_v,begin_bank,input wire [15:0] begin_epoch,
 input wire [31:0] fill_v,fill_bank,input wire [191:0] fill_slot,
 input wire [511:0] fill_epoch,input wire [8191:0] fill_data,
 output wire [1:0] block_ready,
 input wire start,start_bank,input wire [15:0] start_epoch,start_base_sector,
 output wire [2247:0] dq,output wire busy,output wire fault
);
 wire [7:0] full0,full1,pcbad;
 wire [1:0] br [0:7]; wire [7:0] bz,ft;
 assign block_ready=br[0]; assign busy=bz[0]; assign fault=ft[0];
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  ot_hbm_svc_vmdel_lane u_lane (.clk(clk),.clk_cap(clk),.rst_n(rst_n),.bank_id(b[2:0]),
   .begin_v_i(begin_v),.begin_bank_i(begin_bank),.begin_epoch_i(begin_epoch),
   .start_i(start),.start_bank_i(start_bank),.start_epoch_i(start_epoch),.start_base_sector_i(start_base_sector),
   .fill_v_i({fill_v[24+b],fill_v[16+b],fill_v[8+b],fill_v[b]}),
   .fill_bank_i({fill_bank[24+b],fill_bank[16+b],fill_bank[8+b],fill_bank[b]}),
   .fill_slot_i({fill_slot[(24+b)*6+:6],fill_slot[(16+b)*6+:6],fill_slot[(8+b)*6+:6],fill_slot[b*6+:6]}),
   .fill_epoch_i({fill_epoch[(24+b)*16+:16],fill_epoch[(16+b)*16+:16],fill_epoch[(8+b)*16+:16],fill_epoch[b*16+:16]}),
   .fill_data_i({fill_data[(24+b)*256+:256],fill_data[(16+b)*256+:256],fill_data[(8+b)*256+:256],fill_data[b*256+:256]}),
   .full0_all(full0),.full1_all(full1),.pcbad_all(pcbad),
   .full0(full0[b]),.full1(full1[b]),.pcbad(pcbad[b]),
   .block_ready(br[b]),.busy(bz[b]),.fault(ft[b]),.dq(dq[b*281+:281]));
 end endgenerate
endmodule

// One VM bank lane: PCs b, 8+b, 16+b, 24+b (local index g = read group), their real SRAMs, dq[b], and a replica of
// the landing/delivery control state.
// History: v3 pin registers on every begin/start/fill input and every output (LAT=2 vs the monolithic module); v4 rst_n
// pin flops; v5/v5b cross-lane status registered at both pins (reference STATUS_LAT=2); v5b CLOSED
// hv15_vmdel_lane-hv15-20b84db92 (TT +49.22 / FF +10.13) but FAILED the native pin audit: R 286.7 / spread 96.4 ps on one
// root, capture 274.2 rst_n (async clears) + 63 pins > 190 (fill_data_i 42, AND/OR-before-flop status 21), launch
// 346.6 on dq[264..266] (= bank_id strap: an in -> flop -> out chain placed at the W pins).
// ---- v6 (H-NETLIST/vmdel 10-16): calendar pattern, two related phase-0 CTS roots.
//  clk_cap: the input pin-flop band only (every input pin incl. rst_n and the bank_id strap lands on the D pin of one
//           flop on clk_cap, S/W faces); clk: the body (control, PC state, SRAMs, output flops).
//  rst_n -> D pin of ONE synchronous pin flop rst_s (no async clear on the port); the body resets SYNCHRONOUSLY from
//  rst_s (release timing unchanged: the body first updates on the 2nd edge after rst_n rises, as v4's rst_ctl).  The
//  512 seen bits are unreset: every bank is cleared by its accepted begin before any fill can be accepted (owned=0
//  after reset), so they are never observed before that clear.  Valid pin flops are plain data flops (ports are 0
//  while the die is in reset).
//  Cross-lane status: 24 plain pin flops; the 8-lane AND/OR reduction moves AFTER the flop (body logic).
//  bank_id: captured in 3 band flops, so dq[266:264] launch from N-face output flops like every other dq bit.
//  Function, LAT=2 and STATUS_LAT=2 unchanged.
module ot_hbm_svc_vmdel_lane (
 input wire clk,clk_cap,rst_n,input wire [2:0] bank_id,
 input wire begin_v_i,begin_bank_i,input wire [15:0] begin_epoch_i,
 input wire start_i,start_bank_i,input wire [15:0] start_epoch_i,start_base_sector_i,
 input wire [3:0] fill_v_i,fill_bank_i,input wire [23:0] fill_slot_i,input wire [63:0] fill_epoch_i,input wire [1023:0] fill_data_i,
 input wire [7:0] full0_all,full1_all,pcbad_all,
 output reg full0,full1,pcbad,
 output reg [1:0] block_ready,output reg busy,output reg fault,
 output reg [280:0] dq
);
 // ---- input pin-flop band (clk_cap): one flop per input pin, no logic, no async clear
 reg rst_s;
 reg begin_v,begin_bank,start,start_bank; reg [15:0] begin_epoch,start_epoch,start_base_sector;
 reg [3:0] fill_v,fill_bank; reg [23:0] fill_slot; reg [63:0] fill_epoch; reg [1023:0] fill_data;
 reg [7:0] full0_p,full1_p,pcbad_p; reg [2:0] bank_q;
 always @(posedge clk_cap) begin
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
 wire aperture_ok=start_base_sector[4:0]==0 && start_base_sector[12:0]<=13'd6144 &&
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
    if(slot_q==63 && group_q==2'd3) begin running<=0;owned[bank_r]<=0;end
    else if(group_q==2'd3)begin slot_q<=slot_q+1'b1;group_q<=0;end
    else group_q<=group_q+1'b1;
   end
  end
 end
 // ---- the four PCs of this lane ----
 wire [1023:0] macro_data; wire [3:0] f0,f1,bad_v;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:pc
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
 wire [255:0] sel=({256{out_group==2'd0}}&macro_data[0+:256])|({256{out_group==2'd1}}&macro_data[256+:256])|
                  ({256{out_group==2'd2}}&macro_data[512+:256])|({256{out_group==2'd3}}&macro_data[768+:256]);
 wire [15:0] sector0=base_q+{5'b0,out_slot,out_group,3'b0};
 assign dq_c={out_v && !fault_c,sector0[15:3],bank_q,sel,8'hff};
endmodule
`default_nettype wire
