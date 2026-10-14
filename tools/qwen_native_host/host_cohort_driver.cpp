#include "host_owner.hpp"
#ifdef QWEN_HOST_DRAIN_GATE
#include "qkd_host_drain_8bb.hpp"
#endif
#include <iostream>
#include <filesystem>
using namespace qwen_native_host;
int main(int argc,char**argv){
 try{
  std::string out=argc>1?argv[1]:".";std::filesystem::create_directories(out);
  HostOwner h;Inputs in;in.engine_admit_ready=true;
  unsigned phase=0,bar_index=0,bar_baseline=0;uint64_t delayed_begin=0;bool paused=false,reported=false;
  const std::array<std::pair<unsigned,unsigned>,9> bars={{{0x10,0x100},{0x14,0},{0x18,2},
     {0x24,0x800},{0x28,0},{0x2c,5},{0x3c,1},{0x08,1},{0x1c,1}}};
  std::ofstream trace(out+"/actual_admissions.txt"),metadata(out+"/actual_program_metadata.txt");
  for(unsigned n=0;n<1600000;++n){
   in.por_n=n>=8;in.link_up=n>=24?63:0;
   for(unsigned r=0;r<8;++r)in.boot[r]=n>=24?3:0;
   unsigned sys=0,service=0,permission=0;
   for(unsigned r=0;r<8;++r){sys|=unsigned(h.hosts[r]->sys_ready)<<r;
    service|=unsigned(h.hosts[r]->service_ready)<<r;permission|=unsigned(h.hosts[r]->ingest_permission)<<r;}
   if(phase==0&&sys==255){
    if(!h.router.service_begin())throw std::runtime_error("service BAR reservation failed");
    phase=1;std::cout<<"SYS_READY core="<<n<<"\n"<<std::flush;
   }
   if(phase==1&&h.hosts[0]->ingest_permission){
    for(unsigned r=0;r<8;++r)if(!h.router.boot_end(r))throw std::runtime_error("zero-row BOOT reservation failed");
    phase=2;std::cout<<"ACTUAL_INGEST_PERMISSION core="<<n<<"\n"<<std::flush;
   }
   if(phase==2&&service==255){
    h.router.pause_ctrl_destination(7,true);paused=true;
    h.router.fmt1_descriptor(0x100,0x400,{0},1);
    phase=3;std::cout<<"SERVICE_READY core="<<n<<"\n"<<std::flush;
   }
   if(phase==3&&bar_index<bars.size()&&h.router.bar_responses().size()>=bar_baseline){
    auto [a,v]=bars[bar_index++];bar_baseline=h.router.bar_responses().size()+1;
    if(!h.router.write_bar(0,a,v,15,bar_index))throw std::runtime_error("FMT1 BAR reservation failed");
   }
   if(h.accepted_ranks()==127&&paused){
    if(!delayed_begin)delayed_begin=n;
    if(h.dispatch())throw std::runtime_error("execution launched before delayed actual peer7");
    if(n-delayed_begin>=1000){h.router.pause_ctrl_destination(7,false);paused=false;
     std::cout<<"RELEASE_REAL_PEER7 core="<<n<<"\n"<<std::flush;}
   }
   auto old_admissions=h.admissions.size();h.low(in);h.rise();h.fall();
   for(size_t a=old_admissions;a<h.admissions.size();++a){auto&e=h.admissions[a];
    trace<<e.rank<<" "<<e.edge<<" "<<std::hex<<e.tag<<std::dec<<" "<<e.generation<<" "<<e.token<<" "<<e.position<<"\n";
    metadata<<e.rank<<" "<<e.edge<<" ";for(unsigned w=0;w<5;++w)metadata<<std::hex<<e.program_metadata[4-w]<<" ";metadata<<std::dec<<"\n";
    for(auto word:e.program_metadata)if(word)throw std::runtime_error("unexpected HOST PW/DW program override in fixture");}
   if(h.fault())throw std::runtime_error("actual allocator/cohort identity fault");
   for(unsigned r=0;r<8;++r)if(h.hosts[r]->service_abort||h.hosts[r]->service_faults||h.boards[r]->faults){
    std::cerr<<"RTL_FAULT rank="<<r<<" core="<<n<<" hostfaults="<<h.hosts[r]->service_faults
       <<" diag="<<h.hosts[r]->service_diag_raw<<" board="<<unsigned(h.boards[r]->faults)<<"\n";
    throw std::runtime_error("actual HOST/board component fault");}
   if(n&&n%100000==0)std::cout<<"PROGRESS core="<<n<<" sys="<<sys<<" service="<<service
      <<" permission="<<permission<<" phase="<<phase<<" ctrl="<<h.router.ctrl_forwarded()<<"\n"<<std::flush;
   if(h.dispatch()){
    if(paused||!delayed_begin||h.accepted_ranks()!=255||h.actual_allocations!=1||h.actual_grants!=1||h.admissions.size()!=8)
     throw std::runtime_error("missing actual cohort admission provenance");
    for(auto&e:h.admissions)if(e.tag!=h.tag()||e.generation!=h.generation()||e.token!=0||e.position!=0)
     throw std::runtime_error("actual endpoint tuple mismatch");
    if(!reported){std::ofstream f(out+"/receipt.json");
    f<<"{\n  \"scope\": \"ACTUAL_EIGHT_HOST_ALLOCATOR_COHORT_CONTROL_WITH_EXPLICIT_BOARD_AND_BOOT_FIXTURES\",\n"
      <<"  \"passed\": true, \"whole_token\": false, \"native_numerical_execution\": false,\n"
      <<"  \"startup_boot_producer\": \"fixture local_boot3; genuine producer binding pending\",\n"
      <<"  \"actual_endpoint_admissions\": 8, \"actual_allocations\": 1, \"actual_grants\": 1,\n"
      <<"  \"token\": 0, \"position\": 0, \"epoch\": "<<h.epoch()<<", \"generation\": "<<h.generation()<<",\n"
      <<"  \"delayed_peer7_core_edges\": "<<n-delayed_begin<<", \"core_edges\": "<<h.core_edges<<",\n"
      <<"  \"real_PHY_delay_cycles\": 223, \"completion_callback_offered\": false\n}\n";
    std::cout<<"PASS actual eight endpoint admissions core="<<h.core_edges<<" epoch="<<h.epoch()<<" tag="
        <<std::hex<<h.tag()<<std::dec<<"\n";reported=true;}
#ifdef QWEN_HOST_DRAIN_GATE
    bool transport=h.router.router_empty()&&h.router.fdi_pipelines_empty();
    for(unsigned id=0;id<8;++id){auto host_report=qkd_host_fixture::host_transport_drain(*h.hosts[id]);
     auto board_report=qkd_host_fixture::board_transport_drain(*h.boards[id]);transport&=host_report.drained()&&board_report.drained();
     if(n%1000==0&&!host_report.drained())std::cout<<"DRAIN_BLOCK HOST="<<id<<" bits="<<host_report.blocked<<" first="<<host_report.first<<"\n";
     if(n%1000==0&&!board_report.drained())std::cout<<"DRAIN_BLOCK BOARD="<<id<<" bits="<<board_report.blocked<<" first="<<board_report.first<<"\n";
    }
    if(!transport)continue;
    std::ofstream d(out+"/pre_terminal_receipt.json");d<<"{\"scope\":\"ACTUAL_PRE_TERMINAL_TRANSPORT_QUIESCENCE_NOT_POST_RETIREMENT\",\"passed\":true,\"actual_core_edge\":"<<h.core_edges<<",\"whole_token\":false,\"numerical_callback_offered\":false}\n";
    std::cout<<"PASS actual all-eight PRE_TERMINAL transport drain core="<<h.core_edges<<"\n";
#endif
    return 0;
   }
  }
  throw std::runtime_error("bounded control observer ended before actual eight-rank admission");
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
