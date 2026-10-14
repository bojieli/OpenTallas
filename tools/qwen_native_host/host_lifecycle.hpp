#pragma once
// Token lifecycle around the actual eight-HOST owner, shared by the HOST-only
// lifecycle gate and the whole-token driver:
//   startup stimulus -> cohort dispatch -> PRE_TERMINAL accepted-traffic
//   certificate (latched, tag-bound) -> ONE credited head37 result pulse ->
//   endpoint retire + allocator/cohort terminal acceptance -> POST_TERMINAL
//   ND8/CQ/IRQ/transport certificate -> typed retirement -> warm_ready again.
// The HOST is never required to show active/inflight==0 before the terminal:
// the endpoint only retires after the result, so that requirement deadlocks.
#include "host_owner.hpp"
#include "qkd_host_drain_8bb.hpp"
#include <string>
namespace qwen_native_host {

// Board/startup stimulus identical to the qualified admission gate (2617717)
// and HOST->embedding gate (2734693): POR, straps, BEGIN, BOOT_END, FMT1 prompt
// [token0] max_new1, nine BAR writes, peer7 CTRL held 1000 CORE edges.
struct Startup {
 unsigned phase=0,bar_index=0;size_t bar_baseline=0;uint64_t delayed_begin=0;bool paused=false;
 const std::array<std::pair<unsigned,unsigned>,9> bars={{{0x10,0x100},{0x14,0},{0x18,2},
   {0x24,0x800},{0x28,0},{0x2c,5},{0x3c,1},{0x08,1},{0x1c,1}}};
 void operator()(HostOwner&host,Inputs&in){
  uint64_t n=host.core_edges;
  in.por_n=n>=8;in.link_up=n>=24?63:0;for(unsigned r=0;r<8;r++)in.boot[r]=n>=24?3:0;
  unsigned sys=0,permission=0,service=0;
  for(unsigned rank=0;rank<8;rank++){auto*h=host.host_for_rank(rank);sys|=unsigned(h->sys_ready)<<rank;
   permission|=unsigned(h->ingest_permission)<<rank;service|=unsigned(h->service_ready)<<rank;}
  if(phase==0&&sys==255){if(!host.router.service_begin())throw std::runtime_error("service reservation");phase=1;}
  if(phase==1&&permission==255){for(unsigned id=0;id<8;id++)if(!host.router.boot_end(id))throw std::runtime_error("BOOT reservation");phase=2;}
  if(phase==2&&service==255){host.router.pause_ctrl_destination(7,true);paused=true;host.router.fmt1_descriptor(0x100,0x400,{0},1);phase=3;}
  if(phase==3&&bar_index<bars.size()&&host.router.bar_responses().size()>=bar_baseline){
   auto[a,v]=bars[bar_index++];bar_baseline=host.router.bar_responses().size()+1;
   if(!host.router.write_bar(0,a,v,15,bar_index))throw std::runtime_error("FMT1 BAR reservation");}
  if(host.accepted_ranks()==127&&paused){if(!delayed_begin)delayed_begin=n;
   if(host.dispatch())throw std::runtime_error("cohort dispatch before delayed actual peer7");
   if(n-delayed_begin>=1000){host.router.pause_ctrl_destination(7,false);paused=false;}}
 }
 bool stimulus_complete(const HostOwner&host)const{
  return phase==3&&bar_index==bars.size()&&!paused&&delayed_begin&&host.router.bar_responses().size()>=bars.size();
 }
};

inline bool all_reset_released(const HostOwner&h){
 bool ok=true;for(unsigned id=0;id<8;id++)ok&=h.hosts[id]->host_rst_n&&h.hosts[id]->die_rst_n;return ok;}

// PRE_TERMINAL accepted-traffic certificate from the source-bound accessor on
// all eight HOSTs and boards plus router/FDI emptiness. Taken only after the
// last board stimulus and after dispatch, bound to the held cohort tag and then
// latched: the terminal's own TK/status traffic must not oscillate it.
// STRICT (negative control) instead demands the last-descriptor predicate
// (native active/pending/rv, HOST inflight, slot FREE) before the terminal.
struct PreTerminal {
 bool strict=false,latched=false;uint64_t tag=0,edge=0;std::string first;
 bool predicate(const HostOwner&h){
  bool ok=h.router.router_empty()&&h.router.fdi_pipelines_empty();first.clear();
  if(!ok)first="router/FDI";
  for(unsigned id=0;id<8;id++){
   auto a=strict?qkd_host_fixture::host_last_descriptor_retired(*h.hosts[id],true,true,true):qkd_host_fixture::host_transport_drain(*h.hosts[id]);
   auto b=qkd_host_fixture::board_transport_drain(*h.boards[id]);
   if(!a.drained()){ok=false;if(first.empty())first="HOST"+std::to_string(id)+":"+a.first;}
   if(!b.drained()){ok=false;if(first.empty())first="BOARD"+std::to_string(id)+":"+b.first;}
  }
  return ok;
 }
 uint8_t operator()(const HostOwner&h,const Startup&s){
  if(latched&&!all_reset_released(h))throw std::runtime_error("coherent reset after PRE_TERMINAL certificate: preserve failure");
  if(latched){if(h.dispatch()&&h.tag()!=tag)throw std::runtime_error("PRE_TERMINAL certificate identity changed");return 255;}
  if(h.dispatch()&&s.stimulus_complete(h)&&predicate(h)){latched=true;tag=h.tag();edge=h.core_edges;return 255;}
  return 0;
 }
};

// Credited terminal and POST_TERMINAL retirement driven one CORE edge at a time
// by the caller (who owns the numerical models' clocks). Call before_low() just
// before host.low(in) and after_rise() just after host.rise().
struct Terminal {
 enum Phase {RESULT,ACCEPT,POST,DONE} phase=RESULT;
 uint64_t head_tag=0,result_edge=0,terminal_edge=0,post_edge=0,retired_edge=0;unsigned generation=0,token=0,value=0,cycles=0;
 unsigned result_credits=0;bool pulsed=false,certified=false,retire_sent=false,cq=false,irq=false;
 size_t completions_at_result=0;std::string post_block;
 // Negative controls: corrupt POST certificate identity / suppress drains.
 bool stale_certificate=false;
 void begin(const HostOwner&h,unsigned tok,unsigned val,unsigned cyc){
  head_tag=h.tag()|(uint64_t(37)<<37);generation=h.generation();token=tok;value=val;cycles=cyc;
  completions_at_result=h.router.completions().size();phase=RESULT;
 }
 void before_low(const HostOwner&h,Inputs&in){
  in.result_valid=false;in.post_terminal_retired=false;
  if(phase==RESULT&&!pulsed){
   in.result_valid=true;in.result_done=true;in.result_fault=false;in.result_cause=0;in.result_tag=head_tag;
   in.result_generation=generation;in.result_token=token;in.result_value=value;in.result_cycles=cycles;
   pulsed=true;result_edge=h.core_edges;phase=ACCEPT;
  }
  if(phase==POST&&certified&&!retire_sent){
   in.post_terminal_retired=true;in.post_terminal_tag=h.acknowledged_terminal_tag();
   in.post_terminal_generation=stale_certificate?(generation+1)&3:generation;retire_sent=true;
  }
 }
 bool post_predicate(const HostOwner&h){
  cq=h.router.completions().size()>completions_at_result;irq=h.router.irq(0);
  bool ok=h.router.router_empty()&&h.router.fdi_pipelines_empty();post_block.clear();if(!ok)post_block="router/FDI";
  for(unsigned id=0;id<8;id++){
   auto d=id==0?qkd_host_fixture::host_last_descriptor_retired(*h.hosts[0],result_credits>=8,cq,irq):qkd_host_fixture::host_transport_drain(*h.hosts[id]);
   auto b=qkd_host_fixture::board_transport_drain(*h.boards[id]);
   if(!d.drained()){ok=false;if(post_block.empty())post_block="HOST"+std::to_string(id)+":"+d.first;}
   if(!b.drained()){ok=false;if(post_block.empty())post_block="BOARD"+std::to_string(id)+":"+b.first;}}
  return ok;
 }
 void after_rise(const HostOwner&h){
  for(unsigned id=0;id<8;id++)result_credits+=h.hosts[id]->native_result_cr;
  if(phase==ACCEPT&&h.awaiting_post_terminal_retirement()){
   if(h.acknowledged_terminal_tag()!=head_tag||h.acknowledged_terminal_generation()!=generation)
    throw std::runtime_error("accepted terminal identity differs from held cohort head37");
   terminal_edge=h.core_edges;phase=POST;}
  if(phase==POST&&!certified&&post_predicate(h)){certified=true;post_edge=h.core_edges;}
  if(phase==POST&&retire_sent&&!h.awaiting_post_terminal_retirement()){retired_edge=h.core_edges;phase=DONE;}
 }
 bool done()const{return phase==DONE;}
 std::string json()const{
  return std::string("{\"head_tag\":")+std::to_string(head_tag)+",\"generation\":"+std::to_string(generation)+
   ",\"token\":"+std::to_string(token)+",\"value_bits\":"+std::to_string(value)+",\"result_core_edge\":"+std::to_string(result_edge)+
   ",\"terminal_accepted_core_edge\":"+std::to_string(terminal_edge)+",\"post_certificate_core_edge\":"+std::to_string(post_edge)+
   ",\"retired_core_edge\":"+std::to_string(retired_edge)+",\"native_result_credits\":"+std::to_string(result_credits)+
   ",\"cq_completion\":"+(cq?"true":"false")+",\"irq_host0\":"+(irq?"true":"false")+"}";
 }
};
} // namespace qwen_native_host
