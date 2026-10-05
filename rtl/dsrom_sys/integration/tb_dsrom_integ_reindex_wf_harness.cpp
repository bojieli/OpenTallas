// Verilator driver for rtl/dsrom_sys/integration/tb_dsrom_integ_reindex_wf.sv: toggles the clock until $finish.
#include "Vtb_dsrom_integ_reindex_wf.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_integ_reindex_wf* top = new Vtb_dsrom_integ_reindex_wf;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
