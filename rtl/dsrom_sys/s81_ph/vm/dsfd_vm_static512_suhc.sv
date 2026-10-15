`timescale 1ns/1ps
// Four actual128b physical slices, unchanged16384x512 capacity.
// Wires-only parent: each leaf retains its own externally delivered clock.
// Compiler assigns every request and release edge; no ready/credits or waits.
// Per-slice valids and commit observations remain separate: this parent does
// not hide a late physical slice by pretending that a logical row is complete.
module dsfd_vm_static512_suhc(
 input wire [3:0] ck_rscatter,ck_return,input wire [15:0] ck_wscatter,
 input wire [127:0] ck_wcapture,ck_bank,input wire rst_n,
 input wire [47:0] ck_relay_req,ck_relay_rsp,
 input wire [3:0] rst_rscatter_n,rst_return_n,input wire [15:0] rst_wscatter_n,
 input wire [127:0] rst_wcapture_n,rst_bank_n,input wire [47:0] rst_relay_n,
 input wire [17:0] native_rq_v,input wire [251:0] native_rq_row,input wire [89:0] native_rq_slot,
 input wire [2:0] native_rq_group,input wire [11:0] aux_rq_v,input wire [167:0] aux_rq_row,
 input wire [31:0] wq_v,input wire [447:0] wq_row,input wire [511:0] wq_mask,
 input wire [16383:0] wq_data,input wire [255:0] wq_tag,
 input wire release_v,input wire [2:0] release_group,input wire [31:0] release_mask,
 input wire [17:0] native_expected_v,input wire [89:0] native_release_slot,
 output wire [71:0] native_v,output wire [9215:0] native_data,
 output wire [127:0] group_v,output wire [16383:0] group_data,output wire [11:0] group_id,
 output wire [127:0] commit_v,output wire [1151:0] commit_addr,
 output wire [511:0] commit_mask,output wire [1023:0] commit_tag,
 output wire [15:0] fault
);
 localparam integer NROW=32,SLOT_BITS=5;
 genvar s,q;generate for(s=0;s<4;s=s+1)begin:slice
  wire [4095:0] wd,rd;wire [127:0] wm;wire [31:0] rv;wire [255:0] rt;
  wire [128*NROW-1:0] gd;wire [2303:0] nd;
  for(q=0;q<32;q=q+1)begin:write_rows
   assign wd[128*q+:128]=wq_data[512*q+128*s+:128];
   assign wm[4*q+:4]=wq_mask[16*q+4*s+:4];
  end
  dsfd_vm_static_slice128_suhc u_slice(.ck_rscatter(ck_rscatter[s]),.ck_wcapture(ck_wcapture[32*s+:32]),.ck_wscatter(ck_wscatter[4*s+:4]),
   .ck_bank(ck_bank[32*s+:32]),.rst_n(rst_n),
   .rst_rscatter_n(rst_rscatter_n[s]),.rst_wcapture_n(rst_wcapture_n[32*s+:32]),.rst_wscatter_n(rst_wscatter_n[4*s+:4]),
   .rst_bank_n(rst_bank_n[32*s+:32]),.rst_relay_n(rst_relay_n[12*s+:12]),.ck_relay_req(ck_relay_req[12*s+:12]),.ck_relay_rsp(ck_relay_rsp[12*s+:12]),.native_rq_v(native_rq_v),.native_rq_row(native_rq_row),.native_rq_slot(native_rq_slot),
   .native_rq_group(native_rq_group),.aux_rq_v(aux_rq_v),.aux_rq_row(aux_rq_row),
   .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wm),.wq_data(wd),.wq_tag(wq_tag),
   .rs_v(rv),.rs_data(rd),.rs_tag(rt),.commit_v(commit_v[32*s+:32]),
   .commit_addr(commit_addr[288*s+:288]),.commit_mask(commit_mask[128*s+:128]),
   .commit_tag(commit_tag[256*s+:256]),.fault(fault[4*s+:2]));
  dsfd_vm_static_return #(.NROW(NROW)) u_return(.ck(ck_return[s]),.rst_n(rst_return_n[s]),.i_v(rv),.i_tag(rt),.i_data(rd),
   .release_v(release_v),.release_group(release_group),.release_mask(release_mask),
   .o_v(group_v[NROW*s+:NROW]),.o_data(gd),.o_group(group_id[(8-SLOT_BITS)*s+:8-SLOT_BITS]),.fault(fault[4*s+2]));
  dsfd_vm_static_suhc_return_map u_native(.i_v(group_v[32*s+:32]),.i_data(gd),
   .expected_v(native_expected_v),.release_slot(native_release_slot),
   .o_v(native_v[18*s+:18]),.o_data(nd),.fault(fault[4*s+3]));
  for(q=0;q<18;q=q+1)begin:native_rows
   assign native_data[512*q+128*s+:128]=nd[128*q+:128];
  end
  for(q=0;q<NROW;q=q+1)begin:read_rows
`ifdef OT_VM_512_MUT_SWAP_SLICES
   assign group_data[512*q+128*((s+1)%4)+:128]=gd[128*q+:128];
`else
   assign group_data[512*q+128*s+:128]=gd[128*q+:128];
`endif
  end
 end endgenerate
endmodule
