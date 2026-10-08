#include "Vtb.h"
#include "verilated.h"
#if VM_TRACE_FST
#include "verilated_fst_c.h"
#endif
#include <memory>
#include <string>
int main(int argc, char** argv) {
    auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
#if VM_TRACE_FST
    context->traceEverOn(true);
#endif
    auto top = std::make_unique<Vtb>(context.get());
#if VM_TRACE_FST
    std::unique_ptr<VerilatedFstC> trace;
    for (int i=1;i<argc;++i) if (std::string(argv[i]).rfind("+ACTIVITY=",0)==0) {
        trace=std::make_unique<VerilatedFstC>();
        top->trace(trace.get(),99);trace->open(argv[i]+10);
    }
#endif
    top->clk=0;
    while (!context->gotFinish()) {
        top->eval();
#if VM_TRACE_FST
        if(trace)trace->dump(context->time());
#endif
        // 1 ps simulation precision: alternating 417/416 ps half periods.
        context->timeInc(top->clk?416:417);
        top->clk=!top->clk;
    }
    top->final();
#if VM_TRACE_FST
    if(trace)trace->close();
#endif
    return 0;
}
