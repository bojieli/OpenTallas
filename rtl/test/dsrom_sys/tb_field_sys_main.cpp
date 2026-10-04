// Clock driver of rtl/test/dsrom_sys/tb_field_sys.sv (Verilator): one eval per clock edge until $finish.
// Runtime: +verilator+rand+reset+<0|2> +verilator+seed+<n> select the initial values of unassigned state.
#include <memory>
#include "Vtb.h"
#include "verilated.h"
int main(int argc, char** argv) {
    auto ctx = std::make_unique<VerilatedContext>();
    ctx->commandArgs(argc, argv);
    auto top = std::make_unique<Vtb>(ctx.get(), "tb");
    top->clk = 0;
    top->eval();
    while (!ctx->gotFinish()) {
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
    }
    top->final();
    return 0;
}
