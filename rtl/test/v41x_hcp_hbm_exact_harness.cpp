#include "Vtb_hdc_v41x_hcp_hbm_exact.h"
#include "verilated.h"

double sc_time_stamp() { return 0.0; }

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_v41x_hcp_hbm_exact top;
    while (!Verilated::gotFinish()) {
        top.clk = 0;
        top.eval();
        top.clk = 1;
        top.eval();
    }
    top.final();
    return 0;
}
