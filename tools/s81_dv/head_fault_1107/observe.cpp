#include "Vhead_guard_tb.h"
#include "Vhead_guard_tb___024root.h"
#include "verilated.h"
#include <cstdio>
#include <memory>
#define P(n) (top.rootp->head_guard_tb__DOT__probe_sp0___05Fx_i__DOT__##n)
#define R(n) P(u_ring__DOT__##n)
int main(int argc, char** argv) {
    auto ctx=std::make_unique<VerilatedContext>(); ctx->commandArgs(argc,argv);
    Vhead_guard_tb top{ctx.get()};
    bool writer=false, reader=false, base=false, seen=false, fault=false;
    while(!ctx->gotFinish()) {
        top.eval();
        if(R(rp)==38) base=true;
        if(!writer && R(tc)==1) {
            writer=true; std::printf("FIRST_WRITER_COUNT0 fs%llu tc%u rp%u\n",
                (unsigned long long)ctx->time(),unsigned(R(tc)),unsigned(R(rp)));
        }
        if(!reader && base && R(rp)==39) {
            reader=true; std::printf("FIRST_READER_COUNT0 fs%llu tc%u rp%u\n",
                (unsigned long long)ctx->time(),unsigned(R(tc)),unsigned(R(rp)));
        }
        if(!seen && P(seen)) {
            seen=true; std::printf("FIRST_SEEN fs%llu tc%u rp%u rv%u lap%u glo%u ghi%u\n",
                (unsigned long long)ctx->time(),unsigned(R(tc)),unsigned(R(rp)),
                unsigned(R(r_v_q)),unsigned(R(r_lap_q)),unsigned(R(glo3)),unsigned(R(ghi3)));
        }
        if(!fault && P(fault_state)) {
            fault=true; std::printf("FIRST_FAULT_STATE fs%llu tc%u rp%u seen%u armed%u tmo%u rv%u lap%u glo%u ghi%u\n",
                (unsigned long long)ctx->time(),unsigned(R(tc)),unsigned(R(rp)),
                unsigned(P(seen)),unsigned(P(armed)),unsigned(P(tmo_cnt)),
                unsigned(R(r_v_q)),unsigned(R(r_lap_q)),unsigned(R(glo3)),unsigned(R(ghi3)));
        }
        if(!top.eventsPending()) break;
        ctx->time(top.nextTimeSlot());
    }
    top.final();
    return 0;
}
