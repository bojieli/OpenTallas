// Verilator driver for rtl/test/tb_hdc_kv_stream.sv: toggles the clock until $finish.
#include "Vtb_hdc_kv_stream.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_kv_stream* top = new Vtb_hdc_kv_stream;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
