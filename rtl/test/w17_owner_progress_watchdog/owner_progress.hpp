#pragma once
#include <cstdint>
#include <stdexcept>
namespace owner_progress {
struct Snapshot {
 uint64_t su_retired=0,accepted=0,returned=0;
 uint32_t pc=0,rows=0,desc=0,win=0,fault=0;
 bool su_idle=true,kv_ok=false,req_v=false,req_ready=false;
 bool backend_req_v=false,backend_req_ready=false,backend_rsp_v=false,backend_rsp_ready=false;
};
enum Reason {NONE=0,FAULT=1,HBM_REQUEST_REFUSAL=2,HBM_RETURN_DELIVERY=3,SU_RETIREMENT=4,
 WINDOW_REQUEST_REFUSAL=5,OVERALL_CAP=6,WINDOW_MEMORY_SERVICE=7,DESCRIPTOR_ADMISSION=8,OTHER_PC_STALL=9};
inline const char* name(Reason r) {
 switch(r){case NONE:return "NONE";case FAULT:return "SOURCE_FAULT";
 case HBM_REQUEST_REFUSAL:return "KARB_TO_HBM_REQUEST_REFUSAL";
 case HBM_RETURN_DELIVERY:return "HBM_TO_KARB_RETURN_DELIVERY";
 case SU_RETIREMENT:return "SU_RETIREMENT";
 case WINDOW_REQUEST_REFUSAL:return "WINDOW_TO_OWNER_REQUEST_REFUSAL";
 case OVERALL_CAP:return "OVERALL_CYCLE_CAP";
 case WINDOW_MEMORY_SERVICE:return "WINDOW_WAITING_MEMORY_SERVICE";
 case DESCRIPTOR_ADMISSION:return "DESCRIPTOR_ADMISSION";case OTHER_PC_STALL:return "OTHER_PC_STALL";}
 return "INVALID";
}
class Watchdog {
 Snapshot previous{};bool initialized=false;uint64_t last_su=0,last_window=0,last_pc=0;
 uint64_t su_gap,window_gap,overall;
public:
 Watchdog(uint64_t s,uint64_t w,uint64_t cap):su_gap(s),window_gap(w),overall(cap){
  if(!s||!w||!cap)throw std::invalid_argument("finite positive watchdog limits required");
 }
 Reason sample(uint64_t cycle,const Snapshot& now){
  if(now.fault)return FAULT;
  if(cycle>=overall)return OVERALL_CAP;
  if(!initialized){initialized=true;previous=now;last_su=last_window=last_pc=cycle;return NONE;}
  if(now.su_retired<previous.su_retired||now.accepted<previous.accepted||now.returned<previous.returned)
   throw std::runtime_error("owner counters regressed without reset");
  if(now.su_retired!=previous.su_retired||now.su_idle!=previous.su_idle)last_su=cycle;
  // An unrelated SU or another rank's progress never refreshes this timer.
  if(now.accepted!=previous.accepted||now.returned!=previous.returned||now.rows!=previous.rows||
     now.desc!=previous.desc||now.win!=previous.win||now.kv_ok!=previous.kv_ok)last_window=cycle;
  if(now.pc!=previous.pc)last_pc=cycle;
  previous=now;
  if(now.pc!=24){last_su=last_window=cycle;return cycle-last_pc>window_gap ? OTHER_PC_STALL : NONE;}
  if(!now.su_idle && cycle-last_su>su_gap)return SU_RETIREMENT;
  if((now.desc==1||now.win!=0) && cycle-last_window>window_gap){
   if(now.backend_req_v&&!now.backend_req_ready)return HBM_REQUEST_REFUSAL;
   if(now.backend_rsp_v&&!now.backend_rsp_ready)return HBM_RETURN_DELIVERY;
   if(now.req_v&&!now.req_ready)return WINDOW_REQUEST_REFUSAL;
   return WINDOW_MEMORY_SERVICE;
  }
  if(now.su_idle && !now.kv_ok && cycle-last_window>window_gap)return DESCRIPTOR_ADMISSION;
  return NONE;
 }
};
}
