// HOST-only token lifecycle gate (component scope). Actual eight HOST/board
// models, sole allocator and cohort; numerical engines are ABSENT: the result
// token/value and the KV/VM/collective drain flags are declared fixtures. The
// HOST drain is the actual accessor certificate. Modes:
//   positive : PRE cert -> result pulse -> terminal accepted -> POST cert -> retired
//   strict   : negative control, PRE requires last-descriptor (active==0): must deadlock
//   stale    : negative control, POST certificate carries a wrong generation: must throw
#include "host_lifecycle.hpp"
#include <filesystem>
#include <iostream>
using namespace qwen_native_host;
int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("usage: out positive|strict|stale");
 std::string out=argv[1],mode=argv[2];std::filesystem::create_directories(out);
 HostOwner h;Inputs in;Startup s;PreTerminal pre;pre.strict=mode=="strict";Terminal t;t.stale_certificate=mode=="stale";
 in.engine_admit_ready=true;uint64_t dispatch_edge=0,limit=400000;bool begun=false;
 for(uint64_t n=0;n<limit;n++){
  s(h,in);
  if(h.dispatch()&&!dispatch_edge){dispatch_edge=h.core_edges;
   if(h.accepted_ranks()!=255||h.admissions.size()!=8||h.actual_allocations!=1||h.actual_grants!=1)throw std::runtime_error("missing actual cohort provenance");}
  in.host_drained=pre(h,s);
  // Fixture engines: drained only after dispatch + a declared 2000-edge compute window.
  bool engines=dispatch_edge&&h.core_edges>=dispatch_edge+2000;
  in.kv_drained=in.vm_drained=in.collective_drained=engines?255:0;
  if(engines&&!begun&&(pre.latched||mode=="strict")){t.begin(h,50994,1100755280u,unsigned(h.core_edges-dispatch_edge));begun=true;}
  if(begun)t.before_low(h,in);
  h.low(in);h.rise();h.fall();
  if(h.fault())throw std::runtime_error("actual allocator/cohort identity fault");
  for(unsigned r=0;r<8;r++)if(h.hosts[r]->service_abort||h.hosts[r]->service_faults||h.boards[r]->faults)throw std::runtime_error("actual HOST/board fault");
  if(begun)t.after_rise(h);
  if(n%50000==0)std::cout<<"PROGRESS core="<<h.core_edges<<" pre="<<pre.latched<<"("<<pre.first<<") phase="<<t.phase<<" post_block="<<t.post_block<<" cr="<<t.result_credits<<"\n"<<std::flush;
  if(t.done()){
   bool warm=h.hosts[0]->service_ready&&!h.awaiting_post_terminal_retirement();
   std::ofstream f(out+"/receipt.json");
   f<<"{\"scope\":\"ACTUAL_EIGHT_HOST_TOKEN_LIFECYCLE_COMPONENT_NUMERICAL_ENGINES_ABSENT\",\"mode\":\""<<mode<<"\",\"passed\":true,"
    <<"\"dispatch_core_edge\":"<<dispatch_edge<<",\"pre_terminal_certificate_core_edge\":"<<pre.edge<<",\"terminal\":"<<t.json()
    <<",\"warm_ready_after_retirement\":"<<(warm?"true":"false")<<",\"fixtures\":[\"result token/value\",\"KV/VM/collective drains\",\"board/BOOT stimulus\"],\"whole_token\":false}\n";
   std::cout<<"PASS lifecycle "<<t.json()<<"\n";return 0;
  }
 }
 std::cout<<"FAIL lifecycle did not complete: phase="<<t.phase<<" pre="<<pre.latched<<" first="<<pre.first<<" post="<<t.post_block<<"\n";return 1;
}catch(const std::exception&e){std::cout<<"FAIL "<<e.what()<<"\n";return 2;}}
