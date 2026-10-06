`timescale 1ns/1ps
// Successor of retained w2_parent_on_elaboration/r3 source; historic snapshot unchanged.
// EXEC-only combined successor: one shared SM0 owner. Standalone bf3 sources untouched.
// Existing executor and provider interfaces; opt-in, physical unqualified.
// Existing LAUNCH PC bank and SM0 IM64 loader, unchanged doorbell/CPL authority.
// Source-selected DS cluster with real SM/memory/collective ports exposed on
// clk_sm for the DSpark sequencer. Host16/rings are intentionally not in this
// path. Token17 reaches UR0 and actual RESULT17; no truncation or synthetic ACK.
module ot_ds_hbm_cluster20_integrated #(
 parameter integer COMBINED_ENABLE=0,SFU_C12_ENABLE=0,SFU_NATIVE_VM_ENABLE=0,NORM_C12_ENABLE=0,NORM_NATIVE_VM_ENABLE=0,NORM_NATIVE_INPUT_CP=0,SU_ENABLE=0,SU_REGISTERED_OUTPUTS=0,SU_REGISTERED_STATUS=0,SU_REGISTERED_BOUNDARY=0,SU_BALANCED_OWNER_BOUNDARY=0,SU_FOUR_COMBINATIONAL_CUTS=0,SU_FAST_OWNER_FRONTIER=0,SU_PARALLEL_PHASE_VALIDATION=0,SU_PROVIDER_ADAPTER=0,W2_RESULT_ENABLE=0,W2_SECTOR_ENABLE=0,FORMATTER_ENABLE=0,NORMAL_GATHER_ENABLE=0,LOCAL_CP_RESET_ENABLE=0,VM_AW=0,
 parameter integer NORM_KIND=0,NORM_N=64,NORM_D=5120,NORM_RD=0,NORM_AW=24,NORM_PUBLISH_QUANT=1,
 parameter integer ENABLE=0, TW=17, PW=20, CONTEXT_POSITIONS=1048576, ND=2, NSM=2, NL=128, IMW=14,
 parameter integer CB=8, NS=2, NPC=2, MEM_WORDS=2097152,
 parameter integer SW_PIPE=8, USE_W2=0, HAS_DIV=1, HAS_BD=1,
 parameter integer W2_PROTECTED_TRANSACTION_PIPELINE=0
)(
 input wire por_n, clk_host, clk_sm, clk_mem, clk_link,
 // Local reset is deferred; it never resets shared credit or the provider.
 input wire [ND-1:0] cp_reset_req,output wire [ND-1:0] cp_reset_ack,
 input wire [ND-1:0] cmd_we,
 input wire [ND*CB-1:0] cmd_addr,
 input wire [ND*64-1:0] cmd_wdata,
 input wire [ND-1:0] db_v, output wire [ND-1:0] db_rdy,
 input wire [ND*TW-1:0] db_token,
 input wire [ND*PW-1:0] db_pos,
 input wire [ND*32-1:0] db_job,
 input wire [ND*4-1:0] db_generation,
 output wire [ND-1:0] cpl_v, input wire [ND-1:0] cpl_rdy,
 output wire [ND*(TW+PW+72)-1:0] cpl_data,
 input wire [ND*NSM-1:0] im_we,
 input wire [IMW-1:0] im_addr, input wire [63:0] im_data,
 // Actual finite SFU operation caller. Full73 must match the held CP context;
 // accepted exclusive allocation is explicit, never inferred from an address.
 input wire [ND-1:0] sfu_enroll_v,sfu_allocation_valid,sfu_publication_r,
 input wire [ND*73-1:0] sfu_enroll_frame,sfu_allocation_frame,sfu_publication_owner,
 input wire [ND*32-1:0] sfu_pc,sfu_op,sfu_source_addr,sfu_dest_addr,
 input wire [ND*32-1:0] sfu_source_base,sfu_source_limit,sfu_dest_base,sfu_dest_limit,sfu_local_tag,
 input wire [ND*16-1:0] sfu_source,
 input wire [ND*9-1:0] sfu_expert,sfu_count,input wire [ND-1:0] sfu_matrix,
 input wire [ND*12-1:0] sfu_row,input wire [ND*3-1:0] sfu_fn,
 output wire [ND-1:0] sfu_enroll_r,sfu_publication_v,sfu_retained,sfu_fault,sfu_warm_ack,
 output wire [ND*73-1:0] sfu_held_frame,
 // Native VM root caller ABI, one existing 32-SRAM root per die.
 input wire [ND*1-1:0] sfu_vm_bind_v,
 output wire [ND*1-1:0] sfu_vm_bind_r,
 input wire [ND*73-1:0] sfu_vm_bind_frame,
 input wire [ND*7-1:0] sfu_vm_bind_rank,
 input wire [ND*32-1:0] sfu_vm_bind_base,
 input wire [ND*32-1:0] sfu_vm_bind_span,
 input wire [ND*1-1:0] sfu_vm_retire_v,
 output wire [ND*1-1:0] sfu_vm_retire_r,
 input wire [ND*73-1:0] sfu_vm_retire_frame,
 output wire [ND*73-1:0] sfu_vm_held_frame,
 output wire [ND*1-1:0] sfu_vm_retained,
 output wire [ND*1-1:0] sfu_vm_warm_ack,
 output wire [ND*1-1:0] sfu_vm_fault,
 input wire [ND*1-1:0] sfu_vm_activation_wr_v,
 output wire [ND*1-1:0] sfu_vm_activation_wr_r,
 input wire [ND*73-1:0] sfu_vm_activation_wr_frame,
 input wire [ND*1-1:0] sfu_vm_activation_wr_bank,
 input wire [ND*7-1:0] sfu_vm_activation_wr_addr,
 input wire [ND*2063-1:0] sfu_vm_activation_wr_data,
 input wire [ND*192-1:0] sfu_vm_activation_wr_owner,
 output wire [ND*1-1:0] sfu_vm_activation_ACK_v,
 input wire [ND*1-1:0] sfu_vm_activation_ACK_r,
 output wire [ND*73-1:0] sfu_vm_activation_ACK_frame,
 output wire [ND*192-1:0] sfu_vm_activation_ACK_owner,
 input wire [ND*1-1:0] sfu_vm_activation_rd_v,
 output wire [ND*1-1:0] sfu_vm_activation_rd_r,
 input wire [ND*73-1:0] sfu_vm_activation_rd_frame,
 input wire [ND*1-1:0] sfu_vm_activation_rd_bank,
 input wire [ND*7-1:0] sfu_vm_activation_rd_addr,
 input wire [ND*192-1:0] sfu_vm_activation_rd_owner,
 output wire [ND*4-1:0] sfu_vm_tap_v,
 input wire [ND*4-1:0] sfu_vm_tap_r,
 output wire [ND*8252-1:0] sfu_vm_tap_data,
 output wire [ND*768-1:0] sfu_vm_tap_owner,
 output wire [ND*292-1:0] sfu_vm_tap_frame,
 output wire [ND*4-1:0] sfu_vm_tap_source_clk,
 input wire [ND*4-1:0] sfu_vm_tap_ACK_v,
 output wire [ND*4-1:0] sfu_vm_tap_ACK_r,
 input wire [ND*768-1:0] sfu_vm_tap_ACK_owner,
 input wire [ND*292-1:0] sfu_vm_tap_ACK_frame,
 output wire [ND*1-1:0] sfu_vm_activation_release,
 input wire [ND*1-1:0] sfu_vm_activation_release_r,
 output wire [ND*73-1:0] sfu_vm_activation_release_frame,
 output wire [ND*192-1:0] sfu_vm_activation_release_owner,
 input wire [ND*1-1:0] sfu_vm_su_pub_v,
 output wire [ND*1-1:0] sfu_vm_su_pub_r,
 input wire [ND*73-1:0] sfu_vm_su_pub_frame,
 input wire [ND*32-1:0] sfu_vm_su_pub_addr,
 input wire [ND*1024-1:0] sfu_vm_su_pub_data,
 output wire [ND*1-1:0] sfu_vm_su_ACK_v,
 input wire [ND*1-1:0] sfu_vm_su_ACK_r,
 output wire [ND*32-1:0] sfu_vm_publication_ACK_addr,
 output wire [ND*73-1:0] sfu_vm_publication_ACK_frame,
 input wire [ND*1-1:0] sfu_vm_index_read_v,
 output wire [ND*1-1:0] sfu_vm_index_read_r,
 input wire [ND*73-1:0] sfu_vm_index_read_frame,
 input wire [ND*7-1:0] sfu_vm_index_read_rank,
 input wire [ND*32-1:0] sfu_vm_index_read_addr,
 input wire [ND*6-1:0] sfu_vm_index_read_words,
 input wire [ND*8-1:0] sfu_vm_index_read_tag,
 output wire [ND*1-1:0] sfu_vm_index_rsp_v,
 input wire [ND*1-1:0] sfu_vm_index_rsp_r,
 output wire [ND*1024-1:0] sfu_vm_index_rsp_data,
 output wire [ND*8-1:0] sfu_vm_index_rsp_tag,
 output wire [ND*73-1:0] sfu_vm_index_rsp_frame,
 output wire [ND*7-1:0] sfu_vm_index_rsp_rank,
 // Actual selected norm endpoint; real clock-held vectorVM supplier ABI.
 output wire [ND*(1)-1:0] norm_warm_ack,
 input wire [ND*(1)-1:0] norm_enroll_v,
 output wire [ND*(1)-1:0] norm_enroll_r,
 input wire [ND*(72+1)-1:0] norm_enroll_frame,
 input wire [ND*(31+1)-1:0] norm_enroll_pc,
 input wire [ND*(31+1)-1:0] norm_enroll_op,
 input wire [ND*(15+1)-1:0] norm_enroll_source,
 input wire [ND*(8+1)-1:0] norm_enroll_expert,
 input wire [ND*(1)-1:0] norm_enroll_matrix,
 input wire [ND*(11+1)-1:0] norm_enroll_row,
 input wire [ND*(8+1)-1:0] norm_enroll_count,
 input wire [ND*(1)-1:0] norm_allocation_valid,
 input wire [ND*(72+1)-1:0] norm_allocation_frame,
 input wire [ND*(1)-1:0] norm_landing_reserved,
 input wire [ND*(72+1)-1:0] norm_landing_frame,
 input wire [ND*(1)-1:0] norm_provider_drained,
 input wire [ND*(1)-1:0] norm_publication_checked,
 input wire [ND*(72+1)-1:0] norm_publication_frame,
 output wire [ND*(1)-1:0] norm_publication_v,
 input wire [ND*(1)-1:0] norm_publication_r,
 input wire [ND*(72+1)-1:0] norm_publication_owner,
 input wire [ND*(NORM_AW-1+1)-1:0] norm_xbase,
 input wire [ND*(NORM_AW-1+1)-1:0] norm_ubase,
 input wire [ND*(NORM_AW-1+1)-1:0] norm_wbase,
 input wire [ND*(NORM_AW-1+1)-1:0] norm_ybase,
 input wire [ND*(NORM_AW-1+1)-1:0] norm_gain_base,
 input wire [ND*(511+1)-1:0] norm_comb,
 input wire [ND*(127+1)-1:0] norm_post_pre,
 input wire [ND*(31+1)-1:0] norm_n_f,
 input wire [ND*(31+1)-1:0] norm_eps,
 input wire [ND*(31+1)-1:0] norm_lim,
 input wire [ND*((NORM_RD?NORM_RD/2:1)*32)-1:0] norm_cos_t,
 input wire [ND*((NORM_RD?NORM_RD/2:1)*32)-1:0] norm_sin_t,
 output wire [ND*(4*NORM_N*NORM_AW-1+1)-1:0] norm_rd_addr,
 output wire [ND*(4*NORM_N-1+1)-1:0] norm_rd_re,
 output wire [ND*(8*NORM_N-1+1)-1:0] norm_rd_src,
 input wire [ND*(4*NORM_N*32-1+1)-1:0] norm_rd_q,
 output wire [ND*(NORM_N-1+1)-1:0] norm_vm_we,
 output wire [ND*(NORM_N*NORM_AW-1+1)-1:0] norm_vm_waddr,
 output wire [ND*(NORM_N*32-1+1)-1:0] norm_vm_wdata,
 output wire [ND*(1)-1:0] norm_q_valid,
 output wire [ND*(7+1)-1:0] norm_q_index,
 output wire [ND*(NORM_N*8-1+1)-1:0] norm_q_codes,
 output wire [ND*((NORM_N/32)*10-1+1)-1:0] norm_q_exp,
 output wire [ND*(NORM_N*16-1+1)-1:0] norm_q_bf16,
 output wire [ND*(15+1)-1:0] norm_reserve_events,
 output wire [ND*(72+1)-1:0] norm_held_frame,
 output wire [ND*(1)-1:0] norm_retained,
 output wire [ND*(1)-1:0] norm_fault,
 output wire [ND*(1)-1:0] norm_ce,
 output wire [ND*(1)-1:0] norm_due,
 // Owned combined callbacks. Descriptor/GO must originate from the actual
 // installed recipe; absent 96x512 source/entry remains compiler-failclosed.
 input wire [ND-1:0] gather_desc_v,gather_start_v,gather_book_valid,gather_req_v,gather_rsp_r,
 input wire [ND*3-1:0] gather_desc_index,input wire [ND*64-1:0] gather_desc_data,
 input wire [ND*649-1:0] gather_req,
 output wire [ND-1:0] gather_desc_r,gather_start_r,gather_req_r,gather_rsp_v,
 output wire [ND*637-1:0] gather_rsp,
 input wire [ND-1:0] gather_release_v,gather_result_published,gather_reverse_done,
 input wire [ND*73-1:0] gather_release_frame,output wire [ND-1:0] gather_release_r,
 output wire [ND-1:0] gather_retained,gather_arena_visible,gather_sink_visible,
 // Original normal W15 synchronous VM / collective ports; no ready/data ties.
 input wire [ND-1:0] normal_go,normal_id_plane,normal_e_ready,normal_o_valid,normal_o_last,normal_o_err,normal_engine_fault,
 input wire [ND*16-1:0] normal_command_tag,input wire [ND*32-1:0] normal_source_word,
 input wire [ND*512-1:0] normal_vm_rq,normal_o_data,input wire [ND*7-1:0] normal_o_rank,
 output wire [ND-1:0] normal_busy,normal_done,normal_vm_re,normal_e_valid,normal_e_last,normal_e_mode,normal_o_ready,
 output wire [ND*32-1:0] normal_vm_raddr,output wire [ND*512-1:0] normal_e_data,output wire [ND*16-1:0] normal_e_tag,
 // Ordered adapter request85 low tag16/word6/rank7/pos20/gen4/job32.
 // Response599 low UE1/checked1/data512/tag16/word6/rank7/pos20/gen4/job32.
 input wire [ND-1:0] formatter_start_v,index_pair_v,index_pairs_r,formatter_release_v,
 // TOKEN comes from the retained request caller, not the live CP launch.
 input wire [ND*85-1:0] index_pair,input wire [ND*17-1:0] index_pair_token17,
 output wire [ND-1:0] formatter_start_r,index_pair_r,index_pairs_v,formatter_release_r,
 output wire [ND*599-1:0] index_pairs,output wire [ND*73-1:0] index_pairs_frame73,
 // Existing caller rv/rop/rrow NC8 fields, held installed output extents.
 input wire [ND-1:0] w2_reserve_v,w2_output_installed,w2_pair_op,w2_result_v,w2_native_done,w2_assembly_drained,
 input wire [ND*2-1:0] w2_rows_a,w2_rows_b,
 input wire [ND*32-1:0] w2_op_a,w2_op_b,w2_output_base_a,w2_output_limit_a,w2_output_base_b,w2_output_limit_b,w2_result_op,
 input wire [ND*16-1:0] w2_output_tag,input wire [ND*12-1:0] w2_result_row,
 input wire [ND*256-1:0] w2_result_data,
 output wire [ND-1:0] w2_reserve_r,w2_source_permit,w2_output_done,
 input wire [ND-1:0] w2_lease_v,w2_release_v,w2_quiet,w2_req_v,w2_rsp_r,
 input wire [ND*73-1:0] w2_lease_frame,w2_release_frame,
 input wire [ND*337-1:0] w2_req,output wire [ND*273-1:0] w2_rsp,
 output wire [ND-1:0] w2_lease_granted,w2_release_r,w2_req_r,w2_rsp_v,
 // Existing readyless native caller and literal installed compact-sector map.
 // weights_installed comes only after loading Erdos w2_p0/p1 overlays into
 // the selected NS2 provider; CSV addresses/tags are never derived by truncation.
 input wire [ND-1:0] w2_weights_installed,w2_native_req_v,w2_native_delivery_permit,w2_map_valid,
 input wire [ND*32-1:0] w2_native_req_addr,w2_map_native_addr,
 input wire [ND*10-1:0] w2_native_req_tag,
 input wire [ND*73-1:0] w2_map_frame,
 input wire [ND*3-1:0] w2_map_sm,w2_map_count,
 input wire [ND*16-1:0] w2_map_compact_offset,
 input wire [ND*4-1:0] w2_map_lanes,
 input wire [ND*192-1:0] w2_map_byte_addresses,
 input wire [ND*96-1:0] w2_map_tags,w2_map_cfg,
 output wire [ND-1:0] w2_native_req_r,w2_native_rsp_pending,w2_native_rsp_v,w2_sector_drained,w2_sector_fault,w2_sector_foreign_rsp,
 output wire [ND*10-1:0] w2_native_rsp_tag,
 output wire [ND*1088-1:0] w2_native_rsp_data,
 output wire rst_sm_n, output wire sys_fault
);
localparam integer NORM_QROWS=(NORM_N*8+1023)/1024+((NORM_N/32)*10+1023)/1024+(NORM_N*16+1023)/1024;
initial if(NORM_NATIVE_VM_ENABLE&&(!NORM_C12_ENABLE||!SFU_NATIVE_VM_ENABLE||NORM_N%32||NORM_D%NORM_N||NORM_D/NORM_N>256||NORM_KIND>2||NORM_KIND<0||NORM_AW>30||
 (NORM_NATIVE_INPUT_CP?(NORM_D+(NORM_PUBLISH_QUANT?(NORM_D/NORM_N)*NORM_QROWS*32:0)>16384):
 (NORM_KIND!=1||NORM_RD!=0||NORM_D*3+(NORM_PUBLISH_QUANT?(NORM_D/NORM_N)*NORM_QROWS*32:0)>16384))))
 $fatal(1,"native norm requires actual CP input lease for HC/KV and output SRAM window <=16384 words");
initial if(NORM_C12_ENABLE&&(!COMBINED_ENABLE||!ENABLE||TW!=17||PW!=20)) $fatal(1,"norm requires enabled protected full73 combined parent");
initial if(SFU_NATIVE_VM_ENABLE&&!SFU_C12_ENABLE) $fatal(1,"native VM requires actual SFUc12 stage");
initial if(SFU_C12_ENABLE && (!COMBINED_ENABLE||!ENABLE||TW!=17||PW!=20))
 $fatal(1,"SFU c12 requires enabled combined full73 parent");
initial if(COMBINED_ENABLE && (TW!=17 || PW!=20 || NSM!=2 || IMW!=14 || NS!=2 || NPC!=2 || USE_W2!=0))
 $fatal(1,"installed SU parent requires NSM2/IMW14/NS2/NPC2/defaultW2");
initial if(COMBINED_ENABLE && W2_SECTOR_ENABLE && (!W2_RESULT_ENABLE || NS!=2 || MEM_WORDS!=2097152))
 $fatal(1,"native W2 sector join requires real result seats and installed NS2/2097152 aperture");
generate if(COMBINED_ENABLE==0) begin:g_original
 ot_ds_hbm_cluster20 #(.ENABLE(ENABLE),.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS),
  .ND(ND),.NSM(NSM),.NL(NL),.IMW(IMW),.CB(CB),.NS(NS),.NPC(NPC),.MEM_WORDS(MEM_WORDS),
  .SW_PIPE(SW_PIPE),.USE_W2(USE_W2),.HAS_DIV(HAS_DIV),.HAS_BD(HAS_BD)) u_original(
  .por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
  .cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),.db_v(db_v),.db_rdy(db_rdy),
  .db_token(db_token),.db_pos(db_pos),.db_job(db_job),.db_generation(db_generation),
  .cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_data(cpl_data),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),
  .rst_sm_n(rst_sm_n),.sys_fault(sys_fault));

 assign sfu_vm_bind_r=0;
 assign sfu_vm_retire_r=0;
 assign sfu_vm_held_frame=0;
 assign sfu_vm_retained=0;
 assign sfu_vm_warm_ack=0;
 assign sfu_vm_fault=0;
 assign sfu_vm_activation_wr_r=0;
 assign sfu_vm_activation_ACK_v=0;
 assign sfu_vm_activation_ACK_frame=0;
 assign sfu_vm_activation_ACK_owner=0;
 assign sfu_vm_activation_rd_r=0;
 assign sfu_vm_tap_v=0;
 assign sfu_vm_tap_data=0;
 assign sfu_vm_tap_owner=0;
 assign sfu_vm_tap_frame=0;
 assign sfu_vm_tap_source_clk=0;
 assign sfu_vm_tap_ACK_r=0;
 assign sfu_vm_activation_release=0;
 assign sfu_vm_activation_release_frame=0;
 assign sfu_vm_activation_release_owner=0;
 assign sfu_vm_su_pub_r=0;
 assign sfu_vm_su_ACK_v=0;
 assign sfu_vm_publication_ACK_addr=0;
 assign sfu_vm_publication_ACK_frame=0;
 assign sfu_vm_index_read_r=0;
 assign sfu_vm_index_rsp_v=0;
 assign sfu_vm_index_rsp_data=0;
 assign sfu_vm_index_rsp_tag=0;
 assign sfu_vm_index_rsp_frame=0;
 assign sfu_vm_index_rsp_rank=0;
 assign norm_warm_ack=0;
 assign norm_enroll_r=0;
 assign norm_publication_v=0;
 assign norm_rd_addr=0;
 assign norm_rd_re=0;
 assign norm_rd_src=0;
 assign norm_vm_we=0;
 assign norm_vm_waddr=0;
 assign norm_vm_wdata=0;
 assign norm_q_valid=0;
 assign norm_q_index=0;
 assign norm_q_codes=0;
 assign norm_q_exp=0;
 assign norm_q_bf16=0;
 assign norm_reserve_events=0;
 assign norm_held_frame=0;
 assign norm_retained=0;
 assign norm_fault=0;
 assign norm_ce=0;
 assign norm_due=0;
 assign sfu_enroll_r=0;assign sfu_publication_v=0;assign sfu_retained=0;assign sfu_fault=0;assign sfu_warm_ack=0;assign sfu_held_frame=0;
 assign normal_busy=0;assign normal_done=0;assign normal_vm_re=0;assign normal_vm_raddr=0;
 assign normal_e_valid=0;assign normal_e_data=0;assign normal_e_last=0;assign normal_e_mode=0;assign normal_e_tag=0;assign normal_o_ready=0;
 assign cp_reset_ack=0;
 assign formatter_start_r=0;assign index_pair_r=0;assign index_pairs_v=0;assign index_pairs=0;assign index_pairs_frame73=0;assign formatter_release_r=0;
 assign gather_desc_r=0;assign gather_start_r=0;assign gather_req_r=0;assign gather_rsp_v=0;assign gather_rsp=0;
 assign gather_release_r=0;assign gather_retained=0;assign gather_arena_visible=0;assign gather_sink_visible=0;
 assign w2_native_req_r=0;assign w2_native_rsp_pending=0;assign w2_native_rsp_v=0;
 assign w2_native_rsp_tag=0;assign w2_native_rsp_data=0;assign w2_sector_drained=1;
 assign w2_sector_fault=0;assign w2_sector_foreign_rsp=0;
 assign w2_reserve_r=0;assign w2_source_permit=0;assign w2_output_done=0;
 assign w2_lease_granted=0;assign w2_release_r=0;assign w2_req_r=0;assign w2_rsp_v=0;assign w2_rsp=0;
end else if(ENABLE==0) begin:g_off
 assign db_rdy=0; assign cpl_v=0; assign cpl_data=0;
 assign rst_sm_n=0; assign sys_fault=0;
 assign sfu_vm_bind_r=0;
 assign sfu_vm_retire_r=0;
 assign sfu_vm_held_frame=0;
 assign sfu_vm_retained=0;
 assign sfu_vm_warm_ack=0;
 assign sfu_vm_fault=0;
 assign sfu_vm_activation_wr_r=0;
 assign sfu_vm_activation_ACK_v=0;
 assign sfu_vm_activation_ACK_frame=0;
 assign sfu_vm_activation_ACK_owner=0;
 assign sfu_vm_activation_rd_r=0;
 assign sfu_vm_tap_v=0;
 assign sfu_vm_tap_data=0;
 assign sfu_vm_tap_owner=0;
 assign sfu_vm_tap_frame=0;
 assign sfu_vm_tap_source_clk=0;
 assign sfu_vm_tap_ACK_r=0;
 assign sfu_vm_activation_release=0;
 assign sfu_vm_activation_release_frame=0;
 assign sfu_vm_activation_release_owner=0;
 assign sfu_vm_su_pub_r=0;
 assign sfu_vm_su_ACK_v=0;
 assign sfu_vm_publication_ACK_addr=0;
 assign sfu_vm_publication_ACK_frame=0;
 assign sfu_vm_index_read_r=0;
 assign sfu_vm_index_rsp_v=0;
 assign sfu_vm_index_rsp_data=0;
 assign sfu_vm_index_rsp_tag=0;
 assign sfu_vm_index_rsp_frame=0;
 assign sfu_vm_index_rsp_rank=0;
 assign norm_warm_ack=0;
 assign norm_enroll_r=0;
 assign norm_publication_v=0;
 assign norm_rd_addr=0;
 assign norm_rd_re=0;
 assign norm_rd_src=0;
 assign norm_vm_we=0;
 assign norm_vm_waddr=0;
 assign norm_vm_wdata=0;
 assign norm_q_valid=0;
 assign norm_q_index=0;
 assign norm_q_codes=0;
 assign norm_q_exp=0;
 assign norm_q_bf16=0;
 assign norm_reserve_events=0;
 assign norm_held_frame=0;
 assign norm_retained=0;
 assign norm_fault=0;
 assign norm_ce=0;
 assign norm_due=0;
 assign sfu_enroll_r=0;assign sfu_publication_v=0;assign sfu_retained=0;assign sfu_fault=0;assign sfu_warm_ack=0;assign sfu_held_frame=0;
 assign normal_busy=0;assign normal_done=0;assign normal_vm_re=0;assign normal_vm_raddr=0;
 assign normal_e_valid=0;assign normal_e_data=0;assign normal_e_last=0;assign normal_e_mode=0;assign normal_e_tag=0;assign normal_o_ready=0;
 assign cp_reset_ack=0;
 assign formatter_start_r=0;assign index_pair_r=0;assign index_pairs_v=0;assign index_pairs=0;assign index_pairs_frame73=0;assign formatter_release_r=0;
 assign gather_desc_r=0;assign gather_start_r=0;assign gather_req_r=0;assign gather_rsp_v=0;assign gather_rsp=0;
 assign gather_release_r=0;assign gather_retained=0;assign gather_arena_visible=0;assign gather_sink_visible=0;
 assign w2_native_req_r=0;assign w2_native_rsp_pending=0;assign w2_native_rsp_v=0;
 assign w2_native_rsp_tag=0;assign w2_native_rsp_data=0;assign w2_sector_drained=1;
 assign w2_sector_fault=0;assign w2_sector_foreign_rsp=0;
 assign w2_reserve_r=0;assign w2_source_permit=0;assign w2_output_done=0;
 assign w2_lease_granted=0;assign w2_release_r=0;assign w2_req_r=0;assign w2_rsp_v=0;assign w2_rsp=0;

end else begin:g_on
 localparam integer NCL=2*NSM;
 wire rst_host_n, rst_mem_n, rst_link_n;
 ot_gpu_reset_ctrl #(.ENABLE(1)) u_rst(.por_n(por_n),
 .clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),
 .rst_host_n(rst_host_n),.rst_sm_n(rst_sm_n),.rst_mem_n(rst_mem_n),.rst_link_n(rst_link_n));
    // ------------------------------------------------------------------ collective fabric
    wire [ND-1:0]         ep_req_v, ep_req_rdy, ep_mode, ep_rsp_v, ep_rsp_rdy;
    wire [ND*8-1:0]       ep_count;
    wire [ND*NL*32-1:0]   ep_data, ep_rsp_data;
    wire                  coll_fault;
    ot_gpu_coll_system #(.ENABLE(1), .R(ND), .NL(NL), .SW_PIPE(SW_PIPE)) u_coll (
        .clk_sm(clk_sm), .rst_sm_n(rst_sm_n), .clk_link(clk_link), .rst_link_n(rst_link_n),
        .req_v(ep_req_v), .req_rdy(ep_req_rdy), .mode(ep_mode), .count(ep_count), .data(ep_data),
        .rsp_v(ep_rsp_v), .rsp_rdy(ep_rsp_rdy), .rsp_data(ep_rsp_data), .fault(coll_fault));

    // ------------------------------------------------------------------ dies
    wire [ND-1:0] die_fault;
    genvar d, s;
    for (d = 0; d < ND; d = d + 1) begin : g_die
        wire [NSM-1:0] launch_v, sm_done, sm_fault, res_v, bar_arr, bar_rel, busy;
        wire [NSM-1:0] native_done,native_fault;
        wire su_pending,su_owned,su_qualified_owned,su_executor_owned,su_new_request_permit,su_association_fault,su_done,su_fault,su_exec_done,su_exec_fault;
        wire [31:0] su_pc;
        wire [NSM-1:0] native_launch;
        wire su_selected,su_quiet;wire [31:0] su_job;wire [3:0] su_gen;
        wire [16:0] su_token;wire [19:0] su_pos;
        wire su_lease_v,su_release_v,su_release_r;wire [3:0] su_retired;
        wire cp_idle,cp_cpl_v,cp_retire_ready,native_credit_empty,shared_idle;
        wire cp_reset_wait,cp_reset_n,cp_reset_fault;
        ot_hbm_integrated_cp_reset #(.ENABLE(LOCAL_CP_RESET_ENABLE)) u_cp_reset(
         .clk(clk_sm),.por_n(rst_sm_n),.reset_req(cp_reset_req[d]),.cp_idle(cp_idle),
         .routes_drained(all_routes_drained),.cp_reset_n(cp_reset_n),.reset_ack(cp_reset_ack[d]),
         .block_new(cp_reset_wait),.fault(cp_reset_fault));
        wire shared_fault;wire [1:0] peer_grants,peer_releases;
        wire [3:0] response_authorized,return_offer;
        assign sm_done=su_selected?{{(NSM-1){1'b0}},su_done}:native_done;
        assign sm_fault=native_fault | {NSM{su_fault|su_exec_fault|su_association_fault|fmt_fault|cp_reset_fault|store_fault|sfu_fault[d]|norm_fault[d]}};
        wire [31:0] launch_pc;
        wire [TW-1:0] launch_token; wire [PW-1:0] launch_pos;
        wire [NSM*32-1:0] res_data;
        wire [TW-1:0] cpl_token; wire [PW-1:0] cpl_position; wire [31:0] cpl_job; wire [3:0] cpl_generation; wire [3:0] cpl_status; wire [31:0] cpl_cycles, st_kernels, st_busy;
        ot_ds_hbm_cmdproc20 #(.TW(TW),.PW(PW),.CONTEXT_POSITIONS(CONTEXT_POSITIONS), .ENABLE(1), .NSM(NSM), .NCMD(1 << CB)) u_cp (
            .clk(clk_sm), .rst_n(cp_reset_n), .cmd_we(cmd_we[d]&&!cp_reset_wait), .cmd_addr(cmd_addr[d*CB +: CB]), .cmd_wdata(cmd_wdata[d*64 +: 64]),
            .db_v(db_v[d] && db_rdy[d]), .db_rdy(cp_idle), .db_token(db_token[d*TW +: TW]), .db_pos(db_pos[d*PW +: PW]),
            .db_job(db_job[d*32+:32]),.db_generation(db_generation[d*4+:4]),
            .cpl_position(cpl_position),.cpl_job(cpl_job),.cpl_generation(cpl_generation),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data),
            .cpl_v(cp_cpl_v), .cpl_rdy(cp_retire_ready), .cpl_token(cpl_token), .cpl_status(cpl_status),
            .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
        // The CP's context cannot change across any prior native/borrower debt.
        wire all_prior_quiet=!(|busy)&&!(|launch_v)&&!(|a_req_v)&&!(|a_rsp_v)&&
                             !(|obs_req)&&!(|obs_rsp);
        wire all_routes_drained=native_credit_empty&&shared_idle&&!su_pending&&!su_owned&&
                                !gather_retained[d]&&!fmt_retained&&!sfu_retained[d]&&!norm_retained[d]&&(!SFU_NATIVE_VM_ENABLE||!sfu_vm_retained[d])&&w2_route_quiet&&!w2_sink_retained&&all_prior_quiet;
        assign db_rdy[d]=cp_idle&&all_routes_drained&&!cp_reset_wait;
        assign cpl_v[d]=cp_cpl_v&&all_routes_drained;
        assign cp_retire_ready=cpl_rdy[d]&&all_routes_drained;
        assign cpl_data[d*(TW+PW+72) +: (TW+PW+72)] = {cpl_job,cpl_generation,cpl_cycles,cpl_status,cpl_position,cpl_token};
        // grid barrier: one node, the SMs of the die as children (root: release = own arrival sense)
        wire bar_up;
        ot_gpu_barrier_node #(.K(NSM)) u_bar (.clk(clk_sm), .rst_n(rst_sm_n), .arr(bar_arr), .up(bar_up),
                                              .rel_in(bar_up), .rel(bar_rel));
        // memory clients (clk_sm side) and their crossings
        wire [NCL-1:0]       c_req_v, c_req_rdy, c_req_we, c_rsp_v, c_rsp_rdy, c_rsp_we;
        wire [NCL*32-1:0]    c_req_addr, c_req_wstrb;
        wire [NCL*256-1:0]   c_req_wdata, c_rsp_data;
        wire [NCL*16-1:0]    c_req_tag, c_rsp_tag;
        wire [NCL-1:0]       x_req_v, x_req_rdy, x_req_we, x_rsp_v, x_rsp_rdy, x_rsp_we, cdc_f;
        wire [NCL*32-1:0]    x_req_addr, x_req_wstrb;
        wire [NCL*256-1:0]   x_req_wdata, x_rsp_data;
        wire [NCL*16-1:0]    x_req_tag, x_rsp_tag;
        // Original producer side of the actual LSU/bulk interfaces.
        wire [NCL-1:0] a_req_v,a_req_rdy,a_req_we,a_rsp_v,a_rsp_rdy,a_rsp_we;
        wire [NCL*32-1:0] a_req_addr,a_req_wstrb;
        wire [NCL*256-1:0] a_req_wdata,a_rsp_data;
        wire [NCL*16-1:0] a_req_tag,a_rsp_tag;
        wire su_req_v,su_req_rdy,su_rsp_v,su_rsp_rdy;
        wire [336:0] su_request;
        wire [272:0] su_response;
        wire su_provider_req_v,su_provider_rsp_r,su_caller_done,su_caller_fault;
        wire sfu_req_v,sfu_rsp_r,sfu_lease_v,sfu_release_v,sfu_quiet,sfu_offer_r;
        wire [336:0] sfu_req;
        wire norm_lease_v,norm_quiet,norm_release_v,norm_offer_r;
        wire norm_clk_enable,norm_read_permit,norm_backend_drained,norm_checked,norm_backend_fault;
        wire norm_cp_req_v,norm_cp_rsp_r;wire [336:0] norm_cp_req;wire [72:0] norm_quant_frame;
        wire norm_read_v,norm_read_r,norm_rsp_v,norm_rsp_r,norm_pub_v,norm_pub_r,norm_ACK_v,norm_ACK_r;
        wire [31:0] norm_read_addr,norm_pub_addr;wire [7:0] norm_read_tag;wire [6:0] norm_read_rank;
        wire [4*NORM_N*32-1:0] norm_native_q;
        wire [1023:0] norm_pub_data;
        wire norm_native_route=NORM_NATIVE_VM_ENABLE&&norm_retained[d];
        wire norm_root_reads=norm_native_route&&!NORM_NATIVE_INPUT_CP;
        wire norm_result_reads=!norm_native_route||(NORM_NATIVE_INPUT_CP&&norm_checked);
        wire norm_route=NORM_C12_ENABLE&&norm_retained[d];
        wire sfu_route=SFU_C12_ENABLE&&sfu_retained[d];
        wire [72:0] peer0_frame=sfu_route?sfu_held_frame[d*73+:73]:norm_route?norm_held_frame[d*73+:73]:su_provider_frame;
        wire [72:0] actual_cp_frame={launch_pos,launch_token,cpl_generation,cpl_job};
        wire sfu_admit=!su_pending&&!su_selected&&!su_owned&&!norm_retained[d]&&!cp_reset_wait&&
                       sfu_enroll_frame[d*73+:73]==actual_cp_frame;
        // Admission checks the offered tuple; after acceptance the SAME coded
        // stage owns the tuple. No preseeded or shadow descriptor.
        wire [72:0] norm_allocation_target=norm_retained[d]?norm_held_frame[d*73+:73]:norm_enroll_frame[d*73+:73];
        wire norm_admit=!su_pending&&!su_selected&&!su_owned&&!cp_reset_wait&&!sfu_retained[d]&&!sfu_enroll_v[d]&&norm_enroll_frame[d*73+:73]==actual_cp_frame&&(!NORM_NATIVE_VM_ENABLE||(sfu_vm_retained[d]&&!sfu_vm_fault[d]&&sfu_vm_held_frame[d*73+:73]==actual_cp_frame&&(!NORM_NATIVE_INPUT_CP||(norm_allocation_valid[d]&&norm_allocation_frame[d*73+:73]==actual_cp_frame))));
        assign norm_enroll_r[d]=norm_offer_r&&norm_admit;
        assign sfu_enroll_r[d]=sfu_offer_r&&sfu_admit;
        wire [336:0] su_provider_req;
        wire [3:0] su_caller_retired;
        wire [31:0] su_executor_pc;
        wire [72:0] su_provider_frame;
        wire [NCL-1:0] obs_req,obs_rsp,obs_req_we,obs_rsp_we;
        wire [NCL*16-1:0] obs_req_tag,obs_rsp_tag;
        wire [2:0] p_req_v,p_req_rdy,p_req_we,p_rsp_v,p_rsp_rdy,p_rsp_we;
        wire [95:0] p_req_addr,p_req_wstrb;wire [767:0] p_req_wdata,p_rsp_data;
        wire [47:0] p_req_tag,p_rsp_tag;
        wire w2_sink_req_v,w2_sink_req_r,w2_sink_rsp_v,w2_sink_rsp_r,w2_sink_retained,w2_sink_fault,w2_sink_retire_r;
        wire [336:0] w2_sink_req;wire [272:0] w2_provider_rsp;
        wire w2_adapter_req_v,w2_adapter_req_r,w2_adapter_rsp_v,w2_adapter_rsp_r,w2_adapter_busy;
        wire [336:0] w2_adapter_req;
        wire w2_route_drained=W2_SECTOR_ENABLE?w2_sector_drained[d]:(!W2_RESULT_ENABLE||w2_assembly_drained[d]);
        wire w2_route_quiet=w2_quiet[d]&&(!W2_SECTOR_ENABLE||w2_sector_drained[d]);
        wire w2_route_req_v=W2_SECTOR_ENABLE?w2_adapter_req_v:w2_req_v[d];
        wire [336:0] w2_route_req=W2_SECTOR_ENABLE?w2_adapter_req:w2_req[d*337+:337];
        wire w2_route_rsp_r=W2_SECTOR_ENABLE?w2_adapter_rsp_r:w2_rsp_r[d];
        if(W2_SECTOR_ENABLE)begin:g_w2_sectors
        ot_hbm_integrated_w2_sector_adapter #(.ENABLE(1)) u_w2_sectors(
         .clk(clk_sm),.por_n(rst_sm_n),.owner_valid(peer_grants[1]),.owner_frame(w2_lease_frame[d*73+:73]),
         .source_accept_permit(w2_source_permit[d]&&w2_weights_installed[d]),
         .result_seat_permit(w2_source_permit[d]),
         .native_req_v(w2_native_req_v[d]),.native_req_r(w2_native_req_r[d]),
         .native_req_addr(w2_native_req_addr[d*32+:32]),.native_req_tag(w2_native_req_tag[d*10+:10]),
         .map_valid(w2_map_valid[d]&&w2_weights_installed[d]),.map_frame(w2_map_frame[d*73+:73]),
         .map_native_addr(w2_map_native_addr[d*32+:32]),.map_sm(w2_map_sm[d*3+:3]),
         .map_compact_offset(w2_map_compact_offset[d*16+:16]),.map_lanes(w2_map_lanes[d*4+:4]),
         .map_count(w2_map_count[d*3+:3]),.map_byte_addresses(w2_map_byte_addresses[d*192+:192]),
         .map_tags(w2_map_tags[d*96+:96]),.map_cfg(w2_map_cfg[d*96+:96]),
         .sector_req_v(w2_adapter_req_v),.sector_req_r(w2_adapter_req_r),.sector_req(w2_adapter_req),
         .sector_rsp_v(w2_adapter_rsp_v),.sector_rsp_r(w2_adapter_rsp_r),.sector_rsp(w2_provider_rsp),
         .native_delivery_permit(w2_native_delivery_permit[d]),
         .native_rsp_pending(w2_native_rsp_pending[d]),.native_rsp_v(w2_native_rsp_v[d]),
         .native_rsp_tag(w2_native_rsp_tag[d*10+:10]),.native_rsp_data(w2_native_rsp_data[d*1088+:1088]),
         .busy(w2_adapter_busy),.drained(w2_sector_drained[d]),.fault(w2_sector_fault[d]),.foreign_rsp(w2_sector_foreign_rsp[d]));
        end else begin:g_no_w2_sectors
         assign w2_adapter_req_v=0;assign w2_adapter_req=0;assign w2_adapter_rsp_r=0;assign w2_adapter_busy=0;
         assign w2_native_req_r[d]=0;assign w2_native_rsp_pending[d]=0;assign w2_native_rsp_v[d]=0;
         assign w2_native_rsp_tag[d*10+:10]=0;assign w2_native_rsp_data[d*1088+:1088]=0;
         assign w2_sector_drained[d]=1;assign w2_sector_fault[d]=0;assign w2_sector_foreign_rsp[d]=0;
        end
        wire w2_sink_route=W2_RESULT_ENABLE&&w2_sink_req_v&&w2_route_drained;
        // Reservation gates NEW native acceptance in the adapter. Once accepted,
        // its sector debt must drain even if native_done/source permit changes.
        wire w2_native_permit=W2_SECTOR_ENABLE||!W2_RESULT_ENABLE||(w2_source_permit[d]&&!w2_native_done[d]);
        assign p_req_v={w2_sink_route||(w2_route_req_v&&w2_native_permit),(sfu_route?sfu_req_v:norm_route?norm_cp_req_v:su_provider_req_v),a_req_v[0]};
        assign {p_req_we[2],p_req_addr[95:64],p_req_wdata[767:512],p_req_wstrb[95:64],p_req_tag[47:32]}=
         w2_sink_route?w2_sink_req:w2_route_req;
        assign {p_req_we[1],p_req_addr[63:32],p_req_wdata[511:256],p_req_wstrb[63:32],p_req_tag[31:16]}=sfu_route?sfu_req:norm_route?norm_cp_req:su_provider_req;
        assign {p_req_we[0],p_req_addr[31:0],p_req_wdata[255:0],p_req_wstrb[31:0],p_req_tag[15:0]}=
               {a_req_we[0],a_req_addr[31:0],a_req_wdata[255:0],a_req_wstrb[31:0],a_req_tag[15:0]};
        assign w2_adapter_req_r=p_req_rdy[2]&&!w2_sink_route&&w2_native_permit;
        assign w2_req_r[d]=!W2_SECTOR_ENABLE&&w2_adapter_req_r;assign w2_sink_req_r=p_req_rdy[2]&&w2_sink_route;assign a_req_rdy[0]=p_req_rdy[0];
        assign w2_provider_rsp={p_rsp_tag[47:32],p_rsp_we[2],p_rsp_data[767:512]};
        // Assembly drains before a result write starts; the sink retains the
        // same single CAP1 route through write ACK and readback consumption.
        wire sink_response=W2_RESULT_ENABLE&&w2_route_drained&&w2_sink_retained;
        assign w2_sink_rsp_v=p_rsp_v[2]&&sink_response;
        assign w2_adapter_rsp_v=p_rsp_v[2]&&!sink_response;
        assign w2_rsp_v[d]=!W2_SECTOR_ENABLE&&w2_adapter_rsp_v;assign w2_rsp[d*273+:273]=w2_provider_rsp;

        assign a_rsp_v[0]=p_rsp_v[0]&&response_authorized[0];
        assign a_rsp_tag[15:0]=p_rsp_tag[15:0];assign a_rsp_we[0]=p_rsp_we[0];assign a_rsp_data[255:0]=p_rsp_data[255:0];
        assign p_rsp_rdy={sink_response?w2_sink_rsp_r:w2_route_rsp_r,sfu_route?sfu_rsp_r:norm_route?norm_cp_rsp_r:su_provider_rsp_r,a_rsp_rdy[0]&&response_authorized[0]};
        assign return_offer[0]=p_rsp_v[0];
        assign obs_req[0]=a_req_v[0]&&a_req_rdy[0];assign obs_rsp[0]=a_rsp_v[0]&&a_rsp_rdy[0];
        assign obs_req_tag[15:0]=a_req_tag[15:0];assign obs_req_we[0]=a_req_we[0];
        assign obs_rsp_tag[15:0]=p_rsp_tag[15:0];assign obs_rsp_we[0]=p_rsp_we[0];
        assign w2_lease_granted[d]=peer_grants[1];
        assign w2_release_r[d]=peer_releases[1]&&w2_route_drained&&(!W2_RESULT_ENABLE||w2_sink_retire_r);
        ot_hbm_integrated_w2_result_sink #(.ENABLE(W2_RESULT_ENABLE),.PROTECTED_TRANSACTION_PIPELINE(W2_PROTECTED_TRANSACTION_PIPELINE)) u_w2_sink(
         .clk(clk_sm),.por_n(rst_sm_n),.owned(peer_grants[1]),.installed(w2_output_installed[d]),
         .reserve_v(w2_reserve_v[d]),.reserve_r(w2_reserve_r[d]),.pair_op(w2_pair_op[d]),
         .rows_a(w2_rows_a[d*2+:2]),.rows_b(w2_rows_b[d*2+:2]),
         .op_a(w2_op_a[d*32+:32]),.op_b(w2_op_b[d*32+:32]),
         .base_a(w2_output_base_a[d*32+:32]),.limit_a(w2_output_limit_a[d*32+:32]),
         .base_b(w2_output_base_b[d*32+:32]),.limit_b(w2_output_limit_b[d*32+:32]),
         .provider_tag(w2_output_tag[d*16+:16]),.frame(w2_lease_frame[d*73+:73]),
         .source_permit(w2_source_permit[d]),.retained(w2_sink_retained),.done(w2_output_done[d]),.quiet(),.fault(w2_sink_fault),
         .result_v(w2_result_v[d]),.result_op(w2_result_op[d*32+:32]),.result_row(w2_result_row[d*12+:12]),
         .result_data(w2_result_data[d*256+:256]),.native_done(w2_native_done[d]),
         .retire_v(w2_release_v[d]&&peer_releases[1]),.retire_r(w2_sink_retire_r),
         .req_v(w2_sink_req_v),.req_r(w2_sink_req_r&&w2_route_drained),.req(w2_sink_req),
         .rsp_v(w2_sink_rsp_v),.rsp_r(w2_sink_rsp_r),.rsp(w2_provider_rsp));
        assign su_owned=peer_grants[0]&&!sfu_route&&!norm_route;assign su_release_r=peer_releases[0]&&!sfu_route&&!norm_route;
        wire [11:0] su_owned_frontier_terms;
        ot_hbm_integrated_su_cp_bind #(.ENABLE(SU_ENABLE),.REGISTERED_OUTPUTS(SU_REGISTERED_OUTPUTS),.REGISTERED_STATUS(SU_REGISTERED_STATUS),.REGISTERED_BOUNDARY(SU_REGISTERED_BOUNDARY),.GROUPED_OWNER_BOUNDARY(0),.BALANCED_OWNER_BOUNDARY(SU_BALANCED_OWNER_BOUNDARY),.FOUR_COMBINATIONAL_CUTS(SU_FOUR_COMBINATIONAL_CUTS),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER),.PARALLEL_PHASE_VALIDATION(SU_PARALLEL_PHASE_VALIDATION)) u_su_cp(
         .clk(clk_sm),.por_n(rst_sm_n),.launch_v(launch_v),.launch_pc(launch_pc),
         .cp_job(cpl_job),.cp_gen(cpl_generation),.launch_token(launch_token),.launch_pos(launch_pos),
         .native_launch(native_launch),.lease_v(su_lease_v),.lease_granted(su_owned),
         .release_v(su_release_v),.release_r(su_release_r),.exec_done(su_caller_done),.exec_fault(su_caller_fault),
         .retired_original_ops(su_caller_retired),.shared_fault(shared_fault),.owned(su_qualified_owned),.owned_frontier_terms(su_owned_frontier_terms),.pending(su_pending),
         .quiet(su_quiet),.selected(su_selected),.done(su_done),.fault(su_fault),
         .selected_pc(su_pc),.held_job(su_job),.held_gen(su_gen),.held_token(su_token),.held_pos(su_pos));
        // Response valid/ready and captured provider requests are unchanged.
        // New requests use the live veto; admitted execution holds the grant.
        if(SU_PROVIDER_ADAPTER)begin:g_su_provider_adapter
        ot_hbm_integrated_su_provider_adapter #(.ENABLE(SU_ENABLE),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER)) u_su_provider(
         .clk_sm(clk_sm),.por_n(rst_sm_n),.raw_grant(su_owned),.qualified_owned(su_qualified_owned),
         .qualified_owned_terms(su_owned_frontier_terms),.exec_owned(su_executor_owned),
         .new_request_permit(su_new_request_permit),.fault(su_association_fault),
         .exec_req_v(su_req_v),.exec_req_r(su_req_rdy),.exec_req(su_request),
         .provider_req_v(su_provider_req_v),.provider_req_r(p_req_rdy[1]&&!sfu_route&&!norm_route),.provider_req(su_provider_req),
         .provider_rsp_v(p_rsp_v[1]&&!sfu_route&&!norm_route),.provider_rsp_r(su_provider_rsp_r),
         .provider_rsp({p_rsp_tag[31:16],p_rsp_we[1],p_rsp_data[511:256]}),
         .exec_rsp_v(su_rsp_v),.exec_rsp_r(su_rsp_rdy),.exec_rsp(su_response),
         .held_job(su_job),.held_gen(su_gen),.held_token(su_token),.held_pos(su_pos),.owner_frame(su_provider_frame),
         .held_selected_pc(su_pc),.selected_pc(su_executor_pc),
         .exec_done(su_exec_done),.exec_fault(su_exec_fault),.retired_original_ops(su_retired),
         .caller_exec_done(su_caller_done),.caller_exec_fault(su_caller_fault),.caller_retired_original_ops(su_caller_retired));
        end else begin:g_su_legacy_provider
        ot_hbm_integrated_su_cp_association #(.ENABLE(SU_ENABLE&&SU_BALANCED_OWNER_BOUNDARY),.FAST_OWNER_FRONTIER(SU_FAST_OWNER_FRONTIER)) u_su_association(
         .clk(clk_sm),.por_n(rst_sm_n),.raw_grant(su_owned),.qualified_owned(su_qualified_owned),.qualified_owned_terms(su_owned_frontier_terms),
         .exec_owned(su_executor_owned),.new_request_permit(su_new_request_permit),.fault(su_association_fault));
        assign su_provider_req_v=su_req_v&&su_new_request_permit;assign su_provider_req=su_request;
        assign su_req_rdy=p_req_rdy[1]&&su_new_request_permit&&!sfu_route&&!norm_route;
        assign su_rsp_v=p_rsp_v[1]&&!sfu_route&&!norm_route;assign su_provider_rsp_r=su_rsp_rdy;
        assign su_response={p_rsp_tag[31:16],p_rsp_we[1],p_rsp_data[511:256]};
        assign su_provider_frame={su_pos,su_token,su_gen,su_job};assign su_executor_pc=su_pc;
        assign su_caller_done=su_exec_done;assign su_caller_fault=su_exec_fault;assign su_caller_retired=su_retired;
        end
        wire [648:0] shared_gather_req,fmt_req,store_req;
        wire [636:0] shared_gather_rsp;
        wire shared_gather_req_v,shared_gather_req_r,shared_gather_rsp_v,shared_gather_rsp_r;
        wire fmt_req_v,fmt_req_r,fmt_rsp_r,fmt_retained,fmt_fault,bridge_release_r;
        wire fmt_lease_valid;wire [72:0] fmt_lease_frame;
        wire store_req_v,store_req_r,store_rsp_r,store_fault;
        wire [VM_AW-1:0] store_vm_raddr;
        assign normal_vm_raddr[d*32+:32]=32'(store_vm_raddr);
        wire [31:0] bound_arena_base,bound_arena_limit;
        // Normal producer and formatter consume their own real tagged response.
        wire formatter_response=FORMATTER_ENABLE&&shared_gather_rsp[3:1]==3'd3;
        wire store_response=NORMAL_GATHER_ENABLE&&(shared_gather_rsp[3:1]==3'd1||shared_gather_rsp[3:1]==3'd2);
        assign shared_gather_req_v=fmt_req_v||store_req_v||gather_req_v[d];
        assign shared_gather_req=fmt_req_v?fmt_req:store_req_v?store_req:gather_req[d*649+:649];
        assign fmt_req_r=shared_gather_req_r&&fmt_req_v;
        assign store_req_r=shared_gather_req_r&&!fmt_req_v&&store_req_v;
        assign gather_req_r[d]=shared_gather_req_r&&!fmt_req_v&&!store_req_v;
        assign gather_rsp_v[d]=shared_gather_rsp_v&&!formatter_response&&!store_response;
        assign gather_rsp[d*637+:637]=shared_gather_rsp;
        assign shared_gather_rsp_r=formatter_response?fmt_rsp_r:store_response?store_rsp_r:gather_rsp_r[d];
        assign gather_release_r[d]=bridge_release_r&&!fmt_retained;
        ot_hbm_integrated_w15_store #(.ENABLE(NORMAL_GATHER_ENABLE),.VM_AW(VM_AW)) u_normal_store(
         .clk(clk_sm),.por_n(rst_sm_n),.go(normal_go[d]),.id_plane(normal_id_plane[d]),
         .command_tag(normal_command_tag[d*16+:16]),.source_word(normal_source_word[d*32+:32]),
         .arena_base(bound_arena_base),.arena_limit(bound_arena_limit),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),.gather_retained(gather_retained[d]),
         .busy(normal_busy[d]),.done(normal_done[d]),.fault(store_fault),
         .vm_re(normal_vm_re[d]),.vm_raddr(store_vm_raddr),.vm_rq(normal_vm_rq[d*512+:512]),
         .e_valid(normal_e_valid[d]),.e_ready(normal_e_ready[d]),.e_data(normal_e_data[d*512+:512]),
         .e_last(normal_e_last[d]),.e_mode(normal_e_mode[d]),.e_tag(normal_e_tag[d*16+:16]),
         .o_valid(normal_o_valid[d]),.o_ready(normal_o_ready[d]),.o_data(normal_o_data[d*512+:512]),
         .o_last(normal_o_last[d]),.o_rank(normal_o_rank[d*7+:7]),.o_err(normal_o_err[d]),.engine_fault(normal_engine_fault[d]),
         .bridge_req_v(store_req_v),.bridge_req_r(store_req_r),.bridge_req(store_req),
         .bridge_rsp_v(shared_gather_rsp_v&&store_response),.bridge_rsp_r(store_rsp_r),.bridge_rsp(shared_gather_rsp));
        ot_hbm_integrated_formatter_provider #(.ENABLE(FORMATTER_ENABLE),.VM_AW(VM_AW)) u_formatter_provider(
         .clk(clk_sm),.por_n(rst_sm_n),.start(formatter_start_v[d]),.start_ready(formatter_start_r[d]),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),
         .arena_base(bound_arena_base),.arena_limit(bound_arena_limit),
         .gather_retained(gather_retained[d]),.arena_visible(gather_arena_visible[d]),
         .gather_granted(fmt_lease_valid),.gather_frame73(fmt_lease_frame),
         .pair_v(index_pair_v[d]),.pair_r(index_pair_r[d]),.pair_token17(index_pair_token17[d*17+:17]),
         .pair_job(index_pair[d*85+53+:32]),.pair_gen(index_pair[d*85+49+:4]),.pair_pos(index_pair[d*85+29+:20]),
         .pair_rank(index_pair[d*85+22+:7]),.pair_word(index_pair[d*85+16+:6]),.pair_tag(index_pair[d*85+:16]),
         .pairs_v(index_pairs_v[d]),.pairs_r(index_pairs_r[d]),.pairs(index_pairs[d*599+2+:512]),
         .pairs_frame73(index_pairs_frame73[d*73+:73]),
         .pairs_job(index_pairs[d*599+567+:32]),.pairs_gen(index_pairs[d*599+563+:4]),.pairs_pos(index_pairs[d*599+543+:20]),
         .pairs_rank(index_pairs[d*599+536+:7]),.pairs_word(index_pairs[d*599+530+:6]),.pairs_tag(index_pairs[d*599+514+:16]),
         .pairs_checked(index_pairs[d*599+1]),.pairs_uncorrectable(index_pairs[d*599]),.retained(fmt_retained),.fault(fmt_fault),
         .bridge_req_v(fmt_req_v),.bridge_req_r(fmt_req_r),.bridge_req(fmt_req),
         .bridge_rsp_v(shared_gather_rsp_v&&formatter_response),.bridge_rsp_r(fmt_rsp_r),.bridge_rsp(shared_gather_rsp),
         .release_v(formatter_release_v[d]),.release_r(formatter_release_r[d]),
         .release_job(gather_release_frame[d*73+:32]),.release_gen(gather_release_frame[d*73+32+:4]),
         .release_pos(gather_release_frame[d*73+53+:20]),.release_token17(gather_release_frame[d*73+36+:17]),
         .publication_done(gather_result_published[d]),.source_reverse_done(gather_reverse_done[d]));
        ot_hbm_integrated_gather_owner #(.ENABLE(1),.VM_AW(VM_AW)) u_shared(
         .clk(clk_sm),.por_n(rst_sm_n),
         .desc_v(gather_desc_v[d]),.desc_r(gather_desc_r[d]),.desc_index(gather_desc_index[d*3+:3]),.desc_data(gather_desc_data[d*64+:64]),
         .start_v(gather_start_v[d]),.start_r(gather_start_r[d]),.installed_book_valid(gather_book_valid[d]),
         .job(cpl_job),.gen(cpl_generation),.token(launch_token),.pos(launch_pos),
         .retained(gather_retained[d]),.arena_visible(gather_arena_visible[d]),.sink_visible(gather_sink_visible[d]),.fault(shared_fault),
         .bound_arena_base(bound_arena_base),.bound_arena_limit(bound_arena_limit),
         .formatter_lease_valid(fmt_lease_valid),.formatter_lease_frame(fmt_lease_frame),
         .req_v(shared_gather_req_v),.req_r(shared_gather_req_r),
         .req_kind(shared_gather_req[0+:3]),.req_addr(shared_gather_req[3+:32]),.req_tag(shared_gather_req[35+:16]),
         .req_rank(shared_gather_req[51+:7]),.req_word(shared_gather_req[58+:6]),.req_data(shared_gather_req[64+:512]),
         .req_job(shared_gather_req[576+:32]),.req_gen(shared_gather_req[608+:4]),
         .req_token(shared_gather_req[612+:17]),.req_pos(shared_gather_req[629+:20]),
         .rsp_v(shared_gather_rsp_v),.rsp_r(shared_gather_rsp_r),
         .rsp_checked(shared_gather_rsp[0]),.rsp_kind(shared_gather_rsp[1+:3]),.rsp_tag(shared_gather_rsp[4+:16]),
         .rsp_addr(shared_gather_rsp[20+:32]),.rsp_data(shared_gather_rsp[52+:512]),
         .held_job(shared_gather_rsp[564+:32]),.held_gen(shared_gather_rsp[596+:4]),
         .held_token(shared_gather_rsp[600+:17]),.held_pos(shared_gather_rsp[617+:20]),
         .release_v(gather_release_v[d]&&!fmt_retained),.release_r(bridge_release_r),
         .release_job(gather_release_frame[d*73+:32]),.release_gen(gather_release_frame[d*73+32+:4]),
         .release_token(gather_release_frame[d*73+36+:17]),.release_pos(gather_release_frame[d*73+53+:20]),
         .result_published(gather_result_published[d]),.source_reverse_done(gather_reverse_done[d]),
         .native_clients_drained(all_prior_quiet),.cdc_drained(native_credit_empty),.provider_fault(w2_sink_fault|w2_sector_fault[d]|(|cdc_f)|mem_fault|fmt_fault|store_fault),
         .observe_req(obs_req),.observe_rsp(obs_rsp),.observe_req_we(obs_req_we),.observe_rsp_we(obs_rsp_we),
         .observe_req_tag(obs_req_tag),.observe_rsp_tag(obs_rsp_tag),.return_offer(return_offer),.response_authorized(response_authorized),
         .native_job(cpl_job),.native_gen(cpl_generation),.native_token(launch_token),.native_pos(launch_pos),
         .native_credit_empty(native_credit_empty),.shared_idle(shared_idle),
         .peer_lease_v({w2_lease_v[d],sfu_route?sfu_lease_v:norm_route?norm_lease_v:su_lease_v}),.peer_quiet({w2_route_quiet&&!w2_sink_retained,sfu_route?sfu_quiet:norm_route?norm_quiet:su_quiet}),
         .peer_release_v({w2_release_v[d]&&w2_route_drained&&(!W2_RESULT_ENABLE||w2_sink_retire_r),sfu_route?sfu_release_v:norm_route?norm_release_v:su_release_v}),.peer_release_r(peer_releases),.peer_lease_granted(peer_grants),
         .peer_lease_job({w2_lease_frame[d*73+:32],peer0_frame[31:0]}),.peer_lease_gen({w2_lease_frame[d*73+32+:4],peer0_frame[35:32]}),
         .peer_lease_token({w2_lease_frame[d*73+36+:17],peer0_frame[52:36]}),.peer_lease_pos({w2_lease_frame[d*73+53+:20],peer0_frame[72:53]}),
         .peer_release_job({w2_release_frame[d*73+:32],peer0_frame[31:0]}),.peer_release_gen({w2_release_frame[d*73+32+:4],peer0_frame[35:32]}),
         .peer_release_token({w2_release_frame[d*73+36+:17],peer0_frame[52:36]}),.peer_release_pos({w2_release_frame[d*73+53+:20],peer0_frame[72:53]}),
         .p_req_v(p_req_v),.p_req_rdy(p_req_rdy),.p_req_we(p_req_we),.p_req_addr(p_req_addr),.p_req_wdata(p_req_wdata),
         .p_req_wstrb(p_req_wstrb),.p_req_tag(p_req_tag),.p_rsp_v(p_rsp_v),.p_rsp_rdy(p_rsp_rdy),
         .p_rsp_we(p_rsp_we),.p_rsp_tag(p_rsp_tag),.p_rsp_data(p_rsp_data),
         .m_req_v(c_req_v[0]),.m_req_rdy(c_req_rdy[0]),.m_req_we(c_req_we[0]),.m_req_addr(c_req_addr[31:0]),
         .m_req_wdata(c_req_wdata[255:0]),.m_req_wstrb(c_req_wstrb[31:0]),.m_req_tag(c_req_tag[15:0]),
         .m_rsp_v(c_rsp_v[0]),.m_rsp_rdy(c_rsp_rdy[0]),.m_rsp_we(c_rsp_we[0]),.m_rsp_tag(c_rsp_tag[15:0]),.m_rsp_data(c_rsp_data[255:0]));
        wire sfu_stage_warm_ack;
        assign sfu_warm_ack[d]=sfu_stage_warm_ack&&(!SFU_NATIVE_VM_ENABLE||sfu_vm_warm_ack[d]);
        wire nv_enroll_v,nv_enroll_r,nv_tx_v,nv_tx_r,nv_tx_last,nv_done,nv_complete_v,nv_complete_r,nv_drained,nv_fault;
        wire [1023:0] nv_tx_d;wire [72:0] nv_tx_owner,nv_complete_frame;wire [3:0] nv_tx_index;wire [31:0] nv_complete_tag;
        wire nv_source_owned=sfu_allocation_valid[d]&&sfu_allocation_frame[d*73+:73]==actual_cp_frame;
        if(SFU_NATIVE_VM_ENABLE)begin:g_sfu_native_vm
         wire vm_bind_ready,vm_activation_wr_ready,vm_activation_rd_ready,vm_su_pub_ready,vm_index_read_ready,vm_retire_ready;
         wire vm_norm_ACK_v,vm_norm_rsp_v;
         assign norm_ACK_v=vm_norm_ACK_v&&norm_native_route;
         assign sfu_vm_su_ACK_v[d]=vm_norm_ACK_v&&!norm_native_route;
         assign norm_rsp_v=vm_norm_rsp_v&&norm_root_reads;
         assign sfu_vm_index_rsp_v[d]=vm_norm_rsp_v&&!norm_root_reads;
         assign sfu_vm_bind_r[d]=vm_bind_ready&&!cp_reset_req[d];
         assign sfu_vm_activation_wr_r[d]=vm_activation_wr_ready&&!cp_reset_req[d];
         assign sfu_vm_activation_rd_r[d]=vm_activation_rd_ready&&!cp_reset_req[d];
         assign sfu_vm_su_pub_r[d]=vm_su_pub_ready&&!cp_reset_req[d]&&!norm_native_route;
         assign norm_pub_r=vm_su_pub_ready&&norm_native_route;
         assign sfu_vm_index_read_r[d]=vm_index_read_ready&&!cp_reset_req[d]&&norm_result_reads;
         assign norm_read_r=vm_index_read_ready&&norm_root_reads;
         assign sfu_vm_retire_r[d]=vm_retire_ready&&!sfu_retained[d]&&!norm_retained[d];
         ot_hbm_die_vm_sfu_publication_root #(.ENABLE(1)) u_vm(
          .clk_sm(clk_sm),.por_n(rst_sm_n),.warm_req(cp_reset_req[d]&&nv_drained&&(!norm_retained[d]||norm_checked)),
          .bind_v(sfu_vm_bind_v[d]&&!cp_reset_req[d]),
          .bind_r(vm_bind_ready),
          .bind_frame(sfu_vm_bind_frame[d*73+:73]),
          .bind_rank(sfu_vm_bind_rank[d*7+:7]),
          .bind_base(sfu_vm_bind_base[d*32+:32]),
          .bind_span(sfu_vm_bind_span[d*32+:32]),
          .retire_v(sfu_vm_retire_v[d]&&!sfu_retained[d]&&!norm_retained[d]),
          .retire_r(vm_retire_ready),
          .retire_frame(sfu_vm_retire_frame[d*73+:73]),
          .held_frame(sfu_vm_held_frame[d*73+:73]),
          .retained(sfu_vm_retained[d]),
          .warm_ack(sfu_vm_warm_ack[d]),
          .fault(sfu_vm_fault[d]),
          .activation_wr_v(sfu_vm_activation_wr_v[d]&&!cp_reset_req[d]),
          .activation_wr_r(vm_activation_wr_ready),
          .activation_wr_frame(sfu_vm_activation_wr_frame[d*73+:73]),
          .activation_wr_bank(sfu_vm_activation_wr_bank[d]),
          .activation_wr_addr(sfu_vm_activation_wr_addr[d*7+:7]),
          .activation_wr_data(sfu_vm_activation_wr_data[d*2063+:2063]),
          .activation_wr_owner(sfu_vm_activation_wr_owner[d*192+:192]),
          .activation_ACK_v(sfu_vm_activation_ACK_v[d]),
          .activation_ACK_r(sfu_vm_activation_ACK_r[d]),
          .activation_ACK_frame(sfu_vm_activation_ACK_frame[d*73+:73]),
          .activation_ACK_owner(sfu_vm_activation_ACK_owner[d*192+:192]),
          .activation_rd_v(sfu_vm_activation_rd_v[d]&&!cp_reset_req[d]),
          .activation_rd_r(vm_activation_rd_ready),
          .activation_rd_frame(sfu_vm_activation_rd_frame[d*73+:73]),
          .activation_rd_bank(sfu_vm_activation_rd_bank[d]),
          .activation_rd_addr(sfu_vm_activation_rd_addr[d*7+:7]),
          .activation_rd_owner(sfu_vm_activation_rd_owner[d*192+:192]),
          .tap_v(sfu_vm_tap_v[d*4+:4]),
          .tap_r(sfu_vm_tap_r[d*4+:4]),
          .tap_data(sfu_vm_tap_data[d*8252+:8252]),
          .tap_owner(sfu_vm_tap_owner[d*768+:768]),
          .tap_frame(sfu_vm_tap_frame[d*292+:292]),
          .tap_source_clk(sfu_vm_tap_source_clk[d*4+:4]),
          .tap_ACK_v(sfu_vm_tap_ACK_v[d*4+:4]),
          .tap_ACK_r(sfu_vm_tap_ACK_r[d*4+:4]),
          .tap_ACK_owner(sfu_vm_tap_ACK_owner[d*768+:768]),
          .tap_ACK_frame(sfu_vm_tap_ACK_frame[d*292+:292]),
          .activation_release(sfu_vm_activation_release[d]),
          .activation_release_r(sfu_vm_activation_release_r[d]),
          .activation_release_frame(sfu_vm_activation_release_frame[d*73+:73]),
          .activation_release_owner(sfu_vm_activation_release_owner[d*192+:192]),
          .su_pub_v(norm_native_route?norm_pub_v:(sfu_vm_su_pub_v[d]&&!cp_reset_req[d])),
          .su_pub_r(vm_su_pub_ready),
          .su_pub_frame(norm_native_route?norm_held_frame[d*73+:73]:sfu_vm_su_pub_frame[d*73+:73]),
          .su_pub_addr(norm_native_route?norm_pub_addr:sfu_vm_su_pub_addr[d*32+:32]),
          .su_pub_data(norm_native_route?norm_pub_data:sfu_vm_su_pub_data[d*1024+:1024]),
          .su_ACK_v(vm_norm_ACK_v),
          .su_ACK_r(norm_native_route?norm_ACK_r:sfu_vm_su_ACK_r[d]),
          .publication_ACK_addr(sfu_vm_publication_ACK_addr[d*32+:32]),
          .publication_ACK_frame(sfu_vm_publication_ACK_frame[d*73+:73]),
          .index_read_v(norm_root_reads?norm_read_v:(sfu_vm_index_read_v[d]&&!cp_reset_req[d]&&norm_result_reads)),
          .index_read_r(vm_index_read_ready),
          .index_read_frame(norm_root_reads?norm_held_frame[d*73+:73]:sfu_vm_index_read_frame[d*73+:73]),
          .index_read_rank(norm_root_reads?norm_read_rank:sfu_vm_index_read_rank[d*7+:7]),
          .index_read_addr(norm_root_reads?norm_read_addr:sfu_vm_index_read_addr[d*32+:32]),
          .index_read_words(norm_root_reads?6'd32:sfu_vm_index_read_words[d*6+:6]),
          .index_read_tag(norm_root_reads?norm_read_tag:sfu_vm_index_read_tag[d*8+:8]),
          .index_rsp_v(vm_norm_rsp_v),
          .index_rsp_r(norm_root_reads?norm_rsp_r:sfu_vm_index_rsp_r[d]),
          .index_rsp_data(sfu_vm_index_rsp_data[d*1024+:1024]),
          .index_rsp_tag(sfu_vm_index_rsp_tag[d*8+:8]),
          .index_rsp_frame(sfu_vm_index_rsp_frame[d*73+:73]),
          .index_rsp_rank(sfu_vm_index_rsp_rank[d*7+:7]),
          .sfu_source_owned(nv_source_owned),.sfu_enroll_v(nv_enroll_v),.sfu_enroll_r(nv_enroll_r),
          .sfu_enroll_frame(sfu_enroll_frame[d*73+:73]),.sfu_base_word(sfu_dest_addr[d*32+:32]>>2),.sfu_tag(sfu_local_tag[d*32+:32]),
          .sfu_rx_v(nv_tx_v),.sfu_rx_r(nv_tx_r),.sfu_rx_data(nv_tx_d),.sfu_rx_frame(nv_tx_owner),.sfu_rx_index(nv_tx_index),.sfu_rx_last(nv_tx_last),
          .sfu_publication_done(nv_done),.sfu_complete_v(nv_complete_v),.sfu_complete_r(nv_complete_r),
          .sfu_complete_frame(nv_complete_frame),.sfu_complete_tag(nv_complete_tag),.sfu_retained(),.sfu_drained());
         assign nv_fault=sfu_vm_fault[d];
        end else begin:g_no_sfu_native_vm
         assign norm_pub_r=0;assign norm_read_r=0;assign norm_rsp_v=0;assign norm_ACK_v=0;
         assign sfu_vm_bind_r[d*1+:1]=0;
         assign sfu_vm_retire_r[d*1+:1]=0;
         assign sfu_vm_held_frame[d*73+:73]=0;
         assign sfu_vm_retained[d*1+:1]=0;
         assign sfu_vm_warm_ack[d*1+:1]=0;
         assign sfu_vm_fault[d*1+:1]=0;
         assign sfu_vm_activation_wr_r[d*1+:1]=0;
         assign sfu_vm_activation_ACK_v[d*1+:1]=0;
         assign sfu_vm_activation_ACK_frame[d*73+:73]=0;
         assign sfu_vm_activation_ACK_owner[d*192+:192]=0;
         assign sfu_vm_activation_rd_r[d*1+:1]=0;
         assign sfu_vm_tap_v[d*4+:4]=0;
         assign sfu_vm_tap_data[d*8252+:8252]=0;
         assign sfu_vm_tap_owner[d*768+:768]=0;
         assign sfu_vm_tap_frame[d*292+:292]=0;
         assign sfu_vm_tap_source_clk[d*4+:4]=0;
         assign sfu_vm_tap_ACK_r[d*4+:4]=0;
         assign sfu_vm_activation_release[d*1+:1]=0;
         assign sfu_vm_activation_release_frame[d*73+:73]=0;
         assign sfu_vm_activation_release_owner[d*192+:192]=0;
         assign sfu_vm_su_pub_r[d*1+:1]=0;
         assign sfu_vm_su_ACK_v[d*1+:1]=0;
         assign sfu_vm_publication_ACK_addr[d*32+:32]=0;
         assign sfu_vm_publication_ACK_frame[d*73+:73]=0;
         assign sfu_vm_index_read_r[d*1+:1]=0;
         assign sfu_vm_index_rsp_v[d*1+:1]=0;
         assign sfu_vm_index_rsp_data[d*1024+:1024]=0;
         assign sfu_vm_index_rsp_tag[d*8+:8]=0;
         assign sfu_vm_index_rsp_frame[d*73+:73]=0;
         assign sfu_vm_index_rsp_rank[d*7+:7]=0;
         assign nv_enroll_r=0;assign nv_tx_r=0;assign nv_done=0;assign nv_complete_v=0;
         assign nv_complete_frame=0;assign nv_complete_tag=0;assign nv_fault=0;
        end
        ot_hbm_integrated_sfu_provider_join #(.ENABLE(SFU_C12_ENABLE),.NATIVE_VM_PUBLICATION(SFU_NATIVE_VM_ENABLE)) u_sfu_c12(
         .clk(clk_sm),.por_n(rst_sm_n),.warm_req(cp_reset_req[d]),.warm_ack(sfu_stage_warm_ack),
         .enroll_v(sfu_enroll_v[d]&&sfu_admit),.enroll_r(sfu_offer_r),
         .enroll_frame(sfu_enroll_frame[d*73+:73]),.enroll_pc(sfu_pc[d*32+:32]),.enroll_op(sfu_op[d*32+:32]),
         .enroll_source(sfu_source[d*16+:16]),.enroll_expert(sfu_expert[d*9+:9]),.enroll_matrix(sfu_matrix[d]),
         .enroll_row(sfu_row[d*12+:12]),.enroll_count(sfu_count[d*9+:9]),
         .allocation_valid(sfu_allocation_valid[d]),.allocation_frame(sfu_allocation_frame[d*73+:73]),
         .source_addr(sfu_source_addr[d*32+:32]),.dest_addr(sfu_dest_addr[d*32+:32]),
         .source_base(sfu_source_base[d*32+:32]),.source_limit(sfu_source_limit[d*32+:32]),
         .dest_base(sfu_dest_base[d*32+:32]),.dest_limit(sfu_dest_limit[d*32+:32]),
         .fn(sfu_fn[d*3+:3]),.local_tag(sfu_local_tag[d*32+:32]),
         .owner_valid(!cp_reset_wait||sfu_retained[d]),.owner_frame(actual_cp_frame),
         .grant(peer_grants[0]&&sfu_route),.lease_v(sfu_lease_v),.quiet(sfu_quiet),
         .release_v(sfu_release_v),.release_r(peer_releases[0]&&sfu_route),
         .req_v(sfu_req_v),.req_r(p_req_rdy[1]&&sfu_route),.req(sfu_req),
         .rsp_v(p_rsp_v[1]&&sfu_route),.rsp_r(sfu_rsp_r),
         .rsp({p_rsp_tag[31:16],p_rsp_we[1],p_rsp_data[511:256]}),
         .native_enroll_v(nv_enroll_v),.native_enroll_r(nv_enroll_r),
         .native_tx_v(nv_tx_v),.native_tx_r(nv_tx_r),.native_tx_d(nv_tx_d),.native_tx_owner(nv_tx_owner),.native_tx_index(nv_tx_index),.native_tx_last(nv_tx_last),
         .native_publication_done(nv_done),.native_complete_v(nv_complete_v),.native_fault(nv_fault),
         .native_complete_frame(nv_complete_frame),.native_complete_tag(nv_complete_tag),.native_complete_r(nv_complete_r),.native_producer_drained(nv_drained),
         .publication_v(sfu_publication_v[d]),.publication_r(sfu_publication_r[d]),
         .publication_owner(sfu_publication_owner[d*73+:73]),
         .held_frame(sfu_held_frame[d*73+:73]),.retained(sfu_retained[d]),.fault(sfu_fault[d]),.ce(),.due());
        // One norm stage replaces its former standalone VM/stream enclosure.
        // No native1024/512 alias: the real vectorVM caller supplies rd_q and
        // held checked publication/provider receipts with full73 identity.
        ot_hbm_integrated_norm_stage #(.ENABLE(NORM_C12_ENABLE),.NATIVE_VM(NORM_NATIVE_VM_ENABLE),.KIND(NORM_KIND),.N(NORM_N),.D(NORM_D),.RD(NORM_RD),.AW(NORM_AW),.PUBLISH_QUANT(NORM_PUBLISH_QUANT)) u_norm_c12(
         .clk(clk_sm),.por_n(rst_sm_n),.warm_req(cp_reset_req[d]),
         .native_clock_enable(norm_clk_enable),.native_read_permit(norm_read_permit),
         .owner_valid((!cp_reset_wait||norm_retained[d])&&!norm_backend_fault),.owner_frame(actual_cp_frame),
         .grant(peer_grants[0]&&norm_route),.lease_v(norm_lease_v),.quiet(norm_quiet),
         .release_v(norm_release_v),.release_r(peer_releases[0]&&norm_route),
         .warm_ack(norm_warm_ack[d*(1)+:(1)]),
         .enroll_v(norm_enroll_v[d*(1)+:(1)]&&norm_admit),
         .enroll_r(norm_offer_r),
         .enroll_frame(norm_enroll_frame[d*(72+1)+:(72+1)]),
         .enroll_pc(norm_enroll_pc[d*(31+1)+:(31+1)]),
         .enroll_op(norm_enroll_op[d*(31+1)+:(31+1)]),
         .enroll_source(norm_enroll_source[d*(15+1)+:(15+1)]),
         .enroll_expert(norm_enroll_expert[d*(8+1)+:(8+1)]),
         .enroll_matrix(norm_enroll_matrix[d*(1)+:(1)]),
         .enroll_row(norm_enroll_row[d*(11+1)+:(11+1)]),
         .enroll_count(norm_enroll_count[d*(8+1)+:(8+1)]),
         .allocation_valid(NORM_NATIVE_VM_ENABLE?(sfu_vm_retained[d]&&!sfu_vm_fault[d]&&(!NORM_NATIVE_INPUT_CP||(norm_allocation_valid[d]&&norm_allocation_frame[d*73+:73]==norm_allocation_target))):norm_allocation_valid[d]),
         .allocation_frame(NORM_NATIVE_VM_ENABLE?sfu_vm_held_frame[d*73+:73]:norm_allocation_frame[d*73+:73]),
         .landing_reserved(NORM_NATIVE_VM_ENABLE?(sfu_vm_retained[d]&&!norm_backend_fault):norm_landing_reserved[d]),
         .landing_frame(NORM_NATIVE_VM_ENABLE?sfu_vm_held_frame[d*73+:73]:norm_landing_frame[d*73+:73]),
         .provider_drained(NORM_NATIVE_VM_ENABLE?norm_backend_drained:norm_provider_drained[d]),
         .publication_checked(NORM_NATIVE_VM_ENABLE?norm_checked:norm_publication_checked[d]),
         .publication_frame(NORM_NATIVE_VM_ENABLE?norm_held_frame[d*73+:73]:norm_publication_frame[d*73+:73]),
         .publication_v(norm_publication_v[d*(1)+:(1)]),
         .publication_r(norm_publication_r[d*(1)+:(1)]),
         .publication_owner(norm_publication_owner[d*(72+1)+:(72+1)]),
         .xbase(norm_xbase[d*(NORM_AW-1+1)+:(NORM_AW-1+1)]),
         .ubase(norm_ubase[d*(NORM_AW-1+1)+:(NORM_AW-1+1)]),
         .wbase(norm_wbase[d*(NORM_AW-1+1)+:(NORM_AW-1+1)]),
         .ybase(norm_ybase[d*(NORM_AW-1+1)+:(NORM_AW-1+1)]),
         .gain_base(norm_gain_base[d*(NORM_AW-1+1)+:(NORM_AW-1+1)]),
         .comb(norm_comb[d*(511+1)+:(511+1)]),
         .post_pre(norm_post_pre[d*(127+1)+:(127+1)]),
         .n_f(norm_n_f[d*(31+1)+:(31+1)]),
         .eps(norm_eps[d*(31+1)+:(31+1)]),
         .lim(norm_lim[d*(31+1)+:(31+1)]),
         .cos_t(norm_cos_t[d*((NORM_RD?NORM_RD/2:1)*32)+:((NORM_RD?NORM_RD/2:1)*32)]),
         .sin_t(norm_sin_t[d*((NORM_RD?NORM_RD/2:1)*32)+:((NORM_RD?NORM_RD/2:1)*32)]),
         .rd_addr(norm_rd_addr[d*(4*NORM_N*NORM_AW-1+1)+:(4*NORM_N*NORM_AW-1+1)]),
         .rd_re(norm_rd_re[d*(4*NORM_N-1+1)+:(4*NORM_N-1+1)]),
         .rd_src(norm_rd_src[d*(8*NORM_N-1+1)+:(8*NORM_N-1+1)]),
         .rd_q(NORM_NATIVE_VM_ENABLE?norm_native_q:norm_rd_q[d*4*NORM_N*32+:4*NORM_N*32]),
         .vm_we(norm_vm_we[d*(NORM_N-1+1)+:(NORM_N-1+1)]),
         .vm_waddr(norm_vm_waddr[d*(NORM_N*NORM_AW-1+1)+:(NORM_N*NORM_AW-1+1)]),
         .vm_wdata(norm_vm_wdata[d*(NORM_N*32-1+1)+:(NORM_N*32-1+1)]),
         .q_frame(norm_quant_frame),
         .q_valid(norm_q_valid[d*(1)+:(1)]),
         .q_index(norm_q_index[d*(7+1)+:(7+1)]),
         .q_codes(norm_q_codes[d*(NORM_N*8-1+1)+:(NORM_N*8-1+1)]),
         .q_exp(norm_q_exp[d*((NORM_N/32)*10-1+1)+:((NORM_N/32)*10-1+1)]),
         .q_bf16(norm_q_bf16[d*(NORM_N*16-1+1)+:(NORM_N*16-1+1)]),
         .reserve_events(norm_reserve_events[d*(15+1)+:(15+1)]),
         .held_frame(norm_held_frame[d*(72+1)+:(72+1)]),
         .retained(norm_retained[d*(1)+:(1)]),
         .fault(norm_fault[d*(1)+:(1)]),
         .ce(norm_ce[d*(1)+:(1)]),
         .due(norm_due[d*(1)+:(1)]));
        ot_hbm_norm_native_vm_adapter #(.ENABLE(NORM_NATIVE_VM_ENABLE),.N(NORM_N),.D(NORM_D),.AW(NORM_AW),.PUBLISH_QUANT(NORM_PUBLISH_QUANT),.INPUT_CP(NORM_NATIVE_INPUT_CP)) u_norm_native_adapter(
         .clk(clk_sm),.por_n(rst_sm_n),.enroll(norm_enroll_v[d]&&norm_enroll_r[d]),.bind_accept(sfu_vm_bind_v[d]&&sfu_vm_bind_r[d]),
         .retained(norm_retained[d]),.owner_valid(actual_cp_frame==norm_held_frame[d*73+:73]&&sfu_vm_retained[d]&&!sfu_vm_fault[d]&&(!NORM_NATIVE_INPUT_CP||(norm_allocation_valid[d]&&norm_allocation_frame[d*73+:73]==norm_held_frame[d*73+:73]))),
         .frame(norm_held_frame[d*73+:73]),.rank(sfu_vm_bind_rank[d*7+:7]),
         .rd_addr(norm_rd_addr[d*4*NORM_N*NORM_AW+:4*NORM_N*NORM_AW]),.rd_re(norm_rd_re[d*4*NORM_N+:4*NORM_N]),.rd_q(norm_native_q),
         .wr_we(norm_vm_we[d*NORM_N+:NORM_N]),.wr_addr(norm_vm_waddr[d*NORM_N*NORM_AW+:NORM_N*NORM_AW]),.wr_data(norm_vm_wdata[d*NORM_N*32+:NORM_N*32]),
         .q_valid(norm_q_valid[d]),.q_index(norm_q_index[d*8+:8]),.q_codes(norm_q_codes[d*NORM_N*8+:NORM_N*8]),
         .q_exp(norm_q_exp[d*(NORM_N/32)*10+:(NORM_N/32)*10]),.q_bf16(norm_q_bf16[d*NORM_N*16+:NORM_N*16]),
         .q_frame(norm_quant_frame),.quant_base({{(32-NORM_AW){1'b0}},norm_ybase[d*NORM_AW+:NORM_AW]}+NORM_D),
         .cp_req_v(norm_cp_req_v),.cp_req_r(p_req_rdy[1]&&norm_route),.cp_req(norm_cp_req),
         .cp_rsp_v(p_rsp_v[1]&&norm_route),.cp_rsp_r(norm_cp_rsp_r),.cp_rsp({p_rsp_tag[31:16],p_rsp_we[1],p_rsp_data[511:256]}),
         .child_enable(norm_clk_enable),.read_permit(norm_read_permit),.drained(norm_backend_drained),.publication_checked(norm_checked),.fault(norm_backend_fault),
         .read_v(norm_read_v),.read_r(norm_read_r),.read_addr(norm_read_addr),.read_tag(norm_read_tag),.read_rank(norm_read_rank),
         .rsp_v(norm_rsp_v),.rsp_r(norm_rsp_r),.rsp_data(sfu_vm_index_rsp_data[d*1024+:1024]),.rsp_frame(sfu_vm_index_rsp_frame[d*73+:73]),.rsp_tag(sfu_vm_index_rsp_tag[d*8+:8]),.rsp_rank(sfu_vm_index_rsp_rank[d*7+:7]),
         .pub_v(norm_pub_v),.pub_r(norm_pub_r),.pub_addr(norm_pub_addr),.pub_data(norm_pub_data),
         .ACK_v(norm_ACK_v),.ACK_r(norm_ACK_r),.ACK_frame(sfu_vm_publication_ACK_frame[d*73+:73]),.ACK_addr(sfu_vm_publication_ACK_addr[d*32+:32]));
        ot_hbm_accel_su_parent_exec #(.ENABLE(SU_ENABLE),.PROTECTED_FRAME_BIND(1),.IMW(IMW)) u_su_exec(
         .clk(clk_sm),.rst_n(rst_sm_n),.owned(su_executor_owned),.config_idle(db_rdy[d]&&!su_selected&&!gather_retained[d]&&!fmt_retained&&w2_route_quiet),
         .loader_we(SU_ENABLE && im_we[d*NSM] && im_addr[IMW-1]),.loader_addr(im_addr),.loader_data(im_data),
         .selected_pc(su_executor_pc),.job_id(su_provider_frame[31:0]),.protected_frame(su_provider_frame),.req_v(su_req_v),.req_rdy(su_req_rdy),.req(su_request),
         .rsp_v(su_rsp_v),.rsp_rdy(su_rsp_rdy),.rsp(su_response),.done(su_exec_done),.fault(su_exec_fault),
         .virtual_edges(),.read_requests(),.write_requests(),.publication_requests(),.retired_original_ops(su_retired));
        genvar u;
        for(u=1;u<NCL;u=u+1) begin:g_prior
         assign c_req_v[u]=a_req_v[u];assign a_req_rdy[u]=c_req_rdy[u];
         assign c_req_we[u]=a_req_we[u];assign c_req_addr[u*32+:32]=a_req_addr[u*32+:32];
         assign c_req_wdata[u*256+:256]=a_req_wdata[u*256+:256];
         assign c_req_wstrb[u*32+:32]=a_req_wstrb[u*32+:32];assign c_req_tag[u*16+:16]=a_req_tag[u*16+:16];
         assign a_rsp_v[u]=c_rsp_v[u]&&response_authorized[u];assign c_rsp_rdy[u]=a_rsp_rdy[u]&&response_authorized[u];
         assign return_offer[u]=c_rsp_v[u];
         assign a_rsp_we[u]=c_rsp_we[u];assign a_rsp_tag[u*16+:16]=c_rsp_tag[u*16+:16];
         assign a_rsp_data[u*256+:256]=c_rsp_data[u*256+:256];
         assign obs_req[u]=a_req_v[u] && a_req_rdy[u];assign obs_rsp[u]=a_rsp_v[u] && a_rsp_rdy[u];
         assign obs_req_tag[u*16+:16]=a_req_tag[u*16+:16];assign obs_rsp_tag[u*16+:16]=a_rsp_tag[u*16+:16];
         assign obs_req_we[u]=a_req_we[u];assign obs_rsp_we[u]=a_rsp_we[u];
        end
        // collective ports of the SMs
        wire [NSM-1:0] cs_req_v, cs_req_rdy, cs_mode, cs_rsp_v, cs_rsp_rdy;
        wire [NSM*8-1:0] cs_count;
        wire [NSM*NL*32-1:0] cs_data;
        wire [NL*32-1:0] cs_rsp_data;
        for (s = 0; s < NSM; s = s + 1) begin : g_sm
            wire [31:0] st_instr, st_cycles, st_stall_mem, st_tc_rows;
            wire [31:0] rd;
            assign res_data[s*32 +: 32] = rd;
            ot_ds_hbm_simt_sm20 #(.TW(TW),.PW(PW), .ENABLE(1), .NL(NL), .IMW(IMW), .HAS_DIV(HAS_DIV), .HAS_BD(HAS_BD)) u_sm (
                .clk(clk_sm), .rst_n(rst_sm_n), .sm_id(s[7:0]), .die_id(d[7:0]),
                .im_we(im_we[d*NSM + s] && !(SU_ENABLE && s==0 && im_addr[IMW-1])), .im_addr(im_addr), .im_data(im_data),
                .launch_v(native_launch[s]), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
                .sm_done(native_done[s]), .sm_fault(native_fault[s]), .res_v(res_v[s]), .res_data(rd), .busy(busy[s]),
                .bar_arrive(bar_arr[s]), .bar_release(bar_rel[s]),
                .lreq_v(a_req_v[2*s]), .lreq_rdy(a_req_rdy[2*s]), .lreq_we(a_req_we[2*s]),
                .lreq_addr(a_req_addr[2*s*32 +: 32]), .lreq_wdata(a_req_wdata[2*s*256 +: 256]),
                .lreq_wstrb(a_req_wstrb[2*s*32 +: 32]), .lreq_tag(a_req_tag[2*s*16 +: 16]),
                .lrsp_v(a_rsp_v[2*s]), .lrsp_rdy(a_rsp_rdy[2*s]), .lrsp_tag(a_rsp_tag[2*s*16 +: 16]),
                .lrsp_we(a_rsp_we[2*s]), .lrsp_data(a_rsp_data[2*s*256 +: 256]),
                .treq_v(a_req_v[2*s+1]), .treq_rdy(a_req_rdy[2*s+1]), .treq_addr(a_req_addr[(2*s+1)*32 +: 32]),
                .treq_tag(a_req_tag[(2*s+1)*16 +: 16]), .trsp_v(a_rsp_v[2*s+1]), .trsp_rdy(a_rsp_rdy[2*s+1]),
                .trsp_tag(a_rsp_tag[(2*s+1)*16 +: 16]), .trsp_data(a_rsp_data[(2*s+1)*256 +: 256]),
                .coll_req_v(cs_req_v[s]), .coll_req_rdy(cs_req_rdy[s]), .coll_mode(cs_mode[s]),
                .coll_count(cs_count[s*8 +: 8]), .coll_data(cs_data[s*NL*32 +: NL*32]), .coll_rsp_v(cs_rsp_v[s]),
                .coll_rsp_rdy(cs_rsp_rdy[s]), .coll_rsp_data(cs_rsp_data),
                .st_instr(st_instr), .st_cycles(st_cycles), .st_stall_mem(st_stall_mem), .st_tc_rows(st_tc_rows));
            // the bulk-copy port only reads
            assign a_req_we[2*s+1] = 1'b0;
            assign a_req_wdata[(2*s+1)*256 +: 256] = 256'd0;
            assign a_req_wstrb[(2*s+1)*32 +: 32] = 32'd0;
        end
        genvar c;
        for (c = 0; c < NCL; c = c + 1) begin : g_cdc
            ot_gpu_mreq_cdc #(.ENABLE(1), .AW(3)) u_x (
                .clk_s(clk_sm), .rst_s_n(rst_sm_n), .clk_m(clk_mem), .rst_m_n(rst_mem_n),
                .s_req_v(c_req_v[c]), .s_req_rdy(c_req_rdy[c]), .s_req_we(c_req_we[c]), .s_req_addr(c_req_addr[c*32 +: 32]),
                .s_req_wdata(c_req_wdata[c*256 +: 256]), .s_req_wstrb(c_req_wstrb[c*32 +: 32]), .s_req_tag(c_req_tag[c*16 +: 16]),
                .s_rsp_v(c_rsp_v[c]), .s_rsp_rdy(c_rsp_rdy[c]), .s_rsp_tag(c_rsp_tag[c*16 +: 16]), .s_rsp_we(c_rsp_we[c]),
                .s_rsp_data(c_rsp_data[c*256 +: 256]),
                .m_req_v(x_req_v[c]), .m_req_rdy(x_req_rdy[c]), .m_req_we(x_req_we[c]), .m_req_addr(x_req_addr[c*32 +: 32]),
                .m_req_wdata(x_req_wdata[c*256 +: 256]), .m_req_wstrb(x_req_wstrb[c*32 +: 32]), .m_req_tag(x_req_tag[c*16 +: 16]),
                .m_rsp_v(x_rsp_v[c]), .m_rsp_rdy(x_rsp_rdy[c]), .m_rsp_tag(x_rsp_tag[c*16 +: 16]), .m_rsp_we(x_rsp_we[c]),
                .m_rsp_data(x_rsp_data[c*256 +: 256]), .fault(cdc_f[c]));
        end
        wire mem_fault;
        ot_gpu_memsys_adapter #(.ENABLE(1), .NC(NCL), .NS(NS), .NPC(NPC), .MEM_WORDS(MEM_WORDS), .DIE(d), .USE_W2(USE_W2)) u_mem (
            .clk(clk_mem), .rst_n(rst_mem_n),
            .c_req_v(x_req_v), .c_req_rdy(x_req_rdy), .c_req_we(x_req_we), .c_req_addr(x_req_addr),
            .c_req_wdata(x_req_wdata), .c_req_wstrb(x_req_wstrb), .c_req_tag(x_req_tag),
            .c_rsp_v(x_rsp_v), .c_rsp_rdy(x_rsp_rdy), .c_rsp_tag(x_rsp_tag), .c_rsp_we(x_rsp_we), .c_rsp_data(x_rsp_data),
            .fault(mem_fault));
        ot_gpu_coll_mux #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_cmux (
            .clk(clk_sm), .rst_n(rst_sm_n), .s_req_v(cs_req_v), .s_req_rdy(cs_req_rdy), .s_mode(cs_mode),
            .s_count(cs_count), .s_data(cs_data), .s_rsp_v(cs_rsp_v), .s_rsp_rdy(cs_rsp_rdy), .s_rsp_data(cs_rsp_data),
            .m_req_v(ep_req_v[d]), .m_req_rdy(ep_req_rdy[d]), .m_mode(ep_mode[d]), .m_count(ep_count[d*8 +: 8]),
            .m_data(ep_data[d*NL*32 +: NL*32]), .m_rsp_v(ep_rsp_v[d]), .m_rsp_rdy(ep_rsp_rdy[d]),
            .m_rsp_data(ep_rsp_data[d*NL*32 +: NL*32]));
        assign die_fault[d] = (|sm_fault) | (|cdc_f) | mem_fault | shared_fault;
    end
    assign sys_fault = (|die_fault) | coll_fault;
end endgenerate
endmodule
