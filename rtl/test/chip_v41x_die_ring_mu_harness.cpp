// Verilator driver for rtl/test/tb_chip_v41x_die_ring_mu.sv: toggles the clock until $finish.
#include "Vtb_chip_v41x_die_ring_mu.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_chip_v41x_die_ring_mu* top = new Vtb_chip_v41x_die_ring_mu;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
