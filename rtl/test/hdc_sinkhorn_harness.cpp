// Verilator driver for rtl/test/tb_hdc_sinkhorn.sv: toggles the clock until $finish.
// Build with -CFLAGS -DSK_ARITH for the tb_hdc_sk_arith top.
#ifdef SK_ARITH
#include "Vtb_hdc_sk_arith.h"
typedef Vtb_hdc_sk_arith Top;
#else
#include "Vtb_hdc_sinkhorn.h"
typedef Vtb_hdc_sinkhorn Top;
#endif
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Top* top = new Top;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
