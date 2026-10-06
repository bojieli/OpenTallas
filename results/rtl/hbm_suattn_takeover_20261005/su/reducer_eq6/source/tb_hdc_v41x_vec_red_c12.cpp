// drives tb_hdc_v41x_vec_red_c12's clock until $finish; $fatal (a mismatch) exits nonzero
#include "Vtb_hdc_v41x_vec_red_c12.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_v41x_vec_red_c12 t;
    t.clk = 0;
    while (!Verilated::gotFinish()) { t.clk = 0; t.eval(); t.clk = 1; t.eval(); }
    t.final();
    return 0;
}
