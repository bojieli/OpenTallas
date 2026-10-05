#include "owner_progress.hpp"
#include <cstdio>
static owner_progress::Watchdog* monitor=nullptr;
extern "C" void owner_progress_init(int overall){
 if(monitor)throw std::runtime_error("monitor already initialized");
 monitor=new owner_progress::Watchdog(1024,1024,uint64_t(overall));
}
extern "C" int owner_progress_sample(long long cycle,long long su,long long req,long long rsp,
 int rows,int desc,int win,int su_idle,int kv_ok,int req_v,int req_ready,
 int backend_req_v,int backend_req_ready,int backend_rsp_v,int backend_rsp_ready,int fault){
 owner_progress::Snapshot s;s.pc=24;s.su_retired=su;s.accepted=req;s.returned=rsp;
 s.rows=rows;s.desc=desc;s.win=win;s.su_idle=su_idle;s.kv_ok=kv_ok;s.req_v=req_v;s.req_ready=req_ready;
 s.backend_req_v=backend_req_v;s.backend_req_ready=backend_req_ready;
 s.backend_rsp_v=backend_rsp_v;s.backend_rsp_ready=backend_rsp_ready;s.fault=fault;
 if(!monitor)throw std::runtime_error("monitor uninitialized");
 auto result=monitor->sample(cycle,s);
 if(result!=owner_progress::NONE)std::printf("OWNER_WATCHDOG reason=%s cycle=%lld SUret=%lld req=%lld rsp=%lld rows=%d desc=%d win=%d fault=%d\n",owner_progress::name(result),cycle,su,req,rsp,rows,desc,win,fault);
 return int(result);
}
