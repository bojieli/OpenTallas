#include "Vot_qwen_tp8_native_services_frontend.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "Vot_qwen_tp8_kv_sector_adapter.h"
#include "services_vm_adapter.hpp"
#include "kernel_physical_rows.hpp"
#include <fstream>
#include <iostream>
#include <cstring>
#include <cmath>
using namespace qwen_native_services;
using namespace qwen_actual_phy;
static std::vector<uint32_t> words(const std::string& p){std::ifstream f(p);if(!f)throw std::runtime_error("missing "+p);std::string s;std::vector<uint32_t> v;while(f>>s)v.push_back(std::stoul(s,nullptr,16));return v;}
static std::vector<RowBytes> rows(const std::string&p){std::ifstream f(p);if(!f)throw std::runtime_error("missing "+p);std::string s;std::vector<RowBytes>v;while(f>>s){if(s.size()!=256)throw std::runtime_error("KV row width");RowBytes r{};for(unsigned j=0;j<32;j++)r[j]=std::stoul(s.substr(256-8*(j+1),8),nullptr,16);v.push_back(r);}return v;}
static uint32_t fp8(unsigned b){unsigned e=(b>>3)&15,m=b&7;float x=e?std::ldexp(1.0f+m/8.0f,int(e)-7):std::ldexp(float(m),-9);if(b&128)x=-x;uint32_t u;std::memcpy(&u,&x,4);return u;}
int main(int argc,char**argv){try{
 if(argc<2)throw std::runtime_error("vector directory required");std::string mode=argc>2?argv[2]:"positive";bool stalls=mode=="stalls";bool mutated=false;bool transition=mode=="transition"||mode=="transition_ack_mut"||mode=="transition_data_mut";unsigned frame=0;uint64_t prior_target=2040;unsigned previous_errors=0;if(transition&&argc!=4)throw std::runtime_error("next-layer vectors required");
 auto q=words(std::string(argv[1])+"/q.hex"),gold=words(std::string(argv[1])+"/gold.hex");auto kv=rows(std::string(argv[1])+"/kv.hex");
 if(q.size()!=512||gold.size()!=512||kv.size()!=512)throw std::runtime_error("checkpoint vector dimensions");
 VerilatedContext ctx;ctx.threads(1);RowBackend backend(ctx,255);
 Vot_qwen_tp8_native_services_frontend f(&ctx,"frontend");Vot_qwen_tp8_attention_service k(&ctx,"kernel");Vot_qwen_tp8_kv_sector_adapter s(&ctx,"sector");
 std::vector<uint32_t> vm(56816);VmReceiver mem(vm);mem.stalls=stalls;mem.ack_delay=stalls?11:1;KernelRows reads(backend);SectorWrites writes(backend);
 f.rst_n=k.rst_n=s.rst_n=0;f.clk=k.clk=s.clk=0;f.fused_program_capability=1;
 f.native_xbase=13696;f.native_obase=3167;f.native_nout=512;f.native_k=128;f.native_pos=255;
 f.epoch=17;f.layer=0;f.pos=255;f.epoch_begin=0;f.native_go=0;f.kv_issue_accepted=0;f.kv_we=0;
 for(unsigned kind=0;kind<2;kind++)for(unsigned t=0;t<255;t++)for(unsigned quarter=0;quarter<4;quarter++){
  Quarter data{};for(unsigned j=0;j<8;j++)data[j]=kv[kind*256+t][8*quarter+j];backend.enqueue_prior_quarter_via_actual_controller({{17,0,t,kind},quarter},data);
 }
 uint64_t core_next=553667,hbm_next=512000;bool ch=false,hh=false;unsigned stage=0,stage_cycle=0,last_stage=999;bool completed=false;uint64_t native_edge=0;
 for(unsigned events=0;events<4000000&&!completed;events++){
  bool core=core_next<=hbm_next;ctx.time(core?core_next:hbm_next);
  if(!core){hbm_next+=512000;hh=!hh;backend.hbm_edge(hh);continue;}
  core_next+=416667;ch=!ch;
  if(!ch){backend.core_edge(false);f.clk=k.clk=s.clk=0;f.eval();k.eval();s.eval();continue;}
  // Complete all combinational transport while clocks remain low. Sample each
  // owner exactly once; then hold the settled transactions through all rises.
  f.rst_n=k.rst_n=s.rst_n=backend.hbm_edges>=8;
  f.epoch_begin=0;f.kv_issue_accepted=0;f.kv_we=0;f.native_go=0;
  if(stage>=3&&stage<=5){unsigned issue=stage-3;f.kv_issue_kind=issue;f.kv_issue_nout=1;f.kv_issue_nin=issue==0?128:64;f.eval();}
  if(stage!=last_stage){std::cerr<<"stage "<<stage<<" core "<<backend.core_edges<<" prior ACKs "<<backend.write_acks<<"\n";last_stage=stage;}
  if(stage==0&&backend.write_acks==prior_target){WriteAck a;while(backend.pop_write_ack(a)){}stage=1;stage_cycle=0;}
  if(stage==1&&f.epoch_ready){f.epoch_begin=1;mem.reserve(17+frame,frame);stage=2;stage_cycle=0;}
  else if(stage==2&&++stage_cycle>=4){for(unsigned j=0;j<512;j++){vm[13696+j]=q[j];mem.observe_write(13696+j);}stage=3;stage_cycle=0;}
  else if(stage>=3&&stage<=5){unsigned issue=stage-3;
   if(stage_cycle==0&&f.kv_admit_ready){f.kv_issue_accepted=1;f.kv_issue_kind=issue;f.kv_issue_nout=1;f.kv_issue_nin=issue==0?128:64;stage_cycle=1;}
   else if(stage_cycle>=1&&stage_cycle<=(issue==0?2u:1u)){
    unsigned dim0=issue==0?64*(stage_cycle-1):64*(issue-1);unsigned kind=issue==0?1:0;
    f.kv_we=~uint64_t(0);for(unsigned j=0;j<64;j++){unsigned dim=dim0+j;unsigned addr=kind?((65536+255*8+(dim>>4))<<4)|(dim&15):(((255>>4)*128+dim)<<4)|(255&15);
     set_bits(f.kv_waddr,24*j,24,addr);unsigned b=(kv[kind*256+255][dim/4]>>(8*(dim%4)))&255;if((mode=="data_mut"||(mode=="transition_data_mut"&&frame==1))&&kind==0&&dim==0){b=(b&127)?0:56;mutated=true;}f.kv_wdata[j]=fp8(b);
    }++stage_cycle;
   }else if(stage_cycle){if(++stage_cycle>=6){++stage;stage_cycle=0;}}
  }else if(stage==6&&f.native_ready){f.native_go=1;native_edge=backend.core_edges;stage=7;}
  mem.drive(f);if(stage==0){WriteAck a;while(backend.pop_write_ack(a)){}s.ack_v=0;f.store_ack_v=0;}else writes.prepare_acks(s,f);if((mode=="ack_mut"||(mode=="transition_ack_mut"&&frame==1))&&f.store_ack_v&&!mutated){for(unsigned aq=0;aq<4;aq++)if(f.store_ack_v&(1u<<aq)){set_bits(f.store_ack_epoch,16*aq,16,frame?17:18);mutated=true;break;}}reads.drive(k);
  auto face=[&](){std::vector<uint32_t>v={unsigned(f.row_ready),unsigned(f.row_v),unsigned(s.row_ready),unsigned(s.row_v),unsigned(f.native_ready),unsigned(f.kernel_request_valid),unsigned(k.q_ready),unsigned(k.result_valid)};for(unsigned j=0;j<32;j++){v.push_back(f.row_data[j]);v.push_back(s.row_data[j]);}for(unsigned j=0;j<37;j++)v.push_back(s.commands[j]);return v;};
  bool stable=false;for(unsigned n=0;n<16;n++){auto before=face();SectorWrites::connect(s,f);s.eval();settle(f,k);SectorWrites::connect(s,f);s.eval();if(before==face()){stable=true;break;}}
  if(!stable)throw std::runtime_error("sector interfaces did not settle");
  mem.sample(f);writes.sample(s);reads.sample(k);
  backend.core_edge(true);f.clk=k.clk=s.clk=1;f.eval();k.eval();s.eval();mem.store_after_edge();
  if(f.fault||k.fault||s.fault)throw std::runtime_error("composed RTL fault stage "+std::to_string(stage)+" frame "+std::to_string(frame));
  completed=f.native_completed;
  if(completed&&transition&&frame==0){
   for(unsigned j=0;j<512;j++)previous_errors+=vm[50672+j]!=gold[j];
   if(previous_errors||!writes.drained()||!reads.drained()||mem.commit_acks!=32)throw std::runtime_error("first actual frame did not commit exactly before layer transition");
   std::cerr<<"completed first layer without reset, native cycles "<<backend.core_edges-native_edge<<"\n";
   q=words(std::string(argv[3])+"/q.hex");gold=words(std::string(argv[3])+"/gold.hex");kv=rows(std::string(argv[3])+"/kv.hex");
   if(q.size()!=512||gold.size()!=512||kv.size()!=512)throw std::runtime_error("next layer vector dimensions");
   frame=1;prior_target=backend.write_acks+2040;f.epoch=18;f.layer=1;stage=0;stage_cycle=0;last_stage=999;completed=false;
   for(unsigned kind=0;kind<2;kind++)for(unsigned t=0;t<255;t++)for(unsigned quarter=0;quarter<4;quarter++){
    Quarter data{};for(unsigned j=0;j<8;j++)data[j]=kv[kind*256+t][8*quarter+j];backend.enqueue_prior_quarter_via_actual_controller({{18,1,t,kind},quarter},data);
   }
  }
 }
 if(!completed)throw std::runtime_error("timeout stage "+std::to_string(stage));if(mode!="positive"&&mode!="stalls"&&mode!="transition"&&!mutated)throw std::runtime_error("mutation was not exercised");unsigned errors=0;for(unsigned j=0;j<512;j++){if(vm[50672+j]!=gold[j]){if(errors<8)std::cerr<<"mismatch "<<j<<" actual "<<std::hex<<vm[50672+j]<<" expected "<<gold[j]<<std::dec<<"\n";++errors;}}
 if(mem.writes.size()!=32*(frame+1)||mem.commit_acks!=32*(frame+1)||mem.q_requests!=8*(frame+1)||writes.issued!=8*(frame+1)||writes.committed!=8*(frame+1)||!writes.drained()||!reads.drained())throw std::runtime_error("incomplete committed effects");
 std::cout<<"{\"scope\":\"SU_SHAPED_COMPONENT_COMPOSITION_ACTUAL_KERNEL_PHY\",\"whole_layer\":false,\"kernel_frames\":"<<frame+1<<",\"resets_after_boot\":0,\"prior_actual_quarter_writes\":"<<2040*(frame+1)<<",\"current_actual_quarter_writes\":"<<writes.issued<<",\"current_actual_ACKs\":"<<writes.committed<<",\"Q_VM_reads\":"<<mem.q_requests<<",\"ATTN_VM_commits\":"<<mem.commit_acks<<",\"K_rows\":"<<reads.k_returns<<",\"V_rows\":"<<reads.v_returns<<",\"native_cycles\":"<<backend.core_edges-native_edge<<",\"errors\":"<<errors<<",\"stalls\":"<<(stalls?"true":"false")<<"}\n";
 return errors?1:0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
