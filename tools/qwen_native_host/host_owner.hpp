#pragma once
// Functional integration candidate. Eight actual HOST models retain their
// state throughout a token. Board routing/RAM/startup are explicit fixtures.
#include "Vqkd_host_token_service.h"
#include "Vqkd_host_board_port_fixture.h"
#include "Vot_qwen_tp8_token_epoch_allocator.h"
#include "Vot_qwen_tp8_token_cohort.h"
#include "qkd_host_board_router_fixture.hpp"
#include <array>
#include <memory>
#include <limits>
#include <fstream>

namespace qwen_native_host {
// Native-owned boot/kst/drain arrays and masks use native rank.
// HOST and router arrays retain physical HOST ID=2*PKG+DIE.
struct Inputs {
 bool por_n=false,engine_admit_ready=false;
 std::array<uint8_t,8> boot{};
 std::array<uint16_t,8> kst{};
 uint8_t link_up=0;
 uint8_t kv_drained=0,vm_drained=0,collective_drained=0,host_drained=0;
 // A real POST_TERMINAL retirement certificate, qualified by the consumed
 // terminal identity. PRE_TERMINAL HOST drain alone cannot admit another token.
 bool post_terminal_retired=false;uint64_t post_terminal_tag=0;unsigned post_terminal_generation=0;
 bool result_valid=false,result_done=false,result_fault=false;
 uint64_t result_tag=0;unsigned result_generation=0,result_token=0,result_value=0,result_cycles=0,result_cause=0;
};
struct Admission {unsigned rank,generation,token,position;uint64_t tag,edge;std::array<uint32_t,5> program_metadata{};};
class HostOwner {
 struct Context:VerilatedContext {Context(){threads(1);}};
 Context ctx;
 std::array<std::unique_ptr<Vqkd_host_token_service>,8> owned_host;
 std::array<std::unique_ptr<Vqkd_host_board_port_fixture>,8> owned_board;
 Vot_qwen_tp8_token_epoch_allocator allocator;
 Vot_qwen_tp8_token_cohort cohort;
 enum Family {CORE,HOST,INGEST,PHY,BOARD};
 std::array<uint64_t,5> half={416667,500000,833334,521500,500000};
 // Common CORE first rising edge553667fs matches the actual core/PHY
 // composition's137000fs phase. Other rising families have distinct phases.
 std::array<uint64_t,5> next={553667,637002,1110336,892504,693006};
 std::array<bool,5> level{};
 bool primed=false,terminal_pending=false,terminal_rearm=false,post_terminal_pending=false;
 uint64_t acknowledged_tag=0;unsigned acknowledged_gen=0;
 uint64_t terminal_tag=0;unsigned terminal_gen=0;bool terminal_done=false,terminal_fault=false;
 Inputs inputs{};
 template<class T> static void zero(T& value){for(unsigned n=0;n<value.size();++n)value[n]=0;}
 static uint64_t extract(const auto& packed,unsigned offset,unsigned width){
  uint64_t value=0;for(unsigned b=0;b<width;++b)value|=uint64_t((packed[(offset+b)/32]>>((offset+b)%32))&1)<<b;return value;
 }
 void clocks(Family family,bool v){
  level[family]=v;
  for(unsigned r=0;r<8;++r){auto&h=*hosts[r];auto&b=*boards[r];
   if(family==CORE){
    h.ck_host=h.ck_csr=h.ck_rst=h.ck_ctl=h.ck_prompt=h.ck_rx=h.ck_tx=h.ck_axi=h.ck_ctrl=h.ck_hc=v;
    h.ck_phy_rx_r=h.ck_phy_tx_w=v;
    h.ck_qm_queue=h.ck_qm_ing_w=h.ck_qm_done_r=h.ck_qm_core=v;
    h.ck_map=h.ck_sum=h.ck_order=h.ck_fence_core=h.ck_guard=h.ck_native=v;
    for(unsigned n=0;n<4;++n)h.ck_station[n]=h.ck_static[n]=v?0xffffffffu:0;
   }
   if(family==HOST)h.ck_qm_host=h.ck_qm_ing_r=h.ck_qm_credit=h.ck_qm_done_w=h.ck_fence_host=v;
   if(family==INGEST){h.ck_qm_ingest=h.ck_qm_out=v;h.ck_qm_bank=v?3:0;}
   if(family==PHY){h.ck_phy=v?255:0;h.ck_pad=h.ck_phy_rx_w=h.ck_phy_tx_r=v;b.ck_phy=v?255:0;b.ck_pad=v;}
   if(family==BOARD)b.ck_rx_core=b.ck_tx_core=v;
  }
  if(family==CORE)allocator.clk=cohort.clk=v;
 }
 void evaluate(){for(auto*h:hosts)h->eval();for(auto*b:boards)b->eval();allocator.eval();cohort.eval();}
 void connect(){
  allocator.por_n=cohort.por_n=inputs.por_n;
  allocator.warm_ready=cohort.warm_ready=hosts[0]->host_rst_n&&hosts[0]->service_ready&&hosts[0]->sys_ready&&
      !hosts[0]->package_abort&&!hosts[0]->service_abort&&!post_terminal_pending;
  allocator.request_valid=hosts[0]->token_request_valid;allocator.request_token=hosts[0]->token_request_token;
  allocator.request_position=hosts[0]->token_request_position;allocator.request_generation=hosts[0]->token_request_generation;
  allocator.grant_ready=hosts[0]->token_grant_ready;
  cohort.begin_valid=allocator.grant_valid&&allocator.grant_ready;
  cohort.begin_tag=allocator.grant_tag;cohort.begin_generation=allocator.grant_generation;
  cohort.request_valid=0;zero(cohort.request_tag);cohort.request_generation=0;
  bool ready=inputs.engine_admit_ready;
  for(unsigned id=0;id<8;++id){unsigned r=native_rank_for_host(id);auto&h=*hosts[id];auto&b=*boards[id];
   h.por_n=inputs.por_n;h.phy_up=b.phy_up=1;h.link_up=inputs.link_up;
   h.local_boot=inputs.boot[r];h.local_kst=inputs.kst[r];b.rst_n=h.host_rst_n;
   h.token_allocator_fault=allocator.identity_fault||cohort.identity_fault;
   h.token_request_ready=id==0&&allocator.request_ready;
   h.token_grant_valid=id==0&&allocator.grant_valid;h.token_grant_tag=allocator.grant_tag;
   h.token_grant_epoch=allocator.grant_epoch;h.token_grant_token=allocator.grant_token;
   h.token_grant_position=allocator.grant_position;h.token_grant_generation=allocator.grant_generation;
   h.allocated_valid=allocator.allocated_valid;h.allocated_delivered=allocator.allocated_delivered;
   h.allocated_epoch=allocator.grant_epoch;h.allocated_token=allocator.grant_token;
   h.allocated_position=allocator.grant_position;h.allocated_generation=allocator.grant_generation;
   h.native_request_cr=(cohort.request_credit>>r)&1;
   if(h.native_request_v){cohort.request_valid|=1u<<r;cohort.request_generation|=h.native_request_gen<<(2*r);
    for(unsigned bit=0;bit<59;++bit){unsigned n=59*r+bit;cohort.request_tag[n/32]|=uint32_t((h.native_request_tag>>bit)&1)<<(n%32);}}
   ready&=h.sys_ready&&h.die_rst_n&&h.host_rst_n&&h.service_ready&&!h.package_abort&&!h.service_abort;
   h.native_kv_drained=(inputs.kv_drained>>r)&1;h.native_vm_drained=(inputs.vm_drained>>r)&1;
   h.native_collective_drained=(inputs.collective_drained>>r)&1;h.native_host_drained=(inputs.host_drained>>r)&1;
   h.abort_drained=h.native_kv_drained|(h.native_vm_drained<<1)|(h.native_collective_drained<<2)|(h.native_host_drained<<3);
   h.native_result_v=inputs.result_valid;h.native_result_tag=inputs.result_tag;h.native_result_gen=inputs.result_generation;
   h.native_result_done=inputs.result_done;h.native_result_fault=inputs.result_fault;h.native_result_cause=inputs.result_cause;
   h.native_result_token=inputs.result_token;h.native_result_value=inputs.result_value;h.native_result_cycles=inputs.result_cycles;
   // Never clear an unrelated retained cancellation with a global ACK.
   h.token_cancel_accepted=allocator.terminal_accepted&&h.cancel_valid&&
      h.cancel_tag==acknowledged_tag&&h.cancel_generation==acknowledged_gen;
   h.marker_cr=h.marker_v; // zero-row BOOT marker receiver in this fixture
  }
  cohort.dispatch_ready=ready;
  allocator.terminal_valid=terminal_pending;
  // A genuine watchdog can cancel an allocated grant before delivery. The
  // allocator owns that identity, but the cohort has not reserved it yet.
  cohort.terminal_valid=terminal_pending&&cohort.active;
  allocator.terminal_tag=cohort.terminal_tag=terminal_tag;
  allocator.terminal_generation=cohort.terminal_generation=terminal_gen;
  allocator.terminal_done=cohort.terminal_done=terminal_done;
  allocator.terminal_fault=cohort.terminal_fault=terminal_fault;
  allocator.terminal_kv_drained=cohort.kv_drained=inputs.kv_drained==255;
  allocator.terminal_vm_drained=cohort.vm_drained=inputs.vm_drained==255;
  allocator.terminal_collective_drained=cohort.collective_drained=inputs.collective_drained==255;
  allocator.terminal_host_drained=cohort.host_drained=inputs.host_drained==255;
 }
 auto face()const{
  std::vector<uint64_t> v={allocator.request_ready,allocator.grant_valid,allocator.grant_tag,
    allocator.allocated_valid,allocator.allocated_delivered,allocator.identity_fault,
    cohort.begin_ready,cohort.dispatch_valid,cohort.dispatched,cohort.request_credit,
    cohort.accepted_ranks,cohort.identity_fault};
  for(unsigned r=0;r<8;++r){auto&h=*hosts[r];auto&b=*boards[r];
   v.insert(v.end(),{h.host_rst_n,h.sys_ready,h.die_rst_n,h.service_ready,h.service_abort,h.package_abort,
    h.token_request_valid,h.token_request_token,h.token_request_position,h.token_request_generation,h.token_grant_ready,
    h.native_request_v,h.native_request_tag,h.native_request_gen,h.native_request_token,h.native_request_pos,
    h.cancel_valid,h.cancel_tag,h.cancel_generation,uint64_t(b.rst_n)});}
  return v;
 }
 void settle(){
  for(unsigned n=0;n<16;++n){auto before=face();connect();evaluate();if(before==face())return;}
  throw std::runtime_error("actual HOST/allocator/cohort interfaces did not reach a fixed point");
 }
 void other_event(Family family){
  bool rising=!level[family];settle();
  if(rising&&family==PHY)router.step_phy(hosts,boards);
  if(rising&&family==BOARD){router.sample_core(boards);router.drive_core(boards);}
  clocks(family,rising);evaluate();settle();next[family]+=half[family];
 }
 void advance_other(uint64_t until){
  while(true){unsigned selected=1;for(unsigned n=2;n<5;++n)if(next[n]<next[selected])selected=n;
   if(next[selected]>=until)break;time_fs=next[selected];ctx.time(time_fs/1000);other_event(Family(selected));}
  time_fs=until;ctx.time(time_fs/1000);
 }
public:
 static unsigned native_rank_for_host(unsigned id){if(id>=8)throw std::out_of_range("HOST ID");return 4*(id%2)+id/2;}
 static unsigned host_id_for_rank(unsigned rank){if(rank>=8)throw std::out_of_range("native rank");return 2*(rank%4)+rank/4;}
 Vqkd_host_token_service* host_for_rank(unsigned rank)const{return hosts[host_id_for_rank(rank)];}
 std::array<Vqkd_host_token_service*,8> hosts{};
 std::array<Vqkd_host_board_port_fixture*,8> boards{};
 qkd_host_fixture::Router router;
 uint64_t time_fs=0,core_edges=0,actual_allocations=0,actual_grants=0;
 std::vector<Admission> admissions;
 HostOwner():allocator(&ctx,"sole_epoch"),cohort(&ctx,"actual_cohort"){
  for(unsigned r=0;r<8;++r){owned_host[r]=std::make_unique<Vqkd_host_token_service>(&ctx,("host"+std::to_string(r)).c_str());
   owned_board[r]=std::make_unique<Vqkd_host_board_port_fixture>(&ctx,("board"+std::to_string(r)).c_str());hosts[r]=owned_host[r].get();boards[r]=owned_board[r].get();
   auto&h=*hosts[r];h.die_id=r;zero(h.pr);zero(h.local_tk);zero(h.land_es);zero(h.ctrl_er);zero(h.completion_v);zero(h.completion_we);
   h.transport_fault=h.physical_fault=h.crom_fault=0;h.native_collective_busy=h.native_kv_flush=0;
   h.token_wrap_fence_valid=h.token_wrap_drained=h.token_wrap_link_reset_seen=h.token_wrap_retraining_done=0;
  }
  allocator.wrap_fence_valid=allocator.wrap_links_drained=allocator.wrap_link_reset_seen=allocator.wrap_retraining_done=0;
  cohort.recovery_valid=cohort.links_drained=cohort.link_reset_seen=cohort.retraining_done=0;
  for(unsigned f=0;f<5;++f)clocks(Family(f),false);settle();
 }
 void low(const Inputs& in){
  inputs=in;
  if(!in.por_n){terminal_pending=false;terminal_rearm=false;post_terminal_pending=false;}
  if(in.post_terminal_retired){
   if(!post_terminal_pending||in.post_terminal_tag!=acknowledged_tag||
      in.post_terminal_generation!=acknowledged_gen)throw std::runtime_error("stale POST_TERMINAL retirement certificate");
   post_terminal_pending=false;
  }
  bool cancels_clear=true;for(auto*h:hosts)cancels_clear&=!h->cancel_valid;
  if(terminal_rearm&&!in.result_valid&&cancels_clear&&!allocator.terminal_accepted)terminal_rearm=false;
  if(in.result_valid){if(terminal_pending||terminal_rearm)throw std::runtime_error("duplicate native terminal snapshot");
   terminal_pending=true;terminal_tag=in.result_tag;terminal_gen=in.result_generation;terminal_done=in.result_done;terminal_fault=in.result_fault;}
  // Capture real held cancellation, without inventing completion or drains.
  if(!terminal_pending&&!terminal_rearm)for(auto*h:hosts)if(h->cancel_valid){terminal_pending=true;terminal_tag=h->cancel_tag;
   terminal_gen=h->cancel_generation;terminal_done=h->cancel_done;terminal_fault=h->cancel_fault;break;}
  advance_other(next[CORE]);settle();primed=true;
 }
 void rise(){
  if(!primed)throw std::runtime_error("HOST rise without frozen low phase");
  if(allocator.request_valid&&allocator.request_ready)++actual_allocations;
  if(allocator.grant_valid&&allocator.grant_ready)++actual_grants;
  unsigned prior_accepted=cohort.accepted_ranks;
  std::array<Admission,8> offered{};
  for(unsigned r=0;r<8;++r){auto*h=host_for_rank(r);offered[r]={r,h->native_request_gen,
    h->native_request_token,h->native_request_pos,h->native_request_tag,core_edges};
    for(unsigned w=0;w<5;++w)offered[r].program_metadata[w]=h->native_pr[w];}
  bool cohort_terminal_required=cohort.terminal_valid;
  clocks(CORE,true);evaluate(); // all pin inputs remain frozen across every rise
  unsigned accepted_now=cohort.accepted_ranks&~prior_accepted;
  if(accepted_now!=unsigned(cohort.request_credit))throw std::runtime_error("actual cohort acceptance/credit witness disagreement");
  for(unsigned r=0;r<8;++r)if((accepted_now>>r)&1)admissions.push_back(offered[r]);
  ++core_edges;next[CORE]+=half[CORE];settle();
  if(allocator.terminal_accepted){if(cohort_terminal_required&&!cohort.terminal_accepted)throw std::runtime_error("allocator/cohort terminal ownership disagreement");
   acknowledged_tag=terminal_tag;acknowledged_gen=terminal_gen;terminal_pending=false;terminal_rearm=true;post_terminal_pending=true;}
  primed=false;
 }
 void fall(){advance_other(next[CORE]);clocks(CORE,false);evaluate();next[CORE]+=half[CORE];settle();}
 bool awaiting_post_terminal_retirement()const{return post_terminal_pending;}
 uint64_t acknowledged_terminal_tag()const{return acknowledged_tag;}
 unsigned acknowledged_terminal_generation()const{return acknowledged_gen;}
 bool dispatch()const{return cohort.dispatched;}
 bool fault()const{return allocator.identity_fault||cohort.identity_fault;}
 uint64_t tag()const{return cohort.cohort_tag;}
 unsigned epoch()const{return cohort.cohort_tag>>43;}
 unsigned token()const{return (cohort.cohort_tag>>19)&0x3ffff;}
 unsigned position()const{return (cohort.cohort_tag>>6)&8191;}
 unsigned generation()const{return cohort.cohort_generation;}
 unsigned accepted_ranks()const{return cohort.accepted_ranks;}
};
} // namespace qwen_native_host
