#include <verilated.h>
#include "Vtb_qwen_embedding_stage.h"
// Event driver only. Stimuli and bit-exact checks remain in the SV bench;
// every arithmetic unit is RTL, including all hierarchical child models.
int main(int argc, char** argv) {
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vtb_qwen_embedding_stage top{&context};
    while (!context.gotFinish()) {
        top.eval();
        if (!top.eventsPending()) break;
        context.time(top.nextTimeSlot());
    }
    top.final();
    return context.gotFinish() ? 0 : 2;
}
