`default_nettype none
// HBM-V15-HARDEN 2026-10-15: structural physical partition of ot_hbm_svc_static_vm_delivery
// (one quadrant: 32 PC landing SRAMs + 8-bank dq stream into the VM).
//
// Why: the monolithic leaf puts 8,960 fill pins on one face (pin_fit 124 % of slots), spans > 600 um on one clock
// root and needs a runtime-indexed 2,048-bit group mux.  Here the SAME logic is cut along the VM bank axis:
//   ot_hbm_svc_vmdel_bank (x8, hardened once): the four PCs that feed VM bank b (PC b, 8+b, 16+b, 24+b), their
//     real 128x256 SRAMs, seen/fault state, the local 4:1 group select and the 281-bit dq[b] lane;
//   ot_hbm_svc_vmdel_ctl  (x1): begin/start/aperture, owned/epoch/running/slot/group state, block_ready/fault.
// The parent is wires only.  Register boundaries, cycle timing and every output bit are identical to the
// monolithic module (lockstep equivalence bench tb_hbm_svc_vmdel_split_equiv.sv); no credit, ready or retry added.
// Sector = base + slot*32 + group*8 + bank: base is aligned32 (aperture check), so the bank adds no carry and each
// bank leaf appends its 3-bit bank index (port bank_id, a declared die constant per instance).
module ot_hbm_svc_static_vm_delivery_split (
 input wire clk,rst_n,begin_v,begin_bank,input wire [15:0] begin_epoch,
 input wire [31:0] fill_v,fill_bank,input wire [191:0] fill_slot,
 input wire [511:0] fill_epoch,input wire [8191:0] fill_data,
 output wire [1:0] block_ready,
 input wire start,start_bank,input wire [15:0] start_epoch,start_base_sector,
 output wire [2247:0] dq,output wire busy,output wire fault
);
 wire [1:0] owned; wire [31:0] epochs; wire issue,rb,clear_bank,dq_v,landing_fault; wire [1:0] rg,out_group;
 wire [5:0] rs; wire [12:0] sector_hi; wire [7:0] full0,full1,pc_fault;
 ot_hbm_svc_vmdel_ctl u_ctl (.clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
  .start(start),.start_bank(start_bank),.start_epoch(start_epoch),.start_base_sector(start_base_sector),
  .full0(full0),.full1(full1),.pc_fault(pc_fault),.block_ready(block_ready),.busy(busy),.fault(fault),
  .owned(owned),.epochs(epochs),.issue(issue),.rb(rb),.rg(rg),.rs(rs),.clear_bank(clear_bank),
  .landing_fault(landing_fault),.dq_v(dq_v),.out_group(out_group),.sector_hi(sector_hi));
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:g_bank
  ot_hbm_svc_vmdel_bank u_bank (.clk(clk),.rst_n(rst_n),.bank_id(b[2:0]),
   .fill_v({fill_v[24+b],fill_v[16+b],fill_v[8+b],fill_v[b]}),
   .fill_bank({fill_bank[24+b],fill_bank[16+b],fill_bank[8+b],fill_bank[b]}),
   .fill_slot({fill_slot[(24+b)*6+:6],fill_slot[(16+b)*6+:6],fill_slot[(8+b)*6+:6],fill_slot[b*6+:6]}),
   .fill_epoch({fill_epoch[(24+b)*16+:16],fill_epoch[(16+b)*16+:16],fill_epoch[(8+b)*16+:16],fill_epoch[b*16+:16]}),
   .fill_data({fill_data[(24+b)*256+:256],fill_data[(16+b)*256+:256],fill_data[(8+b)*256+:256],fill_data[b*256+:256]}),
   .owned(owned),.epochs(epochs),.issue(issue),.rb(rb),.rg(rg),.rs(rs),.clear_bank(clear_bank),.begin_bank(begin_bank),
   .landing_fault(landing_fault),.dq_v(dq_v),.out_group(out_group),.sector_hi(sector_hi),
   .full0(full0[b]),.full1(full1[b]),.pc_fault(pc_fault[b]),.dq(dq[b*281+:281]));
 end endgenerate
endmodule

// Control: the landing's begin/start/running state and the delivery's aperture/base state, bit-for-bit.
module ot_hbm_svc_vmdel_ctl (
 input wire clk,rst_n,begin_v,begin_bank,input wire [15:0] begin_epoch,
 input wire start,start_bank,input wire [15:0] start_epoch,start_base_sector,
 input wire [7:0] full0,full1,pc_fault,
 output wire [1:0] block_ready,output wire busy,output wire fault,
 output reg [1:0] owned,output wire [31:0] epochs,output wire issue,output wire rb,output wire [1:0] rg,
 output wire [5:0] rs,output wire clear_bank,output wire landing_fault,output wire dq_v,
 output reg [1:0] out_group,output wire [12:0] sector_hi
);
 reg [15:0] epoch0,epoch1,base_q; reg running,bank_q,sticky,bad,out_v; reg [5:0] slot_q,out_slot; reg [1:0] group_q;
 assign epochs={epoch1,epoch0};
 assign landing_fault=sticky || |pc_fault;
 assign fault=bad||landing_fault;
 assign busy=running;
 assign block_ready={owned[1] && (&full1),owned[0] && (&full0)};
 wire aperture_ok=start_base_sector[4:0]==0 && start_base_sector[12:0]<=13'd6144 &&
                  (!start_base_sector[15] || start_base_sector[14:13]==0);
 wire lstart=start && aperture_ok && !bad;
 wire start_ok=lstart && !running && owned[start_bank] && block_ready[start_bank] &&
               start_epoch==(start_bank?epoch1:epoch0) && !landing_fault;
 assign issue=running || start_ok;
 assign rb=running ? bank_q : start_bank;
 assign rg=running ? group_q : 2'd0;
 assign rs=running ? slot_q : 6'd0;
 assign clear_bank=begin_v && !owned[begin_bank] && !(lstart && start_bank==begin_bank);
 assign dq_v=out_v && !fault;
 wire [15:0] sector0=base_q+{5'b0,out_slot,out_group,3'b0};
 assign sector_hi=sector0[15:3];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin base_q<=0;bad<=0;end
 else if(start)begin
  if(!aperture_ok || busy)bad<=1;
  else base_q<=start_base_sector;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   owned<=0;epoch0<=0;epoch1<=0;running<=0;bank_q<=0;slot_q<=0;
   sticky<=0;group_q<=0;out_group<=0;out_v<=0;out_slot<=0;
  end else begin
   out_v<=issue && !landing_fault;out_slot<=rs;out_group<=rg;
   if(begin_v) begin
    if(owned[begin_bank] || (lstart && start_bank==begin_bank)) sticky<=1;
    else begin owned[begin_bank]<=1;if(begin_bank)epoch1<=begin_epoch;else epoch0<=begin_epoch;end
   end
   if(lstart && !start_ok) sticky<=1;
   if(start_ok) begin running<=1;bank_q<=start_bank;slot_q<=6'd0;group_q<=2'd1;end
   if(running) begin
    if(slot_q==63 && group_q==2'd3) begin running<=0;owned[bank_q]<=0;end
    else if(group_q==2'd3)begin slot_q<=slot_q+1'b1;group_q<=0;end
    else group_q<=group_q+1'b1;
   end
  end
 end
endmodule

// One VM bank lane: PCs b, 8+b, 16+b, 24+b (local index g = group), their real SRAMs and the dq[b] lane.
module ot_hbm_svc_vmdel_bank (
 input wire clk,rst_n,input wire [2:0] bank_id,
 input wire [3:0] fill_v,fill_bank,input wire [23:0] fill_slot,input wire [63:0] fill_epoch,input wire [1023:0] fill_data,
 input wire [1:0] owned,input wire [31:0] epochs,input wire issue,rb,input wire [1:0] rg,input wire [5:0] rs,
 input wire clear_bank,begin_bank,landing_fault,dq_v,input wire [1:0] out_group,input wire [12:0] sector_hi,
 output wire full0,full1,pc_fault,output wire [280:0] dq
);
 wire [1023:0] macro_data; wire [3:0] f0,f1,bad_v;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:pc
  reg [63:0] seen0,seen1; reg bad;
  wire fb=fill_bank[g]; wire [5:0] fs=fill_slot[g*6+:6];
  wire [15:0] ep=fb?epochs[31:16]:epochs[15:0];
  wire [63:0] seen_fb=fb?seen1:seen0;
  wire fill_ok=fill_v[g] && owned[fb] && fill_epoch[g*16+:16]==ep && !seen_fb[fs] && !(issue && rb==fb) && !landing_fault;
  assign f0[g]=&seen0; assign f1[g]=&seen1; assign bad_v[g]=bad;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin seen0<=0;seen1<=0;bad<=0;end
   else begin
    if(clear_bank && !begin_bank)seen0<=0;
    if(clear_bank && begin_bank)seen1<=0;
    if(fill_v[g]&&!fill_ok)bad<=1;
    if(fill_ok && !fb)seen0[fs]<=1;
    if(fill_ok && fb)seen1[fs]<=1;
   end
  end
  ot_sram_1r1w_128x256_m1_r2c2 u_payload (
   .clk(clk),.r_ce_in(issue && !landing_fault && rg==g),.r_addr_in({rb,rs}),.rd_out(macro_data[g*256+:256]),
   .w_ce_in(fill_ok),.w_addr_in({fb,fs}),.wd_in(fill_data[g*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 assign full0=&f0; assign full1=&f1; assign pc_fault=|bad_v;
 // decoded constant-index group select (no runtime part-select)
 wire [255:0] sel=({256{out_group==2'd0}}&macro_data[0+:256])|({256{out_group==2'd1}}&macro_data[256+:256])|
                  ({256{out_group==2'd2}}&macro_data[512+:256])|({256{out_group==2'd3}}&macro_data[768+:256]);
 assign dq={dq_v,sector_hi,bank_id,sel,8'hff};
endmodule
`default_nettype wire
