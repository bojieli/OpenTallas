// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: main() simulation loop, created with --main

#include "verilated.h"
#include "Vtb_D1.h"

// D1_OBSERVE_BEGIN
#include <cstdio>
#include <cstdint>
#include <ctime>
#include <unistd.h>
static uint64_t d1_evals = 0;
static void d1_mark(const char* phase, uint64_t simtime=0) {
    struct timespec t{}; clock_gettime(CLOCK_MONOTONIC, &t);
    char b[256]; int n=snprintf(b,sizeof(b),"D1_HOST phase=%s mono_s=%lld mono_ns=%ld simtime=%llu evals=%llu\n",
        phase,(long long)t.tv_sec,t.tv_nsec,(unsigned long long)simtime,(unsigned long long)d1_evals);
    if(n>0 && n<(int)sizeof(b)) { (void)!write(STDERR_FILENO,b,(size_t)n); }
}
// D1_OBSERVE_END
//======================

int main(int argc, char** argv, char**) {
    // Setup context, defaults, and parse command line
// D1_OBSERVE_BEGIN
    setvbuf(stdout, nullptr, _IONBF, 0);
    d1_mark("CONTEXT_ENTER");
// D1_OBSERVE_END
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
// D1_OBSERVE_BEGIN
    d1_mark("CONTEXT_RETURN",contextp->time());
// D1_OBSERVE_END
    contextp->threads(1);
    contextp->commandArgs(argc, argv);

    // Construct the Verilated model, from Vtop.h generated from Verilating
// D1_OBSERVE_BEGIN
    d1_mark("CONSTRUCTOR_ENTER",contextp->time());
// D1_OBSERVE_END
    const std::unique_ptr<Vtb_D1> topp{new Vtb_D1{contextp.get(), ""}};
// D1_OBSERVE_BEGIN
    d1_mark("CONSTRUCTOR_RETURN",contextp->time());
// D1_OBSERVE_END

    // Simulate until $finish
    while (VL_LIKELY(!contextp->gotFinish())) {
        // Evaluate model
// D1_OBSERVE_BEGIN
        if(d1_evals<16) d1_mark("EVAL_ENTER",contextp->time());
// D1_OBSERVE_END
        topp->eval();
// D1_OBSERVE_BEGIN
        ++d1_evals;
        if(d1_evals<=16 || d1_evals%256==0) d1_mark("EVAL_RETURN",contextp->time());
// D1_OBSERVE_END
        // Advance time
        if (!topp->eventsPending()) break;
        contextp->time(topp->nextTimeSlot());
    }

    if (VL_LIKELY(!contextp->gotFinish())) {
        VL_DEBUG_IF(VL_PRINTF("+ Exiting without $finish; no events left\n"););
    }

    // Execute 'final' processes
// D1_OBSERVE_BEGIN
    d1_mark("FINAL_ENTER",contextp->time());
// D1_OBSERVE_END
    topp->final();
// D1_OBSERVE_BEGIN
    d1_mark("FINAL_RETURN",contextp->time());
// D1_OBSERVE_END

    // Print statistical summary report
    contextp->statsPrintSummary();

    return 0;
}
