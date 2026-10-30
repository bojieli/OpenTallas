// Passive native token probe gate for a START-joined KV vehicle.
// Observe from the actual SETUP event through finish, independent of absolute
// boot cycle. Require admission and token calendar activity as well as no faults.
// The standard kv_verdict layer classifier remains a separate numeric gate.
#include "verilated.h"
#include "Vtb_kvslice.h"
#include "Vtb_kvslice___024root.h"
#include <cstdio>
#include <type_traits>
#ifndef DUTP
#define DUTP dut__DOT__u_bound__DOT__
#endif
#define CAT2(a, b) a##b
#define CAT(a, b) CAT2(a, b)
#define R(x) topp->rootp->CAT(tb_kvslice__DOT__, x)
#define F(x) R(u_far__DOT__u_c__DOT__u_core__DOT__##x)
#define K(x) topp->rootp->CAT(CAT(tb_kvslice__DOT__, DUTP), sys_c__DOT__u_d2d_kv__DOT__u_core__DOT__##x)
template <class T> static unsigned long long g(const T& x) {
    if constexpr (std::is_integral_v<T>) return (unsigned long long)x;
    else return (unsigned long long)x.at(0) | ((unsigned long long)x.at(1) << 32);
}
int main(int argc, char** argv, char**) {
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->threads(1);
    contextp->commandArgs(argc, argv);
    const std::unique_ptr<Vtb_kvslice> topp{new Vtb_kvslice{contextp.get(), ""}};
    unsigned long long old = ~0ull, kab = 0, fab = 0, kfc = 0, ffc = 0; unsigned lines = 0, last = 0; bool setup_seen = false;
    while (VL_LIKELY(!contextp->gotFinish())) {
        topp->eval();
        const unsigned cyc = R(cyc_core);
        setup_seen |= static_cast<int>(R(t_setup)) >= 0;
        if (setup_seen) {
            const unsigned long long ka = g(K(ab)), kf = g(K(fc)), fa = g(F(ab)), ff = g(F(fc));
            kab |= ka; fab |= fa; kfc |= kf; ffc |= ff; last = cyc;
            const unsigned long long st = ka | kf << 1 | fa << 9 | ff << 10;
            if (st != old && lines < 200) {
                std::printf("GATE cyc %u farcyc %llu kv ab %llu fc %02llx | far ab %llu fc %02llx\n", cyc, g(R(u_far__DOT__cyc)), ka, kf, fa, ff);
                std::fflush(stdout); ++lines; old = st;
            }
        }
        if (!topp->eventsPending()) break;
        contextp->time(topp->nextTimeSlot());
    }
    const auto admissions = g(R(u_far__DOT__n_adm));
    const auto tokens = g(R(u_far__DOT__n_tok));
    const bool pass = setup_seen && admissions && tokens && !kab && !kfc && !fab && !ffc;
    std::printf("GATE_END last_cyc %u setup %d admissions %llu tokens %llu kv_ab %llu kv_fc %02llx far_ab %llu far_fc %02llx verdict %s\n",
                last, setup_seen, admissions, tokens, kab, kfc, fab, ffc, pass ? "PASS" : "FAIL");
    std::fflush(stdout);
    topp->final();
    contextp->statsPrintSummary();
    return 0;
}
