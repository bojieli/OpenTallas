// Verilator driver for rtl/test/tb_chip_v41x_die_smoke.sv: toggles the clock until $finish.
#include "Vtb_chip_v41x_die_smoke.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_chip_v41x_die_smoke* top = new Vtb_chip_v41x_die_smoke;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
