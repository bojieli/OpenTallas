#include "Vot_gpu_qwen_hbm_integrated.h"
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
 Vot_gpu_qwen_hbm_integrated dut(&context); std::string line; unsigned half=0; const unsigned delta[6]={416,417,417,416,417,417};
 while(std::getline(std::cin,line)){try{std::istringstream in(line);std::string op,name,value,extra;in>>op;
 if(op=="HELLO"){dut.eval();std::cout<<"ot_gpu_qwen_hbm_integrated ENABLE="<<unsigned(dut.assembly_enabled)<<" SM=64 W2=128";}
 else if(op=="EVAL"){if(in>>extra)throw std::runtime_error("extra");dut.eval();std::cout<<"OK";}
 else if(op=="EDGE"){if(in>>extra)throw std::runtime_error("extra");dut.stream_clk=0;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=1;dut.eval();context.timeInc(delta[half++%6]);dut.stream_clk=0;dut.eval();std::cout<<"OK";}
 else if(op=="GET"){in>>name;if(in>>extra)throw std::runtime_error("extra");
 if(name=="stream_clk"){word(dut.stream_clk);} else
 if(name=="assembly_enabled"){word(dut.assembly_enabled);} else
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
 if(name=="kv_shared_valid"){word(dut.kv_shared_valid);} else
 if(name=="kv_shared_write"){word(dut.kv_shared_write);} else
 if(name=="kv_shared_ready"){word(dut.kv_shared_ready);} else
 if(name=="kv_shared_addr"){word(dut.kv_shared_addr);} else
 if(name=="kv_shared_SM"){word(dut.kv_shared_SM);} else
 if(name=="kv_shared_rank"){word(dut.kv_shared_rank);} else
 if(name=="kv_shared_wdata"){for(int i=15;i>=0;i--)word(dut.kv_shared_wdata[i]);} else
 if(name=="kv_shared_done"){word(dut.kv_shared_done);} else
 if(name=="kv_shared_done_ready"){word(dut.kv_shared_done_ready);} else
 if(name=="kv_shared_rdata"){for(int i=15;i>=0;i--)word(dut.kv_shared_rdata[i]);} else
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
 if(name=="kv_metadata_valid"){word(dut.kv_metadata_valid);} else
 if(name=="kv_metadata_ready"){word(dut.kv_metadata_ready);} else
 if(name=="kv_metadata_identity"){word(uint32_t(dut.kv_metadata_identity>>32));word(uint32_t(dut.kv_metadata_identity));} else
 if(name=="kv_metadata_key"){word(dut.kv_metadata_key);} else
 if(name=="kv_metadata_record"){word(dut.kv_metadata_record);} else
 if(name=="kv_consumer_valid"){word(dut.kv_consumer_valid);} else
 if(name=="kv_consumer_ready"){word(dut.kv_consumer_ready);} else
 if(name=="kv_consumer_identity"){word(uint32_t(dut.kv_consumer_identity>>32));word(uint32_t(dut.kv_consumer_identity));} else
 if(name=="kv_consumer_key"){word(dut.kv_consumer_key);} else
 if(name=="kv_consumer_stage"){word(dut.kv_consumer_stage);} else
 if(name=="kv_consumer_accepted"){word(dut.kv_consumer_accepted);} else
 if(name=="kv_consumer_reverse"){word(dut.kv_consumer_reverse);} else
 if(name=="kv_reader_metadata_valid"){word(dut.kv_reader_metadata_valid);} else
 if(name=="kv_reader_metadata_ready"){word(dut.kv_reader_metadata_ready);} else
 if(name=="kv_reader_metadata_identity"){word(uint32_t(dut.kv_reader_metadata_identity>>32));word(uint32_t(dut.kv_reader_metadata_identity));} else
 if(name=="kv_reader_metadata_key"){word(dut.kv_reader_metadata_key);} else
 if(name=="kv_reader_metadata_stage"){word(dut.kv_reader_metadata_stage);} else
 if(name=="kv_hydrate_valid"){word(dut.kv_hydrate_valid);} else
 if(name=="kv_hydrate_ready"){word(dut.kv_hydrate_ready);} else
 if(name=="kv_hydrate_key"){word(dut.kv_hydrate_key);} else
 if(name=="kv_hydrate_producer"){word(uint32_t(dut.kv_hydrate_producer>>32));word(uint32_t(dut.kv_hydrate_producer));} else
 if(name=="kv_drain_valid"){word(dut.kv_drain_valid);} else
 if(name=="kv_drain_ready"){word(dut.kv_drain_ready);} else
 if(name=="kv_drain_identity"){word(uint32_t(dut.kv_drain_identity>>32));word(uint32_t(dut.kv_drain_identity));} else
 if(name=="kv_drain_key"){word(dut.kv_drain_key);} else
 if(name=="kv_drain_done_valid"){word(dut.kv_drain_done_valid);} else
 if(name=="kv_drain_done_ready"){word(dut.kv_drain_done_ready);} else
 if(name=="kv_drain_done_identity"){word(uint32_t(dut.kv_drain_done_identity>>32));word(uint32_t(dut.kv_drain_done_identity));} else
 if(name=="kv_drain_done_key"){word(dut.kv_drain_done_key);} else
 if(name=="kv_drain_done_allcopies"){word(dut.kv_drain_done_allcopies);} else
 if(name=="kv_fault"){word(dut.kv_fault);} else
 if(name=="kv_writer_retained"){word(dut.kv_writer_retained);} else
 if(name=="kv_idle"){word(dut.kv_idle);} else
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
 if(name=="w2_rst_n"){for(int i=3;i>=0;i--)word(dut.w2_rst_n[i]);} else
 if(name=="w2_admission_stop"){for(int i=3;i>=0;i--)word(dut.w2_admission_stop[i]);} else
 if(name=="w2_rearm_v"){for(int i=3;i>=0;i--)word(dut.w2_rearm_v[i]);} else
 if(name=="w2_provider_fenced"){for(int i=3;i>=0;i--)word(dut.w2_provider_fenced[i]);} else
 if(name=="w2_reset_fenced"){for(int i=3;i>=0;i--)word(dut.w2_reset_fenced[i]);} else
 if(name=="w2_rearm_rdy"){for(int i=3;i>=0;i--)word(dut.w2_rearm_rdy[i]);} else
 if(name=="w2_idle"){for(int i=3;i>=0;i--)word(dut.w2_idle[i]);} else
 if(name=="w2_c_req_v"){for(int i=23;i>=0;i--)word(dut.w2_c_req_v[i]);} else
 if(name=="w2_c_req_we"){for(int i=23;i>=0;i--)word(dut.w2_c_req_we[i]);} else
 if(name=="w2_c_req_rdy"){for(int i=23;i>=0;i--)word(dut.w2_c_req_rdy[i]);} else
 if(name=="w2_c_req_addr"){for(int i=815;i>=0;i--)word(dut.w2_c_req_addr[i]);} else
 if(name=="w2_c_req_tag"){for(int i=767;i>=0;i--)word(dut.w2_c_req_tag[i]);} else
 if(name=="w2_c_req_gen"){for(int i=95;i>=0;i--)word(dut.w2_c_req_gen[i]);} else
 if(name=="w2_c_req_data"){for(int i=6143;i>=0;i--)word(dut.w2_c_req_data[i]);} else
 if(name=="w2_c_rsp_v"){for(int i=23;i>=0;i--)word(dut.w2_c_rsp_v[i]);} else
 if(name=="w2_c_wr_done_v"){for(int i=23;i>=0;i--)word(dut.w2_c_wr_done_v[i]);} else
 if(name=="w2_c_rsp_rdy"){for(int i=23;i>=0;i--)word(dut.w2_c_rsp_rdy[i]);} else
 if(name=="w2_c_wr_done_rdy"){for(int i=23;i>=0;i--)word(dut.w2_c_wr_done_rdy[i]);} else
 if(name=="w2_c_rsp_tag"){for(int i=767;i>=0;i--)word(dut.w2_c_rsp_tag[i]);} else
 if(name=="w2_c_wr_done_tag"){for(int i=767;i>=0;i--)word(dut.w2_c_wr_done_tag[i]);} else
 if(name=="w2_c_rsp_gen"){for(int i=95;i>=0;i--)word(dut.w2_c_rsp_gen[i]);} else
 if(name=="w2_c_wr_done_gen"){for(int i=95;i>=0;i--)word(dut.w2_c_wr_done_gen[i]);} else
 if(name=="w2_c_rsp_data"){for(int i=6143;i>=0;i--)word(dut.w2_c_rsp_data[i]);} else
 if(name=="w2_p_req_v"){for(int i=3;i>=0;i--)word(dut.w2_p_req_v[i]);} else
 if(name=="w2_p_req_we"){for(int i=3;i>=0;i--)word(dut.w2_p_req_we[i]);} else
 if(name=="w2_p_req_rdy"){for(int i=3;i>=0;i--)word(dut.w2_p_req_rdy[i]);} else
 if(name=="w2_p_req_addr"){for(int i=135;i>=0;i--)word(dut.w2_p_req_addr[i]);} else
 if(name=="w2_p_req_tag"){for(int i=139;i>=0;i--)word(dut.w2_p_req_tag[i]);} else
 if(name=="w2_p_req_gen"){for(int i=15;i>=0;i--)word(dut.w2_p_req_gen[i]);} else
 if(name=="w2_p_req_data"){for(int i=1023;i>=0;i--)word(dut.w2_p_req_data[i]);} else
 if(name=="w2_p_rsp_v"){for(int i=3;i>=0;i--)word(dut.w2_p_rsp_v[i]);} else
 if(name=="w2_p_wr_done_v"){for(int i=3;i>=0;i--)word(dut.w2_p_wr_done_v[i]);} else
 if(name=="w2_p_rsp_rdy"){for(int i=3;i>=0;i--)word(dut.w2_p_rsp_rdy[i]);} else
 if(name=="w2_p_wr_done_ready"){for(int i=3;i>=0;i--)word(dut.w2_p_wr_done_ready[i]);} else
 if(name=="w2_p_rsp_tag"){for(int i=139;i>=0;i--)word(dut.w2_p_rsp_tag[i]);} else
 if(name=="w2_p_wr_done_tag"){for(int i=139;i>=0;i--)word(dut.w2_p_wr_done_tag[i]);} else
 if(name=="w2_p_rsp_gen"){for(int i=15;i>=0;i--)word(dut.w2_p_rsp_gen[i]);} else
 if(name=="w2_p_wr_done_gen"){for(int i=15;i>=0;i--)word(dut.w2_p_wr_done_gen[i]);} else
 if(name=="w2_p_rsp_data"){for(int i=1023;i>=0;i--)word(dut.w2_p_rsp_data[i]);} else
 if(name=="w2_fault"){for(int i=3;i>=0;i--)word(dut.w2_fault[i]);} else
 if(name=="w2_repair_busy"){for(int i=3;i>=0;i--)word(dut.w2_repair_busy[i]);} else
 if(name=="w2_reverse_fenced"){for(int i=3;i>=0;i--)word(dut.w2_reverse_fenced[i]);} else
 throw std::runtime_error("unknown pin");}
 else if(op=="SET"){in>>name>>value;if(in>>extra)throw std::runtime_error("extra");
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
 if(name=="kv_shared_ready"){auto v=unpack(value,1);dut.kv_shared_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_shared_done"){auto v=unpack(value,1);dut.kv_shared_done=v[0];std::cout<<"OK";} else
 if(name=="kv_shared_rdata"){auto v=unpack(value,512);for(unsigned i=0;i<v.size();i++)dut.kv_shared_rdata[i]=v[i];std::cout<<"OK";} else
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
 if(name=="kv_metadata_valid"){auto v=unpack(value,1);dut.kv_metadata_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_metadata_identity"){auto v=unpack(value,64);dut.kv_metadata_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_metadata_key"){auto v=unpack(value,20);dut.kv_metadata_key=v[0];std::cout<<"OK";} else
 if(name=="kv_metadata_record"){auto v=unpack(value,1);dut.kv_metadata_record=v[0];std::cout<<"OK";} else
 if(name=="kv_consumer_valid"){auto v=unpack(value,1);dut.kv_consumer_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_consumer_identity"){auto v=unpack(value,64);dut.kv_consumer_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_consumer_key"){auto v=unpack(value,20);dut.kv_consumer_key=v[0];std::cout<<"OK";} else
 if(name=="kv_consumer_stage"){auto v=unpack(value,1);dut.kv_consumer_stage=v[0];std::cout<<"OK";} else
 if(name=="kv_consumer_accepted"){auto v=unpack(value,1);dut.kv_consumer_accepted=v[0];std::cout<<"OK";} else
 if(name=="kv_consumer_reverse"){auto v=unpack(value,1);dut.kv_consumer_reverse=v[0];std::cout<<"OK";} else
 if(name=="kv_reader_metadata_valid"){auto v=unpack(value,1);dut.kv_reader_metadata_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_reader_metadata_identity"){auto v=unpack(value,64);dut.kv_reader_metadata_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_reader_metadata_key"){auto v=unpack(value,20);dut.kv_reader_metadata_key=v[0];std::cout<<"OK";} else
 if(name=="kv_reader_metadata_stage"){auto v=unpack(value,1);dut.kv_reader_metadata_stage=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_valid"){auto v=unpack(value,1);dut.kv_hydrate_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_key"){auto v=unpack(value,20);dut.kv_hydrate_key=v[0];std::cout<<"OK";} else
 if(name=="kv_hydrate_producer"){auto v=unpack(value,64);dut.kv_hydrate_producer=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_drain_ready"){auto v=unpack(value,1);dut.kv_drain_ready=v[0];std::cout<<"OK";} else
 if(name=="kv_drain_done_valid"){auto v=unpack(value,1);dut.kv_drain_done_valid=v[0];std::cout<<"OK";} else
 if(name=="kv_drain_done_identity"){auto v=unpack(value,64);dut.kv_drain_done_identity=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="kv_drain_done_key"){auto v=unpack(value,20);dut.kv_drain_done_key=v[0];std::cout<<"OK";} else
 if(name=="kv_drain_done_allcopies"){auto v=unpack(value,8);dut.kv_drain_done_allcopies=v[0];std::cout<<"OK";} else
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
 if(name=="sm_scratch_valid"){auto v=unpack(value,64);dut.sm_scratch_valid=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_scratch_write"){auto v=unpack(value,64);dut.sm_scratch_write=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_scratch_addr"){auto v=unpack(value,640);for(unsigned i=0;i<v.size();i++)dut.sm_scratch_addr[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_scratch_wdata"){auto v=unpack(value,32768);for(unsigned i=0;i<v.size();i++)dut.sm_scratch_wdata[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_scratch_done_ready"){auto v=unpack(value,64);dut.sm_scratch_done_ready=uint64_t(v[0])|(uint64_t(v[1])<<32);std::cout<<"OK";} else
 if(name=="sm_host_owner"){auto v=unpack(value,2944);for(unsigned i=0;i<v.size();i++)dut.sm_host_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="sm_simd_owner"){auto v=unpack(value,2944);for(unsigned i=0;i<v.size();i++)dut.sm_simd_owner[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_rst_n"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_rst_n[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_admission_stop"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_admission_stop[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_rearm_v"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_rearm_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_provider_fenced"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_provider_fenced[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_reset_fenced"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_reset_fenced[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_v"){auto v=unpack(value,768);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_we"){auto v=unpack(value,768);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_we[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_addr"){auto v=unpack(value,26112);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_addr[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_tag"){auto v=unpack(value,24576);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_gen"){auto v=unpack(value,3072);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_req_data"){auto v=unpack(value,196608);for(unsigned i=0;i<v.size();i++)dut.w2_c_req_data[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_rsp_rdy"){auto v=unpack(value,768);for(unsigned i=0;i<v.size();i++)dut.w2_c_rsp_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_c_wr_done_rdy"){auto v=unpack(value,768);for(unsigned i=0;i<v.size();i++)dut.w2_c_wr_done_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_req_rdy"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_p_req_rdy[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_v"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_v"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_v[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_tag"){auto v=unpack(value,4480);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_tag"){auto v=unpack(value,4480);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_tag[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_gen"){auto v=unpack(value,512);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_wr_done_gen"){auto v=unpack(value,512);for(unsigned i=0;i<v.size();i++)dut.w2_p_wr_done_gen[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_p_rsp_data"){auto v=unpack(value,32768);for(unsigned i=0;i<v.size();i++)dut.w2_p_rsp_data[i]=v[i];std::cout<<"OK";} else
 if(name=="w2_reverse_fenced"){auto v=unpack(value,128);for(unsigned i=0;i<v.size();i++)dut.w2_reverse_fenced[i]=v[i];std::cout<<"OK";} else
 throw std::runtime_error("unknown/output pin");}
 else throw std::runtime_error("command");
 std::cout<<"\n"<<std::flush;}catch(const std::exception&e){std::cout<<"ERR "<<e.what()<<"\n"<<std::flush;return 2;}}dut.final();return 0;}
