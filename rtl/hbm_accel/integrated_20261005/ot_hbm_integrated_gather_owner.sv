`timescale 1ns/1ps
// Additive combined parent hook. Native/index/SU/W2 share ONE actual SM0
// request/response route upstream of existing AW3 CDC. All caller and provider
// signals remain real enclosing ports; no grants/ready/values are constant-tied.
// Installer/source phase and original W15 held-caller enrollment remain required.
module ot_hbm_integrated_gather_owner #(
 parameter integer ENABLE=0,VM_AW=0
)(
 input wire clk,por_n,
 input wire desc_v, output wire desc_r, input wire [2:0] desc_index,
 input wire [63:0] desc_data,
 input wire start_v, output wire start_r, input wire installed_book_valid,
 input wire [31:0] job, input wire [3:0] gen,
 input wire [16:0] token, input wire [19:0] pos,
 output wire retained,arena_visible,sink_visible,fault,
 output wire [31:0] bound_arena_base,bound_arena_limit,
 // Existing checked shared-borrow grant and existing protected retained frame.
 // Export only: no second owner seat, grant source, or completion authority.
 output wire formatter_lease_valid,output wire [72:0] formatter_lease_frame,
 // All addresses here are BYTE addresses. kind: 0 source read, 1 score
 // store, 2 ID store, 3 formatter read, 4 final ID sink store.
 input wire req_v, output wire req_r, input wire [2:0] req_kind,
 input wire [31:0] req_addr, input wire [15:0] req_tag,
 input wire [6:0] req_rank, input wire [5:0] req_word,
 input wire [511:0] req_data,
 input wire [31:0] req_job, input wire [3:0] req_gen,
 input wire [16:0] req_token, input wire [19:0] req_pos,
 output wire rsp_v, input wire rsp_r, output wire [511:0] rsp_data,
 output wire [31:0] rsp_addr, output wire [15:0] rsp_tag,
 output wire [2:0] rsp_kind, output wire rsp_checked,
 output wire [31:0] held_job, output wire [3:0] held_gen,
 output wire [16:0] held_token, output wire [19:0] held_pos,
 // Connect to shared borrower's existing SM-side AW3 CDC, not a new port.
 output wire m_req_v, input wire m_req_rdy, output wire m_req_we,
 output wire [31:0] m_req_addr, output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb, output wire [15:0] m_req_tag,
 input wire m_rsp_v, output wire m_rsp_rdy, input wire m_rsp_we,
 input wire [255:0] m_rsp_data, input wire [15:0] m_rsp_tag,
 input wire release_v, output wire release_r,
 input wire [31:0] release_job, input wire [3:0] release_gen,
 input wire [16:0] release_token, input wire [19:0] release_pos,
 input wire result_published,source_reverse_done,
 // Existing native, SU and W2 requesters respectively; no new provider port.
 input wire native_clients_drained,cdc_drained,provider_fault,
 input wire [3:0] observe_req,observe_rsp,observe_req_we,observe_rsp_we,
 input wire [63:0] observe_req_tag,observe_rsp_tag,
 input wire [3:0] return_offer,output wire [3:0] response_authorized,
 input wire [31:0] native_job,input wire [3:0] native_gen,
 input wire [16:0] native_token,input wire [19:0] native_pos,
 output wire native_credit_empty,shared_idle,
 input wire [1:0] peer_lease_v,peer_quiet,peer_release_v,
 input wire [63:0] peer_lease_job,peer_release_job,
 input wire [7:0] peer_lease_gen,peer_release_gen,
 input wire [33:0] peer_lease_token,peer_release_token,
 input wire [39:0] peer_lease_pos,peer_release_pos,
 output wire [1:0] peer_lease_granted,peer_release_r,
 input wire [2:0] p_req_v,p_req_we,output wire [2:0] p_req_rdy,
 input wire [95:0] p_req_addr,p_req_wstrb,input wire [767:0] p_req_wdata,
 input wire [47:0] p_req_tag,output wire [2:0] p_rsp_v,p_rsp_we,
 input wire [2:0] p_rsp_rdy,output wire [47:0] p_rsp_tag,
 output wire [767:0] p_rsp_data
);
 wire borrow_v,borrow_granted,borrow_fault,borrow_release,borrow_release_ack;
 wire bridge_fault,arb_fault;
 wire b_req_v,b_req_rdy,b_req_we,b_rsp_v,b_rsp_rdy,b_rsp_we;
 wire [31:0] b_req_addr,b_req_wstrb;wire [255:0] b_req_wdata,b_rsp_data;
 wire [15:0] b_req_tag,b_rsp_tag;
 wire [2:0] grants,releases;
 wire [3:0] all_req_rdy,all_rsp_v,all_rsp_we;
 wire [63:0] all_rsp_tag;wire [1023:0] all_rsp_data;
 assign borrow_granted=grants[0];assign borrow_release_ack=releases[0];
 assign borrow_fault=arb_fault|provider_fault;
 assign formatter_lease_valid=ENABLE&&borrow_granted&&retained&&!fault;
 assign formatter_lease_frame={held_pos,held_token,held_gen,held_job};
 assign fault=bridge_fault|arb_fault|(ENABLE!=0&&provider_fault);
 assign peer_lease_granted=grants[2:1];assign peer_release_r=releases[2:1];
 assign p_req_rdy={all_req_rdy[3:2],all_req_rdy[0]};assign b_req_rdy=all_req_rdy[1];
 assign p_rsp_v={all_rsp_v[3:2],all_rsp_v[0]};assign b_rsp_v=all_rsp_v[1];
 assign p_rsp_we={all_rsp_we[3:2],all_rsp_we[0]};assign b_rsp_we=all_rsp_we[1];
 assign p_rsp_tag={all_rsp_tag[63:32],all_rsp_tag[15:0]};assign b_rsp_tag=all_rsp_tag[31:16];
 assign p_rsp_data={all_rsp_data[1023:512],all_rsp_data[255:0]};assign b_rsp_data=all_rsp_data[511:256];
 ot_hbm_integrated_gather_bridge #(.ENABLE(ENABLE),.VM_AW(VM_AW)) u_bridge (
  .fault(bridge_fault),.m_req_v(b_req_v),.m_req_rdy(b_req_rdy),.m_req_we(b_req_we),
  .m_req_addr(b_req_addr),.m_req_wdata(b_req_wdata),.m_req_wstrb(b_req_wstrb),.m_req_tag(b_req_tag),
  .m_rsp_v(b_rsp_v),.m_rsp_rdy(b_rsp_rdy),.m_rsp_we(b_rsp_we),.m_rsp_tag(b_rsp_tag),.m_rsp_data(b_rsp_data),.*);
 ot_hbm_integrated_sm0_borrow #(.ENABLE(ENABLE)) u_shared_owner (
  .clk(clk),.por_n(por_n),.native_clients_drained(native_clients_drained),.cdc_drained(cdc_drained),
  .lease_v({peer_lease_v,borrow_v}),.borrower_quiet({peer_quiet,!retained}),
  .lease_job({peer_lease_job,job}),.lease_gen({peer_lease_gen,gen}),
  .lease_token({peer_lease_token,token}),.lease_pos({peer_lease_pos,pos}),.lease_granted(grants),
  .release_v({peer_release_v,borrow_release}),.release_r(releases),
  .release_job({peer_release_job,held_job}),.release_gen({peer_release_gen,held_gen}),
  .release_token({peer_release_token,held_token}),.release_pos({peer_release_pos,held_pos}),
  .req_v({p_req_v[2:1],b_req_v,p_req_v[0]}),.req_rdy(all_req_rdy),
  .req_we({p_req_we[2:1],b_req_we,p_req_we[0]}),
  .req_addr({p_req_addr[95:32],b_req_addr,p_req_addr[31:0]}),
  .req_wdata({p_req_wdata[767:256],b_req_wdata,p_req_wdata[255:0]}),
  .req_wstrb({p_req_wstrb[95:32],b_req_wstrb,p_req_wstrb[31:0]}),
  .req_tag({p_req_tag[47:16],b_req_tag,p_req_tag[15:0]}),
  .rsp_v(all_rsp_v),.rsp_rdy({p_rsp_rdy[2:1],b_rsp_rdy,p_rsp_rdy[0]}),
  .rsp_we(all_rsp_we),.rsp_tag(all_rsp_tag),.rsp_data(all_rsp_data),
  .idle(shared_idle),.fault(arb_fault),.*);
endmodule
