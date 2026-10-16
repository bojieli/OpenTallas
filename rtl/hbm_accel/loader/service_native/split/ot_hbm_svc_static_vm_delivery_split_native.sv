`default_nettype none
// HBM-V15-HARDEN 2026-10-15 physical clock ownership: each lane has its own die clock entry.
// These are related, phase-compensated clocks; independent asynchronous operation is not supported.
// Source lane module is supplied by ot_hbm_svc_static_vm_delivery_split.sv.
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
// Register boundaries, cycle timing and every output bit equal the monolithic module (lockstep equivalence bench
// tb_hbm_svc_vmdel_split_equiv.sv); no credit, ready or retry added. Lane 0 drives block_ready/busy/fault.
// Sector = base + slot*32 + group*8 + bank: base is aligned32 (aperture check), so the bank adds no carry and each
// lane appends its 3-bit bank index (port bank_id, a declared die constant per instance).
module ot_hbm_svc_static_vm_delivery_split_native (
 input wire [7:0] clk_lane,
 input wire rst_n,begin_v,begin_bank,input wire [15:0] begin_epoch,
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
  ot_hbm_svc_vmdel_lane u_lane (.clk(clk_lane[b]),.rst_n(rst_n),.bank_id(b[2:0]),
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

`default_nettype wire
