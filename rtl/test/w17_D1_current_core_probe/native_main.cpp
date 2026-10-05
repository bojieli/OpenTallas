// SIMULATION ONLY: bounded event-loop diagnostic; never an original token restart.
#include "Vtb_D1_current_core.h"
#include "verilated.h"
#include "svdpi.h"
#include <cstdio>
#include <memory>
static svScope g_diescope[4] = {nullptr,nullptr,nullptr,nullptr};
extern "C" void v41rt_die_register(int rank) { g_diescope[rank & 3] = svGetScope(); }
int main(int argc,char**argv) {
  std::setvbuf(stdout,nullptr,_IONBF,0);
  auto ctx=std::make_unique<VerilatedContext>();
  ctx->randReset(0);ctx->commandArgs(argc,argv);ctx->threads(1);
  auto top=std::make_unique<Vtb_D1_current_core>(ctx.get());
  if(ctx->timeprecision()!=-12) {
    std::fprintf(stderr,"D1_UNEXPECTED_TIME_PRECISION_NO_CLOCK_CREDIT\n");return 4;
  }
  unsigned long long evals=0;
  while(!ctx->gotFinish()) {
    top->eval();++evals;
    if(evals<=16 || evals%64==0)
      std::fprintf(stderr,"D1_HEARTBEAT evals=%llu time_ps=%llu cycles=%u\n",evals,
        (unsigned long long)ctx->time(),unsigned(top->observed_cycle));
    if(ctx->gotFinish())break;
    if(!top->eventsPending()) {
      std::fprintf(stderr,"D1_NO_PENDING_EVENTS_NO_SERVICE_CREDIT\n");return 3;
    }
    ctx->time(top->nextTimeSlot());
  }
  top->final();
  std::fprintf(stderr,"D1_TERMINAL_PREFIX_ONLY evals=%llu time_ps=%llu cycles=%u\n",evals,
    (unsigned long long)ctx->time(),unsigned(top->observed_cycle));return 0;
}
