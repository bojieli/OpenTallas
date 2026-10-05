#include "Vot_gpu_qwen_hbm_integrated_ranked.h"
#include "verilated.h"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <string>
#include <vector>
#ifndef CANONICAL_ENABLE
#define CANONICAL_ENABLE 0
#endif
static std::vector<uint32_t> unpack(std::string s, unsigned bits) {
 if(s.empty() || s.size()>(bits+3)/4) throw std::runtime_error("width");
 std::vector<uint32_t> v((bits+31)/32,0);
 for(unsigned i=0;i<s.size();i++){char c=s[s.size()-1-i]; unsigned n;
 if(c>='0'&&c<='9')n=c-'0'; else if(c>='a'&&c<='f')n=c-'a'+10;else throw std::runtime_error("hex");
 v[i/8]|=n<<((i%8)*4);}
 if(bits%32 && (v.back()>>(bits%32)))throw std::runtime_error("width");return v;}
static void word(uint32_t v){std::cout<<std::hex<<std::setfill('0')<<std::setw(8)<<v;}
int main(int argc,char**argv){VerilatedContext context;context.commandArgs(argc,argv);
 Vot_gpu_qwen_hbm_integrated_ranked dut(&context); std::string line; unsigned half=0; const unsigned delta[6]={416,417,417,416,417,417};
 while(std::getline(std::cin,line)){try{std::istringstream in(line);std::string op,name,value,extra;in>>op;
 if(op=="HELLO"){dut.eval();std::cout<<"ot_gpu_qwen_hbm_integrated_ranked ENABLE="<<unsigned(dut.assembly_enabled)<<" SM=64 W2=256 RANKS=2 PC_PER_RANK=128";}
 else if(op=="EVAL"){if(in>>extra)throw std::runtime_error("extra");dut.eval();std::cout<<"OK";}
 else if(op=="EDGE"){if(in>>extra)throw std::runtime_error("extra");dut.stream_clk=0;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=1;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=0;dut.eval();std::cout<<"OK";}
 else if(op=="GET"){in>>name;if(in>>extra)throw std::runtime_error("extra");
 if(name=="stream_clk"){word(dut.stream_clk);} else
 if(name=="assembly_enabled"){word(dut.assembly_enabled);} else
 if(name=="sector_map_rank"){word(dut.sector_map_rank);} else
 if(name=="sector_reverse_rank"){word(dut.sector_reverse_rank);} else
 if(name=="sector_rank_refusal"){word(dut.sector_rank_refusal);} else
 if(name=="state_rpc_por_n"){word(dut.state_rpc_por_n);} else
 if(name=="state_rpc_run_enable"){word(dut.state_rpc_run_enable);} else
 if(name=="state_rpc_local_reset"){word(dut.state_rpc_local_reset);} else
 if(name=="state_rpc_source_bound"){word(dut.state_rpc_source_bound);} else
 if(name=="state_rpc_state_base_rank0"){word(uint32_t(dut.state_rpc_state_base_rank0>>32));word(uint32_t(dut.state_rpc_state_base_rank0));} else
 if(name=="state_rpc_state_base_rank1"){word(uint32_t(dut.state_rpc_state_base_rank1>>32));word(uint32_t(dut.state_rpc_state_base_rank1));} else
 if(name=="state_rpc_rpc_valid"){word(dut.state_rpc_rpc_valid);} else
 if(name=="state_rpc_rpc_ready"){word(dut.state_rpc_rpc_ready);} else
 if(name=="state_rpc_rpc_identity"){word(uint32_t(dut.state_rpc_rpc_identity>>32));word(uint32_t(dut.state_rpc_rpc_identity));} else
 if(name=="state_rpc_rpc_rank"){word(dut.state_rpc_rpc_rank);} else
 if(name=="state_rpc_rpc_write"){word(dut.state_rpc_rpc_write);} else
 if(name=="state_rpc_rpc_address"){word(uint32_t(dut.state_rpc_rpc_address>>32));word(uint32_t(dut.state_rpc_rpc_address));} else
 if(name=="state_rpc_rpc_bytes"){word(dut.state_rpc_rpc_bytes);} else
 if(name=="state_rpc_rpc_payload"){for(int i=7;i>=0;i--)word(dut.state_rpc_rpc_payload[i]);} else
 if(name=="state_rpc_rpc_reply_valid"){word(dut.state_rpc_rpc_reply_valid);} else
 if(name=="state_rpc_rpc_reply_ready"){word(dut.state_rpc_rpc_reply_ready);} else
 if(name=="state_rpc_rpc_reply_identity"){word(uint32_t(dut.state_rpc_rpc_reply_identity>>32));word(uint32_t(dut.state_rpc_rpc_reply_identity));} else
 if(name=="state_rpc_rpc_reply_rank"){word(dut.state_rpc_rpc_reply_rank);} else
 if(name=="state_rpc_rpc_reply_address"){word(uint32_t(dut.state_rpc_rpc_reply_address>>32));word(uint32_t(dut.state_rpc_rpc_reply_address));} else
 if(name=="state_rpc_rpc_reply_bytes"){word(dut.state_rpc_rpc_reply_bytes);} else
 if(name=="state_rpc_root_accept"){word(dut.state_rpc_root_accept);} else
 if(name=="state_rpc_root_admit"){word(dut.state_rpc_root_admit);} else
 if(name=="state_rpc_root_identity"){word(uint32_t(dut.state_rpc_root_identity>>32));word(uint32_t(dut.state_rpc_root_identity));} else
 if(name=="state_rpc_root_retire"){word(dut.state_rpc_root_retire);} else
 if(name=="state_rpc_root_retire_ready"){word(dut.state_rpc_root_retire_ready);} else
 if(name=="state_rpc_root_retire_identity"){word(uint32_t(dut.state_rpc_root_retire_identity>>32));word(uint32_t(dut.state_rpc_root_retire_identity));} else
 if(name=="state_rpc_sector_offer_valid"){word(dut.state_rpc_sector_offer_valid);} else
 if(name=="state_rpc_sector_offer_rank"){word(dut.state_rpc_sector_offer_rank);} else
 if(name=="state_rpc_sector_offer_write"){word(dut.state_rpc_sector_offer_write);} else
 if(name=="state_rpc_sector_offer_identity"){word(uint32_t(dut.state_rpc_sector_offer_identity>>32));word(uint32_t(dut.state_rpc_sector_offer_identity));} else
 if(name=="state_rpc_sector_offer_source_addr"){word(uint32_t(dut.state_rpc_sector_offer_source_addr>>32));word(uint32_t(dut.state_rpc_sector_offer_source_addr));} else
 if(name=="state_rpc_map_valid"){word(dut.state_rpc_map_valid);} else
 if(name=="state_rpc_map_ready"){word(dut.state_rpc_map_ready);} else
 if(name=="state_rpc_map_rank"){word(dut.state_rpc_map_rank);} else
 if(name=="state_rpc_map_sector_granted"){word(dut.state_rpc_map_sector_granted);} else
 if(name=="state_rpc_map_source_addr"){word(uint32_t(dut.state_rpc_map_source_addr>>32));word(uint32_t(dut.state_rpc_map_source_addr));} else
 if(name=="state_rpc_map_physical_addr"){word(uint32_t(dut.state_rpc_map_physical_addr>>32));word(uint32_t(dut.state_rpc_map_physical_addr));} else
 if(name=="state_rpc_map_owner"){word(uint32_t(dut.state_rpc_map_owner>>32));word(uint32_t(dut.state_rpc_map_owner));} else
 if(name=="state_rpc_tap_command_valid"){word(dut.state_rpc_tap_command_valid);} else
 if(name=="state_rpc_tap_command_ready"){word(dut.state_rpc_tap_command_ready);} else
 if(name=="state_rpc_tap_command_rank"){word(dut.state_rpc_tap_command_rank);} else
 if(name=="state_rpc_tap_command_write"){word(dut.state_rpc_tap_command_write);} else
 if(name=="state_rpc_tap_command_sector_granted"){word(dut.state_rpc_tap_command_sector_granted);} else
 if(name=="state_rpc_tap_command_identity"){word(uint32_t(dut.state_rpc_tap_command_identity>>32));word(uint32_t(dut.state_rpc_tap_command_identity));} else
 if(name=="state_rpc_tap_command_source_addr"){word(uint32_t(dut.state_rpc_tap_command_source_addr>>32));word(uint32_t(dut.state_rpc_tap_command_source_addr));} else
 if(name=="state_rpc_tap_command_physical_addr"){word(uint32_t(dut.state_rpc_tap_command_physical_addr>>32));word(uint32_t(dut.state_rpc_tap_command_physical_addr));} else
 if(name=="state_rpc_tap_command_owner"){word(uint32_t(dut.state_rpc_tap_command_owner>>32));word(uint32_t(dut.state_rpc_tap_command_owner));} else
 if(name=="state_rpc_tap_command_new_data"){for(int i=7;i>=0;i--)word(dut.state_rpc_tap_command_new_data[i]);} else
 if(name=="state_rpc_tap_command_byte_mask"){word(dut.state_rpc_tap_command_byte_mask);} else
 if(name=="state_rpc_tap_reply_valid"){word(dut.state_rpc_tap_reply_valid);} else
 if(name=="state_rpc_tap_reply_ready"){word(dut.state_rpc_tap_reply_ready);} else
 if(name=="state_rpc_tap_reply_identity"){word(uint32_t(dut.state_rpc_tap_reply_identity>>32));word(uint32_t(dut.state_rpc_tap_reply_identity));} else
 if(name=="state_rpc_tap_reply_rank"){word(dut.state_rpc_tap_reply_rank);} else
 if(name=="state_rpc_tap_reply_owner"){word(uint32_t(dut.state_rpc_tap_reply_owner>>32));word(uint32_t(dut.state_rpc_tap_reply_owner));} else
 if(name=="state_rpc_tap_reply_physical_addr"){word(uint32_t(dut.state_rpc_tap_reply_physical_addr>>32));word(uint32_t(dut.state_rpc_tap_reply_physical_addr));} else
 if(name=="state_rpc_tap_reply_old_data"){for(int i=7;i>=0;i--)word(dut.state_rpc_tap_reply_old_data[i]);} else
 if(name=="state_rpc_sector_capture_valid"){word(dut.state_rpc_sector_capture_valid);} else
 if(name=="state_rpc_sector_capture_ready"){word(dut.state_rpc_sector_capture_ready);} else
 if(name=="state_rpc_sector_capture_source_addr"){word(uint32_t(dut.state_rpc_sector_capture_source_addr>>32));word(uint32_t(dut.state_rpc_sector_capture_source_addr));} else
 if(name=="state_rpc_sector_capture_old_data"){for(int i=7;i>=0;i--)word(dut.state_rpc_sector_capture_old_data[i]);} else
 if(name=="state_rpc_quiescent"){word(dut.state_rpc_quiescent);} else
 if(name=="state_rpc_fault"){word(dut.state_rpc_fault);} else
 if(name=="local_por_n"){word(dut.local_por_n);} else
 if(name=="local_run_enable"){word(dut.local_run_enable);} else
 if(name=="local_local_reset"){word(dut.local_local_reset);} else
 if(name=="local_source_bound"){word(dut.local_source_bound);} else
 if(name=="local_stage_root_accept"){word(uint32_t(dut.local_stage_root_accept>>32));word(uint32_t(dut.local_stage_root_accept));} else
 if(name=="local_stage_root_retire"){word(uint32_t(dut.local_stage_root_retire>>32));word(uint32_t(dut.local_stage_root_retire));} else
 if(name=="local_stage_root_owner"){for(int i=109;i>=0;i--)word(dut.local_stage_root_owner[i]);} else
 if(name=="local_stage_root_retire_owner"){for(int i=109;i>=0;i--)word(dut.local_stage_root_retire_owner[i]);} else
 if(name=="local_stage_root_admit"){word(uint32_t(dut.local_stage_root_admit>>32));word(uint32_t(dut.local_stage_root_admit));} else
 if(name=="local_stage_root_retire_ready"){word(uint32_t(dut.local_stage_root_retire_ready>>32));word(uint32_t(dut.local_stage_root_retire_ready));} else
 if(name=="local_shared_router_drained"){word(dut.local_shared_router_drained);} else
 if(name=="local_writer_retained"){word(dut.local_writer_retained);} else
 if(name=="local_shared_service_ready"){word(uint32_t(dut.local_shared_service_ready>>32));word(uint32_t(dut.local_shared_service_ready));} else
 if(name=="local_shared_service_done"){word(uint32_t(dut.local_shared_service_done>>32));word(uint32_t(dut.local_shared_service_done));} else
 if(name=="local_state_root_accept"){word(dut.local_state_root_accept);} else
 if(name=="local_state_root_retire"){word(dut.local_state_root_retire);} else
 if(name=="local_state_root_identity"){word(uint32_t(dut.local_state_root_identity>>32));word(uint32_t(dut.local_state_root_identity));} else
 if(name=="local_state_root_retire_identity"){word(uint32_t(dut.local_state_root_retire_identity>>32));word(uint32_t(dut.local_state_root_retire_identity));} else
 if(name=="local_state_root_admit"){word(dut.local_state_root_admit);} else
 if(name=="local_state_root_retire_ready"){word(dut.local_state_root_retire_ready);} else
 if(name=="local_state_tap_quiescent"){word(dut.local_state_tap_quiescent);} else
 if(name=="local_state_observer_drained"){word(dut.local_state_observer_drained);} else
 if(name=="local_metadata_ACK_held"){word(dut.local_metadata_ACK_held);} else
 if(name=="local_metadata_reverse_held"){word(dut.local_metadata_reverse_held);} else
 if(name=="local_metadata_event_held"){word(dut.local_metadata_event_held);} else
 if(name=="local_request_valid"){word(dut.local_request_valid);} else
 if(name=="local_request_ready"){word(dut.local_request_ready);} else
 if(name=="local_request_identity"){word(uint32_t(dut.local_request_identity>>32));word(uint32_t(dut.local_request_identity));} else
 if(name=="local_request_key"){word(dut.local_request_key);} else
 if(name=="local_response_valid"){word(dut.local_response_valid);} else
 if(name=="local_response_ready"){word(dut.local_response_ready);} else
 if(name=="local_response_identity"){for(int i=3;i>=0;i--)word(dut.local_response_identity[i]);} else
 if(name=="local_response_key"){word(uint32_t(dut.local_response_key>>32));word(uint32_t(dut.local_response_key));} else
 if(name=="local_response_quiet"){word(dut.local_response_quiet);} else
 if(name=="local_quiesce"){word(dut.local_quiesce);} else
 if(name=="local_roots_empty"){word(dut.local_roots_empty);} else
 if(name=="local_fault"){word(dut.local_fault);} else
 if(name=="issuer_inputs_bound_valid"){word(uint32_t(dut.issuer_inputs_bound_valid>>32));word(uint32_t(dut.issuer_inputs_bound_valid));} else
 if(name=="issuer_inputs_bound_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_inputs_bound_tuple[i]);} else
 if(name=="issuer_inputs_bound_mask"){for(int i=13;i>=0;i--)word(dut.issuer_inputs_bound_mask[i]);} else
 if(name=="issuer_issue_output_page_mask"){for(int i=63;i>=0;i--)word(dut.issuer_issue_output_page_mask[i]);} else
 if(name=="issuer_inputs_bound_ready"){word(uint32_t(dut.issuer_inputs_bound_ready>>32));word(uint32_t(dut.issuer_inputs_bound_ready));} else
 if(name=="issuer_rf_range_ack_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_rf_range_ack_tuple[i]);} else
 if(name=="issuer_rf_range_ack_page_mask"){for(int i=63;i>=0;i--)word(dut.issuer_rf_range_ack_page_mask[i]);} else
 if(name=="issuer_publish_page_mask"){for(int i=63;i>=0;i--)word(dut.issuer_publish_page_mask[i]);} else
 if(name=="issuer_input_terminal_valid"){word(uint32_t(dut.issuer_input_terminal_valid>>32));word(uint32_t(dut.issuer_input_terminal_valid));} else
 if(name=="issuer_input_reverse_valid"){word(uint32_t(dut.issuer_input_reverse_valid>>32));word(uint32_t(dut.issuer_input_reverse_valid));} else
 if(name=="issuer_input_terminal_ready"){word(uint32_t(dut.issuer_input_terminal_ready>>32));word(uint32_t(dut.issuer_input_terminal_ready));} else
 if(name=="issuer_input_reverse_ready"){word(uint32_t(dut.issuer_input_reverse_ready>>32));word(uint32_t(dut.issuer_input_reverse_ready));} else
 if(name=="issuer_input_terminal_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_input_terminal_tuple[i]);} else
 if(name=="issuer_input_reverse_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_input_reverse_tuple[i]);} else
 if(name=="issuer_input_terminal_mask"){for(int i=13;i>=0;i--)word(dut.issuer_input_terminal_mask[i]);} else
 if(name=="issuer_input_reverse_mask"){for(int i=13;i>=0;i--)word(dut.issuer_input_reverse_mask[i]);} else
 if(name=="issuer_por_n"){word(dut.issuer_por_n);} else
 if(name=="issuer_run_enable"){word(dut.issuer_run_enable);} else
 if(name=="issuer_session_begin_valid"){word(dut.issuer_session_begin_valid);} else
 if(name=="issuer_session_begin_id"){word(uint32_t(dut.issuer_session_begin_id>>32));word(uint32_t(dut.issuer_session_begin_id));} else
 if(name=="issuer_source_quiescent"){word(dut.issuer_source_quiescent);} else
 if(name=="issuer_session_begin_ready"){word(dut.issuer_session_begin_ready);} else
 if(name=="issuer_session_valid"){word(dut.issuer_session_valid);} else
 if(name=="issuer_session_fault"){word(dut.issuer_session_fault);} else
 if(name=="issuer_session_id"){word(uint32_t(dut.issuer_session_id>>32));word(uint32_t(dut.issuer_session_id));} else
 if(name=="issuer_issue_valid"){word(uint32_t(dut.issuer_issue_valid>>32));word(uint32_t(dut.issuer_issue_valid));} else
 if(name=="issuer_row_barrier_ready"){word(uint32_t(dut.issuer_row_barrier_ready>>32));word(uint32_t(dut.issuer_row_barrier_ready));} else
 if(name=="issuer_backend_go_ready"){word(uint32_t(dut.issuer_backend_go_ready>>32));word(uint32_t(dut.issuer_backend_go_ready));} else
 if(name=="issuer_issue_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_issue_tuple[i]);} else
 if(name=="issuer_issue_owner"){for(int i=109;i>=0;i--)word(dut.issuer_issue_owner[i]);} else
 if(name=="issuer_issue_ready"){word(uint32_t(dut.issuer_issue_ready>>32));word(uint32_t(dut.issuer_issue_ready));} else
 if(name=="issuer_backend_go_valid"){word(uint32_t(dut.issuer_backend_go_valid>>32));word(uint32_t(dut.issuer_backend_go_valid));} else
 if(name=="issuer_backend_go_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_backend_go_tuple[i]);} else
 if(name=="issuer_backend_go_owner"){for(int i=109;i>=0;i--)word(dut.issuer_backend_go_owner[i]);} else
 if(name=="issuer_producer_visible_valid"){word(uint32_t(dut.issuer_producer_visible_valid>>32));word(uint32_t(dut.issuer_producer_visible_valid));} else
 if(name=="issuer_rf_range_ack_valid"){word(uint32_t(dut.issuer_rf_range_ack_valid>>32));word(uint32_t(dut.issuer_rf_range_ack_valid));} else
 if(name=="issuer_whole_terminal_valid"){word(uint32_t(dut.issuer_whole_terminal_valid>>32));word(uint32_t(dut.issuer_whole_terminal_valid));} else
 if(name=="issuer_whole_reverse_valid"){word(uint32_t(dut.issuer_whole_reverse_valid>>32));word(uint32_t(dut.issuer_whole_reverse_valid));} else
 if(name=="issuer_producer_visible_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_producer_visible_tuple[i]);} else
 if(name=="issuer_whole_terminal_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_whole_terminal_tuple[i]);} else
 if(name=="issuer_whole_reverse_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_whole_reverse_tuple[i]);} else
 if(name=="issuer_rf_range_ack_owner"){for(int i=109;i>=0;i--)word(dut.issuer_rf_range_ack_owner[i]);} else
 if(name=="issuer_producer_visible_ready"){word(uint32_t(dut.issuer_producer_visible_ready>>32));word(uint32_t(dut.issuer_producer_visible_ready));} else
 if(name=="issuer_rf_range_ack_ready"){word(uint32_t(dut.issuer_rf_range_ack_ready>>32));word(uint32_t(dut.issuer_rf_range_ack_ready));} else
 if(name=="issuer_whole_terminal_ready"){word(uint32_t(dut.issuer_whole_terminal_ready>>32));word(uint32_t(dut.issuer_whole_terminal_ready));} else
 if(name=="issuer_whole_reverse_ready"){word(uint32_t(dut.issuer_whole_reverse_ready>>32));word(uint32_t(dut.issuer_whole_reverse_ready));} else
 if(name=="issuer_publish_valid"){word(uint32_t(dut.issuer_publish_valid>>32));word(uint32_t(dut.issuer_publish_valid));} else
 if(name=="issuer_frame_retire_valid"){word(uint32_t(dut.issuer_frame_retire_valid>>32));word(uint32_t(dut.issuer_frame_retire_valid));} else
 if(name=="issuer_publish_ready"){word(uint32_t(dut.issuer_publish_ready>>32));word(uint32_t(dut.issuer_publish_ready));} else
 if(name=="issuer_frame_retire_ready"){word(uint32_t(dut.issuer_frame_retire_ready>>32));word(uint32_t(dut.issuer_frame_retire_ready));} else
 if(name=="issuer_publish_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_publish_tuple[i]);} else
 if(name=="issuer_frame_retire_tuple"){for(int i=477;i>=0;i--)word(dut.issuer_frame_retire_tuple[i]);} else
 if(name=="issuer_publish_owner"){for(int i=109;i>=0;i--)word(dut.issuer_publish_owner[i]);} else
 if(name=="issuer_frame_retire_owner"){for(int i=109;i>=0;i--)word(dut.issuer_frame_retire_owner[i]);} else
 if(name=="issuer_busy"){word(uint32_t(dut.issuer_busy>>32));word(uint32_t(dut.issuer_busy));} else
 if(name=="issuer_fault"){word(uint32_t(dut.issuer_fault>>32));word(uint32_t(dut.issuer_fault));} else
 if(name=="state_por_n"){word(dut.state_por_n);} else
 if(name=="state_run_enable"){word(dut.state_run_enable);} else
 if(name=="state_local_reset"){word(dut.state_local_reset);} else
 if(name=="state_source_bound"){word(dut.state_source_bound);} else
 if(name=="state_command_valid"){word(dut.state_command_valid);} else
 if(name=="state_command_ready"){word(dut.state_command_ready);} else
 if(name=="state_command_rank"){word(dut.state_command_rank);} else
 if(name=="state_command_write"){word(dut.state_command_write);} else
 if(name=="state_command_sector_granted"){word(dut.state_command_sector_granted);} else
 if(name=="state_state_client_mask"){word(dut.state_state_client_mask);} else
 if(name=="state_command_identity"){word(uint32_t(dut.state_command_identity>>32));word(uint32_t(dut.state_command_identity));} else
 if(name=="state_command_source_addr"){word(uint32_t(dut.state_command_source_addr>>32));word(uint32_t(dut.state_command_source_addr));} else
 if(name=="state_command_physical_addr"){word(uint32_t(dut.state_command_physical_addr>>32));word(uint32_t(dut.state_command_physical_addr));} else
 if(name=="state_command_owner"){word(uint32_t(dut.state_command_owner>>32));word(uint32_t(dut.state_command_owner));} else
 if(name=="state_command_new_data"){for(int i=7;i>=0;i--)word(dut.state_command_new_data[i]);} else
 if(name=="state_command_byte_mask"){word(dut.state_command_byte_mask);} else
 if(name=="state_reply_valid"){word(dut.state_reply_valid);} else
 if(name=="state_reply_ready"){word(dut.state_reply_ready);} else
 if(name=="state_reply_identity"){word(uint32_t(dut.state_reply_identity>>32));word(uint32_t(dut.state_reply_identity));} else
 if(name=="state_reply_old_data"){for(int i=7;i>=0;i--)word(dut.state_reply_old_data[i]);} else
 if(name=="state_reply_rank"){word(dut.state_reply_rank);} else
 if(name=="state_reply_owner"){word(uint32_t(dut.state_reply_owner>>32));word(uint32_t(dut.state_reply_owner));} else
 if(name=="state_reply_physical_addr"){word(uint32_t(dut.state_reply_physical_addr>>32));word(uint32_t(dut.state_reply_physical_addr));} else
 if(name=="state_quiescent"){word(dut.state_quiescent);} else
 if(name=="state_bus_rank"){word(dut.state_bus_rank);} else
 if(name=="state_bus_PC"){word(dut.state_bus_PC);} else
 if(name=="state_caller_req_v"){word(dut.state_caller_req_v);} else
 if(name=="state_caller_req_we"){word(dut.state_caller_req_we);} else
 if(name=="state_raw_req_rdy"){word(dut.state_raw_req_rdy);} else
 if(name=="state_caller_req_addr"){for(int i=6;i>=0;i--)word(dut.state_caller_req_addr[i]);} else
 if(name=="state_caller_req_tag"){for(int i=5;i>=0;i--)word(dut.state_caller_req_tag[i]);} else
 if(name=="state_caller_req_gen"){word(dut.state_caller_req_gen);} else
 if(name=="state_caller_req_data"){for(int i=47;i>=0;i--)word(dut.state_caller_req_data[i]);} else
 if(name=="state_req_permit"){word(dut.state_req_permit);} else
 if(name=="state_raw_rsp_v"){word(dut.state_raw_rsp_v);} else
 if(name=="state_raw_wr_done_v"){word(dut.state_raw_wr_done_v);} else
 if(name=="state_caller_rsp_rdy"){word(dut.state_caller_rsp_rdy);} else
 if(name=="state_caller_wr_done_rdy"){word(dut.state_caller_wr_done_rdy);} else
 if(name=="state_raw_rsp_tag"){for(int i=5;i>=0;i--)word(dut.state_raw_rsp_tag[i]);} else
 if(name=="state_raw_wr_done_tag"){for(int i=5;i>=0;i--)word(dut.state_raw_wr_done_tag[i]);} else
 if(name=="state_raw_rsp_gen"){word(dut.state_raw_rsp_gen);} else
 if(name=="state_raw_wr_done_gen"){word(dut.state_raw_wr_done_gen);} else
 if(name=="state_raw_rsp_data"){for(int i=47;i>=0;i--)word(dut.state_raw_rsp_data[i]);} else
 if(name=="state_W2_fault"){word(dut.state_W2_fault);} else
 if(name=="state_repair_busy"){word(dut.state_repair_busy);} else
 if(name=="state_capture_permit"){word(dut.state_capture_permit);} else
 if(name=="state_reverse_valid"){word(dut.state_reverse_valid);} else
 if(name=="state_reverse_ready"){word(dut.state_reverse_ready);} else
 if(name=="state_reverse_rank"){word(dut.state_reverse_rank);} else
 if(name=="state_reverse_write"){word(dut.state_reverse_write);} else
 if(name=="state_reverse_owner"){word(uint32_t(dut.state_reverse_owner>>32));word(uint32_t(dut.state_reverse_owner));} else
 if(name=="state_reverse_physical_addr"){word(uint32_t(dut.state_reverse_physical_addr>>32));word(uint32_t(dut.state_reverse_physical_addr));} else
 if(name=="state_observe_valid"){word(dut.state_observe_valid);} else
 if(name=="state_observe_ready"){word(dut.state_observe_ready);} else
 if(name=="state_observe_rank"){word(dut.state_observe_rank);} else
 if(name=="state_observe_old_captured"){word(dut.state_observe_old_captured);} else
 if(name=="state_observe_source_addr"){word(uint32_t(dut.state_observe_source_addr>>32));word(uint32_t(dut.state_observe_source_addr));} else
 if(name=="state_observe_physical_addr"){word(uint32_t(dut.state_observe_physical_addr>>32));word(uint32_t(dut.state_observe_physical_addr));} else
 if(name=="state_observe_owner"){word(uint32_t(dut.state_observe_owner>>32));word(uint32_t(dut.state_observe_owner));} else
 if(name=="state_observe_old_data"){for(int i=7;i>=0;i--)word(dut.state_observe_old_data[i]);} else
 if(name=="state_observe_new_data"){for(int i=7;i>=0;i--)word(dut.state_observe_new_data[i]);} else
 if(name=="state_ACK_valid"){word(dut.state_ACK_valid);} else
 if(name=="state_ACK_ready"){word(dut.state_ACK_ready);} else
 if(name=="state_ACK_owner"){word(uint32_t(dut.state_ACK_owner>>32));word(uint32_t(dut.state_ACK_owner));} else
 if(name=="state_ACK_physical_addr"){word(uint32_t(dut.state_ACK_physical_addr>>32));word(uint32_t(dut.state_ACK_physical_addr));} else
 if(name=="state_ACK_visible"){word(dut.state_ACK_visible);} else
 if(name=="state_ACK_reverse"){word(dut.state_ACK_reverse);} else
 if(name=="state_fault"){word(dut.state_fault);} else
 if(name=="rfdrain_por_n"){word(uint32_t(dut.rfdrain_por_n>>32));word(uint32_t(dut.rfdrain_por_n));} else
 if(name=="rfdrain_rst_n"){word(uint32_t(dut.rfdrain_rst_n>>32));word(uint32_t(dut.rfdrain_rst_n));} else
 if(name=="rfdrain_run_enable"){word(uint32_t(dut.rfdrain_run_enable>>32));word(uint32_t(dut.rfdrain_run_enable));} else
 if(name=="rfdrain_source_fault"){word(uint32_t(dut.rfdrain_source_fault>>32));word(uint32_t(dut.rfdrain_source_fault));} else
 if(name=="rfdrain_rf_write_accept"){word(uint32_t(dut.rfdrain_rf_write_accept>>32));word(uint32_t(dut.rfdrain_rf_write_accept));} else
 if(name=="rfdrain_rf_write_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_rf_write_owner55[i]);} else
 if(name=="rfdrain_wr_binding_valid"){word(uint32_t(dut.rfdrain_wr_binding_valid>>32));word(uint32_t(dut.rfdrain_wr_binding_valid));} else
 if(name=="rfdrain_wr_KV_related"){word(uint32_t(dut.rfdrain_wr_KV_related>>32));word(uint32_t(dut.rfdrain_wr_KV_related));} else
 if(name=="rfdrain_wr_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_wr_identity[i]);} else
 if(name=="rfdrain_wr_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_wr_key[i]);} else
 if(name=="rfdrain_wr_permit"){word(uint32_t(dut.rfdrain_wr_permit>>32));word(uint32_t(dut.rfdrain_wr_permit));} else
 if(name=="rfdrain_wr_continuation_valid"){word(uint32_t(dut.rfdrain_wr_continuation_valid>>32));word(uint32_t(dut.rfdrain_wr_continuation_valid));} else
 if(name=="rfdrain_wr_continuation_source"){word(uint32_t(dut.rfdrain_wr_continuation_source>>32));word(uint32_t(dut.rfdrain_wr_continuation_source));} else
 if(name=="rfdrain_rd_continuation_valid"){word(uint32_t(dut.rfdrain_rd_continuation_valid>>32));word(uint32_t(dut.rfdrain_rd_continuation_valid));} else
 if(name=="rfdrain_rd_continuation_source"){word(uint32_t(dut.rfdrain_rd_continuation_source>>32));word(uint32_t(dut.rfdrain_rd_continuation_source));} else
 if(name=="rfdrain_rd_context_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_rd_context_owner55[i]);} else
 if(name=="rfdrain_simd_context_accept"){word(uint32_t(dut.rfdrain_simd_context_accept>>32));word(uint32_t(dut.rfdrain_simd_context_accept));} else
 if(name=="rfdrain_simd_binding_valid"){word(uint32_t(dut.rfdrain_simd_binding_valid>>32));word(uint32_t(dut.rfdrain_simd_binding_valid));} else
 if(name=="rfdrain_simd_KV_related"){word(uint32_t(dut.rfdrain_simd_KV_related>>32));word(uint32_t(dut.rfdrain_simd_KV_related));} else
 if(name=="rfdrain_simd_context_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_simd_context_owner55[i]);} else
 if(name=="rfdrain_simd_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_simd_identity[i]);} else
 if(name=="rfdrain_simd_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_simd_key[i]);} else
 if(name=="rfdrain_simd_context_permit"){word(uint32_t(dut.rfdrain_simd_context_permit>>32));word(uint32_t(dut.rfdrain_simd_context_permit));} else
 if(name=="rfdrain_simd_context_retire"){word(uint32_t(dut.rfdrain_simd_context_retire>>32));word(uint32_t(dut.rfdrain_simd_context_retire));} else
 if(name=="rfdrain_simd_retire_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_simd_retire_owner55[i]);} else
 if(name=="rfdrain_rf_ack_valid"){word(uint32_t(dut.rfdrain_rf_ack_valid>>32));word(uint32_t(dut.rfdrain_rf_ack_valid));} else
 if(name=="rfdrain_rf_ack_accept"){word(uint32_t(dut.rfdrain_rf_ack_accept>>32));word(uint32_t(dut.rfdrain_rf_ack_accept));} else
 if(name=="rfdrain_rf_ack_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_rf_ack_owner55[i]);} else
 if(name=="rfdrain_rf_ack_fault"){word(uint32_t(dut.rfdrain_rf_ack_fault>>32));word(uint32_t(dut.rfdrain_rf_ack_fault));} else
 if(name=="rfdrain_rf_ack_allow"){word(uint32_t(dut.rfdrain_rf_ack_allow>>32));word(uint32_t(dut.rfdrain_rf_ack_allow));} else
 if(name=="rfdrain_rf_read_accept"){word(uint32_t(dut.rfdrain_rf_read_accept>>32));word(uint32_t(dut.rfdrain_rf_read_accept));} else
 if(name=="rfdrain_rf_read_a"){for(int i=17;i>=0;i--)word(dut.rfdrain_rf_read_a[i]);} else
 if(name=="rfdrain_rf_read_b"){for(int i=17;i>=0;i--)word(dut.rfdrain_rf_read_b[i]);} else
 if(name=="rfdrain_rd_binding_valid"){word(uint32_t(dut.rfdrain_rd_binding_valid>>32));word(uint32_t(dut.rfdrain_rd_binding_valid));} else
 if(name=="rfdrain_rd_KV_related"){word(uint32_t(dut.rfdrain_rd_KV_related>>32));word(uint32_t(dut.rfdrain_rd_KV_related));} else
 if(name=="rfdrain_rd_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_rd_identity[i]);} else
 if(name=="rfdrain_rd_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_rd_key[i]);} else
 if(name=="rfdrain_rd_permit"){word(uint32_t(dut.rfdrain_rd_permit>>32));word(uint32_t(dut.rfdrain_rd_permit));} else
 if(name=="rfdrain_rf_rsp_valid"){word(uint32_t(dut.rfdrain_rf_rsp_valid>>32));word(uint32_t(dut.rfdrain_rf_rsp_valid));} else
 if(name=="rfdrain_rf_rsp_accept"){word(uint32_t(dut.rfdrain_rf_rsp_accept>>32));word(uint32_t(dut.rfdrain_rf_rsp_accept));} else
 if(name=="rfdrain_rf_rsp_allow"){word(uint32_t(dut.rfdrain_rf_rsp_allow>>32));word(uint32_t(dut.rfdrain_rf_rsp_allow));} else
 if(name=="rfdrain_w6_request_accept"){word(uint32_t(dut.rfdrain_w6_request_accept>>32));word(uint32_t(dut.rfdrain_w6_request_accept));} else
 if(name=="rfdrain_w6_request_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_request_owner55[i]);} else
 if(name=="rfdrain_w6_binding_valid"){word(uint32_t(dut.rfdrain_w6_binding_valid>>32));word(uint32_t(dut.rfdrain_w6_binding_valid));} else
 if(name=="rfdrain_w6_KV_related"){word(uint32_t(dut.rfdrain_w6_KV_related>>32));word(uint32_t(dut.rfdrain_w6_KV_related));} else
 if(name=="rfdrain_w6_internal_SIMD"){word(uint32_t(dut.rfdrain_w6_internal_SIMD>>32));word(uint32_t(dut.rfdrain_w6_internal_SIMD));} else
 if(name=="rfdrain_w6_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_w6_identity[i]);} else
 if(name=="rfdrain_w6_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_w6_key[i]);} else
 if(name=="rfdrain_w6_permit"){word(uint32_t(dut.rfdrain_w6_permit>>32));word(uint32_t(dut.rfdrain_w6_permit));} else
 if(name=="rfdrain_w6_host_ACK_accept"){word(uint32_t(dut.rfdrain_w6_host_ACK_accept>>32));word(uint32_t(dut.rfdrain_w6_host_ACK_accept));} else
 if(name=="rfdrain_w6_SIMD_ACK_accept"){word(uint32_t(dut.rfdrain_w6_SIMD_ACK_accept>>32));word(uint32_t(dut.rfdrain_w6_SIMD_ACK_accept));} else
 if(name=="rfdrain_w6_ACK_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_ACK_owner55[i]);} else
 if(name=="rfdrain_w6_consumer_accept"){word(uint32_t(dut.rfdrain_w6_consumer_accept>>32));word(uint32_t(dut.rfdrain_w6_consumer_accept));} else
 if(name=="rfdrain_w6_consumer_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_consumer_owner55[i]);} else
 if(name=="rfdrain_w6_child_accept"){word(uint32_t(dut.rfdrain_w6_child_accept>>32));word(uint32_t(dut.rfdrain_w6_child_accept));} else
 if(name=="rfdrain_w6_child_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_child_owner55[i]);} else
 if(name=="rfdrain_w6_parent_accept"){word(uint32_t(dut.rfdrain_w6_parent_accept>>32));word(uint32_t(dut.rfdrain_w6_parent_accept));} else
 if(name=="rfdrain_w6_parent_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_parent_owner55[i]);} else
 if(name=="rfdrain_w6_CDC_accept"){word(uint32_t(dut.rfdrain_w6_CDC_accept>>32));word(uint32_t(dut.rfdrain_w6_CDC_accept));} else
 if(name=="rfdrain_w6_CDC_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_CDC_owner55[i]);} else
 if(name=="rfdrain_w6_retire_accept"){word(uint32_t(dut.rfdrain_w6_retire_accept>>32));word(uint32_t(dut.rfdrain_w6_retire_accept));} else
 if(name=="rfdrain_w6_retire_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_retire_owner55[i]);} else
 if(name=="rfdrain_w6_local_drain_owner55"){for(int i=109;i>=0;i--)word(dut.rfdrain_w6_local_drain_owner55[i]);} else
 if(name=="rfdrain_w6_local_drain_has_owner"){word(uint32_t(dut.rfdrain_w6_local_drain_has_owner>>32));word(uint32_t(dut.rfdrain_w6_local_drain_has_owner));} else
 if(name=="rfdrain_w6_local_drain_reset_scope"){word(uint32_t(dut.rfdrain_w6_local_drain_reset_scope>>32));word(uint32_t(dut.rfdrain_w6_local_drain_reset_scope));} else
 if(name=="rfdrain_drain_req_valid"){word(uint32_t(dut.rfdrain_drain_req_valid>>32));word(uint32_t(dut.rfdrain_drain_req_valid));} else
 if(name=="rfdrain_drain_req_ready"){word(uint32_t(dut.rfdrain_drain_req_ready>>32));word(uint32_t(dut.rfdrain_drain_req_ready));} else
 if(name=="rfdrain_drain_req_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_drain_req_identity[i]);} else
 if(name=="rfdrain_drain_req_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_drain_req_key[i]);} else
 if(name=="rfdrain_drain_hold"){word(uint32_t(dut.rfdrain_drain_hold>>32));word(uint32_t(dut.rfdrain_drain_hold));} else
 if(name=="rfdrain_drain_rsp_valid"){word(uint32_t(dut.rfdrain_drain_rsp_valid>>32));word(uint32_t(dut.rfdrain_drain_rsp_valid));} else
 if(name=="rfdrain_drain_rsp_ready"){word(uint32_t(dut.rfdrain_drain_rsp_ready>>32));word(uint32_t(dut.rfdrain_drain_rsp_ready));} else
 if(name=="rfdrain_drain_rsp_identity"){for(int i=127;i>=0;i--)word(dut.rfdrain_drain_rsp_identity[i]);} else
 if(name=="rfdrain_drain_rsp_key"){for(int i=39;i>=0;i--)word(dut.rfdrain_drain_rsp_key[i]);} else
 if(name=="rfdrain_drain_rsp_empty"){word(uint32_t(dut.rfdrain_drain_rsp_empty>>32));word(uint32_t(dut.rfdrain_drain_rsp_empty));} else
 if(name=="rfdrain_drain_retained"){word(uint32_t(dut.rfdrain_drain_retained>>32));word(uint32_t(dut.rfdrain_drain_retained));} else
 if(name=="rfdrain_write_retained"){word(uint32_t(dut.rfdrain_write_retained>>32));word(uint32_t(dut.rfdrain_write_retained));} else
 if(name=="rfdrain_read_retained"){word(uint32_t(dut.rfdrain_read_retained>>32));word(uint32_t(dut.rfdrain_read_retained));} else
 if(name=="rfdrain_w6_retained"){word(uint32_t(dut.rfdrain_w6_retained>>32));word(uint32_t(dut.rfdrain_w6_retained));} else
 if(name=="rfdrain_w6_local_RF_empty"){word(uint32_t(dut.rfdrain_w6_local_RF_empty>>32));word(uint32_t(dut.rfdrain_w6_local_RF_empty));} else
 if(name=="rfdrain_fault"){word(uint32_t(dut.rfdrain_fault>>32));word(uint32_t(dut.rfdrain_fault));} else
 if(name=="rfjoin_por_n"){word(dut.rfjoin_por_n);} else
 if(name=="rfjoin_rst_n"){word(dut.rfjoin_rst_n);} else
 if(name=="rfjoin_run_enable"){word(dut.rfjoin_run_enable);} else
 if(name=="rfjoin_drain_req_valid"){word(dut.rfjoin_drain_req_valid);} else
 if(name=="rfjoin_drain_req_ready"){word(dut.rfjoin_drain_req_ready);} else
 if(name=="rfjoin_drain_req_identity"){for(int i=3;i>=0;i--)word(dut.rfjoin_drain_req_identity[i]);} else
 if(name=="rfjoin_drain_req_key"){word(uint32_t(dut.rfjoin_drain_req_key>>32));word(uint32_t(dut.rfjoin_drain_req_key));} else
 if(name=="rfjoin_drain_hold"){word(dut.rfjoin_drain_hold);} else
 if(name=="rfjoin_leaf_req_valid"){word(uint32_t(dut.rfjoin_leaf_req_valid>>32));word(uint32_t(dut.rfjoin_leaf_req_valid));} else
 if(name=="rfjoin_leaf_req_ready"){word(uint32_t(dut.rfjoin_leaf_req_ready>>32));word(uint32_t(dut.rfjoin_leaf_req_ready));} else
 if(name=="rfjoin_leaf_identity"){for(int i=3;i>=0;i--)word(dut.rfjoin_leaf_identity[i]);} else
 if(name=="rfjoin_leaf_key"){word(uint32_t(dut.rfjoin_leaf_key>>32));word(uint32_t(dut.rfjoin_leaf_key));} else
 if(name=="rfjoin_leaf_hold"){word(uint32_t(dut.rfjoin_leaf_hold>>32));word(uint32_t(dut.rfjoin_leaf_hold));} else
 if(name=="rfjoin_leaf_rsp_valid"){word(uint32_t(dut.rfjoin_leaf_rsp_valid>>32));word(uint32_t(dut.rfjoin_leaf_rsp_valid));} else
 if(name=="rfjoin_leaf_rsp_ready"){word(uint32_t(dut.rfjoin_leaf_rsp_ready>>32));word(uint32_t(dut.rfjoin_leaf_rsp_ready));} else
 if(name=="rfjoin_leaf_rsp_tuple"){for(int i=167;i>=0;i--)word(dut.rfjoin_leaf_rsp_tuple[i]);} else
 if(name=="rfjoin_leaf_rsp_empty"){word(uint32_t(dut.rfjoin_leaf_rsp_empty>>32));word(uint32_t(dut.rfjoin_leaf_rsp_empty));} else
 if(name=="rfjoin_leaf_fault"){word(uint32_t(dut.rfjoin_leaf_fault>>32));word(uint32_t(dut.rfjoin_leaf_fault));} else
 if(name=="rfjoin_drain_rsp_valid"){word(dut.rfjoin_drain_rsp_valid);} else
 if(name=="rfjoin_drain_rsp_ready"){word(dut.rfjoin_drain_rsp_ready);} else
 if(name=="rfjoin_drain_rsp_identity"){for(int i=3;i>=0;i--)word(dut.rfjoin_drain_rsp_identity[i]);} else
 if(name=="rfjoin_drain_rsp_key"){word(uint32_t(dut.rfjoin_drain_rsp_key>>32));word(uint32_t(dut.rfjoin_drain_rsp_key));} else
 if(name=="rfjoin_drain_rsp_empty"){word(dut.rfjoin_drain_rsp_empty);} else
 if(name=="rfjoin_drain_retained"){word(dut.rfjoin_drain_retained);} else
 if(name=="rfjoin_fault"){word(dut.rfjoin_fault);} else
 if(name=="sector_por_n"){word(dut.sector_por_n);} else
 if(name=="sector_run_enable"){word(dut.sector_run_enable);} else
 if(name=="sector_local_reset"){word(dut.sector_local_reset);} else
 if(name=="sector_alloc_valid"){word(dut.sector_alloc_valid);} else
 if(name=="sector_alloc_ready"){word(dut.sector_alloc_ready);} else
 if(name=="sector_alloc_source"){for(int i=3;i>=0;i--)word(dut.sector_alloc_source[i]);} else
 if(name=="sector_alloc_rmw"){word(dut.sector_alloc_rmw);} else
 if(name=="sector_map_valid"){word(dut.sector_map_valid);} else
 if(name=="sector_map_sector_clear"){word(dut.sector_map_sector_clear);} else
 if(name=="sector_map_addr"){word(uint32_t(dut.sector_map_addr>>32));word(uint32_t(dut.sector_map_addr));} else
 if(name=="sector_map_PC"){word(dut.sector_map_PC);} else
 if(name=="sector_map_client"){word(dut.sector_map_client);} else
 if(name=="sector_map_tag"){word(dut.sector_map_tag);} else
 if(name=="sector_map_gen"){word(dut.sector_map_gen);} else
 if(name=="sector_grant_live"){word(dut.sector_grant_live);} else
 if(name=="sector_grant_identity"){for(int i=6;i>=0;i--)word(dut.sector_grant_identity[i]);} else
 if(name=="sector_grant_rmw"){word(dut.sector_grant_rmw);} else
 if(name=="sector_grant_phase"){word(dut.sector_grant_phase);} else
 if(name=="sector_req_permit"){word(dut.sector_req_permit);} else
 if(name=="sector_capture_permit"){word(dut.sector_capture_permit);} else
 if(name=="sector_reverse_valid"){word(dut.sector_reverse_valid);} else
 if(name=="sector_reverse_ready"){word(dut.sector_reverse_ready);} else
 if(name=="sector_reverse_route"){for(int i=2;i>=0;i--)word(dut.sector_reverse_route[i]);} else
 if(name=="sector_reverse_write"){word(dut.sector_reverse_write);} else
 if(name=="sector_release_valid"){word(dut.sector_release_valid);} else
 if(name=="sector_release_ready"){word(dut.sector_release_ready);} else
 if(name=="sector_release_identity"){for(int i=6;i>=0;i--)word(dut.sector_release_identity[i]);} else
 if(name=="sector_fault"){word(dut.sector_fault);} else
 if(name=="sector_issue_ready"){word(dut.sector_issue_ready);} else
 if(name=="kv_por_n"){word(dut.kv_por_n);} else
 if(name=="kv_run_enable"){word(dut.kv_run_enable);} else
 if(name=="kv_quiesce"){word(dut.kv_quiesce);} else
 if(name=="kv_cmd_valid"){word(dut.kv_cmd_valid);} else
 if(name=="kv_cmd_ready"){word(dut.kv_cmd_ready);} else
 if(name=="kv_cmd_op"){word(dut.kv_cmd_op);} else
 if(name=="kv_cmd_identity"){word(uint32_t(dut.kv_cmd_identity>>32));word(uint32_t(dut.kv_cmd_identity));} else
 if(name=="kv_cmd_key"){word(dut.kv_cmd_key);} else
 if(name=="kv_cmd_producer"){word(uint32_t(dut.kv_cmd_producer>>32));word(uint32_t(dut.kv_cmd_producer));} else
 if(name=="kv_cmd_sequence"){word(uint32_t(dut.kv_cmd_sequence>>32));word(uint32_t(dut.kv_cmd_sequence));} else
 if(name=="kv_cmd_PC"){word(dut.kv_cmd_PC);} else
 if(name=="kv_cmd_consumer"){word(dut.kv_cmd_consumer);} else
 if(name=="kv_cmd_stage_beat"){word(dut.kv_cmd_stage_beat);} else
 if(name=="kv_cmd_stage_base"){word(dut.kv_cmd_stage_base);} else
 if(name=="kv_cmd_stage_SM"){word(dut.kv_cmd_stage_SM);} else
 if(name=="kv_cmd_stage_data"){for(int i=15;i>=0;i--)word(dut.kv_cmd_stage_data[i]);} else
 if(name=="kv_cmd_K_base"){word(uint32_t(dut.kv_cmd_K_base>>32));word(uint32_t(dut.kv_cmd_K_base));} else
 if(name=="kv_cmd_V_base"){word(uint32_t(dut.kv_cmd_V_base>>32));word(uint32_t(dut.kv_cmd_V_base));} else
 if(name=="kv_rsp_valid"){word(dut.kv_rsp_valid);} else
 if(name=="kv_rsp_ready"){word(dut.kv_rsp_ready);} else
 if(name=="kv_rsp_fault"){word(dut.kv_rsp_fault);} else
 if(name=="kv_rsp_op"){word(dut.kv_rsp_op);} else
 if(name=="kv_rsp_identity"){word(uint32_t(dut.kv_rsp_identity>>32));word(uint32_t(dut.kv_rsp_identity));} else
 if(name=="kv_rsp_key"){word(dut.kv_rsp_key);} else
 if(name=="kv_rsp_sequence"){word(uint32_t(dut.kv_rsp_sequence>>32));word(uint32_t(dut.kv_rsp_sequence));} else
 if(name=="kv_rsp_PC"){word(dut.kv_rsp_PC);} else
 if(name=="kv_rsp_capture"){for(int i=15;i>=0;i--)word(dut.kv_rsp_capture[i]);} else
 if(name=="kv_rsp_producer"){word(uint32_t(dut.kv_rsp_producer>>32));word(uint32_t(dut.kv_rsp_producer));} else
 if(name=="kv_rsp_consumer"){word(dut.kv_rsp_consumer);} else
 if(name=="kv_rsp_stage_beat"){word(dut.kv_rsp_stage_beat);} else
 if(name=="kv_commit_valid"){word(dut.kv_commit_valid);} else
 if(name=="kv_commit_ready"){word(dut.kv_commit_ready);} else
 if(name=="kv_writer_identity"){word(uint32_t(dut.kv_writer_identity>>32));word(uint32_t(dut.kv_writer_identity));} else
 if(name=="kv_writer_key"){word(dut.kv_writer_key);} else
 if(name=="kv_writer_stage_base"){word(dut.kv_writer_stage_base);} else
 if(name=="kv_writer_stage_SM"){word(dut.kv_writer_stage_SM);} else
 if(name=="kv_writer_K_base"){word(uint32_t(dut.kv_writer_K_base>>32));word(uint32_t(dut.kv_writer_K_base));} else
 if(name=="kv_writer_V_base"){word(uint32_t(dut.kv_writer_V_base>>32));word(uint32_t(dut.kv_writer_V_base));} else
 if(name=="kv_payload_valid"){word(dut.kv_payload_valid);} else
 if(name=="kv_payload_ready"){word(dut.kv_payload_ready);} else
 if(name=="kv_payload_identity"){word(uint32_t(dut.kv_payload_identity>>32));word(uint32_t(dut.kv_payload_identity));} else
 if(name=="kv_payload_key"){word(dut.kv_payload_key);} else
 if(name=="kv_payload_sector"){word(dut.kv_payload_sector);} else
 if(name=="kv_payload_source_addr"){word(uint32_t(dut.kv_payload_source_addr>>32));word(uint32_t(dut.kv_payload_source_addr));} else
 if(name=="kv_payload_visible"){word(dut.kv_payload_visible);} else
 if(name=="kv_payload_reverse"){word(dut.kv_payload_reverse);} else
 if(name=="kv_payload_write"){word(dut.kv_payload_write);} else
 if(name=="kv_payload_rdata"){for(int i=7;i>=0;i--)word(dut.kv_payload_rdata[i]);} else
 if(name=="kv_payload_req_valid"){word(dut.kv_payload_req_valid);} else
 if(name=="kv_payload_req_ready"){word(dut.kv_payload_req_ready);} else
 if(name=="kv_payload_req_write"){word(dut.kv_payload_req_write);} else
 if(name=="kv_payload_req_sector"){word(dut.kv_payload_req_sector);} else
 if(name=="kv_payload_req_source_addr"){word(uint32_t(dut.kv_payload_req_source_addr>>32));word(uint32_t(dut.kv_payload_req_source_addr));} else
 if(name=="kv_payload_req_data"){for(int i=7;i>=0;i--)word(dut.kv_payload_req_data[i]);} else
 if(name=="kv_payload_req_rmw"){word(dut.kv_payload_req_rmw);} else
 if(name=="kv_payload_req_rmw_last"){word(dut.kv_payload_req_rmw_last);} else
 if(name=="kv_hydrate_valid"){word(dut.kv_hydrate_valid);} else
 if(name=="kv_hydrate_ready"){word(dut.kv_hydrate_ready);} else
 if(name=="kv_hydrate_key"){word(dut.kv_hydrate_key);} else
 if(name=="kv_hydrate_producer"){word(uint32_t(dut.kv_hydrate_producer>>32));word(uint32_t(dut.kv_hydrate_producer));} else
 if(name=="kv_writer_retained"){word(dut.kv_writer_retained);} else
 if(name=="kv_idle"){word(dut.kv_idle);} else
 if(name=="kv_native_valid"){word(uint32_t(dut.kv_native_valid>>32));word(uint32_t(dut.kv_native_valid));} else
 if(name=="kv_native_write"){word(uint32_t(dut.kv_native_write>>32));word(uint32_t(dut.kv_native_write));} else
 if(name=="kv_native_addr"){for(int i=19;i>=0;i--)word(dut.kv_native_addr[i]);} else
 if(name=="kv_native_wdata"){for(int i=1023;i>=0;i--)word(dut.kv_native_wdata[i]);} else
 if(name=="kv_native_ready"){word(uint32_t(dut.kv_native_ready>>32));word(uint32_t(dut.kv_native_ready));} else
 if(name=="kv_native_done"){word(uint32_t(dut.kv_native_done>>32));word(uint32_t(dut.kv_native_done));} else
 if(name=="kv_native_done_ready"){word(uint32_t(dut.kv_native_done_ready>>32));word(uint32_t(dut.kv_native_done_ready));} else
 if(name=="kv_native_rdata"){for(int i=1023;i>=0;i--)word(dut.kv_native_rdata[i]);} else
 if(name=="kv_shared_drained"){word(dut.kv_shared_drained);} else
 if(name=="kv_source_bound"){word(dut.kv_source_bound);} else
 if(name=="kv_state_base_rank0"){word(uint32_t(dut.kv_state_base_rank0>>32));word(uint32_t(dut.kv_state_base_rank0));} else
 if(name=="kv_state_base_rank1"){word(uint32_t(dut.kv_state_base_rank1>>32));word(uint32_t(dut.kv_state_base_rank1));} else
 if(name=="kv_observe_valid"){word(dut.kv_observe_valid);} else
 if(name=="kv_observe_ready"){word(dut.kv_observe_ready);} else
 if(name=="kv_observe_rank"){word(dut.kv_observe_rank);} else
 if(name=="kv_observe_source_addr"){word(uint32_t(dut.kv_observe_source_addr>>32));word(uint32_t(dut.kv_observe_source_addr));} else
 if(name=="kv_observe_physical_addr"){word(uint32_t(dut.kv_observe_physical_addr>>32));word(uint32_t(dut.kv_observe_physical_addr));} else
 if(name=="kv_observe_owner"){word(uint32_t(dut.kv_observe_owner>>32));word(uint32_t(dut.kv_observe_owner));} else
 if(name=="kv_observe_old_data"){for(int i=7;i>=0;i--)word(dut.kv_observe_old_data[i]);} else
 if(name=="kv_observe_new_data"){for(int i=7;i>=0;i--)word(dut.kv_observe_new_data[i]);} else
 if(name=="kv_observe_old_captured"){word(dut.kv_observe_old_captured);} else
 if(name=="kv_ACK_valid"){word(dut.kv_ACK_valid);} else
 if(name=="kv_ACK_ready"){word(dut.kv_ACK_ready);} else
 if(name=="kv_ACK_owner"){word(uint32_t(dut.kv_ACK_owner>>32));word(uint32_t(dut.kv_ACK_owner));} else
 if(name=="kv_ACK_physical_addr"){word(uint32_t(dut.kv_ACK_physical_addr>>32));word(uint32_t(dut.kv_ACK_physical_addr));} else
 if(name=="kv_ACK_visible"){word(dut.kv_ACK_visible);} else
 if(name=="kv_ACK_reverse"){word(dut.kv_ACK_reverse);} else
 if(name=="kv_state_observer_drained"){word(dut.kv_state_observer_drained);} else
 if(name=="kv_rst_n"){word(dut.kv_rst_n);} else
 if(name=="kv_endpoint_fault"){word(dut.kv_endpoint_fault);} else
 if(name=="kv_native_issue_valid"){word(dut.kv_native_issue_valid);} else
 if(name=="kv_native_issue_ready"){word(dut.kv_native_issue_ready);} else
 if(name=="kv_native_issue_tuple"){for(int i=7;i>=0;i--)word(dut.kv_native_issue_tuple[i]);} else
 if(name=="kv_native_complete_valid"){word(dut.kv_native_complete_valid);} else
 if(name=="kv_native_complete_ready"){word(dut.kv_native_complete_ready);} else
 if(name=="kv_native_complete_tuple"){for(int i=7;i>=0;i--)word(dut.kv_native_complete_tuple[i]);} else
 if(name=="kv_native_reverse_valid"){word(dut.kv_native_reverse_valid);} else
 if(name=="kv_native_reverse_ready"){word(dut.kv_native_reverse_ready);} else
 if(name=="kv_native_reverse_tuple"){for(int i=7;i>=0;i--)word(dut.kv_native_reverse_tuple[i]);} else
 if(name=="kv_cohort_quiesce"){word(dut.kv_cohort_quiesce);} else
 if(name=="kv_cohort_req_valid"){word(dut.kv_cohort_req_valid);} else
 if(name=="kv_cohort_req_ready"){word(dut.kv_cohort_req_ready);} else
 if(name=="kv_cohort_identity"){word(uint32_t(dut.kv_cohort_identity>>32));word(uint32_t(dut.kv_cohort_identity));} else
 if(name=="kv_cohort_key"){word(dut.kv_cohort_key);} else
 if(name=="kv_cohort_rsp_valid"){word(dut.kv_cohort_rsp_valid);} else
 if(name=="kv_cohort_rsp_ready"){word(dut.kv_cohort_rsp_ready);} else
 if(name=="kv_cohort_rsp_tuple"){for(int i=20;i>=0;i--)word(dut.kv_cohort_rsp_tuple[i]);} else
 if(name=="kv_cohort_rsp_empty"){word(dut.kv_cohort_rsp_empty);} else
 if(name=="kv_native_retained"){word(dut.kv_native_retained);} else
 if(name=="kv_drain_retained"){word(dut.kv_drain_retained);} else
 if(name=="kv_fault"){word(dut.kv_fault);} else
 if(name=="native_por_n"){word(dut.native_por_n);} else
 if(name=="native_rst_n"){word(dut.native_rst_n);} else
 if(name=="native_publish_valid"){word(dut.native_publish_valid);} else
 if(name=="native_publish_ready"){word(dut.native_publish_ready);} else
 if(name=="native_publish_data"){for(int i=127;i>=0;i--)word(dut.native_publish_data[i]);} else
 if(name=="native_publish_owner46"){word(uint32_t(dut.native_publish_owner46>>32));word(uint32_t(dut.native_publish_owner46));} else
 if(name=="native_publish_native_tag"){word(uint32_t(dut.native_publish_native_tag>>32));word(uint32_t(dut.native_publish_native_tag));} else
 if(name=="native_publish_native_generation"){word(uint32_t(dut.native_publish_native_generation>>32));word(uint32_t(dut.native_publish_native_generation));} else
 if(name=="native_source_lease_reserved"){word(dut.native_source_lease_reserved);} else
 if(name=="native_workspace_reserved"){word(dut.native_workspace_reserved);} else
 if(name=="native_issuer_namespace_reserved"){word(dut.native_issuer_namespace_reserved);} else
 if(name=="native_source_release_valid"){word(dut.native_source_release_valid);} else
 if(name=="native_source_release_identity"){word(uint32_t(dut.native_source_release_identity>>32));word(uint32_t(dut.native_source_release_identity));} else
 if(name=="native_source_release_ready"){word(dut.native_source_release_ready);} else
 if(name=="native_source_lease_live"){word(dut.native_source_lease_live);} else
 if(name=="native_workspace_lease_live"){word(dut.native_workspace_lease_live);} else
 if(name=="native_source_published"){word(dut.native_source_published);} else
 if(name=="native_issuer_binding_valid"){word(dut.native_issuer_binding_valid);} else
 if(name=="native_visibility_enable"){word(dut.native_visibility_enable);} else
 if(name=="native_rd_valid"){word(dut.native_rd_valid);} else
 if(name=="native_rd_ready"){word(dut.native_rd_ready);} else
 if(name=="native_rd_a"){word(dut.native_rd_a);} else
 if(name=="native_rd_b"){word(dut.native_rd_b);} else
 if(name=="native_rsp_valid"){word(dut.native_rsp_valid);} else
 if(name=="native_rsp_a"){for(int i=127;i>=0;i--)word(dut.native_rsp_a[i]);} else
 if(name=="native_rsp_b"){for(int i=127;i>=0;i--)word(dut.native_rsp_b[i]);} else
 if(name=="native_rsp_ready"){word(dut.native_rsp_ready);} else
 if(name=="native_wr_valid"){word(dut.native_wr_valid);} else
 if(name=="native_wr_ready"){word(dut.native_wr_ready);} else
 if(name=="native_wr_addr"){word(dut.native_wr_addr);} else
 if(name=="native_wr_data"){for(int i=127;i>=0;i--)word(dut.native_wr_data[i]);} else
 if(name=="native_ack_valid"){word(dut.native_ack_valid);} else
 if(name=="native_ack_ready"){word(dut.native_ack_ready);} else
 if(name=="native_ack_owner"){word(uint32_t(dut.native_ack_owner>>32));word(uint32_t(dut.native_ack_owner));} else
 if(name=="native_ack_slot"){word(dut.native_ack_slot);} else
 if(name=="native_ack_identity_fault"){word(dut.native_ack_identity_fault);} else
 if(name=="native_wr_owner"){word(uint32_t(dut.native_wr_owner>>32));word(uint32_t(dut.native_wr_owner));} else
 if(name=="native_ack_integration_fault"){word(dut.native_ack_integration_fault);} else
 if(name=="native_visible_valid"){word(dut.native_visible_valid);} else
 if(name=="native_visible_identity"){word(uint32_t(dut.native_visible_identity>>32));word(uint32_t(dut.native_visible_identity));} else
 if(name=="native_result_valid"){word(dut.native_result_valid);} else
 if(name=="native_result_ready"){word(dut.native_result_ready);} else
 if(name=="native_result"){for(int i=127;i>=0;i--)word(dut.native_result[i]);} else
 if(name=="native_consumer_accepted"){word(dut.native_consumer_accepted);} else
 if(name=="native_consumer_identity"){word(uint32_t(dut.native_consumer_identity>>32));word(uint32_t(dut.native_consumer_identity));} else
 if(name=="native_child_reverse_valid"){word(dut.native_child_reverse_valid);} else
 if(name=="native_child_reverse_identity"){word(uint32_t(dut.native_child_reverse_identity>>32));word(uint32_t(dut.native_child_reverse_identity));} else
 if(name=="native_child_reverse_ready"){word(dut.native_child_reverse_ready);} else
 if(name=="native_parent_reverse_valid"){word(dut.native_parent_reverse_valid);} else
 if(name=="native_parent_reverse_identity"){word(uint32_t(dut.native_parent_reverse_identity>>32));word(uint32_t(dut.native_parent_reverse_identity));} else
 if(name=="native_parent_reverse_ready"){word(dut.native_parent_reverse_ready);} else
 if(name=="native_reverse_CDC_valid"){word(dut.native_reverse_CDC_valid);} else
 if(name=="native_reverse_CDC_identity"){word(uint32_t(dut.native_reverse_CDC_identity>>32));word(uint32_t(dut.native_reverse_CDC_identity));} else
 if(name=="native_reverse_CDC_ready"){word(dut.native_reverse_CDC_ready);} else
 if(name=="native_drain_req_valid"){word(dut.native_drain_req_valid);} else
 if(name=="native_drain_req_identity"){word(uint32_t(dut.native_drain_req_identity>>32));word(uint32_t(dut.native_drain_req_identity));} else
 if(name=="native_drain_req_has_owner"){word(dut.native_drain_req_has_owner);} else
 if(name=="native_drain_req_reset_scope"){word(dut.native_drain_req_reset_scope);} else
 if(name=="native_drain_req_ready"){word(dut.native_drain_req_ready);} else
 if(name=="native_drain_rsp_valid"){word(dut.native_drain_rsp_valid);} else
 if(name=="native_drain_rsp_identity"){word(uint32_t(dut.native_drain_rsp_identity>>32));word(uint32_t(dut.native_drain_rsp_identity));} else
 if(name=="native_drain_rsp_has_owner"){word(dut.native_drain_rsp_has_owner);} else
 if(name=="native_drain_rsp_reset_scope"){word(dut.native_drain_rsp_reset_scope);} else
 if(name=="native_alldrain_live"){word(dut.native_alldrain_live);} else
 if(name=="native_drain_rsp_ready"){word(dut.native_drain_rsp_ready);} else
 if(name=="native_done_valid"){word(dut.native_done_valid);} else
 if(name=="native_done_ready"){word(dut.native_done_ready);} else
 if(name=="native_done_native_tag"){word(uint32_t(dut.native_done_native_tag>>32));word(uint32_t(dut.native_done_native_tag));} else
 if(name=="native_done_native_generation"){word(uint32_t(dut.native_done_native_generation>>32));word(uint32_t(dut.native_done_native_generation));} else
 if(name=="native_rearm_valid"){word(dut.native_rearm_valid);} else
 if(name=="native_admission_stop"){word(dut.native_admission_stop);} else
 if(name=="native_issuer_allcopy_fenced"){word(dut.native_issuer_allcopy_fenced);} else
 if(name=="native_rearm_ready"){word(dut.native_rearm_ready);} else
 if(name=="native_exclusive_lease"){word(dut.native_exclusive_lease);} else
 if(name=="native_fault"){word(dut.native_fault);} else
 if(name=="sm_rst_n"){word(uint32_t(dut.sm_rst_n>>32));word(uint32_t(dut.sm_rst_n));} else
 if(name=="sm_host_rd_valid"){word(uint32_t(dut.sm_host_rd_valid>>32));word(uint32_t(dut.sm_host_rd_valid));} else
 if(name=="sm_host_rd_ready"){word(uint32_t(dut.sm_host_rd_ready>>32));word(uint32_t(dut.sm_host_rd_ready));} else
 if(name=="sm_host_a"){for(int i=17;i>=0;i--)word(dut.sm_host_a[i]);} else
 if(name=="sm_host_b"){for(int i=17;i>=0;i--)word(dut.sm_host_b[i]);} else
 if(name=="sm_host_rsp_valid"){word(uint32_t(dut.sm_host_rsp_valid>>32));word(uint32_t(dut.sm_host_rsp_valid));} else
 if(name=="sm_host_rsp_ready"){word(uint32_t(dut.sm_host_rsp_ready>>32));word(uint32_t(dut.sm_host_rsp_ready));} else
 if(name=="sm_host_rsp_a"){for(int i=8191;i>=0;i--)word(dut.sm_host_rsp_a[i]);} else
 if(name=="sm_host_rsp_b"){for(int i=8191;i>=0;i--)word(dut.sm_host_rsp_b[i]);} else
 if(name=="sm_host_wr_valid"){word(uint32_t(dut.sm_host_wr_valid>>32));word(uint32_t(dut.sm_host_wr_valid));} else
 if(name=="sm_host_wr_ready"){word(uint32_t(dut.sm_host_wr_ready>>32));word(uint32_t(dut.sm_host_wr_ready));} else
 if(name=="sm_host_dst"){for(int i=17;i>=0;i--)word(dut.sm_host_dst[i]);} else
 if(name=="sm_host_wdata"){for(int i=8191;i>=0;i--)word(dut.sm_host_wdata[i]);} else
 if(name=="sm_host_ack_valid"){word(uint32_t(dut.sm_host_ack_valid>>32));word(uint32_t(dut.sm_host_ack_valid));} else
 if(name=="sm_host_ack_ready"){word(uint32_t(dut.sm_host_ack_ready>>32));word(uint32_t(dut.sm_host_ack_ready));} else
 if(name=="sm_simd_valid"){word(uint32_t(dut.sm_simd_valid>>32));word(uint32_t(dut.sm_simd_valid));} else
 if(name=="sm_simd_ready"){word(uint32_t(dut.sm_simd_ready>>32));word(uint32_t(dut.sm_simd_ready));} else
 if(name=="sm_simd_mul"){word(uint32_t(dut.sm_simd_mul>>32));word(uint32_t(dut.sm_simd_mul));} else
 if(name=="sm_simd_a"){for(int i=17;i>=0;i--)word(dut.sm_simd_a[i]);} else
 if(name=="sm_simd_b"){for(int i=17;i>=0;i--)word(dut.sm_simd_b[i]);} else
 if(name=="sm_simd_dst"){for(int i=17;i>=0;i--)word(dut.sm_simd_dst[i]);} else
 if(name=="sm_simd_done"){word(uint32_t(dut.sm_simd_done>>32));word(uint32_t(dut.sm_simd_done));} else
 if(name=="sm_simd_done_ready"){word(uint32_t(dut.sm_simd_done_ready>>32));word(uint32_t(dut.sm_simd_done_ready));} else
 if(name=="sm_simd_fault"){word(uint32_t(dut.sm_simd_fault>>32));word(uint32_t(dut.sm_simd_fault));} else
 if(name=="sm_scratch_valid"){word(uint32_t(dut.sm_scratch_valid>>32));word(uint32_t(dut.sm_scratch_valid));} else
 if(name=="sm_scratch_write"){word(uint32_t(dut.sm_scratch_write>>32));word(uint32_t(dut.sm_scratch_write));} else
 if(name=="sm_scratch_ready"){word(uint32_t(dut.sm_scratch_ready>>32));word(uint32_t(dut.sm_scratch_ready));} else
 if(name=="sm_scratch_addr"){for(int i=19;i>=0;i--)word(dut.sm_scratch_addr[i]);} else
 if(name=="sm_scratch_wdata"){for(int i=1023;i>=0;i--)word(dut.sm_scratch_wdata[i]);} else
 if(name=="sm_scratch_done"){word(uint32_t(dut.sm_scratch_done>>32));word(uint32_t(dut.sm_scratch_done));} else
 if(name=="sm_scratch_done_ready"){word(uint32_t(dut.sm_scratch_done_ready>>32));word(uint32_t(dut.sm_scratch_done_ready));} else
 if(name=="sm_scratch_rdata"){for(int i=1023;i>=0;i--)word(dut.sm_scratch_rdata[i]);} else
 if(name=="sm_host_owner"){for(int i=91;i>=0;i--)word(dut.sm_host_owner[i]);} else
 if(name=="sm_simd_owner"){for(int i=91;i>=0;i--)word(dut.sm_simd_owner[i]);} else
 if(name=="sm_host_ack_owner"){for(int i=91;i>=0;i--)word(dut.sm_host_ack_owner[i]);} else
 if(name=="sm_simd_done_owner"){for(int i=91;i>=0;i--)word(dut.sm_simd_done_owner[i]);} else
 if(name=="sm_host_ack_slot"){for(int i=17;i>=0;i--)word(dut.sm_host_ack_slot[i]);} else
 if(name=="sm_simd_done_slot"){for(int i=17;i>=0;i--)word(dut.sm_simd_done_slot[i]);} else
 if(name=="sm_identity_fault"){word(uint32_t(dut.sm_identity_fault>>32));word(uint32_t(dut.sm_identity_fault));} else
 if(name=="sm_simd_context_permit"){word(uint32_t(dut.sm_simd_context_permit>>32));word(uint32_t(dut.sm_simd_context_permit));} else
 if(name=="sm_rd_permit"){word(uint32_t(dut.sm_rd_permit>>32));word(uint32_t(dut.sm_rd_permit));} else
 if(name=="sm_wr_permit"){word(uint32_t(dut.sm_wr_permit>>32));word(uint32_t(dut.sm_wr_permit));} else
 if(name=="sm_rf_rsp_allow"){word(uint32_t(dut.sm_rf_rsp_allow>>32));word(uint32_t(dut.sm_rf_rsp_allow));} else
 if(name=="sm_rf_ack_allow"){word(uint32_t(dut.sm_rf_ack_allow>>32));word(uint32_t(dut.sm_rf_ack_allow));} else
 if(name=="sm_simd_binding_valid"){word(uint32_t(dut.sm_simd_binding_valid>>32));word(uint32_t(dut.sm_simd_binding_valid));} else
 if(name=="sm_simd_KV_related"){word(uint32_t(dut.sm_simd_KV_related>>32));word(uint32_t(dut.sm_simd_KV_related));} else
 if(name=="sm_simd_source_identity"){for(int i=127;i>=0;i--)word(dut.sm_simd_source_identity[i]);} else
 if(name=="sm_simd_key"){for(int i=39;i>=0;i--)word(dut.sm_simd_key[i]);} else
 if(name=="sm_host_rd_binding_valid"){word(uint32_t(dut.sm_host_rd_binding_valid>>32));word(uint32_t(dut.sm_host_rd_binding_valid));} else
 if(name=="sm_host_rd_KV_related"){word(uint32_t(dut.sm_host_rd_KV_related>>32));word(uint32_t(dut.sm_host_rd_KV_related));} else
 if(name=="sm_host_rd_identity"){for(int i=127;i>=0;i--)word(dut.sm_host_rd_identity[i]);} else
 if(name=="sm_host_rd_key"){for(int i=39;i>=0;i--)word(dut.sm_host_rd_key[i]);} else
 if(name=="sm_host_wr_binding_valid"){word(uint32_t(dut.sm_host_wr_binding_valid>>32));word(uint32_t(dut.sm_host_wr_binding_valid));} else
 if(name=="sm_host_wr_KV_related"){word(uint32_t(dut.sm_host_wr_KV_related>>32));word(uint32_t(dut.sm_host_wr_KV_related));} else
 if(name=="sm_host_wr_identity"){for(int i=127;i>=0;i--)word(dut.sm_host_wr_identity[i]);} else
 if(name=="sm_host_wr_key"){for(int i=39;i>=0;i--)word(dut.sm_host_wr_key[i]);} else
 if(name=="sm_host_rd_continuation_valid"){word(uint32_t(dut.sm_host_rd_continuation_valid>>32));word(uint32_t(dut.sm_host_rd_continuation_valid));} else
 if(name=="sm_host_wr_continuation_valid"){word(uint32_t(dut.sm_host_wr_continuation_valid>>32));word(uint32_t(dut.sm_host_wr_continuation_valid));} else
 if(name=="sm_rf_write_accept"){word(uint32_t(dut.sm_rf_write_accept>>32));word(uint32_t(dut.sm_rf_write_accept));} else
 if(name=="sm_rf_write_owner55"){for(int i=109;i>=0;i--)word(dut.sm_rf_write_owner55[i]);} else
 if(name=="sm_rf_ack_valid"){word(uint32_t(dut.sm_rf_ack_valid>>32));word(uint32_t(dut.sm_rf_ack_valid));} else
 if(name=="sm_rf_ack_accept"){word(uint32_t(dut.sm_rf_ack_accept>>32));word(uint32_t(dut.sm_rf_ack_accept));} else
 if(name=="sm_rf_ack_owner55"){for(int i=109;i>=0;i--)word(dut.sm_rf_ack_owner55[i]);} else
 if(name=="sm_rf_ack_fault"){word(uint32_t(dut.sm_rf_ack_fault>>32));word(uint32_t(dut.sm_rf_ack_fault));} else
 if(name=="sm_rf_read_accept"){word(uint32_t(dut.sm_rf_read_accept>>32));word(uint32_t(dut.sm_rf_read_accept));} else
 if(name=="sm_rf_read_a"){for(int i=17;i>=0;i--)word(dut.sm_rf_read_a[i]);} else
 if(name=="sm_rf_read_b"){for(int i=17;i>=0;i--)word(dut.sm_rf_read_b[i]);} else
 if(name=="sm_rf_rsp_valid"){word(uint32_t(dut.sm_rf_rsp_valid>>32));word(uint32_t(dut.sm_rf_rsp_valid));} else
 if(name=="sm_rf_rsp_accept"){word(uint32_t(dut.sm_rf_rsp_accept>>32));word(uint32_t(dut.sm_rf_rsp_accept));} else
 if(name=="sm_simd_context_accept"){word(uint32_t(dut.sm_simd_context_accept>>32));word(uint32_t(dut.sm_simd_context_accept));} else
 if(name=="sm_simd_context_owner55"){for(int i=109;i>=0;i--)word(dut.sm_simd_context_owner55[i]);} else
 if(name=="sm_simd_context_retire"){word(uint32_t(dut.sm_simd_context_retire>>32));word(uint32_t(dut.sm_simd_context_retire));} else
 if(name=="sm_simd_retire_owner55"){for(int i=109;i>=0;i--)word(dut.sm_simd_retire_owner55[i]);} else
 if(name=="sm_wr_continuation_valid"){word(uint32_t(dut.sm_wr_continuation_valid>>32));word(uint32_t(dut.sm_wr_continuation_valid));} else
 if(name=="sm_wr_continuation_source"){word(uint32_t(dut.sm_wr_continuation_source>>32));word(uint32_t(dut.sm_wr_continuation_source));} else
 if(name=="sm_rd_continuation_valid"){word(uint32_t(dut.sm_rd_continuation_valid>>32));word(uint32_t(dut.sm_rd_continuation_valid));} else
 if(name=="sm_rd_continuation_source"){word(uint32_t(dut.sm_rd_continuation_source>>32));word(uint32_t(dut.sm_rd_continuation_source));} else
 if(name=="sm_rd_context_owner55"){for(int i=109;i>=0;i--)word(dut.sm_rd_context_owner55[i]);} else
 if(name=="sm_wr_context_identity"){for(int i=127;i>=0;i--)word(dut.sm_wr_context_identity[i]);} else
 if(name=="sm_wr_context_key"){for(int i=39;i>=0;i--)word(dut.sm_wr_context_key[i]);} else
 if(name=="sm_wr_context_binding_valid"){word(uint32_t(dut.sm_wr_context_binding_valid>>32));word(uint32_t(dut.sm_wr_context_binding_valid));} else
 if(name=="sm_wr_context_KV_related"){word(uint32_t(dut.sm_wr_context_KV_related>>32));word(uint32_t(dut.sm_wr_context_KV_related));} else
 if(name=="sm_rd_context_identity"){for(int i=127;i>=0;i--)word(dut.sm_rd_context_identity[i]);} else
 if(name=="sm_rd_context_key"){for(int i=39;i>=0;i--)word(dut.sm_rd_context_key[i]);} else
 if(name=="sm_rd_context_binding_valid"){word(uint32_t(dut.sm_rd_context_binding_valid>>32));word(uint32_t(dut.sm_rd_context_binding_valid));} else
 if(name=="sm_rd_context_KV_related"){word(uint32_t(dut.sm_rd_context_KV_related>>32));word(uint32_t(dut.sm_rd_context_KV_related));} else
 if(name=="w2_rst_n"){for(int i=7;i>=0;i--)word(dut.w2_rst_n[i]);} else
 if(name=="w2_admission_stop"){for(int i=7;i>=0;i--)word(dut.w2_admission_stop[i]);} else
 if(name=="w2_rearm_v"){for(int i=7;i>=0;i--)word(dut.w2_rearm_v[i]);} else
 if(name=="w2_provider_fenced"){for(int i=7;i>=0;i--)word(dut.w2_provider_fenced[i]);} else
 if(name=="w2_reset_fenced"){for(int i=7;i>=0;i--)word(dut.w2_reset_fenced[i]);} else
 if(name=="w2_rearm_rdy"){for(int i=7;i>=0;i--)word(dut.w2_rearm_rdy[i]);} else
 if(name=="w2_idle"){for(int i=7;i>=0;i--)word(dut.w2_idle[i]);} else
 if(name=="w2_c_req_v"){for(int i=47;i>=0;i--)word(dut.w2_c_req_v[i]);} else
 if(name=="w2_c_req_we"){for(int i=47;i>=0;i--)word(dut.w2_c_req_we[i]);} else
 if(name=="w2_c_req_rdy"){for(int i=47;i>=0;i--)word(dut.w2_c_req_rdy[i]);} else
 if(name=="w2_c_req_addr"){for(int i=1631;i>=0;i--)word(dut.w2_c_req_addr[i]);} else
 if(name=="w2_c_req_tag"){for(int i=1535;i>=0;i--)word(dut.w2_c_req_tag[i]);} else
 if(name=="w2_c_req_gen"){for(int i=191;i>=0;i--)word(dut.w2_c_req_gen[i]);} else
 if(name=="w2_c_req_data"){for(int i=12287;i>=0;i--)word(dut.w2_c_req_data[i]);} else
 if(name=="w2_c_rsp_v"){for(int i=47;i>=0;i--)word(dut.w2_c_rsp_v[i]);} else
 if(name=="w2_c_wr_done_v"){for(int i=47;i>=0;i--)word(dut.w2_c_wr_done_v[i]);} else
 if(name=="w2_c_rsp_rdy"){for(int i=47;i>=0;i--)word(dut.w2_c_rsp_rdy[i]);} else
 if(name=="w2_c_wr_done_rdy"){for(int i=47;i>=0;i--)word(dut.w2_c_wr_done_rdy[i]);} else
 if(name=="w2_c_rsp_tag"){for(int i=1535;i>=0;i--)word(dut.w2_c_rsp_tag[i]);} else
 if(name=="w2_c_wr_done_tag"){for(int i=1535;i>=0;i--)word(dut.w2_c_wr_done_tag[i]);} else
 if(name=="w2_c_rsp_gen"){for(int i=191;i>=0;i--)word(dut.w2_c_rsp_gen[i]);} else
 if(name=="w2_c_wr_done_gen"){for(int i=191;i>=0;i--)word(dut.w2_c_wr_done_gen[i]);} else
 if(name=="w2_c_rsp_data"){for(int i=12287;i>=0;i--)word(dut.w2_c_rsp_data[i]);} else
 if(name=="w2_p_req_v"){for(int i=7;i>=0;i--)word(dut.w2_p_req_v[i]);} else
 if(name=="w2_p_req_we"){for(int i=7;i>=0;i--)word(dut.w2_p_req_we[i]);} else
 if(name=="w2_p_req_rdy"){for(int i=7;i>=0;i--)word(dut.w2_p_req_rdy[i]);} else
 if(name=="w2_p_req_addr"){for(int i=271;i>=0;i--)word(dut.w2_p_req_addr[i]);} else
 if(name=="w2_p_req_tag"){for(int i=279;i>=0;i--)word(dut.w2_p_req_tag[i]);} else
 if(name=="w2_p_req_gen"){for(int i=31;i>=0;i--)word(dut.w2_p_req_gen[i]);} else
 if(name=="w2_p_req_data"){for(int i=2047;i>=0;i--)word(dut.w2_p_req_data[i]);} else
 if(name=="w2_p_rsp_v"){for(int i=7;i>=0;i--)word(dut.w2_p_rsp_v[i]);} else
 if(name=="w2_p_wr_done_v"){for(int i=7;i>=0;i--)word(dut.w2_p_wr_done_v[i]);} else
 if(name=="w2_p_rsp_rdy"){for(int i=7;i>=0;i--)word(dut.w2_p_rsp_rdy[i]);} else
 if(name=="w2_p_wr_done_ready"){for(int i=7;i>=0;i--)word(dut.w2_p_wr_done_ready[i]);} else
 if(name=="w2_p_rsp_tag"){for(int i=279;i>=0;i--)word(dut.w2_p_rsp_tag[i]);} else
 if(name=="w2_p_wr_done_tag"){for(int i=279;i>=0;i--)word(dut.w2_p_wr_done_tag[i]);} else
 if(name=="w2_p_rsp_gen"){for(int i=31;i>=0;i--)word(dut.w2_p_rsp_gen[i]);} else
 if(name=="w2_p_wr_done_gen"){for(int i=31;i>=0;i--)word(dut.w2_p_wr_done_gen[i]);} else
 if(name=="w2_p_rsp_data"){for(int i=2047;i>=0;i--)word(dut.w2_p_rsp_data[i]);} else
 if(name=="w2_fault"){for(int i=7;i>=0;i--)word(dut.w2_fault[i]);} else
 if(name=="w2_repair_busy"){for(int i=7;i>=0;i--)word(dut.w2_repair_busy[i]);} else
 if(name=="w2_reverse_fenced"){for(int i=7;i>=0;i--)word(dut.w2_reverse_fenced[i]);} else
 if(name=="source_owner_allcopies_fenced"){word(uint32_t(dut.source_owner_allcopies_fenced>>32));word(uint32_t(dut.source_owner_allcopies_fenced));} else
 if(name=="source_owner_bind_mask"){for(int i=13;i>=0;i--)word(dut.source_owner_bind_mask[i]);} else
 if(name=="source_owner_bind_ready"){word(uint32_t(dut.source_owner_bind_ready>>32));word(uint32_t(dut.source_owner_bind_ready));} else
 if(name=="source_owner_bind_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_bind_tuple[i]);} else
 if(name=="source_owner_bind_valid"){word(uint32_t(dut.source_owner_bind_valid>>32));word(uint32_t(dut.source_owner_bind_valid));} else
 if(name=="source_owner_claim_initial"){word(uint32_t(dut.source_owner_claim_initial>>32));word(uint32_t(dut.source_owner_claim_initial));} else
 if(name=="source_owner_claim_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_claim_owner[i]);} else
 if(name=="source_owner_claim_ready"){word(uint32_t(dut.source_owner_claim_ready>>32));word(uint32_t(dut.source_owner_claim_ready));} else
 if(name=="source_owner_claim_row"){for(int i=5;i>=0;i--)word(dut.source_owner_claim_row[i]);} else
 if(name=="source_owner_claim_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_claim_tuple[i]);} else
 if(name=="source_owner_claim_valid"){word(uint32_t(dut.source_owner_claim_valid>>32));word(uint32_t(dut.source_owner_claim_valid));} else
 if(name=="source_owner_consumer_rows"){for(int i=13;i>=0;i--)word(dut.source_owner_consumer_rows[i]);} else
 if(name=="source_owner_expected_output_page_mask"){for(int i=63;i>=0;i--)word(dut.source_owner_expected_output_page_mask[i]);} else
 if(name=="source_owner_fault"){word(uint32_t(dut.source_owner_fault>>32));word(uint32_t(dut.source_owner_fault));} else
 if(name=="source_owner_frame_retire_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_frame_retire_owner[i]);} else
 if(name=="source_owner_frame_retire_ready"){word(uint32_t(dut.source_owner_frame_retire_ready>>32));word(uint32_t(dut.source_owner_frame_retire_ready));} else
 if(name=="source_owner_frame_retire_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_frame_retire_tuple[i]);} else
 if(name=="source_owner_frame_retire_valid"){word(uint32_t(dut.source_owner_frame_retire_valid>>32));word(uint32_t(dut.source_owner_frame_retire_valid));} else
 if(name=="source_owner_go_accepted"){word(uint32_t(dut.source_owner_go_accepted>>32));word(uint32_t(dut.source_owner_go_accepted));} else
 if(name=="source_owner_go_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_go_tuple[i]);} else
 if(name=="source_owner_held_session"){for(int i=127;i>=0;i--)word(dut.source_owner_held_session[i]);} else
 if(name=="source_owner_ingress_quiet"){word(uint32_t(dut.source_owner_ingress_quiet>>32));word(uint32_t(dut.source_owner_ingress_quiet));} else
 if(name=="source_owner_input_reverse_mask"){for(int i=13;i>=0;i--)word(dut.source_owner_input_reverse_mask[i]);} else
 if(name=="source_owner_input_reverse_ready"){word(uint32_t(dut.source_owner_input_reverse_ready>>32));word(uint32_t(dut.source_owner_input_reverse_ready));} else
 if(name=="source_owner_input_reverse_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_input_reverse_tuple[i]);} else
 if(name=="source_owner_input_reverse_valid"){word(uint32_t(dut.source_owner_input_reverse_valid>>32));word(uint32_t(dut.source_owner_input_reverse_valid));} else
 if(name=="source_owner_input_terminal_mask"){for(int i=13;i>=0;i--)word(dut.source_owner_input_terminal_mask[i]);} else
 if(name=="source_owner_input_terminal_ready"){word(uint32_t(dut.source_owner_input_terminal_ready>>32));word(uint32_t(dut.source_owner_input_terminal_ready));} else
 if(name=="source_owner_input_terminal_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_input_terminal_tuple[i]);} else
 if(name=="source_owner_input_terminal_valid"){word(uint32_t(dut.source_owner_input_terminal_valid>>32));word(uint32_t(dut.source_owner_input_terminal_valid));} else
 if(name=="source_owner_inputs_bound_mask"){for(int i=13;i>=0;i--)word(dut.source_owner_inputs_bound_mask[i]);} else
 if(name=="source_owner_inputs_bound_ready"){word(uint32_t(dut.source_owner_inputs_bound_ready>>32));word(uint32_t(dut.source_owner_inputs_bound_ready));} else
 if(name=="source_owner_inputs_bound_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_inputs_bound_tuple[i]);} else
 if(name=="source_owner_inputs_bound_valid"){word(uint32_t(dut.source_owner_inputs_bound_valid>>32));word(uint32_t(dut.source_owner_inputs_bound_valid));} else
 if(name=="source_owner_issued_input_live"){word(uint32_t(dut.source_owner_issued_input_live>>32));word(uint32_t(dut.source_owner_issued_input_live));} else
 if(name=="source_owner_issued_input_started"){word(uint32_t(dut.source_owner_issued_input_started>>32));word(uint32_t(dut.source_owner_issued_input_started));} else
 if(name=="source_owner_live_rows"){for(int i=13;i>=0;i--)word(dut.source_owner_live_rows[i]);} else
 if(name=="source_owner_next_source_PC"){for(int i=21;i>=0;i--)word(dut.source_owner_next_source_PC[i]);} else
 if(name=="source_owner_page_ack_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_page_ack_owner[i]);} else
 if(name=="source_owner_page_ack_ready"){word(uint32_t(dut.source_owner_page_ack_ready>>32));word(uint32_t(dut.source_owner_page_ack_ready));} else
 if(name=="source_owner_page_ack_valid"){word(uint32_t(dut.source_owner_page_ack_valid>>32));word(uint32_t(dut.source_owner_page_ack_valid));} else
 if(name=="source_owner_por_n"){word(uint32_t(dut.source_owner_por_n>>32));word(uint32_t(dut.source_owner_por_n));} else
 if(name=="source_owner_producer_visible_ready"){word(uint32_t(dut.source_owner_producer_visible_ready>>32));word(uint32_t(dut.source_owner_producer_visible_ready));} else
 if(name=="source_owner_producer_visible_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_producer_visible_tuple[i]);} else
 if(name=="source_owner_producer_visible_valid"){word(uint32_t(dut.source_owner_producer_visible_valid>>32));word(uint32_t(dut.source_owner_producer_visible_valid));} else
 if(name=="source_owner_publish_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_publish_owner[i]);} else
 if(name=="source_owner_publish_page_mask"){for(int i=63;i>=0;i--)word(dut.source_owner_publish_page_mask[i]);} else
 if(name=="source_owner_publish_ready"){word(uint32_t(dut.source_owner_publish_ready>>32));word(uint32_t(dut.source_owner_publish_ready));} else
 if(name=="source_owner_publish_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_publish_tuple[i]);} else
 if(name=="source_owner_publish_valid"){word(uint32_t(dut.source_owner_publish_valid>>32));word(uint32_t(dut.source_owner_publish_valid));} else
 if(name=="source_owner_published_rows"){for(int i=13;i>=0;i--)word(dut.source_owner_published_rows[i]);} else
 if(name=="source_owner_query_ready"){word(uint32_t(dut.source_owner_query_ready>>32));word(uint32_t(dut.source_owner_query_ready));} else
 if(name=="source_owner_query_result_owner"){for(int i=91;i>=0;i--)word(dut.source_owner_query_result_owner[i]);} else
 if(name=="source_owner_query_result_ready"){word(uint32_t(dut.source_owner_query_result_ready>>32));word(uint32_t(dut.source_owner_query_result_ready));} else
 if(name=="source_owner_query_result_slot"){for(int i=17;i>=0;i--)word(dut.source_owner_query_result_slot[i]);} else
 if(name=="source_owner_query_result_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_query_result_tuple[i]);} else
 if(name=="source_owner_query_result_valid"){word(uint32_t(dut.source_owner_query_result_valid>>32));word(uint32_t(dut.source_owner_query_result_valid));} else
 if(name=="source_owner_query_slot"){for(int i=17;i>=0;i--)word(dut.source_owner_query_slot[i]);} else
 if(name=="source_owner_query_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_query_tuple[i]);} else
 if(name=="source_owner_query_valid"){word(uint32_t(dut.source_owner_query_valid>>32));word(uint32_t(dut.source_owner_query_valid));} else
 if(name=="source_owner_query_version"){for(int i=21;i>=0;i--)word(dut.source_owner_query_version[i]);} else
 if(name=="source_owner_query_write"){word(uint32_t(dut.source_owner_query_write>>32));word(uint32_t(dut.source_owner_query_write));} else
 if(name=="source_owner_reverse_fenced"){word(uint32_t(dut.source_owner_reverse_fenced>>32));word(uint32_t(dut.source_owner_reverse_fenced));} else
 if(name=="source_owner_rf_range_ack_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_rf_range_ack_owner[i]);} else
 if(name=="source_owner_rf_range_ack_page_mask"){for(int i=63;i>=0;i--)word(dut.source_owner_rf_range_ack_page_mask[i]);} else
 if(name=="source_owner_rf_range_ack_ready"){word(uint32_t(dut.source_owner_rf_range_ack_ready>>32));word(uint32_t(dut.source_owner_rf_range_ack_ready));} else
 if(name=="source_owner_rf_range_ack_tuple"){for(int i=477;i>=0;i--)word(dut.source_owner_rf_range_ack_tuple[i]);} else
 if(name=="source_owner_rf_range_ack_valid"){word(uint32_t(dut.source_owner_rf_range_ack_valid>>32));word(uint32_t(dut.source_owner_rf_range_ack_valid));} else
 if(name=="source_owner_row_barrier_ready"){word(uint32_t(dut.source_owner_row_barrier_ready>>32));word(uint32_t(dut.source_owner_row_barrier_ready));} else
 if(name=="source_owner_session_begin_id"){for(int i=127;i>=0;i--)word(dut.source_owner_session_begin_id[i]);} else
 if(name=="source_owner_session_begin_ready"){word(uint32_t(dut.source_owner_session_begin_ready>>32));word(uint32_t(dut.source_owner_session_begin_ready));} else
 if(name=="source_owner_session_begin_valid"){word(uint32_t(dut.source_owner_session_begin_valid>>32));word(uint32_t(dut.source_owner_session_begin_valid));} else
 if(name=="source_owner_source_native_retire_owner"){for(int i=109;i>=0;i--)word(dut.source_owner_source_native_retire_owner[i]);} else
 if(name=="source_owner_source_native_retire_ready"){word(uint32_t(dut.source_owner_source_native_retire_ready>>32));word(uint32_t(dut.source_owner_source_native_retire_ready));} else
 if(name=="source_owner_source_native_retire_session"){for(int i=127;i>=0;i--)word(dut.source_owner_source_native_retire_session[i]);} else
 if(name=="source_owner_source_native_retire_valid"){word(uint32_t(dut.source_owner_source_native_retire_valid>>32));word(uint32_t(dut.source_owner_source_native_retire_valid));} else
 if(name=="source_owner_source_native_retire_version"){for(int i=21;i>=0;i--)word(dut.source_owner_source_native_retire_version[i]);} else
 if(name=="source_owner_source_owner_retained"){word(uint32_t(dut.source_owner_source_owner_retained>>32));word(uint32_t(dut.source_owner_source_owner_retained));} else
 if(name=="source_owner_warm_reset"){word(uint32_t(dut.source_owner_warm_reset>>32));word(uint32_t(dut.source_owner_warm_reset));} else
 throw std::runtime_error("unknown pin");}
 else if(op=="SET"){in>>name>>value;if(in>>extra)throw std::runtime_error("extra");
 if(name=="sector_map_rank"){auto v=unpack(value,1);dut.sector_map_rank=v[0];std::cout<<"OK";} else
 if(name=="sector_reverse_rank"){auto v=unpack(value,1);dut.sector_reverse_rank=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_por_n"){auto v=unpack(value,1);dut.state_rpc_por_n=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_run_enable"){auto v=unpack(value,1);dut.state_rpc_run_enable=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_local_reset"){auto v=unpack(value,1);dut.state_rpc_local_reset=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_source_bound"){auto v=unpack(value,1);dut.state_rpc_source_bound=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_state_base_rank0"){auto v=unpack(value,34);dut.state_rpc_state_base_rank0=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_state_base_rank1"){auto v=unpack(value,34);dut.state_rpc_state_base_rank1=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_rpc_valid"){auto v=unpack(value,1);dut.state_rpc_rpc_valid=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_rpc_identity"){auto v=unpack(value,64);dut.state_rpc_rpc_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_rpc_rank"){auto v=unpack(value,1);dut.state_rpc_rpc_rank=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_rpc_write"){auto v=unpack(value,1);dut.state_rpc_rpc_write=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_rpc_address"){auto v=unpack(value,34);dut.state_rpc_rpc_address=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_rpc_bytes"){auto v=unpack(value,16);dut.state_rpc_rpc_bytes=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_rpc_payload"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.state_rpc_rpc_payload[i]=v[i];std::cout<<"OK";} else
 if(name=="state_rpc_rpc_reply_ready"){auto v=unpack(value,1);dut.state_rpc_rpc_reply_ready=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_map_valid"){auto v=unpack(value,1);dut.state_rpc_map_valid=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_map_rank"){auto v=unpack(value,1);dut.state_rpc_map_rank=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_map_sector_granted"){auto v=unpack(value,1);dut.state_rpc_map_sector_granted=v[0];std::cout<<"OK";} else
 if(name=="state_rpc_map_source_addr"){auto v=unpack(value,34);dut.state_rpc_map_source_addr=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_map_physical_addr"){auto v=unpack(value,34);dut.state_rpc_map_physical_addr=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_map_owner"){auto v=unpack(value,46);dut.state_rpc_map_owner=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="state_rpc_sector_capture_ready"){auto v=unpack(value,1);dut.state_rpc_sector_capture_ready=v[0];std::cout<<"OK";} else
 if(name=="local_por_n"){auto v=unpack(value,1);dut.local_por_n=v[0];std::cout<<"OK";} else
 if(name=="local_run_enable"){auto v=unpack(value,1);dut.local_run_enable=v[0];std::cout<<"OK";} else
 if(name=="local_local_reset"){auto v=unpack(value,1);dut.local_local_reset=v[0];std::cout<<"OK";} else
 if(name=="local_source_bound"){auto v=unpack(value,1);dut.local_source_bound=v[0];std::cout<<"OK";} else
 if(name=="local_stage_root_accept"){auto v=unpack(value,64);dut.local_stage_root_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="local_stage_root_retire"){auto v=unpack(value,64);dut.local_stage_root_retire=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="local_stage_root_owner"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.local_stage_root_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="local_stage_root_retire_owner"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.local_stage_root_retire_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="issuer_por_n"){auto v=unpack(value,1);dut.issuer_por_n=v[0];std::cout<<"OK";} else
 if(name=="issuer_run_enable"){auto v=unpack(value,1);dut.issuer_run_enable=v[0];std::cout<<"OK";} else
 if(name=="issuer_session_begin_valid"){auto v=unpack(value,1);dut.issuer_session_begin_valid=v[0];std::cout<<"OK";} else
 if(name=="issuer_session_begin_id"){auto v=unpack(value,64);dut.issuer_session_begin_id=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_source_quiescent"){auto v=unpack(value,8);dut.issuer_source_quiescent=v[0];std::cout<<"OK";} else
 if(name=="issuer_issue_valid"){auto v=unpack(value,64);dut.issuer_issue_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_backend_go_ready"){auto v=unpack(value,64);dut.issuer_backend_go_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_issue_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.issuer_issue_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="issuer_issue_owner"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.issuer_issue_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="issuer_producer_visible_valid"){auto v=unpack(value,64);dut.issuer_producer_visible_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_whole_terminal_valid"){auto v=unpack(value,64);dut.issuer_whole_terminal_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_whole_reverse_valid"){auto v=unpack(value,64);dut.issuer_whole_reverse_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="issuer_producer_visible_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.issuer_producer_visible_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="issuer_whole_terminal_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.issuer_whole_terminal_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="issuer_whole_reverse_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.issuer_whole_reverse_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="state_por_n"){auto v=unpack(value,1);dut.state_por_n=v[0];std::cout<<"OK";} else
 if(name=="state_run_enable"){auto v=unpack(value,1);dut.state_run_enable=v[0];std::cout<<"OK";} else
 if(name=="state_local_reset"){auto v=unpack(value,1);dut.state_local_reset=v[0];std::cout<<"OK";} else
 if(name=="state_source_bound"){auto v=unpack(value,1);dut.state_source_bound=v[0];std::cout<<"OK";} else
 if(name=="state_state_client_mask"){auto v=unpack(value,6);dut.state_state_client_mask=v[0];std::cout<<"OK";} else
 if(name=="rfdrain_por_n"){auto v=unpack(value,64);dut.rfdrain_por_n=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_rst_n"){auto v=unpack(value,64);dut.rfdrain_rst_n=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_run_enable"){auto v=unpack(value,64);dut.rfdrain_run_enable=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_request_accept"){auto v=unpack(value,64);dut.rfdrain_w6_request_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_request_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_request_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_binding_valid"){auto v=unpack(value,64);dut.rfdrain_w6_binding_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_KV_related"){auto v=unpack(value,64);dut.rfdrain_w6_KV_related=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_internal_SIMD"){auto v=unpack(value,64);dut.rfdrain_w6_internal_SIMD=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_identity"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_identity[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_key"){auto v=unpack(value,1280);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_key[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_host_ACK_accept"){auto v=unpack(value,64);dut.rfdrain_w6_host_ACK_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_SIMD_ACK_accept"){auto v=unpack(value,64);dut.rfdrain_w6_SIMD_ACK_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_ACK_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_ACK_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_consumer_accept"){auto v=unpack(value,64);dut.rfdrain_w6_consumer_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_consumer_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_consumer_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_child_accept"){auto v=unpack(value,64);dut.rfdrain_w6_child_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_child_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_child_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_parent_accept"){auto v=unpack(value,64);dut.rfdrain_w6_parent_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_parent_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_parent_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_CDC_accept"){auto v=unpack(value,64);dut.rfdrain_w6_CDC_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_CDC_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_CDC_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_retire_accept"){auto v=unpack(value,64);dut.rfdrain_w6_retire_accept=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_retire_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_retire_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_local_drain_owner55"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.rfdrain_w6_local_drain_owner55[i]=v[i];std::cout<<"OK";} else
 if(name=="rfdrain_w6_local_drain_has_owner"){auto v=unpack(value,64);dut.rfdrain_w6_local_drain_has_owner=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfdrain_w6_local_drain_reset_scope"){auto v=unpack(value,64);dut.rfdrain_w6_local_drain_reset_scope=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="rfjoin_por_n"){auto v=unpack(value,2);dut.rfjoin_por_n=v[0];std::cout<<"OK";} else
 if(name=="rfjoin_rst_n"){auto v=unpack(value,2);dut.rfjoin_rst_n=v[0];std::cout<<"OK";} else
 if(name=="rfjoin_run_enable"){auto v=unpack(value,2);dut.rfjoin_run_enable=v[0];std::cout<<"OK";} else
 if(name=="sector_por_n"){auto v=unpack(value,1);dut.sector_por_n=v[0];std::cout<<"OK";} else
 if(name=="sector_run_enable"){auto v=unpack(value,1);dut.sector_run_enable=v[0];std::cout<<"OK";} else
 if(name=="sector_local_reset"){auto v=unpack(value,1);dut.sector_local_reset=v[0];std::cout<<"OK";} else
 if(name=="sector_alloc_valid"){auto v=unpack(value,1);dut.sector_alloc_valid=v[0];std::cout<<"OK";} else
 if(name=="sector_alloc_source"){auto v=unpack(value,127);for(unsigned i=0;i<v.size();i++)dut.sector_alloc_source[i]=v[i];std::cout<<"OK";} else
 if(name=="sector_alloc_rmw"){auto v=unpack(value,1);dut.sector_alloc_rmw=v[0];std::cout<<"OK";} else
 if(name=="sector_map_valid"){auto v=unpack(value,1);dut.sector_map_valid=v[0];std::cout<<"OK";} else
 if(name=="sector_map_sector_clear"){auto v=unpack(value,1);dut.sector_map_sector_clear=v[0];std::cout<<"OK";} else
 if(name=="sector_map_addr"){auto v=unpack(value,34);dut.sector_map_addr=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sector_map_PC"){auto v=unpack(value,7);dut.sector_map_PC=v[0];std::cout<<"OK";} else
 if(name=="sector_map_client"){auto v=unpack(value,3);dut.sector_map_client=v[0];std::cout<<"OK";} else
 if(name=="sector_map_tag"){auto v=unpack(value,32);dut.sector_map_tag=v[0];std::cout<<"OK";} else
 if(name=="sector_map_gen"){auto v=unpack(value,4);dut.sector_map_gen=v[0];std::cout<<"OK";} else
 if(name=="sector_reverse_valid"){auto v=unpack(value,1);dut.sector_reverse_valid=v[0];std::cout<<"OK";} else
 if(name=="sector_reverse_route"){auto v=unpack(value,80);for(unsigned i=0;i<v.size();i++)dut.sector_reverse_route[i]=v[i];std::cout<<"OK";} else
 if(name=="sector_reverse_write"){auto v=unpack(value,1);dut.sector_reverse_write=v[0];std::cout<<"OK";} else
 if(name=="sector_release_valid"){auto v=unpack(value,1);dut.sector_release_valid=v[0];std::cout<<"OK";} else
 if(name=="sector_release_identity"){auto v=unpack(value,207);for(unsigned i=0;i<v.size();i++)dut.sector_release_identity[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_por_n"){auto v=unpack(value,1);dut.kv_por_n=v[0];std::cout<<"OK";} else
 if(name=="kv_run_enable"){auto v=unpack(value,1);dut.kv_run_enable=v[0];std::cout<<"OK";} else
 if(name=="kv_quiesce"){auto v=unpack(value,1);dut.kv_quiesce=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_valid"){auto v=unpack(value,1);dut.kv_cmd_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_op"){auto v=unpack(value,3);dut.kv_cmd_op=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_identity"){auto v=unpack(value,64);dut.kv_cmd_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_cmd_key"){auto v=unpack(value,20);dut.kv_cmd_key=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_producer"){auto v=unpack(value,64);dut.kv_cmd_producer=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_cmd_sequence"){auto v=unpack(value,64);dut.kv_cmd_sequence=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_cmd_PC"){auto v=unpack(value,11);dut.kv_cmd_PC=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_consumer"){auto v=unpack(value,1);dut.kv_cmd_consumer=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_stage_beat"){auto v=unpack(value,4);dut.kv_cmd_stage_beat=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_stage_base"){auto v=unpack(value,10);dut.kv_cmd_stage_base=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_stage_SM"){auto v=unpack(value,5);dut.kv_cmd_stage_SM=v[0];std::cout<<"OK";} else
 if(name=="kv_cmd_stage_data"){auto v=unpack(value,512);for(unsigned i=0;i<v.size();i++)dut.kv_cmd_stage_data[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_cmd_K_base"){auto v=unpack(value,34);dut.kv_cmd_K_base=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_cmd_V_base"){auto v=unpack(value,34);dut.kv_cmd_V_base=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_rsp_ready"){auto v=unpack(value,1);dut.kv_rsp_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_commit_ready"){auto v=unpack(value,1);dut.kv_commit_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_valid"){auto v=unpack(value,1);dut.kv_payload_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_identity"){auto v=unpack(value,64);dut.kv_payload_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_payload_key"){auto v=unpack(value,20);dut.kv_payload_key=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_sector"){auto v=unpack(value,9);dut.kv_payload_sector=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_source_addr"){auto v=unpack(value,34);dut.kv_payload_source_addr=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_payload_visible"){auto v=unpack(value,1);dut.kv_payload_visible=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_reverse"){auto v=unpack(value,1);dut.kv_payload_reverse=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_write"){auto v=unpack(value,1);dut.kv_payload_write=v[0];std::cout<<"OK";} else
 if(name=="kv_payload_rdata"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.kv_payload_rdata[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_payload_req_ready"){auto v=unpack(value,1);dut.kv_payload_req_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_valid"){auto v=unpack(value,1);dut.kv_hydrate_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_key"){auto v=unpack(value,20);dut.kv_hydrate_key=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_producer"){auto v=unpack(value,64);dut.kv_hydrate_producer=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_native_valid"){auto v=unpack(value,64);dut.kv_native_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_native_write"){auto v=unpack(value,64);dut.kv_native_write=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_native_addr"){auto v=unpack(value,640);for(unsigned i=0;i<v.size();i++)dut.kv_native_addr[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_native_wdata"){auto v=unpack(value,32768);for(unsigned i=0;i<v.size();i++)dut.kv_native_wdata[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_native_done_ready"){auto v=unpack(value,64);dut.kv_native_done_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_source_bound"){auto v=unpack(value,1);dut.kv_source_bound=v[0];std::cout<<"OK";} else
 if(name=="kv_state_base_rank0"){auto v=unpack(value,34);dut.kv_state_base_rank0=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_state_base_rank1"){auto v=unpack(value,34);dut.kv_state_base_rank1=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_rst_n"){auto v=unpack(value,1);dut.kv_rst_n=v[0];std::cout<<"OK";} else
 if(name=="kv_endpoint_fault"){auto v=unpack(value,1);dut.kv_endpoint_fault=v[0];std::cout<<"OK";} else
 if(name=="kv_native_issue_valid"){auto v=unpack(value,1);dut.kv_native_issue_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_native_issue_tuple"){auto v=unpack(value,230);for(unsigned i=0;i<v.size();i++)dut.kv_native_issue_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_native_complete_valid"){auto v=unpack(value,1);dut.kv_native_complete_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_native_complete_tuple"){auto v=unpack(value,230);for(unsigned i=0;i<v.size();i++)dut.kv_native_complete_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_native_reverse_valid"){auto v=unpack(value,1);dut.kv_native_reverse_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_native_reverse_tuple"){auto v=unpack(value,230);for(unsigned i=0;i<v.size();i++)dut.kv_native_reverse_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_cohort_req_ready"){auto v=unpack(value,8);dut.kv_cohort_req_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_cohort_rsp_valid"){auto v=unpack(value,8);dut.kv_cohort_rsp_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_cohort_rsp_tuple"){auto v=unpack(value,672);for(unsigned i=0;i<v.size();i++)dut.kv_cohort_rsp_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="kv_cohort_rsp_empty"){auto v=unpack(value,8);dut.kv_cohort_rsp_empty=v[0];std::cout<<"OK";} else
 if(name=="native_por_n"){auto v=unpack(value,1);dut.native_por_n=v[0];std::cout<<"OK";} else
 if(name=="native_rst_n"){auto v=unpack(value,1);dut.native_rst_n=v[0];std::cout<<"OK";} else
 if(name=="native_publish_valid"){auto v=unpack(value,1);dut.native_publish_valid=v[0];std::cout<<"OK";} else
 if(name=="native_publish_data"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.native_publish_data[i]=v[i];std::cout<<"OK";} else
 if(name=="native_publish_owner46"){auto v=unpack(value,46);dut.native_publish_owner46=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_publish_native_tag"){auto v=unpack(value,64);dut.native_publish_native_tag=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_publish_native_generation"){auto v=unpack(value,64);dut.native_publish_native_generation=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_source_lease_reserved"){auto v=unpack(value,1);dut.native_source_lease_reserved=v[0];std::cout<<"OK";} else
 if(name=="native_workspace_reserved"){auto v=unpack(value,1);dut.native_workspace_reserved=v[0];std::cout<<"OK";} else
 if(name=="native_issuer_namespace_reserved"){auto v=unpack(value,1);dut.native_issuer_namespace_reserved=v[0];std::cout<<"OK";} else
 if(name=="native_source_release_valid"){auto v=unpack(value,1);dut.native_source_release_valid=v[0];std::cout<<"OK";} else
 if(name=="native_source_release_identity"){auto v=unpack(value,55);dut.native_source_release_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_issuer_binding_valid"){auto v=unpack(value,1);dut.native_issuer_binding_valid=v[0];std::cout<<"OK";} else
 if(name=="native_visibility_enable"){auto v=unpack(value,1);dut.native_visibility_enable=v[0];std::cout<<"OK";} else
 if(name=="native_rd_ready"){auto v=unpack(value,1);dut.native_rd_ready=v[0];std::cout<<"OK";} else
 if(name=="native_rsp_valid"){auto v=unpack(value,1);dut.native_rsp_valid=v[0];std::cout<<"OK";} else
 if(name=="native_rsp_a"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.native_rsp_a[i]=v[i];std::cout<<"OK";} else
 if(name=="native_rsp_b"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.native_rsp_b[i]=v[i];std::cout<<"OK";} else
 if(name=="native_wr_ready"){auto v=unpack(value,1);dut.native_wr_ready=v[0];std::cout<<"OK";} else
 if(name=="native_ack_valid"){auto v=unpack(value,1);dut.native_ack_valid=v[0];std::cout<<"OK";} else
 if(name=="native_ack_owner"){auto v=unpack(value,46);dut.native_ack_owner=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_ack_slot"){auto v=unpack(value,9);dut.native_ack_slot=v[0];std::cout<<"OK";} else
 if(name=="native_ack_identity_fault"){auto v=unpack(value,1);dut.native_ack_identity_fault=v[0];std::cout<<"OK";} else
 if(name=="native_result_ready"){auto v=unpack(value,1);dut.native_result_ready=v[0];std::cout<<"OK";} else
 if(name=="native_child_reverse_valid"){auto v=unpack(value,1);dut.native_child_reverse_valid=v[0];std::cout<<"OK";} else
 if(name=="native_child_reverse_identity"){auto v=unpack(value,55);dut.native_child_reverse_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_parent_reverse_valid"){auto v=unpack(value,1);dut.native_parent_reverse_valid=v[0];std::cout<<"OK";} else
 if(name=="native_parent_reverse_identity"){auto v=unpack(value,55);dut.native_parent_reverse_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_reverse_CDC_valid"){auto v=unpack(value,1);dut.native_reverse_CDC_valid=v[0];std::cout<<"OK";} else
 if(name=="native_reverse_CDC_identity"){auto v=unpack(value,55);dut.native_reverse_CDC_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_drain_req_ready"){auto v=unpack(value,1);dut.native_drain_req_ready=v[0];std::cout<<"OK";} else
 if(name=="native_drain_rsp_valid"){auto v=unpack(value,1);dut.native_drain_rsp_valid=v[0];std::cout<<"OK";} else
 if(name=="native_drain_rsp_identity"){auto v=unpack(value,55);dut.native_drain_rsp_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="native_drain_rsp_has_owner"){auto v=unpack(value,1);dut.native_drain_rsp_has_owner=v[0];std::cout<<"OK";} else
 if(name=="native_drain_rsp_reset_scope"){auto v=unpack(value,1);dut.native_drain_rsp_reset_scope=v[0];std::cout<<"OK";} else
 if(name=="native_alldrain_live"){auto v=unpack(value,9);dut.native_alldrain_live=v[0];std::cout<<"OK";} else
 if(name=="native_done_ready"){auto v=unpack(value,1);dut.native_done_ready=v[0];std::cout<<"OK";} else
 if(name=="native_rearm_valid"){auto v=unpack(value,1);dut.native_rearm_valid=v[0];std::cout<<"OK";} else
 if(name=="native_admission_stop"){auto v=unpack(value,1);dut.native_admission_stop=v[0];std::cout<<"OK";} else
 if(name=="native_issuer_allcopy_fenced"){auto v=unpack(value,1);dut.native_issuer_allcopy_fenced=v[0];std::cout<<"OK";} else
 if(name=="sm_rst_n"){auto v=unpack(value,64);dut.sm_rst_n=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_rd_valid"){auto v=unpack(value,64);dut.sm_host_rd_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_a"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_host_a[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_b"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_host_b[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_rsp_ready"){auto v=unpack(value,64);dut.sm_host_rsp_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_wr_valid"){auto v=unpack(value,64);dut.sm_host_wr_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_dst"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_host_dst[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_wdata"){auto v=unpack(value,262144);for(unsigned i=0;i<v.size();i++)dut.sm_host_wdata[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_ack_ready"){auto v=unpack(value,64);dut.sm_host_ack_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_simd_valid"){auto v=unpack(value,64);dut.sm_simd_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_simd_mul"){auto v=unpack(value,64);dut.sm_simd_mul=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_simd_a"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_simd_a[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_b"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_simd_b[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_dst"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.sm_simd_dst[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_done_ready"){auto v=unpack(value,64);dut.sm_simd_done_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_owner"){auto v=unpack(value,2944);for(unsigned i=0;i<v.size();i++)dut.sm_host_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_owner"){auto v=unpack(value,2944);for(unsigned i=0;i<v.size();i++)dut.sm_simd_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_binding_valid"){auto v=unpack(value,64);dut.sm_simd_binding_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_simd_KV_related"){auto v=unpack(value,64);dut.sm_simd_KV_related=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_simd_source_identity"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.sm_simd_source_identity[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_key"){auto v=unpack(value,1280);for(unsigned i=0;i<v.size();i++)dut.sm_simd_key[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_rd_binding_valid"){auto v=unpack(value,64);dut.sm_host_rd_binding_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_rd_KV_related"){auto v=unpack(value,64);dut.sm_host_rd_KV_related=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_rd_identity"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.sm_host_rd_identity[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_rd_key"){auto v=unpack(value,1280);for(unsigned i=0;i<v.size();i++)dut.sm_host_rd_key[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_wr_binding_valid"){auto v=unpack(value,64);dut.sm_host_wr_binding_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_wr_KV_related"){auto v=unpack(value,64);dut.sm_host_wr_KV_related=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_wr_identity"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.sm_host_wr_identity[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_wr_key"){auto v=unpack(value,1280);for(unsigned i=0;i<v.size();i++)dut.sm_host_wr_key[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_host_rd_continuation_valid"){auto v=unpack(value,64);dut.sm_host_rd_continuation_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_wr_continuation_valid"){auto v=unpack(value,64);dut.sm_host_wr_continuation_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="w2_rst_n"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_rst_n[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_admission_stop"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_admission_stop[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_rearm_v"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_rearm_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_provider_fenced"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_provider_fenced[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_reset_fenced"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_reset_fenced[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_v"){auto v=unpack(value,1536);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_we"){auto v=unpack(value,1536);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_we[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_addr"){auto v=unpack(value,52224);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_addr[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_tag"){auto v=unpack(value,49152);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_gen"){auto v=unpack(value,6144);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_data"){auto v=unpack(value,393216);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_data[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_rsp_rdy"){auto v=unpack(value,1536);for(unsigned i=0;i<v.size();i++)dut.w2_c_rsp_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_wr_done_rdy"){auto v=unpack(value,1536);for(unsigned i=0;i<v.size();i++)dut.w2_c_wr_done_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_req_rdy"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_p_req_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_v"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_v"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_tag"){auto v=unpack(value,8960);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_tag"){auto v=unpack(value,8960);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_gen"){auto v=unpack(value,1024);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_gen"){auto v=unpack(value,1024);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_data"){auto v=unpack(value,65536);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_data[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_reverse_fenced"){auto v=unpack(value,256);for(unsigned i=0;i<v.size();i++)dut.w2_reverse_fenced[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_allcopies_fenced"){auto v=unpack(value,64);dut.source_owner_allcopies_fenced=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_bind_mask"){auto v=unpack(value,448);for(unsigned i=0;i<v.size();i++)dut.source_owner_bind_mask[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_bind_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.source_owner_bind_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_bind_valid"){auto v=unpack(value,64);dut.source_owner_bind_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_claim_initial"){auto v=unpack(value,64);dut.source_owner_claim_initial=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_claim_owner"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.source_owner_claim_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_claim_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.source_owner_claim_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_claim_valid"){auto v=unpack(value,64);dut.source_owner_claim_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_ingress_quiet"){auto v=unpack(value,64);dut.source_owner_ingress_quiet=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_por_n"){auto v=unpack(value,64);dut.source_owner_por_n=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_query_result_ready"){auto v=unpack(value,64);dut.source_owner_query_result_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_query_slot"){auto v=unpack(value,576);for(unsigned i=0;i<v.size();i++)dut.source_owner_query_slot[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_query_tuple"){auto v=unpack(value,15296);for(unsigned i=0;i<v.size();i++)dut.source_owner_query_tuple[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_query_valid"){auto v=unpack(value,64);dut.source_owner_query_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_query_version"){auto v=unpack(value,704);for(unsigned i=0;i<v.size();i++)dut.source_owner_query_version[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_query_write"){auto v=unpack(value,64);dut.source_owner_query_write=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_reverse_fenced"){auto v=unpack(value,64);dut.source_owner_reverse_fenced=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_session_begin_id"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.source_owner_session_begin_id[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_session_begin_valid"){auto v=unpack(value,64);dut.source_owner_session_begin_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_source_native_retire_owner"){auto v=unpack(value,3520);for(unsigned i=0;i<v.size();i++)dut.source_owner_source_native_retire_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_source_native_retire_session"){auto v=unpack(value,4096);for(unsigned i=0;i<v.size();i++)dut.source_owner_source_native_retire_session[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_source_native_retire_valid"){auto v=unpack(value,64);dut.source_owner_source_native_retire_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="source_owner_source_native_retire_version"){auto v=unpack(value,704);for(unsigned i=0;i<v.size();i++)dut.source_owner_source_native_retire_version[i]=v[i];std::cout<<"OK";} else
 if(name=="source_owner_warm_reset"){auto v=unpack(value,64);dut.source_owner_warm_reset=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 throw std::runtime_error("unknown/output pin");}
 else throw std::runtime_error("command");
 std::cout<<"\n"<<std::flush;}catch(const std::exception&e){std::cout<<"ERR "<<e.what()<<"\n"<<std::flush;return 2;}}dut.final();return 0;}
